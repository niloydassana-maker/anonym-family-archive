#!/usr/bin/env python3
"""Public buyer lead research with four-coordinate evidence. Python 3.10+.
Returns up to --limit review candidates, never a guaranteed quota. No sends.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, quote
from hunt_leads import Web, Page, contacts, BUYER, SELLER, CLOSED, TECH, EXCLUDED

FIELDS = ('email', 'linkedin', 'phone', 'whatsapp_number')
FORUMS = ('https://community.n8n.io', 'https://community.make.com')
QUERIES = ['n8n', 'AI agent', 'Python automation', 'API integration', 'CRM automation', 'workflow automation']
TECH_RE = re.compile(TECH.pattern + r'|\bpython\b|\bpostgresql\b|\bRAG\b|\bLLM\b|\bCRM\b', re.I)
MONEY = re.compile(r'(?:USD|SGD|GBP|EUR|INR|\$|₹|£|€)\s*\d[\d,]*(?:\.\d+)?\s*[kK]?(?:\s*[-–]\s*\d[\d,]*(?:\.\d+)?\s*[kK]?)?', re.I)

def now(): return datetime.now(timezone.utc)
def mapping(x): return x if isinstance(x, dict) else {}
def date(value):
    try:
        if isinstance(value, (int, float)): return datetime.fromtimestamp(value, timezone.utc)
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except (ValueError, TypeError, OverflowError, OSError): return None

class UnquotedHTML(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.output, self.blocked = [], []
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        if tag in ('blockquote', 'aside'):
            self.blocked.append(tag)
        elif not self.blocked:
            self.output.append(self.get_starttag_text())
    def handle_startendtag(self, tag, attrs):
        if not self.blocked: self.output.append(self.get_starttag_text())
    def handle_endtag(self, tag):
        if tag in ('blockquote', 'aside') and self.blocked and self.blocked[-1] == tag:
            self.blocked.pop()
        elif not self.blocked: self.output.append('</'+tag+'>')
    def handle_data(self, data):
        if not self.blocked: self.output.append(html.escape(data))

def unquoted(source):
    return ''.join(UnquotedHTML(source or '').output)

def clean_contacts(source):
    """Compatible helper, backed by the shared four-coordinate parser."""
    _, items = contacts(source or '')
    result = {'emails': [], 'linkedin': [], 'phone': [], 'whatsapp_number': [], 'whatsapp_links': []}
    for item in items:
        field = {'email': 'emails', 'whatsapp': 'whatsapp_links'}.get(item['kind'], item['kind'])
        if item['value'] not in result[field]: result[field].append(item['value'])
    for field in FIELDS:
        result[field+'_status'] = 'published_candidate' if result['emails' if field=='email' else field] else 'not_found_in_scanned_content'
    return result

def merge_contacts(lead, source, url, suppressed):
    _, items = contacts(unquoted(source))
    for item in items:
        if item['value'].casefold() in suppressed:
            lead['suppressed_values'] += 1
            continue
        field = 'whatsapp_links' if item['kind']=='whatsapp' else item['kind']
        if item['value'] not in lead[field]: lead[field].append(item['value'])
        proof = {**item, 'source_url': url, 'ownership': 'author_published_candidate_review_required'}
        if proof not in lead['contact_evidence']: lead['contact_evidence'].append(proof)
    for field in FIELDS:
        lead[field+'_status'] = 'published_candidate' if lead[field] else 'not_found_in_scanned_content'
    lead['coordinate_count'] = sum(bool(lead[field]) for field in FIELDS)
    lead['contact_value_count'] = sum(len(lead[field]) for field in FIELDS)

def new_lead(identifier, platform, url, title, created, body):
    return {'lead_id': identifier, 'platform': platform, 'source_url': url, 'title': title,
            'created_at': created.isoformat(), 'captured_at': now().isoformat(), 'brief_snippet': body[:1200],
            'buyer_username': '', 'buyer_real_name': '', 'buyer_company': '', 'buyer_website': '',
            'buyer_profile_url': '', 'buyer_location': '', 'can_direct_message': None,
            'status': 'review_required', 'review_flags': [], 'budget': 'Not established',
            'budget_mentions': [], **{k: [] for k in FIELDS}, 'whatsapp_links': [], 'contact_evidence': [],
            'suppressed_values': 0, 'coordinate_count': 0, 'contact_value_count': 0,
            **{k+'_status': 'not_found_in_scanned_content' for k in FIELDS}}

def qualification(title, body, created, days, location='', marketplace=False):
    reasons = []
    if created is None: reasons.append('publication_date_unknown')
    elif created > now()+timedelta(minutes=5): reasons.append('future_publication_date')
    elif (now()-created).total_seconds()>days*86400: reasons.append('older_than_age_limit')
    if EXCLUDED.search(title+' '+body+' '+location): reasons.append('excluded_territory')
    if SELLER.search(title): reasons.append('seller_advertisement')
    if not TECH_RE.search(title+' '+body): reasons.append('technical_fit_unconfirmed')
    if not marketplace and not BUYER.search(title+' '+body): reasons.append('buyer_request_unconfirmed')
    if CLOSED.search(body): reasons.append('filled_or_closed_notice')
    return reasons

class Research:
    def __init__(self, args, out):
        self.args, self.out = args, out
        self.web = Web(out, args.delay)  # Default verified TLS and public redirect checks.
        self.errors, self.excluded, self.cache = [], [], {}
        self.leads = []  # Checkpointable even if interrupted inside a harvester.
        self.requests = 0
    def get(self, url, api=False):
        if url in self.cache: return self.cache[url]
        for attempt in range(2):
            if self.requests>=self.args.max_requests: raise RuntimeError('Request-attempt budget exhausted')
            self.requests += 1
            try:
                value = self.web.json(url, api=api)
                if not isinstance(value, dict): raise ValueError('Expected JSON object')
                if value.get('status') not in (None, 'success'): raise ValueError('API did not report success')
                self.cache[url] = value
                return value
            except HTTPError as e:
                retry = e.headers.get('Retry-After', '2')
                if attempt==0 and e.code in (429,500,502,503,504) and retry.isdigit() and int(retry)<=10:
                    time.sleep(max(2,int(retry))); continue
                raise
            except (URLError, TimeoutError):
                if attempt==0: time.sleep(2); continue
                raise
    def error(self, stage, url, exc):
        self.errors.append({'stage': stage, 'url': url, 'error': str(exc)})
        print(f'  {stage}: {exc}', flush=True)
    def reject(self, url, reasons): self.excluded.append({'url': url, 'reasons': reasons})
    def profile(self, root, username):
        url = root+'/u/'+quote(username, safe='')+'.json'
        try:
            user = mapping(self.get(url).get('user'))
            return ({} if user.get('profile_hidden') else user), url
        except Exception as e:
            self.error('public_profile',url,e)
            return {}, url

def topic_id(url):
    p = urlparse(url)
    if p.scheme!='https' or p.hostname not in ('community.n8n.io','community.make.com') or p.username or p.password:
        raise ValueError('Only supported public HTTPS forum topic URLs are accepted')
    match = re.search(r'/t/(?:[^/]+/)?(\d+)(?:/|\.|$)',p.path)
    if not match: raise ValueError('Not a forum topic URL')
    return 'https://'+p.hostname, match.group(1)

def process_topic(topic, root, research):
    tid = topic.get('id'); url = root+'/t/'+str(tid)
    stream = mapping(topic.get('post_stream')); posts = list(stream.get('posts') or [])
    op = next((p for p in posts if p.get('post_number')==1),None)
    if not tid or not op: research.reject(url,['original_post_unavailable']); return None
    username = op.get('username') or ''
    if not username: research.reject(url,['buyer_author_unknown']); return None
    title = topic.get('title') or ''; body = Page(unquoted(op.get('cooked',''))).text
    created = date(topic.get('created_at'))
    reasons = qualification(title,body,created,research.args.days)
    if reasons: research.reject(url,reasons); return None
    known = {p.get('id') for p in posts}
    missing = [i for i in stream.get('stream',[]) if i not in known]
    for offset in range(0,min(len(missing),research.args.max_batches*20),20):
        endpoint = url+'/posts.json?'+urlencode([('post_ids[]',i) for i in missing[offset:offset+20]])
        try: posts.extend(mapping(research.get(endpoint).get('post_stream')).get('posts') or [])
        except Exception as e: research.error('topic_replies',endpoint,e)
    authors = {p['id']: p for p in posts if p.get('username')==username and p.get('id')}
    author_text = '\n'.join(Page(unquoted(p.get('cooked',''))).text for p in authors.values())
    if CLOSED.search(author_text): research.reject(url,['author_reported_filled_or_closed']); return None
    platform = 'n8n' if 'n8n.io' in root else 'Make'
    lead = new_lead(f'{platform.upper()}-{tid}',platform,url,title,created,body)
    lead['buyer_username'] = username; lead['buyer_profile_url'] = root+'/u/'+quote(username,safe='')
    lead['topic_closed'] = topic.get('closed') # Comments closure is not hiring closure.
    lead['review_flags'] = ['hiring_availability_unconfirmed','buyer_territory_requires_review']
    lead['budget_mentions'] = list(dict.fromkeys(m.group().strip() for m in MONEY.finditer(body)))
    if lead['budget_mentions']: lead['budget'] = 'Unclassified original-post amounts: '+'; '.join(lead['budget_mentions'])
    if len({p.get('id') for p in posts})<len(stream.get('stream',[])):
        lead['review_flags'].append('partial_thread_later_updates_may_be_missing')
    for post in authors.values(): merge_contacts(lead,post.get('cooked',''),url+'/'+str(post['post_number']),research.args.suppressed)
    if not research.args.no_profiles:
        profile, profile_source = research.profile(root,username)
        location = profile.get('location') or ''
        if EXCLUDED.search(location): research.reject(url,['excluded_profile_territory']); return None
        lead.update(buyer_real_name=profile.get('name') or '',buyer_website=profile.get('website') or '',buyer_location=location)
        can_pm = profile.get('can_send_private_message_to_user')
        lead['can_direct_message'] = can_pm if isinstance(can_pm,bool) else None
        merge_contacts(lead,(profile.get('bio_cooked') or profile.get('bio_raw') or '')+'\n'+html.escape(profile.get('website') or ''),profile_source,research.args.suppressed)
    if lead['suppressed_values']:
        research.reject(url,['buyer_already_contacted']); return None
    lead['contact_route'] = 'Review published contacts and forum rules' if lead['coordinate_count'] else 'Forum profile; messaging permission unconfirmed'
    if lead['can_direct_message'] is False: lead['review_flags'].append('forum_pm_unavailable_for_request_context')
    return lead

def harvest_discourse(research):
    urls = list(research.args.url)
    if research.args.urls_file:
        urls += [s.strip() for s in research.args.urls_file.read_text('utf-8-sig').splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if not urls:
        for root in FORUMS:
            endpoint = root+('/c/jobs/13.json' if 'n8n.io' in root else '/search.json?'+urlencode({'q':'hiring after:'+(now()-timedelta(days=research.args.days)).date().isoformat()}))
            try:
                data=research.get(endpoint)
                topics=mapping(data.get('topic_list')).get('topics',[]) if 'n8n.io' in root else data.get('topics',[])
                for t in topics:
                    title=t.get('title') or ''; created=date(t.get('created_at'))
                    if EXCLUDED.search(title) or SELLER.search(title): continue
                    if created and (now()-created).total_seconds()>research.args.days*86400: continue
                    if BUYER.search(title): urls.append(root+'/t/'+str(t['id']))
            except Exception as e: research.error('forum_discovery',endpoint,e)
    seen=set()
    for raw in urls:
        try:
            root,tid=topic_id(raw)
            if (root,tid) in seen: continue
            if len(seen)>=research.args.max_topics: break
            seen.add((root,tid)); endpoint=root+'/t/'+tid+'.json'
            print(f'Forum {len(seen)}/{research.args.max_topics}: {root}/t/{tid}',flush=True)
            lead=process_topic(research.get(endpoint),root,research)
            if lead: research.leads.append(lead)
        except Exception as e: research.error('forum_topic',raw,e)

def process_project(project,research):
    pid=project.get('id'); url='https://www.freelancer.com/projects/'+str(project.get('seo_url') or pid).lstrip('/')
    title=project.get('title') or ''; desc=project.get('description') or ''; created=date(project.get('time_submitted'))
    loc=mapping(project.get('location'))
    location=', '.join(s for s in (loc.get('city'),mapping(loc.get('country')).get('name')) if s)
    reasons=qualification(title,desc,created,research.args.days,location,marketplace=True)
    if not pid: reasons.append('missing_project_id')
    if project.get('status')!='active': reasons.append('project_not_confirmed_active')
    if project.get('sub_status') in ('awarded','closed','expired','cancelled'): reasons.append('project_no_longer_open')
    if not desc: reasons.append('full_description_unavailable')
    if reasons: research.reject(url,reasons); return None
    lead=new_lead(f'FL-{pid}','Freelancer',url,title,created,Page(desc).text)
    lead['buyer_location']=location; lead['buyer_id']=project.get('owner_id')
    lead['review_flags']=['buyer_identity_and_territory_require_review','api_active_status_not_award_or_payment_guarantee']
    b=mapping(project.get('budget')); c=mapping(project.get('currency')).get('code')
    if b.get('minimum') is not None or b.get('maximum') is not None:
        lead['budget']=f"{c or 'currency unknown'} {b.get('minimum','?')} - {b.get('maximum','?')} ({project.get('type') or 'type unknown'})"
    merge_contacts(lead,desc,url,research.args.suppressed)
    if lead['suppressed_values']:
        research.reject(url,['buyer_already_contacted']); return None
    lead['contact_route']='Freelancer project proposal; keep communication/payment within platform rules'
    return lead

def enrich_freelancer_batch(research, leads):
    """Public owner labels only. Profile availability never implies DM permission."""
    ids = sorted({str(l['buyer_id']) for l in leads if l.get('buyer_id')})
    users = {}
    for offset in range(0, len(ids), 50):
        endpoint = 'https://www.freelancer.com/api/users/0.1/users/?' + urlencode([('users[]', i) for i in ids[offset:offset+50]])
        try:
            raw = mapping(research.get(endpoint, api=True).get('result')).get('users')
            if isinstance(raw, dict): users.update({str(k): mapping(v) for k,v in raw.items()})
            elif isinstance(raw, list): users.update({str(u['id']): u for u in raw if isinstance(u,dict) and u.get('id')})
            else: raise ValueError('Public user result missing')
        except Exception as e: research.error('freelancer_public_owners', endpoint, e)
    retained = []
    for lead in leads:
        owner = users.get(str(lead.get('buyer_id')), {})
        location = mapping(owner.get('location'))
        label = ', '.join(s for s in (location.get('city'), mapping(location.get('country')).get('name')) if s)
        if EXCLUDED.search(label): research.reject(lead['source_url'], ['excluded_owner_territory']); continue
        username = owner.get('username') or ''
        lead.update(buyer_username=username, buyer_real_name=owner.get('public_name') or '',
                    buyer_company=owner.get('company') or '', buyer_location=lead['buyer_location'] or label,
                    buyer_profile_url='https://www.freelancer.com/u/'+quote(username,safe='') if username else '')
        # Verification booleans do not reveal a phone/email or authorize messaging.
        retained.append(lead)
    return retained

def harvest_freelancer(research):
    seen=set(); start=len(research.leads)
    for query in research.args.query or QUERIES:
        endpoint='https://www.freelancer.com/api/projects/0.1/projects/active/?'+urlencode({'query':query,'limit':research.args.per_query,'full_description':'true','sort_field':'time_submitted'})
        try:
            data=research.get(endpoint,api=True)
            projects=mapping(data.get('result')).get('projects')
            if not isinstance(projects,list): raise ValueError('Project list missing from API response')
            print(f'Freelancer {query}: {len(projects)} returned',flush=True)
            for project in projects:
                if project.get('id') in seen: continue
                seen.add(project.get('id'))
                lead=process_project(project,research)
                if lead: research.leads.append(lead)
        except Exception as e: research.error('freelancer_search',endpoint,e)
    if not research.args.no_profiles:
        research.leads[start:] = enrich_freelancer_batch(research, research.leads[start:])

def csv_value(value):
    if isinstance(value,(list,dict)): value=json.dumps(value,ensure_ascii=False)
    elif value is None: return ''
    value=str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value

def write_results(research,interrupted=False):
    leads=list({l['lead_id']:l for l in research.leads}.values())
    leads.sort(key=lambda l:(l['coordinate_count'],l['created_at'],l['lead_id']),reverse=True)
    selected=leads[:research.args.limit]; dest=research.out
    (dest/'MASTER_100_LEADS.json').write_text(json.dumps(selected,indent=2,ensure_ascii=False),encoding='utf-8')
    fields=list(dict.fromkeys(k for lead in selected for k in lead)) or ['lead_id','source_url',*FIELDS,'coordinate_count']
    with (dest/'MASTER_100_LEADS.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for lead in selected: writer.writerow({k:csv_value(v) for k,v in lead.items()})
    counts={k:sum(bool(l[k]) for l in selected) for k in FIELDS}
    audit={'captured_at_utc':now().isoformat(),'options':{k:str(v) if isinstance(v,Path) else v for k,v in vars(research.args).items() if k!='suppressed'},
           'retained_candidates':len(selected),'unique_candidates_before_limit':len(leads),'interrupted':interrupted,
           'leads_with_coordinate':counts,'errors':research.errors,'excluded':research.excluded,
           'http_attempts':research.requests,'receipts':research.web.receipts}
    (dest/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')
    report=['# Public buyer lead candidates','','Generated UTC: '+now().isoformat(),'',
            f'Retained {len(selected)} review candidates, requested maximum {research.args.limit}.',
            'Ownership, hiring availability, territory and contact permissions require review. No messages sent.','',
            'Coordinate coverage: '+json.dumps(counts),'',
            'Exclusions: '+json.dumps(dict(Counter(r for x in research.excluded for r in x['reasons']))),'',
            f'Request errors: {len(research.errors)}. Interrupted: {interrupted}. See audit.json.','']
    for lead in selected:
        report += ['## '+re.sub(r'[\r\n#<>]',' ',lead['title']),'','Source: '+lead['source_url'],
                   'Published: '+lead['created_at'],'Budget: '+lead['budget'],'Route: '+lead['contact_route']]
        for field in FIELDS: report.append(field+': '+(', '.join(lead[field]) or 'not found in scanned content'))
        report += ['Review flags: '+'; '.join(lead['review_flags']),'']
    (dest/'MASTER_100_LEADS_REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    if research.args.deliverables_dir:
        target=research.args.deliverables_dir/dest.name; target.mkdir(parents=True,exist_ok=False)
        for file in dest.iterdir():
            if file.is_file(): shutil.copy2(file,target/file.name)
    print(json.dumps({'output':str(dest),'candidates':len(selected),'coordinate_coverage':counts,'errors':len(research.errors),'excluded':len(research.excluded)},indent=2),flush=True)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sources',choices=['all','discourse','freelancer'],default='all')
    ap.add_argument('--url',action='append',default=[],help='Supported forum topic URL; repeatable')
    ap.add_argument('--urls-file',type=Path,help='Explicit forum URLs replace default forum discovery')
    ap.add_argument('--limit',type=int,default=100,help='Maximum retained candidates, not a guaranteed quota')
    ap.add_argument('--days',type=int,default=14)
    ap.add_argument('--max-topics',type=int,default=30)
    ap.add_argument('--max-batches',type=int,default=2)
    ap.add_argument('--max-requests',type=int,default=150,help='Attempts including retries; robots may add requests')
    ap.add_argument('--delay',type=float,default=1.5)
    ap.add_argument('--per-query',type=int,default=20)
    ap.add_argument('--query',action='append',help='Freelancer query; repeatable')
    ap.add_argument('--no-profiles',action='store_true')
    ap.add_argument('--suppress-file',type=Path,default=Path(__file__).with_name('already_contacted.json'))
    ap.add_argument('--out',type=Path,default=Path(__file__).parent/'output')
    ap.add_argument('--deliverables-dir',type=Path,help='Copy to unique subfolder without overwriting reports')
    args=ap.parse_args(argv)
    if min(args.limit,args.days,args.max_topics,args.max_requests,args.per_query)<1 or args.max_batches<0 or args.delay<0 or args.per_query>100:
        ap.error('Invalid limits; per-query must be 1..100')
    if args.sources=='freelancer' and (args.url or args.urls_file):
        ap.error('--url/--urls-file require discourse or all sources')
    try:
        raw=json.loads(args.suppress_file.read_text('utf-8-sig'))
        if not isinstance(raw,list) or not all(isinstance(x,str) for x in raw): raise ValueError('Expected JSON list of contact strings')
        args.suppressed={x.casefold().strip() for x in raw}
        if args.urls_file: args.urls_file.read_text('utf-8-sig')
    except (OSError,ValueError) as e: ap.error(str(e))
    out=args.out/('master_'+now().strftime('%Y%m%dT%H%M%S%fZ')); out.mkdir(parents=True,exist_ok=False)
    research=Research(args,out); interrupted=False
    try:
        if args.sources in ('all','discourse'): harvest_discourse(research)
        if args.sources in ('all','freelancer'): harvest_freelancer(research)
    except KeyboardInterrupt:
        interrupted=True; research.error('run','','Interrupted by user; incomplete harvest')
    finally: write_results(research,interrupted)
    return 130 if interrupted else (2 if research.errors else 0)

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

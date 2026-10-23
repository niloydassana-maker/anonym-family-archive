#!/usr/bin/env python3
"""Public buyer lead research with purpose-linked email and LinkedIn evidence. Python 3.10+.
Returns up to --limit review candidates, never a guaranteed quota. No sends.
The default delivery lane requires a published email address or LinkedIn
profile tied to the buyer request. Phone and WhatsApp are neither returned
nor sufficient for this lane.
Human ownership and eligibility review remain mandatory.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone, timedelta
import email.utils
import hashlib
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, quote, parse_qsl
import xml.etree.ElementTree as ET
from hunt_leads import Web, Page, contacts, BUYER, SELLER, CLOSED, TECH, EXCLUDED
from lead_quality import validated_contacts, task_fit, NICHE, HELP_TITLE, SELLER_INTRO
from hn_source import harvest_hn

FIELDS = ('email', 'linkedin', 'phone', 'whatsapp_number')
DELIVERY_FIELDS = ('email', 'linkedin')
# Each entry was live-probed with the same robots-respecting client used by the
# hunter on 2026-10-23.  Do not add a proposed community merely because a
# generated source list names it: its public feed and robots policy must first
# be proven usable.
FORUMS = {
    'https://community.n8n.io': '/c/jobs/13.json',
    'https://community.make.com': '/c/74.json',
    'https://discuss.frappe.io': '/c/jobs/24.json',
    'https://community.directus.io': '/latest.json',
    'https://community.weweb.io': '/c/jobs/22.json',
    'https://forum.camunda.io': '/latest.json',
    # Live-probed 2026-10-23: public JSON topic lists + standard Discourse robots
    # (allows /c/ /t/ /u/; disallows /search). Category or latest feeds only.
    'https://forum.bubble.io': '/c/jobs-freelance/13.json',
    'https://community.retool.com': '/latest.json',
    'https://discuss.huggingface.co': '/latest.json',
    'https://forum.langchain.com': '/latest.json',
    'https://community.nocodb.com': '/latest.json',
    'https://community.baserow.io': '/latest.json',
}
QUERIES = ['n8n', 'Make.com', 'LangGraph', 'FastAPI', 'webhook', 'email automation',
           'Stripe integration', 'AI agent', 'Python automation', 'API integration',
           'CRM automation', 'workflow automation', 'WhatsApp Cloud API',
           'Bubble.io', 'Retool', 'Zapier', 'Airtable automation', 'Supabase',
           'LangChain', 'RAG pipeline', 'LLM integration', 'GoHighLevel',
           'Telegram bot', 'Discord bot', 'Notion automation']
TECH_RE = re.compile(TECH.pattern + r'|\bpython\b|\bpostgresql\b|\bRAG\b|\bLLM\b|\bCRM\b|\bdeveloper\b|\bengineer\b|\barchitect\b|\bconsultant\b', re.I)
MONEY = re.compile(r'(?:USD|SGD|GBP|EUR|INR|\$|€|£|₹)\s*\d[\d,]*(?:\.\d+)?\s*[kK]?(?:\s*[-–—]\s*\d[\d,]*(?:\.\d+)?\s*[kK]?)?', re.I)

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
    items, rejected = validated_contacts(unquoted(source), url)
    lead.setdefault('rejected_coordinates', []).extend(rejected)
    for item in items:
        if item['value'].casefold() in suppressed:
            lead['suppressed_values'] += 1
            continue
        field = 'whatsapp_links' if item['kind']=='whatsapp' else item['kind']
        if item['value'] not in lead[field]: lead[field].append(item['value'])
        proof = {**item, 'source_url': url, 'ownership': 'publication_only_owner_not_independently_verified'}
        if proof not in lead['contact_evidence']: lead['contact_evidence'].append(proof)
    for field in FIELDS:
        lead[field+'_status'] = 'published_candidate' if lead[field] else 'not_found_in_scanned_content'
    lead['coordinate_count'] = sum(bool(lead[field]) for field in FIELDS)
    lead['contact_value_count'] = sum(len(lead[field]) for field in FIELDS)

def requested_values(lead, args):
    """Return only the coordinates explicitly requested for this run."""
    if getattr(args, 'coordinate_scope', 'email-linkedin') == 'email-linkedin':
        return {
            'email': list(lead.get('email', [])),
            'linkedin': list(lead.get('linkedin', [])),
        }
    return {field: list(lead.get(field, [])) for field in FIELDS}

def has_requested_coordinate(lead, args):
    return any(requested_values(lead, args).values())

def requested_coordinate_count(lead, args):
    return sum(bool(values) for values in requested_values(lead, args).values())

def export_lead(lead, args):
    """Scrub unrequested contact fields from every deliverable artifact."""
    exported = json.loads(json.dumps(lead))
    values = requested_values(lead, args)
    if getattr(args, 'coordinate_scope', 'email-linkedin') == 'email-linkedin':
        exported['email'] = values['email']
        exported['linkedin'] = values['linkedin']
        exported['phone'] = []
        exported['whatsapp_number'] = []
        exported['whatsapp_links'] = []
        exported['contact_evidence'] = [item for item in exported.get('contact_evidence', [])
                                        if item.get('kind') in DELIVERY_FIELDS]
        for field in ('phone', 'whatsapp_number'):
            exported[field + '_status'] = 'out_of_requested_scope'
    exported['coordinate_count'] = requested_coordinate_count(lead, args)
    exported['contact_value_count'] = sum(len(items) for items in values.values())
    return exported

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
    body = Page(unquoted(body)).text
    reasons = []
    if created is None: reasons.append('publication_date_unknown')
    elif created > now()+timedelta(minutes=5): reasons.append('future_publication_date')
    elif (now()-created).total_seconds()>days*86400: reasons.append('older_than_age_limit')
    if EXCLUDED.search(title+' '+body+' '+location): reasons.append('excluded_territory')
    if SELLER.search(title): reasons.append('seller_advertisement')
    if marketplace:
        buyer_ask=re.search(r'\b(?:(?:I|we)\s+(?:(?:am|are)\s+)?(?:need|seek|want|looking for)|(?:looking|searching) for (?:an? |the )?(?:experienced |talented |skilled )?(?:developer|engineer|freelancer)|please (?:build|implement|develop|complete)|required skills|we.re hiring)\b',body,re.I)
        showcase=re.search(r'\b(?:I (?:built|created|developed)|this project showcases my|designed and engineered an? .{0,80}(?:pipeline|assistant))\b',body,re.I)
        if not buyer_ask and (showcase or SELLER_INTRO.search(body[:250])):
            reasons.append('portfolio_showcase_or_seller_not_buyer_need')
    if not (task_fit(title,body) or (not marketplace and BUYER.search(title) and not SELLER_INTRO.search(body[:250]) and any(p.search(body) for p in NICHE))): reasons.append('specific_automation_or_backend_fit_unconfirmed')
    if not marketplace and not BUYER.search(title+' '+body): reasons.append('buyer_request_unconfirmed')
    if not marketplace and (HELP_TITLE.search(title) or SELLER_INTRO.search(body[:250])): reasons.append('help_request_or_seller_pitch')
    if re.search(r'\b(?:unpaid|commission.only|pay (?:a )?registration fee|fee to apply)\b',title+' '+body,re.I): reasons.append('unpaid_or_applicant_fee_request')
    if re.search(r'US.only|U\.S\. citizens? only|must (?:reside|be located) in (?:the )?(?:US|USA|UK|Europe)|active (?:security|secret) clearance|(?:applicants|candidates|developers|freelancers|contractors) (?:must be |need to be )?(?:US|U\.S\.).based', title+' '+body,re.I): reasons.append('india_remote_eligibility_conflict')
    if CLOSED.search(body): reasons.append('filled_or_closed_notice')
    return reasons

class Research:
    def __init__(self, args, out):
        self.args, self.out = args, out
        self.web = Web(out, args.delay)  # Default verified TLS and public redirect checks.
        self.errors, self.excluded, self.cache = [], [], {}
        self.quarantine, self.rejected_contacts = [], []
        self.leads = []  # Checkpointable even if interrupted inside a harvester.
        self.requests = 0
    def get(self, url, api=False):
        if url in self.cache: return self.cache[url]
        for attempt in range(2):
            if self.requests>=self.args.max_requests: raise RuntimeError('Request-attempt budget exhausted')
            self.requests += 1
            try:
                raw = self.web.json(url, api=api)
                if not isinstance(raw, (dict,list)): raise ValueError('Expected JSON object or array')
                if isinstance(raw,dict) and (raw.get('success') is False or raw.get('status') not in (None,'success')): raise ValueError('Source returned an API error payload')
                self.cache[url] = raw
                return raw
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
    def reject(self, url, reasons, lead=None):
        self.excluded.append({'url': url, 'reasons': reasons})
        if lead: self.rejected_contacts.extend(lead.get('rejected_coordinates',[]))
    def text(self, url):
        if self.requests>=self.args.max_requests: raise RuntimeError('Request-attempt budget exhausted')
        self.requests += 1
        return self.web.get(url,api=True)
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
    supported_hosts = {urlparse(root).hostname for root in FORUMS}
    if p.scheme!='https' or p.hostname not in supported_hosts or p.username or p.password:
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
    if getattr(research.args,'direct_first',False):
        if topic.get('closed') is True: reasons.append('topic_marked_closed')
        if re.search(r'\b(?:founding (?:vendor|creator)|vendor cohort|creator program|sell your (?:existing )?work|marketplace for reusable)\b', body, re.I):
            reasons.append('vendor_marketplace_or_creator_program_not_client_demand')
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
    platform = {
        'community.n8n.io': 'n8n', 'community.make.com': 'Make',
        'discuss.frappe.io': 'ERPNext', 'community.directus.io': 'Directus',
        'community.botpress.com': 'Botpress', 'community.weweb.io': 'WeWeb',
        'forum.camunda.io': 'Camunda',
        'forum.bubble.io': 'Bubble', 'community.retool.com': 'Retool',
        'discuss.huggingface.co': 'HuggingFace', 'forum.langchain.com': 'LangChain',
        'community.nocodb.com': 'NocoDB', 'community.baserow.io': 'Baserow',
    }.get(urlparse(root).hostname, 'Discourse')
    lead = new_lead(f'{platform.upper()}-{tid}',platform,url,title,created,body)
    lead['buyer_username'] = username; lead['buyer_profile_url'] = root+'/u/'+quote(username,safe='')
    lead['topic_closed'] = topic.get('closed')
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
    if not has_requested_coordinate(lead, research.args):
        policy=getattr(research.args,'contact_policy','direct-only')
        if policy!='any-route' or (topic.get('closed') is not False and lead['can_direct_message'] is not True):
            research.reject(url,['no_requested_email_or_linkedin_coordinate_found'],lead); return None
        lead['contact_route']='Native forum reply to the hiring topic; check current account permissions'
        lead['contact_kind']='platform_application'
    else:
        lead['contact_kind']='published_direct_contact'
        lead['contact_route'] = 'Review the published application/contact instructions; ownership and permission require confirmation'
    if lead['can_direct_message'] is False: lead['review_flags'].append('forum_pm_unavailable_for_request_context')
    return lead

def harvest_discourse(research):
    urls = list(research.args.url)
    if research.args.urls_file:
        urls += [s.strip() for s in research.args.urls_file.read_text('utf-8-sig').splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if not urls:
        for root, category in FORUMS.items():
            # Discourse serves 30 topics per category page. Walk only as far as
            # the requested date window, then fetch individual primary topics.
            for page in range(research.args.max_feed_pages):
                endpoint=root+category+'?'+urlencode({'order':'created','page':page})
                try:
                    data=research.get(endpoint)
                    topics=mapping(data.get('topic_list')).get('topics',[])
                    if not topics: break
                    page_has_recent=False
                    for t in topics:
                        title=t.get('title') or ''; created=date(t.get('created_at'))
                        if created and (now()-created).total_seconds()>research.args.days*86400: continue
                        page_has_recent=True
                        if EXCLUDED.search(title) or SELLER.search(title): continue
                        if BUYER.search(title): urls.append(root+'/t/'+str(t['id']))
                    if not page_has_recent: break
                except Exception as e:
                    research.error('forum_discovery',endpoint,e); break
    seen=set(); seen_by_forum=Counter()
    explicit_inputs=bool(research.args.url or research.args.urls_file)
    per_forum=max(1,research.args.max_topics//len(FORUMS))
    for raw in urls:
        try:
            root,tid=topic_id(raw)
            if (root,tid) in seen: continue
            if len(seen)>=research.args.max_topics: break
            if not explicit_inputs and seen_by_forum[root]>=per_forum: continue
            seen.add((root,tid)); endpoint=root+'/t/'+tid+'.json'
            seen_by_forum[root]+=1
            lead=process_topic(research.get(endpoint),root,research)
            if lead: research.leads.append(lead)
            if len(research.leads) >= research.args.limit: break
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
    lead['brief_sha256']=hashlib.sha256(re.sub(r'\s+',' ',Page(desc).text).strip().encode('utf-8')).hexdigest()
    lead['brief_length']=len(Page(desc).text)
    lead['engagement_type']='paid_project_request'
    lead['fit_signals']=[p.pattern for p in NICHE if p.search(title+' '+desc)]
    lead['buyer_location']=location; lead['buyer_id']=project.get('owner_id')
    lead['review_flags']=['buyer_identity_and_territory_require_review','api_active_status_not_award_or_payment_guarantee']
    b=mapping(project.get('budget')); c=mapping(project.get('currency')).get('code')
    if b.get('minimum') is not None or b.get('maximum') is not None:
        lead['budget']=f"{c or 'currency unknown'} {b.get('minimum','?')} - {b.get('maximum','?')} ({project.get('type') or 'type unknown'})"
    lead['budget_source']='Freelancer structured listing fields; not an agreed contract'
    lead['budget_mentions']=list(dict.fromkeys(m.group().strip() for m in MONEY.finditer(Page(desc).text)))
    brief_budget=re.search(r'\bBudget\s*:\s*\**\s*\$\s*([\d,]+(?:\.\d+)?)\s*(?:USD)?',Page(desc).text,re.I)
    if brief_budget and c=='USD' and b.get('minimum') is not None and b.get('maximum') is not None:
        amount=float(brief_budget.group(1).replace(',',''))
        if not b['minimum']<=amount<=b['maximum']:
            lead['review_flags'].append('brief_budget_conflicts_with_structured_listing_confirm_before_quoting')
    merge_contacts(lead,desc,url,research.args.suppressed)
    if lead['suppressed_values']:
        research.reject(url,['buyer_already_contacted']); return None
    if not has_requested_coordinate(lead, research.args) and getattr(research.args,'contact_policy','direct-only')!='any-route':
        research.reject(url,['no_requested_email_or_linkedin_coordinate_found'],lead); return None
    lead['contact_kind']='published_direct_contact' if has_requested_coordinate(lead, research.args) else 'platform_application'
    lead['listing_status']='active'
    lead['listing_status_source']='Freelancer active-project API; see captured response receipt'
    lead['contact_route']='Freelancer proposal route; published coordinates do not authorize off-platform contact'
    return lead

def enrich_freelancer_batch(research, leads):
    ids = sorted({str(l['buyer_id']) for l in leads if l.get('buyer_id')})
    users = {}
    for offset in range(0, len(ids), 50):
        endpoint = 'https://www.freelancer.com/api/users/0.1/users/?' + urlencode([('users[]', i) for i in ids[offset:offset+50]])
        try:
            raw = mapping(research.get(endpoint, api=True).get('result')).get('users')
            if isinstance(raw, dict): users.update({str(k): mapping(v) for k,v in raw.items()})
            elif isinstance(raw, list): users.update({str(u['id']): u for u in raw if isinstance(u,dict) and u.get('id')})
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
            for project in projects:
                if project.get('id') in seen: continue
                seen.add(project.get('id'))
                lead=process_project(project,research)
                if lead: research.leads.append(lead)
                if len(research.leads) >= research.args.limit: break
            if len(research.leads) >= research.args.limit: break
        except Exception as e: research.error('freelancer_search',endpoint,e)
    if not research.args.no_profiles:
        research.leads[start:] = enrich_freelancer_batch(research, research.leads[start:])

def harvest_jobicy(research):
    cursor = None
    cursors = set(); page_count = 0; start = len(research.leads)
    cutoff = now() - timedelta(days=research.args.days)
    seen = set()
    while len(research.leads) < research.args.limit and page_count < getattr(research.args,'max_feed_pages',10):
        params={'count':100}
        if cursor: params['cursor']=cursor
        endpoint = 'https://jobicy.com/api/v2/remote-jobs?' + urlencode(params)
        page_count += 1
        try:
            data = research.get(endpoint, api=True)
            jobs = mapping(data).get('jobs')
            if not isinstance(jobs, list) or not jobs: break
            stop = False
            for j in jobs:
                jid = j.get('id')
                if not jid or jid in seen: continue
                seen.add(jid)
                pub_date = date(j.get('pubDate'))
                if pub_date is None or pub_date < cutoff:
                    research.reject(j.get('url',''),['publication_date_unknown_or_stale']); continue
                title = j.get('jobTitle') or ''
                company = j.get('companyName') or ''
                url = j.get('url') or f"https://jobicy.com/jobs/{jid}"
                desc = j.get('jobDescription') or ''
                location = j.get('jobGeo') or ''
                reasons = qualification(title, desc, pub_date, research.args.days, location, marketplace=True)
                if reasons:
                    research.reject(url, reasons); continue
                lead = new_lead(f"JOBICY-{jid}", 'Jobicy', url, f"{company}: {title}", pub_date, Page(desc).text)
                lead['buyer_company'] = company
                lead['buyer_location'] = location
                lead['review_flags'] = ['aggregated_listing_not_employer_ownership_proof']
                lead['eligibility_location'] = location
                merge_contacts(lead, desc + ' ' + company, url, research.args.suppressed)
                if lead['suppressed_values']:
                    research.reject(url, ['buyer_already_contacted']); continue
                if not has_requested_coordinate(lead, research.args):
                    if getattr(research.args,'contact_policy','direct-only') != 'any-route':
                        research.reject(url, ['no_requested_email_or_linkedin_coordinate_found'],lead); continue
                    lead['contact_kind'] = 'platform_application'
                    lead['contact_route'] = 'Use the Jobicy application route unless an employer application contact is explicitly authorized'
                else:
                    lead['contact_kind'] = 'published_direct_contact'
                    lead['contact_route'] = 'Direct outreach via a published email or LinkedIn coordinate; ownership and permission require confirmation'
                research.leads.append(lead)
                if len(research.leads) >= research.args.limit: break
            cursor = data.get('nextCursor')
            if not cursor or not data.get('hasMore'): break
            if cursor in cursors:
                research.error('jobicy_pagination',endpoint,'Repeated cursor; traversal stopped'); break
            cursors.add(cursor)
        except Exception as e:
            research.error('jobicy_harvest', endpoint, e); break
    # Feed recency is not liveness. Query the provider's explicit status endpoint.
    pending=research.leads[start:]; verified=[]
    for offset in range(0,len(pending),100):
        batch=pending[offset:offset+100]
        endpoint='https://jobicy.com/api/jobs/status?'+urlencode({'ids':','.join(l['lead_id'].split('-',1)[1] for l in batch)})
        try:
            statuses={str(x['id']):x.get('status') for x in research.get(endpoint,api=True).get('jobs',[]) if isinstance(x,dict) and x.get('id')}
        except Exception as e:
            research.error('jobicy_status',endpoint,e); statuses={}
        for lead in batch:
            status=statuses.get(lead['lead_id'].split('-',1)[1],'unknown')
            lead['listing_status']=status
            lead['listing_status_source']=endpoint
            if status=='closed': research.reject(lead['source_url'],['provider_confirmed_closed'],lead)
            else:
                if status!='active': lead['review_flags'].append('listing_status_unconfirmed')
                verified.append(lead)
    research.leads[start:]=verified

def harvest_jobspresso(research):
    cutoff = now() - timedelta(days=research.args.days)
    seen = set()
    page = 1
    while len(research.leads) < research.args.limit and page <= 10:
        endpoint = f'https://jobspresso.co/wp-json/wp/v2/job-listings?per_page=50&page={page}'
        try:
            data = research.get(endpoint, api=True)
            if not isinstance(data, list) or not data: break
            stop = False
            for j in data:
                jid = j.get('id')
                if not jid or jid in seen: continue
                seen.add(jid)
                # WordPress local dates have no offset. Use its explicitly GMT field.
                pub_date = date((j.get('date_gmt')+'+00:00') if j.get('date_gmt') else None)
                if pub_date is None or pub_date < cutoff:
                    research.reject(j.get('link',''),['publication_date_unknown_or_stale']); continue
                title = j.get('title', {}).get('rendered', '') if isinstance(j.get('title'), dict) else str(j.get('title') or '')
                url = j.get('link') or f"https://jobspresso.co/job/{j.get('slug')}"
                desc = j.get('content', {}).get('rendered', '') if isinstance(j.get('content'), dict) else ''
                reasons = qualification(title, desc, pub_date, research.args.days, marketplace=True)
                if reasons:
                    research.reject(url, reasons); continue
                lead = new_lead(f"JOBSPRESSO-{jid}", 'Jobspresso', url, title, pub_date, Page(desc).text)
                lead['review_flags'] = ['aggregated_listing_open_status_unconfirmed']
                merge_contacts(lead, desc, url, research.args.suppressed)
                if lead['suppressed_values']:
                    research.reject(url, ['buyer_already_contacted']); continue
                if not has_requested_coordinate(lead, research.args):
                    if getattr(research.args,'contact_policy','direct-only') != 'any-route':
                        research.reject(url, ['no_requested_email_or_linkedin_coordinate_found'],lead); continue
                    lead['contact_kind'] = 'platform_application'
                    lead['contact_route'] = 'Use the Jobspresso application route unless an employer application contact is explicitly authorized'
                else:
                    lead['contact_kind'] = 'published_direct_contact'
                    lead['contact_route'] = 'Direct outreach via a published email or LinkedIn coordinate; ownership and permission require confirmation'
                research.leads.append(lead)
                if len(research.leads) >= research.args.limit: break
            if stop: break
            page += 1
        except Exception as e:
            research.error('jobspresso_harvest', endpoint, e); break

def harvest_remoteok(research):
    endpoint = 'https://remoteok.com/api'
    cutoff = now() - timedelta(days=research.args.days)
    seen = set()
    try:
        data = research.get(endpoint, api=True)
        jobs = [j for j in data if isinstance(j, dict) and 'id' in j] if isinstance(data, list) else []
        for j in jobs:
            jid = j.get('id')
            if not jid or jid in seen: continue
            seen.add(jid)
            pub_date = date(j.get('date'))
            if pub_date is None or pub_date < cutoff: continue
            title = j.get('position') or ''
            company = j.get('company') or ''
            url = j.get('url') or f"https://remoteok.com/remote-jobs/{jid}"
            desc = j.get('description') or ''
            location = j.get('location') or ''
            reasons = qualification(title, desc, pub_date, research.args.days, location, marketplace=True)
            if reasons:
                research.reject(url, reasons); continue
            lead = new_lead(f"REMOTEOK-{jid}", 'RemoteOK', url, f"{company}: {title}", pub_date, Page(desc).text)
            lead['buyer_company'] = company
            lead['buyer_location'] = location
            lead['review_flags'] = ['aggregated_listing_open_status_unconfirmed']
            lead['eligibility_location'] = location
            merge_contacts(lead, desc + ' ' + company, url, research.args.suppressed)
            if lead['suppressed_values']:
                research.reject(url, ['buyer_already_contacted']); continue
            if not has_requested_coordinate(lead, research.args):
                if getattr(research.args,'contact_policy','direct-only') != 'any-route':
                    research.reject(url, ['no_requested_email_or_linkedin_coordinate_found'],lead); continue
                lead['contact_kind'] = 'platform_application'
                lead['contact_route'] = 'Use the RemoteOK application route unless an employer application contact is explicitly authorized'
            else:
                lead['contact_kind'] = 'published_direct_contact'
                lead['contact_route'] = 'Direct outreach via a published email or LinkedIn coordinate; ownership and permission require confirmation'
            research.leads.append(lead)
            if len(research.leads) >= research.args.limit: break
    except Exception as e:
        research.error('remoteok_harvest', endpoint, e)

def harvest_wwr(research):
    feeds = [
        'https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss',
    ]
    cutoff = now() - timedelta(days=research.args.days)
    seen = set()
    for feed_url in feeds:
        try:
            raw_xml = research.text(feed_url)
            if re.search(r'<!DOCTYPE|<!ENTITY',raw_xml,re.I): raise ValueError('RSS entity declarations not accepted')
            root = ET.fromstring(raw_xml)
            items = root.findall('.//item')
            for it in items:
                link = (it.find('link').text or '').strip() if it.find('link') is not None else ''
                if not link or link in seen: continue
                seen.add(link)
                pub_text = it.find('pubDate').text if it.find('pubDate') is not None else ''
                pub_date = None
                try:
                    pub_date = email.utils.parsedate_to_datetime(pub_text)
                    if pub_date.tzinfo is None: raise ValueError('RSS date timezone unknown')
                    pub_date = pub_date.astimezone(timezone.utc)
                except Exception:
                    continue
                if pub_date < cutoff: continue
                title = it.find('title').text if it.find('title') is not None else ''
                desc = it.find('description').text if it.find('description') is not None else ''
                reasons = qualification(title, desc, pub_date, research.args.days, marketplace=True)
                if reasons:
                    research.reject(link, reasons); continue
                lead = new_lead(f"WWR-{hashlib.sha256(link.encode()).hexdigest()[:10]}", 'WeWorkRemotely', link, title, pub_date, Page(desc).text)
                lead['review_flags'] = ['aggregated_listing_open_status_unconfirmed']
                merge_contacts(lead, desc, link, research.args.suppressed)
                if lead['suppressed_values']:
                    research.reject(link, ['buyer_already_contacted']); continue
                if not has_requested_coordinate(lead, research.args):
                    if getattr(research.args,'contact_policy','direct-only') != 'any-route':
                        research.reject(link, ['no_requested_email_or_linkedin_coordinate_found'],lead); continue
                    lead['contact_kind'] = 'platform_application'
                    lead['contact_route'] = 'Use the WeWorkRemotely application route unless an employer application contact is explicitly authorized'
                else:
                    lead['contact_kind'] = 'published_direct_contact'
                    lead['contact_route'] = 'Direct outreach via a published email or LinkedIn coordinate; ownership and permission require confirmation'
                research.leads.append(lead)
                if len(research.leads) >= research.args.limit: break
            if len(research.leads) >= research.args.limit: break
        except Exception as e:
            research.error('wwr_harvest', feed_url, e)

def csv_value(value):
    if isinstance(value,(list,dict)): value=json.dumps(value,ensure_ascii=False)
    elif value is None: return ''
    value=str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value

def process_hn_comment(item,thread,research):
    identifier=item.get('id'); url='https://news.ycombinator.com/item?id='+str(identifier)
    body=Page(unquoted(item.get('text') or '')).text
    title=next((line.strip() for line in body.splitlines() if line.strip()),'')[:350]
    if 'Freelancer?' in thread['title'] and not re.match(r'^SEEKING FREELANCER\b',body,re.I):
        research.reject(url,['not_a_seeking_freelancer_buyer_post']); return None
    if getattr(research.args,'direct_first',False) and 'Freelancer?' not in thread['title']:
        research.reject(url,['employment_listing_not_direct_service_buyer']); return None
    if re.match(r'^SEEKING WORK\b',body,re.I): research.reject(url,['seller_advertisement']); return None
    created=date(item.get('time'))
    # The actual opening text may put the role below the company/remote header.
    reasons=qualification(body[:600],body,created,research.args.days,marketplace=True)
    if 'Freelancer?' in thread['title'] and any(p.search(body) for p in NICHE):
        reasons=[r for r in reasons if r!='specific_automation_or_backend_fit_unconfirmed']
    if re.search(r'REMOTE\s*\(\s*(?:US|USA|United States|UK|EU|Europe)\s*(?:only)?\s*\)',body[:500],re.I): reasons.append('explicit_remote_country_restriction')
    if re.search(r'\b(?:ONSITE|ON.SITE|HYBRID)\b',body[:400],re.I) and not re.search(r'\bREMOTE\b',body[:400],re.I): reasons.append('onsite_or_hybrid_only')
    if reasons: research.reject(url,reasons); return None
    lead=new_lead('HN-'+str(identifier),'HackerNews',url,title,created,body)
    lead['buyer_username']=item.get('by') or ''
    lead['buyer_profile_url']='https://news.ycombinator.com/user?id='+quote(lead['buyer_username'],safe='')
    lead['engagement_type']='contract_request' if 'Freelancer?' in thread['title'] else 'employer_hiring_post'
    lead['parent_thread_url']='https://news.ycombinator.com/item?id='+str(thread['id'])
    lead['review_flags']=['employer_claim_not_independent_identity_verification','confirm_india_eligibility_and_current_vacancy']
    lead['budget_mentions']=list(dict.fromkeys(m.group().strip() for m in MONEY.finditer(body)))
    if lead['budget_mentions']: lead['budget']='Original-post amounts; confirm salary/project basis: '+'; '.join(lead['budget_mentions'])
    merge_contacts(lead,item.get('text') or '',url,research.args.suppressed)
    if lead['suppressed_values']: research.reject(url,['buyer_already_contacted'],lead); return None
    if not has_requested_coordinate(lead, research.args) and getattr(research.args,'contact_policy','direct-only')!='any-route':
        research.reject(url,['no_requested_email_or_linkedin_coordinate_found'],lead); return None
    lead['contact_kind']='published_direct_contact' if has_requested_coordinate(lead, research.args) else 'platform_application'
    lead['contact_route']='Follow the employer application instructions in the primary HN post; no unsolicited service offers to employment-only contacts'
    return lead

def finalize_candidates(research):
    """Fail closed on unresolved liveness/eligibility and ambiguous attribution."""
    retained=[]; seen_urls=set(); seen_contacts=set(); seen_briefs={}; duplicates=[]
    for lead in sorted(research.leads,key=lambda x:(x['coordinate_count'],x['created_at']),reverse=True):
        flags=[]
        geo=lead.get('eligibility_location','')
        if geo and EXCLUDED.search(geo): flags.append('excluded_territory')
        if any('partial_thread' in flag for flag in lead['review_flags']): flags.append('complete_buyer_updates_not_checked')
        if len(lead.get('linkedin',[]))>1: flags.append('multiple_personal_profiles_owner_ambiguous')
        if flags:
            lead['review_flags'].extend(flags); research.quarantine.append(lead); continue
        parsed=urlparse(lead['source_url'])
        # HN ?id= and ATS requisition queries are identities, not tracking noise.
        canonical=parsed._replace(query=urlencode([(k,v) for k,v in parse_qsl(parsed.query) if not k.lower().startswith('utm_')]),fragment='').geturl().rstrip('/')
        identities={(field,value.casefold()) for field in FIELDS for value in lead[field]}
        normalized_title=re.sub(r'\s*--\s*\d+\s*$','',lead['title']).strip().casefold()
        brief_key=(lead['platform'], normalized_title, lead.get('brief_sha256'))
        if lead.get('brief_sha256') and lead.get('brief_length',0)>=200 and brief_key in seen_briefs:
            duplicates.append({'source_url':lead['source_url'],'retained_source_url':seen_briefs[brief_key],
                               'reason':'identical_full_brief_and_title_repost_not_independent_demand'})
            continue
        if canonical in seen_urls or identities & seen_contacts:
            duplicates.append({'source_url':lead['source_url'],'reason':'same_source_or_shared_published_contact_no_automatic_identity_merge'})
            continue
        seen_urls.add(canonical); seen_contacts.update(identities)
        if lead.get('brief_sha256'): seen_briefs[brief_key]=lead['source_url']
        lead['verification_status']='source_filtered_candidate_requires_human_ownership_and_eligibility_review'
        retained.append(lead)
    return retained,duplicates

def write_results(research,interrupted=False):
    leads,duplicates=finalize_candidates(research)
    leads=list({l['lead_id']:l for l in leads}.values())
    leads.sort(key=lambda l:(l.get('engagement_type') in ('paid_project_request','contract_request'),requested_coordinate_count(l,research.args),l['created_at'],l['lead_id']),reverse=True)
    selected=[export_lead(lead,research.args) for lead in leads[:research.args.limit]]; dest=research.out
    direct=[l for l in selected if l['coordinate_count']]
    platform=[l for l in selected if not l['coordinate_count']]
    for name,data in [('DIRECT_CONTACT_LEADS.json',direct),('PLATFORM_APPLICATION_LEADS.json',platform)]:
        (dest/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

    # Save both 500 and 100 filenames for full compatibility
    for prefix in ('MASTER_500_LEADS', 'MASTER_100_LEADS'):
        (dest/f'{prefix}.json').write_text(json.dumps(selected,indent=2,ensure_ascii=False),encoding='utf-8')
        fields=list(dict.fromkeys(k for lead in selected for k in lead)) or ['lead_id','source_url',*FIELDS,'coordinate_count']
        with (dest/f'{prefix}.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
            for lead in selected: writer.writerow({k:csv_value(v) for k,v in lead.items()})

    delivery_fields=DELIVERY_FIELDS if research.args.coordinate_scope=='email-linkedin' else FIELDS
    counts={k:sum(bool(l[k]) for l in selected) for k in delivery_fields}
    rejected=research.rejected_contacts+[v for l in research.leads+research.quarantine for v in l.get('rejected_coordinates',[])]
    for name,data in [('quarantine.json',research.quarantine),('rejected_coordinates.json',rejected),('duplicates.json',duplicates),('OUTREACH_READY.json',[])]:
        (dest/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    audit={'captured_at_utc':now().isoformat(),'options':{k:str(v) if isinstance(v,Path) else v for k,v in vars(research.args).items() if k!='suppressed'},
           'retained_candidates':len(selected),'unique_candidates_before_limit':len(leads),'interrupted':interrupted,
           'leads_with_coordinate':counts,'errors':research.errors,'excluded':research.excluded,
           'http_attempts':research.requests,'receipts':research.web.receipts,
           'quarantined':len(research.quarantine),'rejected_coordinate_observations':len(rejected),'duplicate_observations':len(duplicates),
           'verification_policy':'No automated ownership or zero-false-positive guarantee. OUTREACH_READY is empty until human verification.'}
    (dest/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')

    lane = 'direct-contact buyer lane' if getattr(research.args,'direct_first',False) else 'mixed buyer research lane'
    report=['# Public buyer lead candidates','','Generated UTC: '+now().isoformat(),'','Lane: '+lane,
            f'Retained {len(selected)} source-filtered review candidates, requested maximum {research.args.limit}.',
            f'Published direct contacts: {len(direct)}. Valid native application routes without public coordinates: {len(platform)}.',
            f'Publication cutoff: {research.args.days} days; recency is separate from confirmed hiring status.',
            'Published contact syntax is not verified ownership. No item is automatically approved for outreach. No messages sent.',
            f'Quarantined {len(research.quarantine)} uncertain records. Rejected coordinate observations: {len(rejected)}. See the accompanying JSON files.','',
            'Coordinate coverage: '+json.dumps(counts),'',
            'Exclusions: '+json.dumps(dict(Counter(r for x in research.excluded for r in x['reasons']))),'',
            f'Request errors: {len(research.errors)}. Interrupted: {interrupted}. See audit.json.','']
    for lead in selected:
        report += ['## '+re.sub(r'[\r\n#<>]',' ',lead['title']),'','Source: '+lead['source_url'],
                   'Published: '+lead['created_at'],'Budget: '+lead['budget'],'Route: '+lead['contact_route']]
        for field in delivery_fields: report.append(field+': '+(', '.join(lead[field]) or 'not found in scanned content'))
        report += ['Review flags: '+'; '.join(lead['review_flags']),'']

    for prefix in ('MASTER_500_LEADS_REPORT', 'MASTER_100_LEADS_REPORT'):
        (dest/f'{prefix}.md').write_text('\n'.join(report),encoding='utf-8')

    if research.args.deliverables_dir:
        target=research.args.deliverables_dir/dest.name; target.mkdir(parents=True,exist_ok=False)
        for file in dest.iterdir():
            if file.is_file(): shutil.copy2(file,target/file.name)
    print(json.dumps({'output':str(dest),'candidates':len(selected),'with_direct_contacts':len(direct),'native_application_routes':len(platform),'quarantined':len(research.quarantine),'rejected_coordinates':len(rejected),'coordinate_coverage':counts,'errors':len(research.errors),'excluded':len(research.excluded)},indent=2),flush=True)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sources',choices=['all','hn','jobicy','jobspresso','remoteok','wwr','freelancer','discourse'],default='all')
    ap.add_argument('--contact-policy',choices=['any-route','direct-only'],default='direct-only',help='direct-only requires a published, purpose-attributable requested coordinate; any-route also keeps native application routes')
    ap.add_argument('--coordinate-scope',choices=['email-linkedin','all'],default='email-linkedin',help='Returned direct-contact leads must have a purpose-linked email or LinkedIn profile by default')
    ap.add_argument('--direct-first',action='store_true',help='Search only direct-contact buyer sources and suppress employment/portal-first acquisition lanes')
    ap.add_argument('--url',action='append',default=[],help='Supported forum topic URL; repeatable')
    ap.add_argument('--urls-file',type=Path,help='Explicit forum URLs replace default forum discovery')
    ap.add_argument('--limit',type=int,default=500,help='Maximum retained candidates, not a guaranteed quota')
    ap.add_argument('--days',type=int,default=5,help='Strict liveness range in days (default: 5)')
    ap.add_argument('--max-topics',type=int,default=30)
    ap.add_argument('--max-batches',type=int,default=2)
    ap.add_argument('--max-feed-pages',type=int,default=10)
    ap.add_argument('--max-requests',type=int,default=600,help='Attempts including retries; robots may add requests')
    ap.add_argument('--delay',type=float,default=0.5)
    ap.add_argument('--per-query',type=int,default=20)
    ap.add_argument('--query',action='append',help='Freelancer query; repeatable')
    ap.add_argument('--no-profiles',action='store_true')
    ap.add_argument('--suppress-file',type=Path,default=Path(__file__).with_name('already_contacted.json'))
    ap.add_argument('--out',type=Path,default=Path(__file__).parent/'output')
    ap.add_argument('--deliverables-dir',type=Path,help='Copy to unique subfolder without overwriting reports')
    args=ap.parse_args(argv)
    if args.contact_policy=='direct-only': args.direct_first=True
    if min(args.limit,args.days,args.max_topics,args.max_requests,args.per_query,args.max_feed_pages)<1 or args.max_batches<0 or args.delay<0 or args.per_query>100:
        ap.error('Invalid limits; per-query must be 1..100')
    if args.sources not in ('discourse','all') and (args.url or args.urls_file):
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
        if args.sources in ('all','hn'): harvest_hn(research,process_hn_comment,now)
        if args.sources in ('all','discourse') and len(research.leads) < args.limit: harvest_discourse(research)
        # Direct-first means a service buyer personally published the need.
        # Aggregated employment boards can publish legitimate HR addresses, but
        # those are not decision-maker contacts for a service offer and must
        # never become direct-outreach leads in this lane.
        if not args.direct_first:
            if args.sources in ('all','jobicy') and len(research.leads) < args.limit: harvest_jobicy(research)
            if args.sources in ('all','jobspresso') and len(research.leads) < args.limit: harvest_jobspresso(research)
            if args.sources in ('all','remoteok') and len(research.leads) < args.limit: harvest_remoteok(research)
            if args.sources in ('all','wwr') and len(research.leads) < args.limit: harvest_wwr(research)
            if args.sources in ('all','freelancer') and len(research.leads) < args.limit: harvest_freelancer(research)
    except KeyboardInterrupt:
        interrupted=True; research.error('run','','Interrupted by user; incomplete harvest')
    finally: write_results(research,interrupted)
    return 130 if interrupted else (2 if research.errors else 0)

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

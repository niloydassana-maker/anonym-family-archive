#!/usr/bin/env python3
"""Public buyer-request discovery and contact extraction. No sending or login access.

Python 3.10+; standard library only. Run --help. All contacts require human review.
"""
import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urljoin, urlencode, unquote, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UA = 'BuyerLeadResearch/1.0'
EMAIL = re.compile(r'(?<![\w.+-])[A-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?\.[A-Z]{2,24}', re.I)
PHONE = re.compile(r'(?<!\w)(?:\+|00)\d[\d ().\-\u00a0]{6,24}\d(?!\w)')
TECH = re.compile(r'\bn8n\b|\bmake\.com\b|automation|webhook|fastapi|langgraph|AI agent|workflow|API integration', re.I)
BUYER = re.compile(r'hiring|looking for|need(?:ed)?\b|seeking|paid trial|paid test|budget', re.I)
SELLER = re.compile(r'\[?for hire\]?|looking for work|seeking work|available for hire', re.I)
CLOSED = re.compile(r'applications? (?:are )?closed|position (?:is )?filled|test (?:has been|is) filled|no longer (?:available|hiring)|found (?:a|our) developer', re.I)
EXCLUDED = re.compile(r'\bKolkata\b|\bWest Bengal\b', re.I)
QUERIES = [
    'site:community.n8n.io/t/ hiring paid n8n automation Singapore OR UAE OR UK OR remote -Kolkata -"West Bengal"',
    'site:community.make.com/t/ "looking for" automation "paid" remote -Kolkata -"West Bengal"',
    '"hiring" "n8n" "email" API automation fixed price -"for hire" -Kolkata -"West Bengal"',
    '"looking for" "automation developer" "WhatsApp" budget remote -"for hire"',
    '"paid" "AI agent" "stress testing" developer -"for hire"',
    '"hiring" "n8n" "lead enrichment" CRM email -"for hire"',
]


def utcnow():
    return datetime.now(timezone.utc)


def public_url(url):
    p = urlparse(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Only public HTTP(S) URLs without credentials are supported')
    for entry in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == 'https' else 80)):
        if not ipaddress.ip_address(entry[4][0]).is_global:
            raise ValueError('Private/local destination refused')
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        # A search API credential must never travel to a redirect destination.
        if req.has_header('X-subscription-token'):
            raise ValueError('Search API redirect refused')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Web:
    def __init__(self, out, delay):
        self.out, self.delay = out, delay
        self.last = 0
        self.robots = {}
        self.opener = build_opener(SafeRedirect())
        self.receipts = []

    def raw(self, url, headers=None):
        public_url(url)
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        req = Request(url, headers={'User-Agent': UA, **(headers or {})})
        with self.opener.open(req, timeout=20) as r:
            data = r.read(3_000_001)
            if len(data) > 3_000_000:
                raise ValueError('Response exceeds 3 MB cap')
            ctype = r.headers.get_content_type()
            if ctype not in ('text/html', 'text/plain', 'application/json', 'application/ld+json', 'application/xml', 'text/xml', 'application/rss+xml'):
                raise ValueError('Unsupported response content type: ' + ctype)
            return data, r.headers.get_content_charset() or 'utf-8', r.geturl()

    def get(self, url, api=False, headers=None):
        public_url(url)
        p = urlparse(url)
        root = f'{p.scheme}://{p.netloc}'
        if not api:
            if root not in self.robots:
                rp = RobotFileParser(root + '/robots.txt')
                try:
                    data, enc, _ = self.raw(root + '/robots.txt')
                    rp.parse(data.decode(enc, errors='replace').splitlines())
                except Exception:
                    # Unknown robots state is reported rather than bypassed.
                    raise RuntimeError('Could not read robots.txt; source skipped: ' + root)
                self.robots[root] = rp
            if not self.robots[root].can_fetch(UA, url):
                raise RuntimeError('robots.txt disallows this source')
        data, enc, final = self.raw(url, headers)
        digest = hashlib.sha256(data).hexdigest()
        evidence = self.out / 'evidence' / (digest + '.bin')
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_bytes(data)
        self.receipts.append({'url': url, 'final_url': final, 'fetched_at': utcnow().isoformat(), 'sha256': digest, 'file': str(evidence)})
        return data.decode(enc, errors='replace')

    def json(self, url, **kwargs):
        return json.loads(self.get(url, **kwargs))


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.skip = [], [], 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if not self.skip and tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if tag in ('p', 'br', 'li', 'div'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    @property
    def text(self):
        return re.sub(r'[ \t]+', ' ', ''.join(self.parts)).strip()


def normalize_phone(value):
    """Keep explicitly supplied local numbers local; do not invent country codes."""
    value = unquote(value).strip()
    value = re.split(r';|\bext\.?|\bx\s*\d', value, maxsplit=1, flags=re.I)[0]
    digits = re.sub(r'\D', '', value)
    if value.startswith('00'):
        digits, prefix = digits[2:], '+'
    else:
        prefix = '+' if value.startswith('+') else ''
    return prefix + digits if 7 <= len(digits) <= 15 else None


def contacts(source):
    page = Page(source)
    text = page.text
    # Only explicit [at]/[dot] obfuscation; never generate name/domain patterns.
    decoded = re.sub(r'\s*(?:\[at\]|\(at\))\s*', '@', text, flags=re.I)
    decoded = re.sub(r'\s*(?:\[dot\]|\(dot\))\s*', '.', decoded, flags=re.I)
    found = {}

    def add(kind, value, evidence):
        if not value:
            return
        key = kind, value
        if key not in found:
            found[key] = {'kind': kind, 'value': value, 'contact_evidence': evidence[:500]}

    def number(kind, raw, evidence):
        normalized = normalize_phone(raw)
        if normalized:
            add(kind, normalized, evidence)
            if kind == 'whatsapp_number':
                add('phone', normalized, evidence + ' (also a published phone number)')

    def link(raw):
        href = html.unescape(raw).strip()
        if href.lower().startswith(('www.', 'linkedin.com/', 'wa.me/', 'api.whatsapp.com/', 'web.whatsapp.com/', 'chat.whatsapp.com/')):
            href = 'https://' + href
        p = urlparse(href)
        host = (p.hostname or '').lower()
        if p.scheme.lower() == 'mailto':
            for m in EMAIL.finditer(unquote(p.path)):
                value = m.group().rstrip('.')
                if not value.lower().startswith(('noreply@', 'no-reply@', 'donotreply@')):
                    add('email', value.lower(), 'Explicit mailto link: ' + href)
        elif p.scheme.lower() == 'tel':
            number('phone', p.path, 'Explicit tel link: ' + href)
        elif host in ('wa.me', 'api.whatsapp.com', 'web.whatsapp.com', 'chat.whatsapp.com') or p.scheme == 'whatsapp':
            add('whatsapp', href, 'Explicit WhatsApp link: ' + href)
            raw_number = p.path.strip('/') if host == 'wa.me' else parse_qs(p.query).get('phone', [''])[0]
            if re.fullmatch(r'\+?[\d\s().-]+', raw_number or ''):
                # wa.me / send?phone international syntax publishes the calling code.
                number('whatsapp_number', '+' + raw_number.lstrip('+').replace(' ', ''), 'Number published in WhatsApp link: ' + href)
        elif (host == 'linkedin.com' or host.endswith('.linkedin.com')):
            path = unquote(p.path)
            m = re.match(r'/in/([^/?#\s]+)', path, re.I)
            if m:
                add('linkedin', 'https://www.linkedin.com/in/' + m.group(1), 'Explicit personal profile: ' + href)
        # A redirect's explicitly encoded target is source evidence, not a guess.
        for key in ('url', 'target', 'redirect'):
            for target in parse_qs(p.query).get(key, []):
                if re.match(r'https?://(?:[\w-]+\.)?linkedin\.com/in/', target, re.I):
                    link(target.split('?', 1)[0])

    for m in EMAIL.finditer(decoded):
        value = m.group().rstrip('.')
        if value.lower().startswith(('noreply@', 'no-reply@', 'donotreply@')) or value.lower().endswith(('.png', '.jpg', '.svg', '.webp')):
            continue
        add('email', value.lower(), decoded[max(0, m.start()-120):m.end()+180])
    for m in PHONE.finditer(text):
        number('phone', m.group(), text[max(0, m.start()-120):m.end()+180])
    for m in re.finditer(r'\b(whats\s*app|phone|telephone|mobile|contact\s*(?:no\.?|number))\s*(?:number|no\.?|text|me|business)?\s*[:\-]?\s*((?:\+|00)?\d[\d ().\-\u00a0]{6,24}\d)', text, re.I):
        kind = 'whatsapp_number' if re.match(r'whats', m.group(1), re.I) else 'phone'
        number(kind, m.group(2), 'Explicit number label: ' + m.group())
    links_in_text = re.findall(r'(?:(?:https?://)?(?:www\.|[\w-]+\.)?linkedin\.com/in/[^\s<>"\')]+|(?:https?://)?(?:wa\.me|api\.whatsapp\.com|web\.whatsapp\.com|chat\.whatsapp\.com)/[^\s<>"\')]+)', text, re.I)
    for href in page.links + links_in_text:
        link(href.rstrip('.,;'))
    # Public schema.org JSON-LD is another explicit publishing format for contacts.
    def structured(node):
        if isinstance(node, list):
            for child in node: structured(child)
        elif isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str):
                    if key.lower() in ('telephone', 'phone', 'faxnumber'):
                        if key.lower() != 'faxnumber': number('phone', value, 'Public JSON-LD telephone: ' + value)
                    elif key.lower() == 'email':
                        for m in EMAIL.finditer(value): add('email', m.group().lower(), 'Public JSON-LD email: ' + value)
                    elif key.lower() in ('url', 'sameas'):
                        link(value)
                elif key.lower() == 'sameas' and isinstance(value, list):
                    for target in value:
                        if isinstance(target, str): link(target)
                else: structured(value)
    for m in re.finditer(r'<script\b[^>]*type\s*=\s*[\'\"]application/ld\+json[\'\"][^>]*>(.*?)</script\s*>', source, re.I | re.S):
        try: structured(json.loads(m.group(1)))
        except (ValueError, RecursionError): pass
    return text, list(found.values())


def coordinate_summary(pages, records):
    """Group by one author in one topic; never join identities across unrelated sites."""
    groups = {}
    for page in pages:
        if any(x in page.get('flags', []) for x in ('seller_advertisement', 'excluded_territory_mention_review', 'possible_filled_or_closed_notice', 'older_than_age_limit')):
            continue
        url = page['url']
        match = re.match(r'(https?://[^/]+/t/\d+)(?:/\d+)?$', url)
        key = (match.group(1) if match else url, page['author'])
        group = groups.setdefault(key, {'source_url': key[0], 'author': key[1], 'title': page['title'],
                                       'ownership': page['ownership'], 'status': 'review_required',
                                       'email': [], 'linkedin': [], 'phone': [], 'whatsapp_number': [], 'whatsapp_links': []})
        for row in records:
            if row['source_url'] == url and row['author'] == page['author']:
                field = 'whatsapp_links' if row['kind'] == 'whatsapp' else row['kind']
                entry = {'value': row['value'], 'source_url': url, 'evidence': row['contact_evidence']}
                if entry not in group[field]: group[field].append(entry)
    for group in groups.values():
        for field in ('email', 'linkedin', 'phone', 'whatsapp_number'):
            group[field + '_status'] = 'published_candidate' if group[field] else 'not_found_in_scanned_content'
        group['coordinate_count'] = sum(bool(group[x]) for x in ('email', 'linkedin', 'phone', 'whatsapp_number'))
    return list(groups.values())


def records_from_topic(web, url, max_batches):
    p = urlparse(url)
    match = re.search(r'/t/(?:[^/]+/)?(\d+)', p.path)
    root = f'{p.scheme}://{p.netloc}'
    data = web.json(root + '/t/' + match.group(1) + '.json')
    stream = data['post_stream']
    posts = stream.get('posts', [])
    original = next((x for x in posts if x.get('post_number') == 1), None)
    if not original:
        raise ValueError('Original author post not available')
    # Only original author replies can provide buyer contacts. Never applicants.
    author = original['username']
    known = {x['id'] for x in posts}
    rest = [x for x in stream.get('stream', []) if x not in known]
    for offset in range(0, min(len(rest), max_batches * 20), 20):
        query = urlencode([('post_ids[]', x) for x in rest[offset:offset+20]])
        batch = web.json(root + '/t/' + str(data['id']) + '/posts.json?' + query)
        posts.extend(batch.get('post_stream', {}).get('posts', []))
    original_text = Page(original.get('cooked', '')).text
    title = data.get('title', '')
    buyer_text = '\n'.join(Page(x.get('cooked', '')).text for x in posts if x.get('username') == author)
    for post in posts:
        if post.get('username') == author:
            yield {'url': root + '/t/' + str(data['id']) + '/' + str(post['post_number']), 'title': title,
                   'author': author, 'created_at': data.get('created_at'), 'updated_at': data.get('last_posted_at'),
                   'topic_closed': data.get('closed'), 'buyer_text': title + '\n' + original_text,
                   'status_text': buyer_text, 'html': post.get('cooked', ''),
                   'ownership': 'topic_author_post_review_required',
                   'coverage': 'all posts loaded' if len({x['id'] for x in posts}) >= len(stream.get('stream', [])) else 'partial thread; later updates may be missing'}


def date_age(value):
    try:
        return (utcnow() - datetime.fromisoformat(value.replace('Z', '+00:00'))).total_seconds() / 86400
    except (ValueError, TypeError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--url', action='append', default=[], help='Public buyer brief URL (repeatable)')
    ap.add_argument('--urls-file', type=Path, help='One URL per line; # comments allowed')
    ap.add_argument('--discover', action='store_true', help='Discover recent n8n Jobs topics through public JSON')
    ap.add_argument('--search', action='store_true', help='Search using BRAVE_SEARCH_API_KEY; optional paid external API')
    ap.add_argument('--query', action='append', help='Custom search query (repeatable)')
    ap.add_argument('--days', type=int, default=14, help='Maximum known topic age in days; default 14')
    ap.add_argument('--max-pages', type=int, default=15)
    ap.add_argument('--max-batches', type=int, default=2, help='Extra forum batches, 20 posts each; default 2')
    ap.add_argument('--delay', type=float, default=1.5)
    ap.add_argument('--timezone', help='Known buyer timezone for this entire batch, e.g. Asia/Singapore; never inferred')
    ap.add_argument('--suppress-file', type=Path, help='JSON list of contact values previously sent or excluded')
    ap.add_argument('--out', type=Path, default=Path(__file__).parent / 'output')
    args = ap.parse_args()
    if not (args.url or args.urls_file or args.discover or args.search):
        ap.error('Provide --url, --urls-file, --discover or --search')
    if args.max_pages < 1 or args.days < 1 or args.max_batches < 0 or args.delay < 0:
        ap.error('Invalid limits')
    if args.timezone:
        try:
            local = utcnow().astimezone(ZoneInfo(args.timezone))
        except ZoneInfoNotFoundError:
            ap.error('Timezone database unavailable/unknown timezone; install tzdata or omit --timezone')
        local_time, workday = local.isoformat(), local.weekday() < 5 and 9 <= local.hour < 18
    else:
        local_time, workday = '', None
    suppressed = {x.lower() for x in json.loads(args.suppress_file.read_text('utf-8-sig'))} if args.suppress_file else set()
    args.out.mkdir(parents=True, exist_ok=True)
    run = args.out / utcnow().strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir()
    web = Web(run, args.delay)
    urls = list(args.url)
    errors, candidates, pages = [], [], []
    if args.urls_file:
        urls += [x.strip() for x in args.urls_file.read_text('utf-8-sig').splitlines() if x.strip() and not x.lstrip().startswith('#')]
    if args.discover:
        try:
            data = web.json('https://community.n8n.io/c/jobs/13.json')
            for topic in data.get('topic_list', {}).get('topics', []):
                title = topic.get('title', '')
                age = date_age(topic.get('created_at'))
                if age is not None and age <= args.days and BUYER.search(title) and not SELLER.search(title) and not EXCLUDED.search(title):
                    urls.append('https://community.n8n.io/t/' + str(topic['id']))
        except Exception as e:
            errors.append({'stage': 'discovery', 'error': str(e)})
    if args.search:
        token = os.environ.get('BRAVE_SEARCH_API_KEY')
        if not token:
            errors.append({'stage': 'search', 'error': 'BRAVE_SEARCH_API_KEY is not set; other inputs still processed'})
        else:
            for query in args.query or QUERIES:
                try:
                    endpoint = 'https://api.search.brave.com/res/v1/web/search?' + urlencode({'q': query, 'count': 10, 'freshness': 'pw'})
                    data = web.json(endpoint, api=True, headers={'X-Subscription-Token': token})
                    for result in data.get('web', {}).get('results', []):
                        if not EXCLUDED.search(result.get('title', '') + ' ' + result.get('description', '')):
                            urls.append(result['url'])
                except Exception as e:
                    errors.append({'stage': 'search', 'query': query, 'error': str(e)})
    for url in list(dict.fromkeys(urls))[:args.max_pages]:
        try:
            p = urlparse(url)
            if p.hostname in ('community.n8n.io', 'community.make.com') and '/t/' in p.path:
                documents = list(records_from_topic(web, url, args.max_batches))
            else:
                body = web.get(url)
                text = Page(body).text
                documents = [{'url': url, 'title': text[:160], 'author': '', 'created_at': None,
                              'buyer_text': text, 'status_text': text, 'html': body,
                              'ownership': 'page_contacts_unattributed_review_required', 'coverage': 'HTML only; no login or JavaScript rendering'}]
            for doc in documents:
                text, found = contacts(doc.pop('html'))
                buyer = doc['buyer_text']
                age = date_age(doc.get('created_at'))
                reasons = []
                if not BUYER.search(buyer) or not TECH.search(buyer): reasons.append('buyer_or_technical_fit_unconfirmed')
                if SELLER.search(doc['title']): reasons.append('seller_advertisement')
                if EXCLUDED.search(buyer): reasons.append('excluded_territory_mention_review')
                if CLOSED.search(doc['status_text']): reasons.append('possible_filled_or_closed_notice')
                if age is not None and age > args.days: reasons.append('older_than_age_limit')
                if age is None: reasons.append('publication_date_unknown')
                doc['flags'] = reasons
                doc['contacts_found'] = len(found)
                pages.append({k: v for k, v in doc.items() if k not in ('buyer_text', 'status_text')})
                # Reject definite stale/seller/territory/closed cases, preserve page audit.
                if any(x in reasons for x in ('seller_advertisement', 'excluded_territory_mention_review', 'possible_filled_or_closed_notice', 'older_than_age_limit')):
                    continue
                for item in found:
                    if item['value'].lower() in suppressed: continue
                    candidates.append({**item, 'source_url': doc['url'], 'title': doc['title'],
                                       'author': doc['author'], 'ownership': doc['ownership'],
                                       'created_at': doc.get('created_at'), 'capture_utc': utcnow().isoformat(),
                                       'buyer_need_excerpt': buyer[:1200], 'review_flags': ';'.join(reasons),
                                       'buyer_timezone_supplied': args.timezone or '', 'buyer_local_time': local_time,
                                       'within_weekday_9_to_18': workday, 'status': 'review_required',
                                       'source_coverage': doc['coverage']})
        except Exception as e:
            errors.append({'stage': 'fetch', 'url': url, 'error': str(e)})
    # Persistent evidence-level dedup. Same contact in another buyer post remains attributable.
    db = sqlite3.connect(args.out / 'contacts.sqlite3')
    db.execute('CREATE TABLE IF NOT EXISTS contacts (identity TEXT PRIMARY KEY, record TEXT NOT NULL)')
    for row in candidates:
        key = hashlib.sha256((row['kind'] + '\n' + row['value'] + '\n' + row['source_url']).encode()).hexdigest()
        db.execute('INSERT OR REPLACE INTO contacts VALUES (?, ?)', (key, json.dumps(row, ensure_ascii=False)))
    db.commit(); db.close()
    unique = {(x['kind'], x['value'], x['source_url']): x for x in candidates}
    records = list(unique.values())
    summary = coordinate_summary(pages, records)
    (run / 'leads.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    summary_fields = ['source_url', 'author', 'title', 'ownership', 'status', 'coordinate_count',
                      'email', 'email_status', 'linkedin', 'linkedin_status', 'phone', 'phone_status',
                      'whatsapp_number', 'whatsapp_number_status', 'whatsapp_links']
    with (run / 'leads.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for lead in summary:
            flat = {k: (' | '.join(dict.fromkeys(x['value'] for x in v)) if isinstance(v, list) else v) for k, v in lead.items()}
            writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v) for k, v in flat.items()})
    (run / 'contacts.json').write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding='utf-8')
    if records:
        with (run / 'contacts.csv').open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            # Prevent spreadsheet formula execution from untrusted website data.
            writer.writerows({k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v) for k, v in row.items()} for row in records)
    totals = {kind: len({r['value'] for r in records if r['kind'] == kind}) for kind in ('email', 'linkedin', 'phone', 'whatsapp_number', 'whatsapp')}
    audit = {'capture_utc': utcnow().isoformat(), 'pages': pages, 'errors': errors, 'receipts': web.receipts,
             'unique_values_by_coordinate': totals,
             'candidate_count': len(records), 'note': 'Published contact candidates only; ownership, business purpose, freshness and deliverability require review. No messages sent.'}
    (run / 'audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'output': str(run), 'contact_candidates': len(records), 'coordinates': totals, 'pages_inspected': len(pages), 'errors': len(errors)}, indent=2))
    return 0 if pages else 1


if __name__ == '__main__':
    sys.exit(main())

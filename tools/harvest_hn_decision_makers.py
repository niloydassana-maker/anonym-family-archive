import urllib.request
import json
import re
import html
from datetime import datetime, timezone

def fetch_hn_comments(story_id):
    leads = []
    page = 0
    while True:
        url = f'https://hn.algolia.com/api/v1/search_by_date?tags=comment,story_{story_id}&hitsPerPage=100&page={page}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f'Error fetching page {page} for story {story_id}: {e}')
            break
            
        hits = data.get('hits', [])
        if not hits:
            break
            
        for h in hits:
            # We ONLY want top-level comments by the actual hiring company/founder
            if h.get('parent_id') != story_id:
                continue
            text = html.unescape(h.get('comment_text') or '')
            
            # Filter out job seekers who mistakenly post in 'Who is hiring'
            # Job seeker keywords
            if re.search(r'\b(SEEKING WORK|looking for (?:a |new )?job|looking for work|I am a|my resume|hire me)\b', text[:200], re.I):
                continue
                
            # Extract emails
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
            clean_emails = []
            for e in emails:
                e_clean = e.strip('.').lower()
                if e_clean.endswith(('.png', '.jpg', '.gif', '.svg', '.jpeg')):
                    continue
                if 'example.com' in e_clean or 'ycombinator.com' in e_clean:
                    continue
                if e_clean not in clean_emails:
                    clean_emails.append(e_clean)
                    
            if not clean_emails:
                continue
                
            # Check for excluded regions (Kolkata/West Bengal)
            if re.search(r'\b(kolkata|calcutta|west bengal)\b', text, re.I):
                continue
                
            # Parse header/company info
            lines = [l.strip() for l in re.sub(r'<[^>]+>', '\n', text).split('\n') if l.strip()]
            header = lines[0] if lines else ''
            
            # Check for website URLs
            urls = re.findall(r'https?://[^\s<>"\']+', text)
            clean_urls = []
            for u in urls:
                u_clean = u.rstrip('.,;)')
                if not any(x in u_clean for x in ['ycombinator', 'github.com', 'linkedin.com', 'twitter.com', 'x.com']):
                    clean_urls.append(u_clean)
            website = clean_urls[0] if clean_urls else ''
            
            # Check for LinkedIn profiles in text
            linkedin_urls = re.findall(r'https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_-]+', text)
            
            # Extract technical needs
            tech_matches = re.findall(r'\b(Python|FastAPI|PostgreSQL|Postgres|AI|LLM|Agents?|RAG|LangChain|LangGraph|n8n|Make\.com|Camunda|BPMN|Docker|Kubernetes|AWS|GCP|Azure|ETL|Data Pipeline|Distributed Systems|Rust|Go|Golang|TypeScript|React)\b', text, re.I)
            unique_tech = list(dict.fromkeys([t.title() for t in tech_matches]))
            
            # Detect location/remote
            is_remote = bool(re.search(r'\b(remote|worldwide|anywhere|wfh)\b', text, re.I))
            
            leads.append({
                'story_id': story_id,
                'comment_id': h.get('objectID'),
                'author': h.get('author'),
                'created_at': h.get('created_at'),
                'header': header,
                'emails': clean_emails,
                'website': website,
                'linkedin_urls': list(set(linkedin_urls)),
                'technologies': unique_tech,
                'is_remote': is_remote,
                'full_text': re.sub(r'<[^>]+>', ' ', text).strip()
            })
            
        if page + 1 >= data.get('nbPages', 1):
            break
        page += 1
        
    return leads

if __name__ == '__main__':
    print('Harvesting HN October 2026 (49922569)...')
    oct_leads = fetch_hn_comments(49922569)
    print(f'October leads: {len(oct_leads)}')
    
    print('Harvesting HN September 2026 (49522897)...')
    sep_leads = fetch_hn_comments(49522897)
    print(f'September leads: {len(sep_leads)}')
    
    all_leads = oct_leads + sep_leads
    with open(r'D:\anonym\deliverables\hn_decision_maker_leads.json', 'w', encoding='utf-8') as f:
        json.dump(all_leads, f, indent=2)
    print(f'Total HN leads saved: {len(all_leads)}')

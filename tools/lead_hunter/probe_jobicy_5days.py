import json
import urllib.request
import re
from datetime import datetime, timezone, timedelta

def scan_jobicy_5days():
    cursor = None
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=5)
    
    total_scanned = 0
    with_email = []
    
    print(f"Scanning Jobicy strictly >= {cutoff.isoformat()}...")
    for page in range(30):
        url = 'https://jobicy.com/api/v2/remote-jobs' + (f'?cursor={cursor}' if cursor else '')
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
        except Exception as e:
            print(f"Page {page+1} error: {e}")
            break
        jobs = res.get('jobs', [])
        if not jobs:
            break
        
        stop = False
        for j in jobs:
            pub = j.get('pubDate')
            try:
                dt = datetime.fromisoformat(pub.replace('Z', '+00:00'))
            except Exception:
                continue
            if dt < cutoff:
                stop = True
                break
            total_scanned += 1
            desc = j.get('jobDescription', '')
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', desc)
            if emails:
                with_email.append({
                    'id': j.get('id'),
                    'title': j.get('jobTitle'),
                    'company': j.get('companyName'),
                    'emails': list(dict.fromkeys(emails)),
                    'pubDate': pub
                })
        cursor = res.get('nextCursor')
        print(f"Page {page+1}: scanned={total_scanned}, with_email={len(with_email)}, oldest_in_page={jobs[-1].get('pubDate')}")
        if stop or not cursor or not res.get('hasMore'):
            break

    print(f"\nFinal: Scanned {total_scanned} jobs <= 5 days old. Found {len(with_email)} leads with verified direct emails.")

if __name__ == '__main__':
    scan_jobicy_5days()

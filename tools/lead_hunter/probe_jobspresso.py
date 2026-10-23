import urllib.request
import json
import re
from datetime import datetime, timezone, timedelta

def scan_jobspresso():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=5)
    total_leads = []
    
    for page in range(1, 10):
        url = f'https://jobspresso.co/wp-json/wp/v2/job-listings?per_page=50&page={page}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
        except Exception as e:
            print(f"Jobspresso page {page} end/error: {e}")
            break
        if not res:
            break
        stop = False
        for j in res:
            dt = datetime.fromisoformat(j['date']).replace(tzinfo=timezone.utc)
            if dt < cutoff:
                stop = True
                break
            content = j.get('content', {}).get('rendered', '')
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
            if emails:
                total_leads.append({
                    'id': j['id'],
                    'title': j.get('title', {}).get('rendered'),
                    'emails': emails,
                    'date': j['date']
                })
        print(f"Page {page}: total leads={len(total_leads)}, last date={res[-1]['date']}")
        if stop:
            break
    print(f"Jobspresso <= 5 days leads with email: {len(total_leads)}")

if __name__ == '__main__':
    scan_jobspresso()

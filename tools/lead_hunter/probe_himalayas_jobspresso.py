import urllib.request
import json
import re
from datetime import datetime, timezone, timedelta

def test_himalayas():
    url = 'https://himalayas.app/jobs/api?limit=50'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    jobs = res.get('jobs', [])
    print(f"Himalayas returned {len(jobs)} jobs. Total count: {res.get('totalCount')}")
    if jobs:
        print("Sample Himalayas keys:", list(jobs[0].keys()))
        print("Sample pubDate:", jobs[0].get('pubDate'))
        # Check emails
        with_email = [j for j in jobs if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', j.get('description', ''))]
        print(f"Himalayas jobs with email: {len(with_email)}")

def test_jobspresso():
    url = 'https://jobspresso.co/wp-json/wp/v2/job-listings?per_page=50'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    print(f"Jobspresso returned {len(res)} jobs.")
    if res:
        print("Sample Jobspresso keys:", list(res[0].keys()))
        print("Sample date:", res[0].get('date'))
        with_email = [j for j in res if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', j.get('content', {}).get('rendered', ''))]
        print(f"Jobspresso jobs with email: {len(with_email)}")

if __name__ == '__main__':
    test_himalayas()
    test_jobspresso()

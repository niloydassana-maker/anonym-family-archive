import urllib.request
import json

endpoints = [
    ('himalayas', 'https://himalayas.app/jobs/api?limit=5'),
    ('jobspresso', 'https://jobspresso.co/wp-json/wp/v2/job-listings?per_page=5'),
    ('crackeddevs', 'https://api.crackeddevs.com/api/v1/get-jobs?limit=5'),
    ('startupjobs', 'https://startup.jobs/api/jobs')
]

for name, url in endpoints:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5)
        raw = res.read().decode('utf-8', errors='ignore')
        data = json.loads(raw)
        print(name, 'Success, count/type:', len(data) if isinstance(data, list) else list(data.keys())[:5])
    except Exception as e:
        print(name, 'Error:', e)

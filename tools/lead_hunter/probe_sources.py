import os
import sys
import json
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from hunt_leads import contacts

def test_remoteok():
    url = 'https://remoteok.com/api'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    jobs = [j for j in data if isinstance(j, dict) and 'id' in j]
    stats = {}
    for j in jobs:
        text = j.get('description', '') + ' ' + j.get('company', '')
        _, items = contacts(text)
        for it in items:
            stats[it['kind']] = stats.get(it['kind'], 0) + 1
    print('RemoteOK Stats:', stats, 'Total jobs:', len(jobs))

if __name__ == '__main__':
    test_remoteok()

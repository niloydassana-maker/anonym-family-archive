import urllib.request
import json
import re

query = 'is:issue is:open "bounty" created:>2026-10-18'
url = 'https://api.github.com/search/issues?q=' + urllib.parse.quote(query) + '&per_page=10'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'})
try:
    res = urllib.request.urlopen(req, timeout=8)
    data = json.loads(res.read().decode('utf-8'))
    print('Total GitHub bounty issues (last 5d):', data.get('total_count'))
    for it in data.get('items', [])[:5]:
        print('-', it.get('title'), it.get('html_url'), it.get('created_at'))
except Exception as e:
    print('GitHub search error:', e)

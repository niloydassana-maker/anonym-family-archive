import urllib.request
import json
import time

url = 'https://hn.algolia.com/api/v1/search?tags=story,author_whoishiring&query=October%202026'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    for h in data.get('hits', []):
        print(h['title'], h['objectID'], h['created_at'])
except Exception as e:
    print('Error:', e)

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import email.utils

feeds = [
    'https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss',
    'https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss',
    'https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss',
]

now = datetime.now(timezone.utc)
cutoff = now - timedelta(days=5)

for url in feeds:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5)
        root = ET.fromstring(res.read())
        items = root.findall('.//item')
        recent = []
        for it in items:
            pub = it.find('pubDate').text
            dt = email.utils.parsedate_to_datetime(pub)
            if dt >= cutoff:
                recent.append(it)
        print(url.split('/')[-1], f"Total: {len(items)}, Recent (<=5d): {len(recent)}")
    except Exception as e:
        print(url.split('/')[-1], 'Error:', e)

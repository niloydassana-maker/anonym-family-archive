import urllib.request
import xml.etree.ElementTree as ET
import re

url = 'https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
root = ET.fromstring(urllib.request.urlopen(req, timeout=5).read())
items = root.findall('.//item')
with_email = []
for it in items:
    desc = it.find('description').text or ''
    m = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', desc)
    if m:
        with_email.append((it.find('title').text, m))
print('WWR full-stack with email:', len(with_email), with_email[:3])

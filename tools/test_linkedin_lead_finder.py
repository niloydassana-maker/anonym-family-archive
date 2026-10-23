import urllib.request
import json
import urllib.parse
import re

def find_linkedin(name, company):
    query = f'site:linkedin.com/in/ "{name}" "{company}"'
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html_text = resp.read().decode('utf-8', errors='ignore')
            links = re.findall(r'https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', html_text)
            clean = [l for l in links if 'duckduckgo' not in l]
            return list(set(clean))
    except Exception as e:
        return [str(e)]
    return []

if __name__ == '__main__':
    print('GovStar Nicholas Hanson:', find_linkedin('Nicholas Hanson', 'GovStar'))
    print('Typify Galen:', find_linkedin('Galen', 'Typify'))
    print('BOSS-IQ Ahmet:', find_linkedin('Ahmet', 'BOSS-IQ'))

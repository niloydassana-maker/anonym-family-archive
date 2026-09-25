import json, glob, os
seen = set(json.load(open('D:/anonym/war-log/directives/seen.json')))
all_files = [os.path.basename(f) for f in glob.glob('D:/anonym/war-log/events/*.json')]
unseen = [f for f in all_files if f not in seen and f.startswith('WEB-')]
for f in unseen:
    try:
        data = json.load(open('D:/anonym/war-log/events/'+f, encoding='utf-8', errors='ignore'))
        url = data.get('page', {}).get('url', '')
        if 'youtube.com' not in url:
            print(f, url)
    except Exception as e:
        print('Error parsing', f, e)

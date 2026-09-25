import json, glob, os
seen = set(json.load(open('D:/anonym/war-log/directives/seen.json')))
unseen = [f for f in glob.glob('D:/anonym/war-log/events/WEB-*.json') if os.path.basename(f) not in seen]
arjun_files = []
for f in unseen:
    try:
        content = open(f, encoding='utf-8', errors='ignore').read().lower()
        if 'arjun' in content:
            arjun_files.append(os.path.basename(f))
    except Exception as e:
        pass
print('Arjun files:', arjun_files)

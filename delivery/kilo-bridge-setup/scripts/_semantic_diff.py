import json
pairs = [
 (r'C:\Users\Admin\.config\opencode\opencode.jsonc', r'C:\Users\Admin\.config\opencode\opencode.jsonc.PRE-E2E-20261006.bak'),
 (r'D:\anonym\opencode.json', r'D:\anonym\opencode.json.PRE-E2E-20261006.bak'),
]

def flat(o, p='', out=None):
    out = {} if out is None else out
    if isinstance(o, dict):
        for k, v in o.items(): flat(v, p+'.'+str(k), out)
    else:
        out[p] = json.dumps(o, sort_keys=True)
    return out

for cur, bak in pairs:
    a = flat(json.load(open(cur, encoding='utf-8')))
    b = flat(json.load(open(bak, encoding='utf-8')))
    removed = sorted(set(b) - set(a))
    added   = sorted(set(a) - set(b))
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    print('==', cur)
    print('  removed keys:', len(removed))
    for k in removed: print('    -', k)
    print('  added keys:', len(added))
    for k in added: print('    +', k)
    print('  value-changed keys:', len(changed))
    for k in changed:
        print('    *', k, ' from', b[k], '->', a[k])

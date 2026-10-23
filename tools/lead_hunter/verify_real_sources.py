"""Regression checks against unmodified, genuine archived public forum responses.

Usage: python verify_real_sources.py --archive D:/anonym/war-log/audits/cash-deadline-20261023
Applicant posts are parser test material, not newly certified buyer leads.
No generated payloads, mocked network, or invented contact fixtures are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
from hunt_leads import contacts


def cooked_posts(node):
    if isinstance(node, dict):
        if isinstance(node.get('cooked'), str):
            yield node['cooked']
        for key, value in node.items():
            if key != 'cooked':
                yield from cooked_posts(value)
    elif isinstance(node, list):
        for value in node:
            yield from cooked_posts(value)
    elif isinstance(node, str) and node.lstrip().startswith(('{', '[')):
        try:
            yield from cooked_posts(json.loads(node))
        except ValueError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    args = parser.parse_args()
    values = {}
    receipts = []
    for path in sorted(args.archive.glob('lead-*.json')):
        raw = path.read_bytes()
        data = json.loads(raw.decode('utf-8-sig'))
        observed = []
        for body in cooked_posts(data):
            _, items = contacts(body)
            pairs = {(item['kind'], item['value']) for item in items}
            for item in items:
                values.setdefault(item['kind'], set()).add(item['value'])
                observed.append(item['kind'])
                if item['kind'] == 'whatsapp_number':
                    assert ('phone', item['value']) in pairs, 'Published WhatsApp number missing from phone coordinate'
                if item['kind'] == 'linkedin':
                    assert item['value'].startswith('https://www.linkedin.com/in/')
        if observed:
            receipts.append({'source_file': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
                             'observed_types': sorted(set(observed))})
    for kind in ('email', 'linkedin', 'phone', 'whatsapp_number'):
        assert values.get(kind), 'No real archived evidence for ' + kind
    # Manually inspected publication: explicit spaced WhatsApp label in this archive.
    assert '+2347087876974' in values['whatsapp_number'], 'Spaced WhatsApp number regression'
    report = {'result': 'PASS', 'unique_values_by_type': {k: len(v) for k, v in values.items()},
              'sources': receipts, 'scope': 'Parser regression on genuine archived posts, including applicants; not buyer verification or a live job-status check.'}
    out = Path(__file__).parent / 'output' / 'four_coordinate_verification'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'regression.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'sources'}, indent=2))


if __name__ == '__main__':
    main()

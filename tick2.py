import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST).isoformat()

with open(r'D:\anonym\war-log\linkedin-lane.json', 'r') as f:
    log = json.load(f)

def post_to_bank(action, evidence):
    try:
        params = urllib.parse.urlencode({'body': f'KILO|{action}|{evidence}|{now}'})
        url = f'http://127.0.0.1:8777/say?token=GOLD24&{params}'
        resp = urllib.request.urlopen(url, timeout=5)
        print(f'  BANK POST OK: {action}')
    except Exception as e:
        print(f'  BANK POST FAIL: {action} - {e}')

evidence1 = 'feed_empty_no_premium_requests'
log['action_log'].append({'t': now, 'client': '', 'action': 'service_marketplace_sweep', 'evidence': evidence1, 'bank_seq': 0})
post_to_bank('service_marketplace_sweep', evidence1)

evidence2 = 'no_actionable_items'
log['action_log'].append({'t': now, 'client': '', 'action': 'notifications_check', 'evidence': evidence2, 'bank_seq': 0})
post_to_bank('notifications_check', evidence2)

evidence3 = 'invitation_manager_no_new_invites'
log['action_log'].append({'t': now, 'client': '', 'action': 'network_triage', 'evidence': evidence3, 'bank_seq': 0})
post_to_bank('network_triage', evidence3)

evidence4 = 'ai_production_reality_comment'
log['action_log'].append({'t': now, 'client': '', 'action': 'authority_comment_attempt', 'evidence': evidence4, 'bank_seq': 0})
post_to_bank('authority_comment_attempt', evidence4)

evidence5 = 'uia_active_cdp_loggedout_feedwatch_dead_awareness_live'
log['action_log'].append({'t': now, 'client': '', 'action': 'health_check', 'evidence': evidence5, 'bank_seq': 0})
post_to_bank('health_check', evidence5)

log['last_tick'] = now
log['stale']['awareness'] = now

with open(r'D:\anonym\war-log\linkedin-lane.json', 'w') as f:
    json.dump(log, f, indent=2)

print('TICK COMPLETE:', now)
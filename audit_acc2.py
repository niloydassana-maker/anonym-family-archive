import requests
import json

sid = 'AC0df25d3d89c42672d99f71501b0bda10'
token = 'd8a70dcdf44b79d35c4ff9ef2366221c'

# 1. Calls
r_calls = requests.get(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json', auth=(sid, token))
calls = r_calls.json().get('calls', [])
print(f'Total Calls on Account 2: {len(calls)}')
for c in calls[:10]:
    print(f" - Call: {c.get('sid')} | To: {c.get('to')} | Status: {c.get('status')} | Duration: {c.get('duration')}s | Price: {c.get('price')} {c.get('price_unit')}")

# 2. Phone Numbers
r_nums = requests.get(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json', auth=(sid, token))
nums = r_nums.json().get('incoming_phone_numbers', [])
print(f'\nTotal Phone Numbers on Account 2: {len(nums)}')
for n in nums:
    print(f" - Number: {n.get('phone_number')} | Created: {n.get('date_created')}")

# 3. Usage Records
r_usage = requests.get(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Usage/Records.json', auth=(sid, token))
records = r_usage.json().get('usage_records', [])
print('\nUsage Records with Price != 0:')
found = False
for u in records:
    price = float(u.get('price') or 0)
    if price != 0:
        found = True
        print(f" - Category: {u.get('category')} | Usage: {u.get('usage')} {u.get('usage_unit')} | Price: ${price} {u.get('price_unit')}")
if not found:
    print(" - No usage records with price != 0 found.")

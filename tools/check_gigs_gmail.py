import imaplib, email
from pathlib import Path

vault = Path(r'D:\anonym\vault\gmail_apppw.txt')
app_pw = vault.read_text(encoding='utf-8').strip().replace(' ', '')
M = imaplib.IMAP4_SSL('imap.gmail.com')
M.login('isearch.xsolve@gmail.com', app_pw)
M.select('INBOX')

for q in ['mercor', 'ethos', 'terac', 'outlier', 'alignerr']:
    status, msgs = M.search(None, f'TEXT "{q}"')
    count = len(msgs[0].split()) if status == 'OK' and msgs[0] else 0
    print(f'Query [{q}]: {count} emails found')
    if count > 0:
        for mid in msgs[0].split()[-3:]:
            _, data = M.fetch(mid, '(BODY[HEADER.FIELDS (SUBJECT DATE FROM)])')
            raw_header = data[0][1].decode('utf-8', errors='ignore').strip()
            print('  ->', raw_header.replace('\r\n', ' | '))

M.close()
M.logout()

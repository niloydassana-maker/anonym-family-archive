import imaplib, email, sys, io
from bs4 import BeautifulSoup
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

vault = Path(r'D:\anonym\vault\gmail_apppw.txt')
app_pw = vault.read_text(encoding='utf-8').strip().replace(' ', '')
M = imaplib.IMAP4_SSL('imap.gmail.com')
M.login('isearch.xsolve@gmail.com', app_pw)
M.select('INBOX')

status, msgs = M.search(None, 'SINCE "15-Oct-2026"')
if status == 'OK' and msgs[0]:
    ids = msgs[0].split()
    print('Total emails since Oct 15:', len(ids))
    human_emails = []
    for mid in ids:
        _, data = M.fetch(mid, '(BODY[HEADER.FIELDS (SUBJECT DATE FROM)])')
        raw = data[0][1].decode('utf-8', errors='ignore').strip()
        sender = ''
        subj = ''
        date_str = ''
        for line in raw.splitlines():
            if line.lower().startswith('from:'): sender = line
            elif line.lower().startswith('subject:'): subj = line
            elif line.lower().startswith('date:'): date_str = line
            
        # Filter out obvious automated bulk senders
        sender_lower = sender.lower()
        if any(x in sender_lower for x in [
            'noreply', 'no-reply', 'linkedin', 'naukri', 'foundit', 'indeed', 
            'google', 'newsletter', 'jobalert', 'digest', 'notifications', 
            'beehiiv', 'mail delivery', 'security', 'kotak', 'axis'
        ]):
            continue
            
        print('-----------------------------------------')
        print(f'{mid.decode()} | {date_str}')
        print(sender)
        print(subj)

M.close()
M.logout()

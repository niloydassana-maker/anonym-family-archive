import imaplib, email, sys, io
from bs4 import BeautifulSoup
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

vault = Path(r'D:\anonym\vault\gmail_apppw.txt')
app_pw = vault.read_text(encoding='utf-8').strip().replace(' ', '')
M = imaplib.IMAP4_SSL('imap.gmail.com')
M.login('isearch.xsolve@gmail.com', app_pw)
M.select('INBOX')

status, msgs = M.search(None, 'TEXT "ethos"')
if status == 'OK' and msgs[0]:
    ids = msgs[0].split()
    for mid in ids[-10:]:
        _, data = M.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        subj = str(msg['Subject'])
        sender = str(msg['From'])
        date_str = str(msg['Date'])
        if any(x in subj.lower() or x in sender.lower() for x in ['ethos', 'askethos']):
            print('=========================================')
            print(f'MID: {mid.decode()} | Date: {date_str}')
            print(f'Subject: {subj}')
            print(f'From: {sender}')
            html_body = ''
            for part in msg.walk():
                if part.get_content_type() in ['text/html', 'text/plain']:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body = payload.decode('utf-8', errors='replace')
                        break
            if html_body:
                soup = BeautifulSoup(html_body, 'html.parser')
                text = soup.get_text().strip()
                print('Snippet:', text[:1000].replace('\n', ' '))

M.close()
M.logout()

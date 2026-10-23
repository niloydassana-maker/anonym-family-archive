import imaplib, email, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from bs4 import BeautifulSoup
from pathlib import Path

vault = Path(r'D:\anonym\vault\gmail_apppw.txt')
app_pw = vault.read_text(encoding='utf-8').strip().replace(' ', '')
M = imaplib.IMAP4_SSL('imap.gmail.com')
M.login('isearch.xsolve@gmail.com', app_pw)
M.select('INBOX')

status, msgs = M.search(None, '(FROM "hannah.cook@veracyte.com")')
if status == 'OK' and msgs[0]:
    mid = msgs[0].split()[-1]
    _, data = M.fetch(mid, '(RFC822)')
    msg = email.message_from_bytes(data[0][1])
    print('Subject:', msg['Subject'])
    print('From:', msg['From'])
    print('Date:', msg['Date'])
    html_body = ''
    for part in msg.walk():
        if part.get_content_type() in ['text/html', 'text/plain']:
            payload = part.get_payload(decode=True)
            if payload:
                html_body = payload.decode('utf-8', errors='replace')
                break
    if html_body:
        soup = BeautifulSoup(html_body, 'html.parser')
        print('Body:', soup.get_text()[:1200].replace('\n', ' '))

M.close()
M.logout()

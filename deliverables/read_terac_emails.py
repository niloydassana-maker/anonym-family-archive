"""Search Gmail for Terac emails using IMAP via the Gmail App Password."""
import imaplib, email, re
from pathlib import Path
from email.header import decode_header

VAULT = Path(r"D:\anonym\vault\gmail_apppw.txt")
ME = "isearch.xsolve@gmail.com"

def decode_str(s):
    if s is None: return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)

def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return body.strip()

pw = VAULT.read_text(encoding="utf-8").strip()
pw = re.sub(r"\s+", "", pw)

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(ME, pw)
mail.select("inbox")

# Search for Terac emails
status, data = mail.search(None, '(FROM "terac")')
ids = data[0].split() if data[0] else []
print(f"Terac emails found in inbox: {len(ids)}")

# Also search all mail
mail.select('"[Gmail]/All Mail"')
status2, data2 = mail.search(None, '(FROM "terac")')
ids2 = data2[0].split() if data2[0] else []
print(f"Terac emails found in All Mail: {len(ids2)}")

all_ids = list(set(ids + ids2))
print(f"Total unique Terac emails: {len(all_ids)}")

for eid in all_ids[-10:]:  # last 10
    try:
        _, msg_data = mail.fetch(eid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subject = decode_str(msg.get("Subject", ""))
        sender = decode_str(msg.get("From", ""))
        date = msg.get("Date", "")
        body = get_body(msg)
        print(f"\n{'='*60}")
        print(f"FROM: {sender}")
        print(f"SUBJECT: {subject}")
        print(f"DATE: {date}")
        print(f"BODY:\n{body[:2000]}")
    except Exception as e:
        print(f"Error reading email {eid}: {e}")

# Also search for sumsub
mail.select('"[Gmail]/All Mail"')
status3, data3 = mail.search(None, '(FROM "sumsub")')
ids3 = data3[0].split() if data3[0] else []
print(f"\nSumsub emails found: {len(ids3)}")
for eid in ids3[-3:]:
    try:
        _, msg_data = mail.fetch(eid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subject = decode_str(msg.get("Subject", ""))
        sender = decode_str(msg.get("From", ""))
        date = msg.get("Date", "")
        body = get_body(msg)
        print(f"\n{'='*60}")
        print(f"FROM: {sender}")
        print(f"SUBJECT: {subject}")
        print(f"DATE: {date}")
        print(f"BODY:\n{body[:2000]}")
    except Exception as e:
        print(f"Error: {e}")

mail.logout()

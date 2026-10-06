import sys
import os
import time
import json
import imaplib
import email
from email.header import decode_header
import subprocess

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def eval_js(client, code):
    c = code.strip()
    if c.startswith('() =>') and not c.endswith(')()'):
        c = f"({c})()"
    elif not (c.startswith('(') and c.endswith(')()')):
        if not c.startswith('('):
            c = f"(() => {{ {c} }})()"
            
    res = client.execute_script(c)
    if isinstance(res, dict) and 'content' in res:
        for item in res.get('content', []):
            if isinstance(item, dict) and item.get('type') == 'text':
                try:
                    return json.loads(item.get('text', '{}'))
                except Exception:
                    return item.get('text')
    return res

def fetch_latest_twilio_email():
    m = imaplib.IMAP4_SSL('imap.gmail.com')
    m.login('isearch.xsolve@gmail.com', 'bjpsndhhhiorkwni')
    m.select('inbox')
    status, data = m.search(None, '(FROM "twilio")')
    if not data or not data[0]:
        status, data = m.search(None, 'ALL')
    
    ids = data[0].split()
    if not ids:
        m.logout()
        return None
    
    # Check the last 5 emails
    for email_id in reversed(ids[-5:]):
        status, msg_data = m.fetch(email_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg['Subject'])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or 'utf-8', errors='replace')
                from_ = msg.get('From', '')
                date_ = msg.get('Date', '')
                print(f"  Found Email: From={from_} | Subject={subject} | Date={date_}")
                if "twilio" in from_.lower() or "twilio" in subject.lower() or "reset" in subject.lower():
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            cdispo = str(part.get('Content-Disposition'))
                            if ctype == 'text/html' and 'attachment' not in cdispo:
                                body = part.get_payload(decode=True).decode(errors='replace')
                                break
                            elif ctype == 'text/plain' and 'attachment' not in cdispo and not body:
                                body = part.get_payload(decode=True).decode(errors='replace')
                    else:
                        body = msg.get_payload(decode=True).decode(errors='replace')
                    m.logout()
                    return {"subject": subject, "body": body}
    m.logout()
    return None

def main():
    print("=" * 60)
    print("TWILIO PASSWORD RESET FLOW VIA GMAIL IMAP")
    print("=" * 60)
    
    # 1. Bring Chrome to front
    ps_cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.AppActivate('Chrome')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to https://www.twilio.com/login ...")
        client.navigate("https://www.twilio.com/login")
        time.sleep(4)
        
        print("[2] Filling email and clicking Continue...")
        client.fill("#email", "isearch.xsolve@gmail.com")
        time.sleep(1)
        client.click("#email-next")
        
        # Wait for login.twilio.com/u/login
        print("[3] Waiting for login.twilio.com/u/login ...")
        for i in range(12):
            url_res = eval_js(client, "() => window.location.href")
            url = url_res.get('result', '') if isinstance(url_res, dict) else str(url_res)
            if "login.twilio.com/u/login" in url:
                break
            time.sleep(1)
            
        time.sleep(3)
        
        # 4. Click 'Reset password' link
        print("[4] Clicking 'Reset password' link...")
        eval_js(client, """
            () => {
                const links = Array.from(document.querySelectorAll('a'));
                const resetLink = links.find(a => a.innerText.toLowerCase().includes('reset password') || (a.href && a.href.includes('reset')));
                if (resetLink) {
                    resetLink.click();
                    return { clicked: true, text: resetLink.innerText, href: resetLink.href };
                }
                return { clicked: false, allLinks: links.map(l => l.innerText) };
            }
        """)
        
        print("[5] Waiting 5 seconds for reset password request screen...")
        time.sleep(5)
        
        client.screenshot("D:/anonym/twilio_reset_screen.png")
        print("[+] Screenshot: D:/anonym/twilio_reset_screen.png")
        
        content = client.get_content()
        print("Page Content on Reset Screen:")
        print(content[:800])
        
        # If there is a form to submit email for reset
        print("[6] Submitting email for password reset...")
        eval_js(client, """
            () => {
                const emailInput = document.querySelector('input[type="email"]') || document.querySelector('input[name="email"]') || document.querySelector('#email');
                if (emailInput && !emailInput.value) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeSetter.call(emailInput, "isearch.xsolve@gmail.com");
                    emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                    emailInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
                const btn = document.querySelector('button[type="submit"]') || document.querySelector('button');
                if (btn) btn.click();
            }
        """)
        
        time.sleep(6)
        client.screenshot("D:/anonym/twilio_reset_requested.png")
        print("[+] Screenshot: D:/anonym/twilio_reset_requested.png")
        
        # 7. Poll Gmail IMAP for password reset link
        print("[7] Polling Gmail for password reset email (up to 40 seconds)...")
        reset_email = None
        for attempt in range(8):
            print(f"  Poll attempt {attempt+1}/8...")
            reset_email = fetch_latest_twilio_email()
            if reset_email:
                print(f"  [+] Got Email: {reset_email.get('subject')}")
                # Save body for inspection
                with open(r"D:\anonym\twilio_reset_email.html", "w", encoding="utf-8") as f:
                    f.write(reset_email.get("body", ""))
                print("  [+] Saved email body to D:\\anonym\\twilio_reset_email.html")
                break
            time.sleep(5)
            
    except Exception as e:
        print("Error during reset password flow:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()

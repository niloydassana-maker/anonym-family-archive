import sys
import os
import time
import json

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def eval_js(client, code):
    res = client.execute_script(code)
    if isinstance(res, dict) and 'content' in res:
        for c in res.get('content', []):
            if isinstance(c, dict) and c.get('type') == 'text':
                try:
                    return json.loads(c.get('text', '{}'))
                except Exception:
                    return c.get('text')
    return res

def main():
    print("=" * 60)
    print("TWILIO FULL FLOW WITH PARSED EVAL & TURNSTILE WAIT")
    print("=" * 60)
    
    client = Agent360Client()
    client.start()
    
    try:
        print("[1] Navigating to https://login.twilio.com/u/login ...")
        client.navigate("https://login.twilio.com/u/login")
        time.sleep(5)
        
        # Check if email is already filled or needs filling
        email_status = eval_js(client, """
            () => {
                const emailInput = document.querySelector('#email');
                const pwInput = document.querySelector('#password') || document.querySelector('input[type="password"]');
                return {
                    hasEmail: !!emailInput,
                    emailVal: emailInput ? emailInput.value : '',
                    hasPw: !!pwInput,
                    pwVal: pwInput ? pwInput.value.length : 0
                };
            }
        """)
        print("Initial form status:", email_status)
        
        # If email not submitted yet (hasEmail is True but pwInput is missing)
        if isinstance(email_status, dict) and email_status.get('hasEmail') and not email_status.get('hasPw'):
            print("[2] Filling email and clicking next...")
            client.fill("#email", "isearch.xsolve@gmail.com")
            time.sleep(1)
            client.click("#email-next")
            time.sleep(5)
            
        # Ensure password is set to Ku3104123!@#456$%
        print("[3] Setting password via native setter...")
        pw_res = eval_js(client, """
            () => {
                const pwInput = document.querySelector('#password') || document.querySelector('input[type="password"]');
                if (pwInput) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeSetter.call(pwInput, "Ku3104123!@#456$%");
                    pwInput.dispatchEvent(new Event('input', { bubbles: true }));
                    pwInput.dispatchEvent(new Event('change', { bubbles: true }));
                    return { ok: true, valLen: pwInput.value.length };
                }
                return { ok: false, reason: 'no pwInput' };
            }
        """)
        print("Password set result:", pw_res)
        time.sleep(1)
        
        # Wait for Turnstile
        print("[4] Waiting for Turnstile token...")
        for i in range(15):
            t_info = eval_js(client, """
                () => {
                    const ts = document.querySelector('[name="cf-turnstile-response"]');
                    const err = document.querySelector('.error-message, [role="alert"]');
                    return {
                        hasToken: !!(ts && ts.value),
                        tokenLen: ts && ts.value ? ts.value.length : 0,
                        errText: err ? err.innerText : null
                    };
                }
            """)
            print(f"  Check {i+1}/15: {t_info}")
            if isinstance(t_info, dict) and t_info.get('hasToken'):
                print("  [+] Turnstile token received!")
                break
            time.sleep(2)
            
        # Screenshot before click
        client.screenshot("D:/anonym/twilio_before_continue.png")
        
        # Click Continue / Submit
        print("[5] Submitting form via button click...")
        click_res = eval_js(client, """
            () => {
                const btn = document.querySelector('button[type="submit"]') || document.querySelector('button[name="action"]');
                if (btn) {
                    btn.disabled = false;
                    btn.click();
                    return { clicked: true, text: btn.innerText };
                }
                const form = document.querySelector('form');
                if (form) {
                    form.requestSubmit();
                    return { submitted: true };
                }
                return { failed: true };
            }
        """)
        print("Submit action result:", click_res)
        
        print("[6] Waiting 12 seconds for navigation/response...")
        time.sleep(12)
        
        client.screenshot("D:/anonym/twilio_after_continue.png")
        print("[+] Screenshot saved to D:/anonym/twilio_after_continue.png")
        
        content = client.get_content()
        print("\n--- FINAL PAGE CONTENT ---")
        print(content[:1500])
        print("--------------------------")
        
    except Exception as e:
        print("Error during full flow:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()

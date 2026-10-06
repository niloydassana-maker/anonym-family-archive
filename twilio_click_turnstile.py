import sys
import os
import time
import json
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

def main():
    print("=" * 60)
    print("TWILIO LOGIN WITH DIRECT TURNSTILE COORDINATE CLICK")
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
        time.sleep(5)
        
        print("[2] Filling email and clicking Continue...")
        client.fill("#email", "isearch.xsolve@gmail.com")
        time.sleep(1)
        client.click("#email-next")
        time.sleep(6)
        
        # 3. Check password and set
        print("[3] Setting password Ku3104123!@#456$% ...")
        eval_js(client, """
            () => {
                const pw = document.querySelector('input[type="password"]');
                if (pw) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeSetter.call(pw, "Ku3104123!@#456$%");
                    pw.dispatchEvent(new Event('input', { bubbles: true }));
                    pw.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        """)
        time.sleep(2)
        
        # 4. Find Turnstile coordinates
        print("[4] Detecting Turnstile widget position...")
        ts_pos = eval_js(client, """
            () => {
                const iframe = document.querySelector('iframe');
                if (iframe) {
                    const r = iframe.getBoundingClientRect();
                    return {
                        found: true,
                        type: 'iframe',
                        src: iframe.src,
                        clickX: Math.round(r.x + 30),
                        clickY: Math.round(r.y + (r.height / 2)),
                        rect: { x: r.x, y: r.y, w: r.width, h: r.height }
                    };
                }
                const container = document.querySelector('[data-turnstile-sitekey], .cf-turnstile') || document.querySelector('form > div:nth-child(3)');
                if (container) {
                    const r = container.getBoundingClientRect();
                    return {
                        found: true,
                        type: 'container',
                        clickX: Math.round(r.x + 30),
                        clickY: Math.round(r.y + (r.height / 2)),
                        rect: { x: r.x, y: r.y, w: r.width, h: r.height }
                    };
                }
                return { found: false };
            }
        """)
        print("Turnstile detection:", ts_pos)
        
        click_x = 0
        click_y = 0
        if isinstance(ts_pos, dict) and ts_pos.get('result', {}).get('found'):
            info = ts_pos['result']
            click_x = info['clickX']
            click_y = info['clickY']
            print(f"[5] Clicking Turnstile at ({click_x}, {click_y}) via browser_click_xy ...")
            c_res = client.call_tool('browser_click_xy', {'x': click_x, 'y': click_y})
            print("Click XY res:", c_res)
        else:
            print("[5] Falling back to generic click on iframe...")
            client.click("iframe")
            
        print("[6] Waiting 6 seconds for Turnstile to verify...")
        time.sleep(6)
        
        client.screenshot("D:/anonym/twilio_after_ts_click.png")
        print("[+] Screenshot saved: D:/anonym/twilio_after_ts_click.png")
        
        # 7. Check if Turnstile token is now present
        ts_check = eval_js(client, """
            () => {
                const input = document.querySelector('[name="cf-turnstile-response"]');
                const btn = document.querySelector('button[type="submit"]') || document.querySelector('button');
                const r = btn ? btn.getBoundingClientRect() : null;
                return {
                    hasToken: !!(input && input.value),
                    tokenLen: input && input.value ? input.value.length : 0,
                    btnFound: !!btn,
                    btnClickX: r ? Math.round(r.x + (r.width / 2)) : 0,
                    btnClickY: r ? Math.round(r.y + (r.height / 2)) : 0
                };
            }
        """)
        print("[7] Turnstile verification check:", ts_check)
        
        # 8. Submit form via button click
        print("[8] Clicking Continue button...")
        btn_info = ts_check.get('result', {}) if isinstance(ts_check, dict) else {}
        if btn_info.get('btnClickX') and btn_info.get('btnClickY'):
            bx = btn_info['btnClickX']
            by = btn_info['btnClickY']
            print(f"Clicking Continue via coordinates ({bx}, {by})...")
            client.call_tool('browser_click_xy', {'x': bx, 'y': by})
        else:
            client.click('button[type="submit"]')
            
        print("[9] Waiting 12 seconds for login redirect...")
        time.sleep(12)
        
        client.screenshot("D:/anonym/twilio_final_login_result.png")
        print("[+] Screenshot saved: D:/anonym/twilio_final_login_result.png")
        
        content = client.get_content()
        print("\n--- FINAL PAGE CONTENT ---")
        print(content[:2500])
        print("--------------------------")
        
    except Exception as e:
        print("Error during login execution:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()

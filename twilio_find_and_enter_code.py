import sys
import os
import time
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    print("Connecting to Agent360...", flush=True)
    client = Agent360Client()
    client.start()
    
    try:
        tabs = client.list_tabs()
        print(f"Tabs count: {len(tabs)}")
        target_tab = None
        for t in tabs:
            url = t.get("url", "")
            title = t.get("title", "")
            tab_id = t.get("id")
            print(f"Tab {tab_id}: {url[:80]} | {title[:50]}")
            if "twilio.com" in url or "auth0" in url or "Email Verification" in title:
                target_tab = tab_id
                
        if target_tab:
            print(f"Switching to target tab {target_tab}...")
            client.switch_tab(target_tab)
            time.sleep(1)
            
            # Inspect inputs
            script = """
            (function() {
                var inputs = Array.from(document.querySelectorAll('input, button')).map(function(el) {
                    return {
                        tag: el.tagName,
                        type: el.type || '',
                        id: el.id || '',
                        name: el.name || '',
                        placeholder: el.placeholder || '',
                        text: (el.innerText || el.value || '').trim()
                    };
                });
                return JSON.stringify({
                    url: window.location.href,
                    elements: inputs
                });
            })()
            """
            inspect_res = client.call_tool("browser_execute_script", {"script": script})
            print("Inspect result:", json.dumps(inspect_res, ensure_ascii=True))
            
            CODE = "P33XA2"
            fill_code_script = f"""
            (function() {{
                var input = document.querySelector('input[type="text"]') || document.querySelector('input');
                if (!input) return 'Input not found';
                var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(input, '{CODE}');
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'Code filled successfully into ' + (input.id || input.name || 'input');
            }})()
            """
            fill_res = client.call_tool("browser_execute_script", {"script": fill_code_script})
            print("Fill result:", json.dumps(fill_res, ensure_ascii=True))
            time.sleep(1)
            
            client.screenshot(r"D:\anonym\twilio_email_code_filled.png")
            
            click_btn_script = """
            (function() {
                var btn = document.querySelector('button[type="submit"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Continue'));
                if (btn) {
                    btn.click();
                    return 'Clicked button: ' + btn.innerText;
                }
                return 'Button not found';
            })()
            """
            click_res = client.call_tool("browser_execute_script", {"script": click_btn_script})
            print("Click result:", json.dumps(click_res, ensure_ascii=True))
            
            time.sleep(6)
            
            client.screenshot(r"D:\anonym\twilio_after_email_code.png")
            print("Captured D:\anonym\twilio_after_email_code.png")
            
            state_script = """
            (function() {
                return JSON.stringify({
                    url: window.location.href,
                    title: document.title,
                    body: document.body.innerText.slice(0, 500)
                });
            })()
            """
            state_res = client.call_tool("browser_execute_script", {"script": state_script})
            print("Next page state:", json.dumps(state_res, ensure_ascii=True))
        else:
            print("No twilio tab found in list_tabs!")
            
    except Exception as e:
        print("Error during execution:", repr(e))
    finally:
        client.close()
        print("Client closed.")

if __name__ == "__main__":
    main()

import sys
import os
import time

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    client = Agent360Client()
    client.start()
    
    try:
        tabs = client.list_tabs()
        for t in tabs:
            if "twilio.com" in t.get("url", ""):
                print(f"Switching to tab {t.get('id')}")
                client.switch_tab(t.get("id"))
                break
        
        time.sleep(2)
        
        text = client.get_content()
        print("FULL PAGE CONTENT:")
        print(text)
        print("-" * 50)
        
        # Check elements inside the page
        info = client.execute_script("""
            () => {
                const iframes = Array.from(document.querySelectorAll('iframe')).map(f => ({
                    src: f.src,
                    name: f.name,
                    id: f.id,
                    box: f.getBoundingClientRect()
                }));
                const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
                    id: b.id,
                    name: b.name,
                    text: b.innerText,
                    disabled: b.disabled,
                    box: b.getBoundingClientRect()
                }));
                const alerts = Array.from(document.querySelectorAll('[role="alert"], .error, .alert')).map(a => a.innerText);
                return {
                    url: window.location.href,
                    title: document.title,
                    iframes,
                    buttons,
                    alerts
                };
            }
        """)
        print("DOM Inspection:", info)
        
        # Screenshot with forward slash
        client.screenshot("D:/anonym/twilio_live_state.png")
        print("Saved D:/anonym/twilio_live_state.png")

    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()

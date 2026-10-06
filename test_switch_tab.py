import sys
import os
import time

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    client = Agent360Client()
    client.start()
    try:
        print("[1] Navigating...")
        client.navigate("https://www.twilio.com/login")
        time.sleep(2)
        
        print("[2] Listing tabs...")
        tabs = client.list_tabs()
        print("Tabs:", tabs)
        
        if tabs:
            tab_id = tabs[0].get('id')
            print(f"[3] Calling switch_tab to {tab_id} ...")
            sw_res = client.switch_tab(tab_id)
            print("Switch res:", sw_res)
            
    finally:
        client.close()

if __name__ == "__main__":
    main()

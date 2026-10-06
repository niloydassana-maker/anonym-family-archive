import sys
import os
import time

sys.path.append(r"D:\anonym\war-log")
from agent360_client import Agent360Client

def main():
    client = Agent360Client()
    client.start()
    
    try:
        # We check current URL / content
        content = client.get_content()
        print("Current URL:", content.get("url"))
        
        # Check inputs via script
        script = """
        () => {
            const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
                id: i.id,
                name: i.name,
                type: i.type,
                placeholder: i.placeholder,
                visible: i.offsetParent !== null
            }));
            const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
                id: b.id,
                type: b.type,
                text: b.innerText,
                visible: b.offsetParent !== null
            }));
            return { inputs, buttons };
        }
        """
        eval_res = client.evaluate(script)
        print("Form Elements:", eval_res)
        
    except Exception as e:
        print("Error:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()

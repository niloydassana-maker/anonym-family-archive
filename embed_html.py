import os

with open('d:/anonym/web_template.py', 'r', encoding='utf-8') as f:
    wt = f.read()

start = wt.find('WEB_DEMO_HTML = """')
end = wt.rfind('"""') + 3
html_def = wt[start:end]

with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    mvs = f.read()

target = """        @web_app.get("/")
        def web_index():
            from fastapi.responses import HTMLResponse
            try:
                from web_template import WEB_DEMO_HTML
                return HTMLResponse(content=WEB_DEMO_HTML)
            except Exception as e:
                return HTMLResponse(content=f"<h1>SugarDoctor AI Clinic</h1><p>{e}</p>")"""

replacement = html_def + """

        @web_app.get("/")
        def web_index():
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=WEB_DEMO_HTML)"""

if target in mvs:
    new_mvs = mvs.replace(target, replacement, 1)
    with open('d:/anonym/modal_voice_service.py', 'w', encoding='utf-8') as f:
        f.write(new_mvs)
    print("SUCCESS: Embedded successfully")
else:
    print("ERROR: Target block not found in modal_voice_service.py")

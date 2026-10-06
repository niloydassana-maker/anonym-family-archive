import os

with open('d:/anonym/web_template.py', 'r', encoding='utf-8') as f:
    wt = f.read()

start = wt.find('WEB_DEMO_HTML = """')
end = wt.rfind('"""') + 3
html_def = wt[start:end]

with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    mvs = f.read()

# 1. Insert WEB_DEMO_HTML after CLINIC_SYSTEM_PROMPT
marker = 'CLINIC_SYSTEM_PROMPT = """'
end_marker = mvs.find('"""', mvs.find(marker) + len(marker)) + 3

mvs_part1 = mvs[:end_marker]
mvs_part2 = mvs[end_marker:]

mvs_new = mvs_part1 + "\n\n" + html_def + "\n" + mvs_part2

# 2. Update web_index()
target_func = '''        @web_app.get("/")
        def web_index():
            from fastapi.responses import HTMLResponse
            try:
                from web_template import WEB_DEMO_HTML
                return HTMLResponse(content=WEB_DEMO_HTML)
            except Exception as e:
                return HTMLResponse(content=f"<h1>SugarDoctor AI Clinic</h1><p>{e}</p>")'''

replacement_func = '''        @web_app.get("/")
        def web_index():
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=WEB_DEMO_HTML)'''

if target_func in mvs_new:
    mvs_new = mvs_new.replace(target_func, replacement_func, 1)
    with open('d:/anonym/modal_voice_service.py', 'w', encoding='utf-8') as f:
        f.write(mvs_new)
    print("SUCCESS: Inserted at module level and updated web_index()")
else:
    print("ERROR: target_func not found")

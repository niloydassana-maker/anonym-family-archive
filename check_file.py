with open(r'D:\anonym\modal_voice_service.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Find the CLINIC_SYSTEM_PROMPT end and WEB_DEMO_HTML start
idx = c.find('WEB_DEMO_HTML =')
print('WEB_DEMO_HTML at:', idx)

# Find the prompt end
idx2 = c.find('"""', 95)
idx3 = c.find('"""', idx2 + 3)
idx4 = c.find('"""', idx3 + 3)
print('Prompt ends at:', idx4)
print('Next 200 chars:', repr(c[idx4:idx4+200]))
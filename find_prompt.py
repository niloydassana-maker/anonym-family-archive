with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    c = f.read()

idx = c.find('CLINIC_SYSTEM_PROMPT =')
print('Found at:', idx)
idx2 = c.find('"""', idx + 20)
idx3 = c.find('"""', idx2 + 3)
idx4 = c.find('"""', idx3 + 3)
print('First prompt ends at:', idx4)
print('Next 200 chars:', repr(c[idx4:idx4+200]))
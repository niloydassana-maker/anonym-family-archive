with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Show content around prompt end
idx4 = 3357
print('Content from 3350 to 3400:')
print(repr(c[3350:3400]))
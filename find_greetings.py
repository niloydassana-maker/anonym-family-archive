with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('d:/anonym/greetings_found.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if any(k in line for k in ['मदद', 'सहायता', 'स्वागत', 'playGreeting', 'hello', 'Hello']):
            out.write(f'{i+1}: {line.strip()[:140]}\n')

print("Written to greetings_found.txt")

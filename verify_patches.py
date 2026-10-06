with open(r'D:\anonym\modal_voice_service.py', 'r', encoding='utf-8') as f:
    c = f.read()

checks = [
    ('CLINIC_SYSTEM_PROMPT_EN', 'CLINIC_SYSTEM_PROMPT_EN' in c),
    ('BILINGUAL DETECTION', 'BILINGUAL DETECTION' in c),
    ('sanitize with lang param', 'lang: str = "hi"' in c),
    ('sanitize_hindi_for_xtts call with lang', 'sanitize_hindi_for_xtts(text, lang=' in c),
    ('greeting_set_en', 'greeting_set_en' in c),
    ('fast_pieces en', 'Sure, how can I help you today' in c),
    ('detect_lang latin count', 'latin > devanagari' in c),
    ('_llm_api_clauses uses CLINIC_SYSTEM_PROMPT_EN', 'CLINIC_SYSTEM_PROMPT_EN' in c),
]

for name, result in checks:
    print(f"{name}: {result}")
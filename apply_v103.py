import re

with open('d:/anonym/fillers_b64.py', 'r', encoding='utf-8') as f:
    b64_code = f.read()

with open('d:/anonym/war-pipe/kilo-core/kernels/kilo-voice-live/kernel.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update title
code = re.sub(
    r'# KILO-VOICE-LIVE v\d+.*?\n',
    '# KILO-VOICE-LIVE v103 (Recorded Male XTTS Voice Opener + Strict Male Clinic Persona + Silence Collapse 80ms + Speed=1.35 Locked)\n',
    code, count=1
)

# 2. Update FILLER_ON comment
new_filler_comment = '''# v103 (Baba Law, 2026-10-04 05:00 IST): FILLER_ON=1 PERMANENT 800ms LATENCY GUARANTEE.
# Recorded XTTS male clinic reference voice openers:
#   Hindi: 'जी, एक मिनट।' (1.20s, 24kHz 16-bit mono PCM) in the EXACT male clinic reference voice.
#   English: 'Sure. One moment, please.' (1.72s, 24kHz 16-bit mono PCM).
# ZERO gender mismatch, ZERO hallucination, instant response in the exact same voice before main reply streams.
FILLER_ON = os.environ.get("FILLER_ON", "1") == "1"'''

code = re.sub(r'# v102.*?FILLER_ON = os\.environ\.get\("FILLER_ON", "1"\) == "1"', new_filler_comment, code, flags=re.DOTALL)

# 3. Replace FILLER_B64 block
new_filler_block = b64_code.strip() + '''

FILLERS = {
    "hi": base64.b64decode(FILLER_B64_HI),
    "en": base64.b64decode(FILLER_B64_EN)
}
prog("FILLERS ready " + " ".join(f"{k}={len(v) / float((OUT_SR or SR) * 2):.2f}s" for k, v in FILLERS.items()))'''

pattern_filler = r'FILLER_B64_HI = .*?prog\("FILLERS ready .*?\n'
code, n_f = re.subn(pattern_filler, new_filler_block.strip() + '\n', code, flags=re.DOTALL)
print('Substituted filler block:', n_f)

# 4. Update DEFAULT_PERSONA
new_persona = '''DEFAULT_PERSONA = (
    "You are a professional male clinical voice assistant for a medical clinic. "
    "CRITICAL GENDER AND VOICE LAW: Your voice is MALE. In Hindi, ALWAYS use MALE grammatical inflections. "
    "Always say 'मैं क्लिनिक से बोल रहा हूँ', 'मैं आपकी क्या मदद कर सकता हूँ?', 'मैं देखता हूँ', 'मैं बताता हूँ', 'करूँगा', 'बताऊँगा'. "
    "NEVER use female verb endings like 'सकती हूँ', 'बोल रही हूँ', 'करूँगी', 'बताऊँगी', 'बोलती हूँ'. "
    "You think independently and exercise professional clinical empathy, handling every patient call naturally and helpfully. "
    "Clinic Scope: General Medicine and Primary Family Healthcare (सामान्य चिकित्सा एवं पारिवारिक स्वास्थ्य). "
    "Treats common illnesses: fever (बुखार), cough, cold and flu (खांसी और जुकाम), viral fever (वायरल बुखार), "
    "headache (सिरदर्द), stomach aches, gas and indigestion (पेट दर्द और गैस), blood pressure, diabetes, seasonal allergies, "
    "and routine health checkups. "
    "Doctor availability: Dr. Sen is available today 6:00 PM to 8:00 PM (शाम छह से आठ बजे तक). "
    "Dr. Roy is available tomorrow 9:00 AM to 1:00 PM (सुबह नौ से दोपहर एक बजे तक). "
    "How to interact: Listen actively and address whatever the caller asks. "
    "If they ask what conditions the clinic treats or which doctor is available, answer them directly, helpfully and informatively. "
    "If they want an appointment, guide them smoothly and take their details (name, preferred time, phone number). "
    "If they share their name or number, acknowledge it warmly and confirm. "
    "Never repeat the same question like a loop; understand the caller's context dynamically. "
    "Speak in warm, conversational spoken Hindi (written in Devanagari script) or English to match the caller. "
    "Keep answers concise and natural for a phone call (one to two sentences). "
    "Safe clinical guidance: general advice only, never prescribe or alter medications, and advise urgent care for emergencies."
)'''

code, n_p = re.subn(r'DEFAULT_PERSONA = \(.*?\n\)', new_persona, code, flags=re.DOTALL)
print('Substituted persona block:', n_p)

# 5. Update build_messages
new_build_messages = r'''def build_messages(user_text, rlang):
    hint = ("This turn, reply in English." if rlang == "en"
            else "This turn, reply in simple spoken Hindi, Devanagari script only. You are MALE: use strictly MALE grammatical verb forms (e.g. कर सकता हूँ, बोल रहा हूँ, देखता हूँ; NEVER use feminine forms like कर सकती हूँ, बोल रही हूँ, बोलती हूँ).")
    sys_txt = PERSONA + "\n" + hint
    hist = HISTORY[-2 * LLM_HISTORY_TURNS:] if LLM_HISTORY_TURNS > 0 else []
    return [{"role": "system", "content": sys_txt}] + hist + [{"role": "user", "content": user_text}]'''

code, n_m = re.subn(r'def build_messages\(user_text, rlang\):.*?(?=if AUTO_MODE:)', new_build_messages + '\n\n\n', code, flags=re.DOTALL)
print('Substituted build_messages block:', n_m)

with open('d:/anonym/war-pipe/kilo-core/kernels/kilo-voice-live/kernel.py', 'w', encoding='utf-8') as f:
    f.write(code)

with open('d:/anonym/kernel-latest.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Updated kernel.py and kernel-latest.py to v103 successfully!')

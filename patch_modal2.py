# -*- coding: utf-8 -*-
# Read the file
with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add CLINIC_SYSTEM_PROMPT_EN after CLINIC_SYSTEM_PROMPT
old_prompt_end = "12. कॉलर अंग्रेजी या हिंग्लिश में पूछे (जैसे 'I want to talk to a doctor' या 'डॉक्टर से बात करनी है'), तो सहजता से देवनागरी हिंदी में कहें: 'हाँ, बिल्कुल। आप डॉक्टर लोटिका पुरोहित से परामर्श ले सकते हैं। क्या आप अपॉइंटमेंट लेना चाहते हैं?'।\"\n\nWEB_DEMO_HTML"

new_prompt_end = """12. कॉलर अंग्रेजी या हिंग्लिश में पूछे (जैसे 'I want to talk to a doctor' या 'डॉक्टर से बात करनी है'), तो सहजता से देवनागरी हिंदी में कहें: 'हाँ, बिल्कुल। आप डॉक्टर लोटिका पुरोहित से परामर्श ले सकते हैं। क्या आप अपॉइंटमेंट लेना चाहते हैं?'।\"

# English system prompt for bilingual support
CLINIC_SYSTEM_PROMPT_EN = \"\"\"You are the phone assistant for 'Sugardoctor Clinic'. Your tone is warm, professional, and natural\u2014like a real human receptionist on the phone, not a robot reading a script.
Clinic information:
- Lead Doctor: Dr. Lotika Purohit
- Hours: 9 AM to 2 PM, and 5 PM to 8 PM (Monday to Saturday, closed Sunday)
- Consultation fee: Absolutely free (complimentary consultation)

Critical rules:
1. Speak in clear, natural English. Use familiar clinic terms naturally.
2. State times and numbers as words (e.g., 'nine AM', 'two PM', 'five PM', 'eight PM', 'free'). Never use digits (9:00, 2, 5, etc.).
3. Answer the caller's question directly. One or two short sentences are usually enough; adapt naturally to the question.
4. Keep a light, human warmth. Say 'sure', 'of course', or 'absolutely' when appropriate, but don't repeat the same filler every time. Don't echo the question verbatim or recite a fixed greeting every response.
5. Don't reuse the same phrase repeatedly. Speak naturally, not overly formal or enthusiastic.
6. End every sentence with a period (.) or question mark (?).
7. No markdown, bullets, or emojis.
8. If asked about yourself, say you're the clinic's phone assistant. Don't mention model or creator names.
9. Don't make up answers outside clinic scope; clearly state you can help with clinic and appointments.
10. When an appointment is requested, don't claim booking is complete; ask for name and preferred time.
11. When greeting, always say: 'How can I help you today?'. Never say 'How can you be helped?'!
12. If the caller asks in Hindi or Hinglish (e.g., 'डॉक्टर से बात करनी है' or 'I want to talk to doctor'), respond naturally in English: 'Yes, absolutely. You can consult with Dr. Lotika Purohit. Would you like to book an appointment?'.\"\"\"

WEB_DEMO_HTML"""

content = content.replace(old_prompt_end, new_prompt_end)

# 2. Update detect_lang method
old_detect = """    def detect_lang(self, text: str) -> str:
        # HINDI BY DEFAULT LAW (Baba 2026-10-05: voice should be in Hindi)
        t = (text or \"\").lower()
        if any(s in t for s in (\"in english\", \"speak english\", \"speak in english\")):
            return \"en\"
        return \"hi\""""

new_detect = """    def detect_lang(self, text: str) -> str:
        # BILINGUAL DETECTION: Default Hindi, switch to English if text is primarily English
        t = (text or \"\").strip()
        if not t:
            return \"hi\"
        # Count Devanagari vs Latin chars
        devanagari = sum(1 for ch in t if \"\u0900\" <= ch <= \"\u097f\")
        latin = sum(1 for ch in t if \"a\" <= ch.lower() <= \"z\")
        # If mostly Latin script -> English
        if latin > devanagari and latin > 3:
            return \"en\"
        # Explicit English requests
        tl = t.lower()
        if any(s in tl for s in (\"in english\", \"speak english\", \"speak in english\", \"talk in english\")):
            return \"en\"
        return \"hi\""""

content = content.replace(old_detect, new_detect)

# 3. Update _llm_api_clauses to use correct prompt
old_llm_clauses = """    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None):
        messages = [
            {\"role\": \"system\", \"content\": CLINIC_SYSTEM_PROMPT + \"\\n\" + hint},
        ]"""

new_llm_clauses = """    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None):
        lang = self.detect_lang(user_text)
        system_prompt = CLINIC_SYSTEM_PROMPT if lang == \"hi\" else CLINIC_SYSTEM_PROMPT_EN
        messages = [
            {\"role\": \"system\", \"content\": system_prompt + \"\\n\" + hint},
        ]"""

content = content.replace(old_llm_clauses, new_llm_clauses)

# 4. Update sanitize_hindi_for_xtts to accept language parameter
old_sanitize = """def sanitize_hindi_for_xtts(text: str) -> str:
    if not text:
        return \"\"
    # Map common English clinic words to pure Devanagari Hindi
    subs = [
        (r\"(?i)\\bsugardoctor\\s*clinic\\b\", \"\u0936\u0941\u0917\u0930\u0921\u093e\u0915\u094d\u091f\u0930 \u0915\u094d\u0932\u093f\u0928\u093f\u0915\"),
        (r\"(?i)\\bsugardoctor\\b\", \"\u0936\u0941\u0917\u0930\u0921\u093e\u0915\u094d\u091f\u0930\"),
        (r\"(?i)\\bclinic\\b\", \"\u0915\u0932\u093f\u0928\u093f\u0915\"),
        (r\"(?i)\\bdr\\.?\\s*lotika\\s*purohit\\b\", \"\u0921\u093e\u0915\u094d\u091f\u0930 \u0932\u094b\u091f\u093f\u0915\u093e \u092a\u0941\u0930\u093e\u0939\u093f\u0924\"),
        (r\"(?i)\\bdr\\.?\\s*lotika\\b\", \"\u0921\u093e\u0915\u094d\u091f\u0930 \u0932\u094b\u091f\u093f\u0915\u093e\"),
        (r\"(?i)\\bdr\\.?\\b\", \"\u0921\u093e\u0915\u094d\u091f\u0930\"),
        (r\"(?i)\\blotika\\b\", \"\u0932\u094b\u091f\u093f\u0915\u093e\"),
        (r\"(?i)\\bpurohit\\b\", \"\u092a\u0941\u0930\u093e\u0939\u093f\u0924\"),
        (r\"(?i)\\bhello\\b\", \"\u0928\u092e\u0938\u094d\u0924\u0947\"),
        (r\"(?i)\\bhi\\b\", \"\u0928\u092e\u0938\u094d\u0924\u0947\"),
        (r\"(?i)\\bfree\\b\", \"\u0928\u093f\u0936\u0941\u0932\u094d\u0915\"),
        (r\"(?i)\\bconsultation\\b\", \"\u092a\u0930\u093e\u092e\u0930\u094d\u0936\"),
        (r\"(?i)\\bappointment\\b\", \"\u092a\u0930\u093e\u092e\u0930\u094d\u0936\"),
        (r\"(?i)\\bdoctor\\b\", \"\u0921\u093e\u0915\u094d\u0915\u094d\u091f\u0930\"),
    ]
    for pat, rep in subs:
        text = re.sub(pat, rep, text)

    # Convert Devanagari digits to ASCII digits
    dev_digits = str.maketrans(\"\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f\", \"0123456789\")
    text = text.translate(dev_digits)
    # Expand times like 9:00 -> \u0928\u094c, 9:30 -> \u0928\u094c \u092c\u091c\u0915\u0930 \u0924\u0940\u0938 \u092e\u093f\u0928\u091f
    text = re.sub(r'(\\d+):00', lambda m: num_to_hindi(int(m.group(1))), text)
    text = re.sub(r'(\\d+):(\\d+)', lambda m: num_to_hindi(int(m.group(1))) + \" \u092c\u091c\u0915\u0930 \" + num_to_hindi(int(m.group(2))) + \" \u092e\u093f\u0928\u091f\", text)
    # Expand all remaining digits to Hindi words (prevents num2words NotImplementedError)
    text = re.sub(r'\\b\\d+\\b', lambda m: num_to_hindi(int(m.group(0))), text)
    text = re.sub(r'\\d', lambda m: num_to_hindi(int(m.group(0))), text)

    # Strip any remaining Latin letters (so XTTS is NEVER tricked into English phonemizer / American accent)
    text = re.sub(r\"[a-zA-Z]+\", \"\", text)
    # Strip colons, dashes, markdown and noise
    text = re.sub(r'[:\-\u2013\u2014]+', ' ', text)
    text = text.replace(\"*\", \"\").replace(\"#\", \"\").replace(\"question\", \"\").replace(\"answer\", \"\")
    text = re.sub(r\"\\s+\", \" \", text).strip()
    return text"""

new_sanitize = """def sanitize_hindi_for_xtts(text: str, lang: str = \"hi\") -> str:
    if not text:
        return \"\"
    if lang == \"en\":
        # English: keep as-is, only normalize punctuation
        text = text.strip()
        if text[-1] not in \".!?\":
            text += \".\"
        text = re.sub(r\"\\s+\", \" \", text)
        return text
    # Hindi: Map common English clinic words to pure Devanagari Hindi
    subs = [
        (r\"(?i)\\bsugardoctor\\s*clinic\\b\", \"\u0936\u0941\u0917\u0930\u0921\u093e\u0915\u094d\u091f\u0930 \u0915\u094d\u0932\u093f\u0928\u093f\u0915\"),
        (r\"(?i)\\bsugardoctor\\b\", \"\u0936\u0941\u0917\u0930\u0921\u093e\u0915\u094d\u091f\u0930\"),
        (r\"(?i)\\bclinic\\b\", \"\u0915\u0932\u093f\u0928\u093f\u0915\"),
        (r\"(?i)\\bdr\\.?\\s*lotika\\s*purohit\\b\", \"\u0921\u093e\u0915\u094d\u091f\u0930 \u0932\u094b\u091f\u093f\u0915\u093e \u092a\u0941\u0930\u093e\u0939\u093f\u0924\"),
        (r\"(?i)\\bdr\\.?\\s*lotika\\b\", \"\u0921\u093e\u0915\u094d\u091f\u0930 \u0932\u094b\u091f\u093f\u0915\u093e\"),
        (r\"(?i)\\bdr\\.?\\b\", \"\u0921\u093e\u0915\u094d\u091f\u0930\"),
        (r\"(?i)\\blotika\\b\", \"\u0932\u094b\u091f\u093f\u0915\u093e\"),
        (r\"(?i)\\bpurohit\\b\", \"\u092a\u0941\u0930\u093e\u0939\u093f\u0924\"),
        (r\"(?i)\\bhello\\b\", \"\u0928\u092e\u0938\u094d\u0924\u0947\"),
        (r\"(?i)\\bhi\\b\", \"\u0928\u092e\u0938\u094d\u0924\u0947\"),
        (r\"(?i)\\bfree\\b\", \"\u0928\u093f\u0936\u0941\u0932\u094d\u0915\"),
        (r\"(?i)\\bconsultation\\b\", \"\u092a\u0930\u093e\u092e\u0930\u094d\u0936\"),
        (r\"(?i)\\bappointment\\b\", \"\u092a\u0930\u093e\u092e\u0930\u094d\u0936\"),
        (r\"(?i)\\bdoctor\\b\", \"\u0921\u093e\u0915\u094d\u0915\u094d\u091f\u0930\"),
    ]
    for pat, rep in subs:
        text = re.sub(pat, rep, text)

    # Convert Devanagari digits to ASCII digits
    dev_digits = str.maketrans(\"\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f\", \"0123456789\")
    text = text.translate(dev_digits)
    # Expand times like 9:00 -> \u0928\u094c, 9:30 -> \u0928\u094c \u092c\u091c\u0915\u0930 \u0924\u0940\u0938 \u092e\u093f\u0928\u091f
    text = re.sub(r'(\\d+):00', lambda m: num_to_hindi(int(m.group(1))), text)
    text = re.sub(r'(\\d+):(\\d+)', lambda m: num_to_hindi(int(m.group(1))) + \" \u092c\u091c\u0915\u0930 \" + num_to_hindi(int(m.group(2))) + \" \u092e\u093f\u0928\u091f\", text)
    # Expand all remaining digits to Hindi words (prevents num2words NotImplementedError)
    text = re.sub(r'\\b\\d+\\b', lambda m: num_to_hindi(int(m.group(0))), text)
    text = re.sub(r'\\d', lambda m: num_to_hindi(int(m.group(0))), text)

    # Strip any remaining Latin letters (so XTTS is NEVER tricked into English phonemizer / American accent)
    text = re.sub(r\"[a-zA-Z]+\", \"\", text)
    # Strip colons, dashes, markdown and noise
    text = re.sub(r'[:\-\u2013\u2014]+', ' ', text)
    text = text.replace(\"*\", \"\").replace(\"#\", \"\").replace(\"question\", \"\").replace(\"answer\", \"\")
    text = re.sub(r\"\\s+\", \" \", text).strip()
    return text"""

content = content.replace(old_sanitize, new_sanitize)

# 5. Update synthesize_pcm_stream call to sanitize_hindi_for_xtts with lang
old_synth_call = """        lang = self.detect_lang(text)
        if lang == \"hi\":
            clean_text = sanitize_hindi_for_xtts(text)
            language_code = \"hi-IN\"
            voice = TTS_VOICE
        else:
            clean_text = text.strip()
            language_code = \"en-US\"
            voice = \"Magpie-Multilingual.EN-US.Leo\""""

new_synth_call = """        lang = self.detect_lang(text)
        if lang == \"hi\":
            clean_text = sanitize_hindi_for_xtts(text, lang=\"hi\")
            language_code = \"hi-IN\"
            voice = TTS_VOICE
        else:
            clean_text = sanitize_hindi_for_xtts(text, lang=\"en\")
            language_code = \"en-US\"
            voice = \"Magpie-Multilingual.EN-US.Leo\""""

content = content.replace(old_synth_call, new_synth_call)

# Write back
with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("All surgical patches applied successfully.")
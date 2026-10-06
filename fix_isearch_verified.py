with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

def rep(old, new, name):
    global c
    n = c.count(old)
    if n != 1:
        raise SystemExit('ABORT: %s matched %d times (expected 1). No changes written.' % (name, n))
    c = c.replace(old, new)
    print('patched: %s' % name)

EN_PROMPT = '''
# English system prompt for bilingual support (isearch multilingual container only)
CLINIC_SYSTEM_PROMPT_EN = """You are the phone assistant for 'Sugardoctor Clinic'. Your tone is warm, professional, and natural - like a real human receptionist on the phone, not a robot reading a script.
Clinic information:
- Lead Doctor: Dr. Lotika Purohit
- Hours: 9 AM to 2 PM, and 5 PM to 8 PM (Monday to Saturday, closed Sunday)
- Consultation fee: Absolutely free (complimentary consultation)
Critical rules:
1. Speak in clear, natural English. Use familiar clinic terms naturally.
2. State times and numbers as words (e.g. nine AM, two PM, five PM, eight PM, free). Never use digits.
3. Answer the caller question directly. One or two short sentences are usually enough.
4. Keep a light human warmth. Do not echo the question verbatim.
5. Do not reuse the same phrase repeatedly.
6. End every sentence with a period (.) or question mark (?).
7. No markdown, bullets, or emojis.
8. If asked about yourself, say you are the clinic phone assistant. Never mention model or creator names.
9. Do not invent answers outside clinic scope.
10. When an appointment is requested, ask for name and preferred time; never claim booking is complete.
11. When greeting, always say: How can I help you today?"""

'''

rep('WEB_DEMO_HTML = """<!DOCTYPE html>', EN_PROMPT + 'WEB_DEMO_HTML = """<!DOCTYPE html>', 'EN prompt insert')

rep('''    def detect_lang(self, text: str) -> str:
        # HINDI ONLY (stable)
        return "hi"''', '''    def detect_lang(self, text: str) -> str:
        # BILINGUAL (isearch only): default Hindi, Latin-majority text -> English
        t = (text or "").strip()
        if not t:
            return "hi"
        devanagari = sum(1 for ch in t if "\\u0900" <= ch <= "\\u097f")
        latin = sum(1 for ch in t if "a" <= ch.lower() <= "z")
        if latin > devanagari and latin > 3:
            return "en"
        tl = t.lower()
        if any(s in tl for s in ("in english", "speak english", "speak in english", "talk in english")):
            return "en"
        return "hi"''', 'detect_lang bilingual')

rep('def sanitize_hindi_for_xtts(text: str) -> str:\n    if not text:\n        return ""',
    'def sanitize_hindi_for_xtts(text: str, lang: str = "hi") -> str:\n    if not text:\n        return ""\n    if lang == "en":\n        text = text.strip()\n        if text and text[-1] not in ".!?":\n            text += "." \n        text = re.sub(r"\\\\s+", " ", text)\n        return text',
    'sanitize signature + EN branch')

rep('''    def llm_stream_clauses(self, user_text: str, history: list = None):
        hint = "Reply in simple spoken Hindi, Devanagari script."
        t0 = time.time()
        emitted = 0
        for clause in self._llm_api_clauses(user_text, hint, history=history):
            clause = sanitize_hindi_for_xtts(clause, lang=lang)''', '''    def llm_stream_clauses(self, user_text: str, history: list = None):
        lang = self.detect_lang(user_text)
        hint = "Reply in simple spoken Hindi, Devanagari script." if lang == "hi" else "Reply in concise spoken English."
        t0 = time.time()
        emitted = 0
        for clause in self._llm_api_clauses(user_text, hint, history=history):
            clause = sanitize_hindi_for_xtts(clause, lang=lang)''', 'llm_stream_clauses lang')

rep('''    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None):
        messages = [
            {"role": "system", "content": CLINIC_SYSTEM_PROMPT + "\\n" + hint},
        ]''', '''    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None):
        lang = self.detect_lang(user_text)
        system_prompt = CLINIC_SYSTEM_PROMPT if lang == "hi" else CLINIC_SYSTEM_PROMPT_EN
        messages = [
            {"role": "system", "content": system_prompt + "\\n" + hint},
        ]''', 'llm prompt select')

rep('''                        delta = delta.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
                        if not delta:''', '''                        delta = delta.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
                        delta = re.sub(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]", "", delta)
                        if not delta:''', 'delta control-char strip')

rep('''        if not text or not text.strip():
            return
        clean_text = sanitize_hindi_for_xtts(text)
        language_code = "hi-IN"
        voice = TTS_VOICE
        if clean_text[-1] not in "।.!?":
            clean_text += "।"''', '''        if not text or not text.strip():
            return
        lang = self.detect_lang(text)
        if lang == "hi":
            clean_text = sanitize_hindi_for_xtts(text, lang="hi")
            language_code = "hi-IN"
            voice = TTS_VOICE
        else:
            clean_text = sanitize_hindi_for_xtts(text, lang="en")
            language_code = "en-US"
            voice = "Magpie-Multilingual.EN-US.Leo"
        if clean_text[-1] not in "।.!?":
            clean_text += "।" if language_code == "hi-IN" else "."''', 'synthesize lang branch')

rep('''            # FAST GREETING INTERCEPT (Baba Law: natural clinic welcome, never reversed pronoun)
            clean_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम", "start", "शुरू"}
            if not clean_toks or clean_toks.issubset(greeting_set):
                full_reply = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            else:
                clauses = list(self.llm_stream_clauses(user_text, history=session_history))
                full_reply = " ".join(clauses).strip()
                if not full_reply:
                    full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"''', '''            # FAST GREETING INTERCEPT (bilingual, isearch only)
            req_lang_param = (data.get("lang") or "").strip().lower()
            if req_lang_param in ("en", "en-us", "english"):
                lang = "en"
            elif req_lang_param in ("hi", "hi-in", "hindi"):
                lang = "hi"
            else:
                lang = self.detect_lang(user_text)
            clean_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set_hi = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम", "start", "शुरू"}
            greeting_set_en = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "start"}
            is_greeting = (not clean_toks or clean_toks.issubset(greeting_set_hi) or clean_toks.issubset(greeting_set_en))
            if is_greeting:
                if lang == "en":
                    full_reply = "Hello! Welcome to Sugardoctor Clinic, Dr. Lotika Purohit speaking. How can I help you today?"
                else:
                    full_reply = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            else:
                clauses = list(self.llm_stream_clauses(user_text, history=session_history))
                full_reply = " ".join(clauses).strip()
                if not full_reply:
                    if lang == "en":
                        full_reply = "I am sorry, I did not catch that. How can I help you today?"
                    else:
                        full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"''', 'api_chat bilingual')

rep('''            # FAST GREETING PATH (<600ms feel latency):
            # If caller says "hello", "hello hello", "नमस्ते", respond immediately with warm Hindi clinic greeting.
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            if clean_user_toks and clean_user_toks.issubset({"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}):
                is_pure_greeting = True''', '''            # FAST GREETING PATH (<600ms feel latency, bilingual isearch only)
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            _greet_hi = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}
            _greet_en = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"}
            turn_lang = self.detect_lang(user_text)
            if clean_user_toks and (clean_user_toks.issubset(_greet_hi) or clean_user_toks.issubset(_greet_en)):
                is_pure_greeting = True''', 'turn greeting detect')

rep('''                if is_pure_greeting:
                    fast_pieces = [
                        "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                    ]''', '''                if is_pure_greeting:
                    if turn_lang == "en":
                        fast_pieces = [
                            "Sure, how can I help you today?"
                        ]
                    else:
                        fast_pieces = [
                            "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                        ]''', 'turn fast pieces')

rep('''                if clarify:
                    clarify_text = "माफ़ कीजिए, आपकी आवाज़ साफ़ नहीं आई। कृपया एक बार फिर कहिए।"''', '''                if clarify:
                    _clar_lang = self.detect_lang(heard_raw) if heard_raw else "hi"
                    if _clar_lang == "en":
                        clarify_text = "Sorry, I did not catch that clearly. Please say it once again."
                    else:
                        clarify_text = "माफ़ कीजिए, आपकी आवाज़ साफ़ नहीं आई। कृपया एक बार फिर कहिए।"''', 'turn clarify lang')

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.write(c)

print('ALL 11 PATCHES APPLIED')

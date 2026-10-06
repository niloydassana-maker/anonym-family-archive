import re

with open('d:/anonym/web_template.py', 'r', encoding='utf-8') as f:
    wt = f.read()

start = wt.find('WEB_DEMO_HTML = """')
end = wt.rfind('"""') + 3
new_html_def = wt[start:end]

with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    mvs = f.read()

# 1. Update CLINIC_SYSTEM_PROMPT
old_prompt_rules = '10. अपॉइंटमेंट मांगे जाने पर बुकिंग पूरी होने का दावा न करें; नाम और सुविधाजनक समय पूछें。\n"""'
new_prompt_rules = '''10. अपॉइंटमेंट मांगे जाने पर बुकिंग पूरी होने का दावा न करें; नाम और सुविधाजनक समय पूछें।
11. कॉलर का स्वागत करते समय हमेशा कहें: 'मैं आपकी क्या सहायता कर सकता हूँ?'। कभी भी 'आप कैसे मदद कर सकते हैं' न कहें!
12. कॉलर अंग्रेजी या हिंग्लिश में पूछे (जैसे 'I want to talk to a doctor' या 'डॉक्टर से बात करनी है'), तो सहजता से देवनागरी हिंदी में कहें: 'हाँ, बिल्कुल। आप डॉक्टर लोटिका पुरोहित से परामर्श ले सकते हैं। क्या आप अपॉइंटमेंट लेना चाहते हैं?'।
"""'''

if '10. अपॉइंटमेंट मांगे जाने पर' in mvs:
    prompt_start = mvs.find('CLINIC_SYSTEM_PROMPT = """')
    prompt_end = mvs.find('"""', prompt_start + 26) + 3
    
    current_prompt = mvs[prompt_start:prompt_end]
    if '11. कॉलर का स्वागत' not in current_prompt:
        updated_prompt = current_prompt[:-3] + """11. कॉलर का स्वागत करते समय हमेशा कहें: 'मैं आपकी क्या सहायता कर सकता हूँ?'। कभी भी 'आप कैसे मदद कर सकते हैं' न कहें!
12. कॉलर अंग्रेजी या हिंग्लिश में पूछे (जैसे 'I want to talk to a doctor' या 'डॉक्टर से बात करनी है'), तो सहजता से देवनागरी हिंदी में कहें: 'हाँ, बिल्कुल। आप डॉक्टर लोटिका पुरोहित से परामर्श ले सकते हैं। क्या आप अपॉइंटमेंट लेना चाहते हैं?'।
\"\"\""""
        mvs = mvs[:prompt_start] + updated_prompt + mvs[prompt_end:]
        print("Updated CLINIC_SYSTEM_PROMPT")

# 2. Update WEB_DEMO_HTML
html_start = mvs.find('WEB_DEMO_HTML = """')
html_end = mvs.find('"""', html_start + 20) + 3
if html_start != -1 and html_end != -1:
    mvs = mvs[:html_start] + new_html_def + mvs[html_end:]
    print("Updated WEB_DEMO_HTML")
else:
    print("ERROR: Could not find WEB_DEMO_HTML boundaries")

# 3. Update api_chat with Fast Greeting Intercept
target_api_chat = '''            clauses = list(self.llm_stream_clauses(user_text, history=session_history))
            full_reply = " ".join(clauses).strip()
            if not full_reply:
                full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"'''

replacement_api_chat = '''            # FAST GREETING INTERCEPT (Baba Law: natural clinic welcome, never reversed pronoun)
            clean_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम", "start", "शुरू"}
            if not clean_toks or clean_toks.issubset(greeting_set):
                full_reply = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            else:
                clauses = list(self.llm_stream_clauses(user_text, history=session_history))
                full_reply = " ".join(clauses).strip()
                if not full_reply:
                    full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"'''

if target_api_chat in mvs:
    mvs = mvs.replace(target_api_chat, replacement_api_chat, 1)
    print("Updated api_chat with Fast Greeting Intercept")
else:
    print("WARNING: target_api_chat not found directly, checking...")

with open('d:/anonym/modal_voice_service.py', 'w', encoding='utf-8') as f:
    f.write(mvs)

print("Saved modal_voice_service.py successfully!")

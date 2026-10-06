# -*- coding: utf-8 -*-
# Read the file
with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update /api/chat greeting logic
old_api_chat_greeting = """            # FAST GREETING INTERCEPT (Baba Law: natural clinic welcome, never reversed pronoun)
            clean_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम", "start", "शुरू"}
            if not clean_toks or clean_toks.issubset(greeting_set):
                full_reply = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            else:
                clauses = list(self.llm_stream_clauses(user_text, history=session_history))
                full_reply = " ".join(clauses).strip()
                if not full_reply:
                    full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"""

new_api_chat_greeting = """            # FAST GREETING INTERCEPT (Baba Law: natural clinic welcome, never reversed pronoun)
            clean_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set_hi = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम", "start", "शुरू"}
            greeting_set_en = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "start"}
            lang = self.detect_lang(user_text)
            is_greeting = (not clean_toks or 
                          clean_toks.issubset(greeting_set_hi) or 
                          clean_toks.issubset(greeting_set_en))
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
                        full_reply = "I'm sorry, I didn't catch that. How can I help you today?"
                    else:
                        full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"""

content = content.replace(old_api_chat_greeting, new_api_chat_greeting)

# 2. Update /turn greeting logic (search for the greeting section in turn)
old_turn_greeting = """            greetings = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "प्रणाम", "हाय", "hi", "सुनिए", "हाँ", "हा", "ji", "जी"}

            def is_hallucination(text):"""

new_turn_greeting = """            greetings_hi = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "प्रणाम", "हाय", "hi", "सुनिए", "हाँ", "हा", "ji", "जी"}
            greetings_en = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "yes", "yeah", "yep"}
            greetings = greetings_hi | greetings_en

            def is_hallucination(text):"""

content = content.replace(old_turn_greeting, new_turn_greeting)

# 3. Update the pure greeting check in /turn stream_generator
old_pure_greeting = """            # FAST GREETING PATH (<600ms feel latency):
            # If caller says "hello", "hello hello", "नमस्ते", respond immediately with warm Hindi clinic greeting.
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            if clean_user_toks and clean_user_toks.issubset({"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}):
                is_pure_greeting = True"""

new_pure_greeting = """            # FAST GREETING PATH (<600ms feel latency):
            # If caller says "hello", "hello hello", "नमस्ते", respond immediately with warm bilingual clinic greeting.
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set_hi = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}
            greeting_set_en = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"}
            lang = self.detect_lang(user_text)
            if clean_user_toks and (clean_user_toks.issubset(greeting_set_hi) or clean_user_toks.issubset(greeting_set_en)):
                is_pure_greeting = True"""

content = content.replace(old_pure_greeting, new_pure_greeting)

# 4. Update the fast greeting pieces in stream_generator
old_fast_pieces = """                if is_pure_greeting:
                    fast_pieces = [
                        "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                    ]"""

new_fast_pieces = """                if is_pure_greeting:
                    if lang == "en":
                        fast_pieces = [
                            "Sure, how can I help you today?"
                        ]
                    else:
                        fast_pieces = [
                            "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                        ]"""

content = content.replace(old_fast_pieces, new_fast_pieces)

# 5. Update Twilio /twilio/voice and /twilio/turn to support both languages
old_twilio_voice = """        @web_app.api_route("/twilio/voice", methods=["GET", "POST"])
        async def twilio_voice(req: Request):
            import xml.sax.saxutils as xml_escape
            from fastapi.responses import Response
            host = req.headers.get("x-forwarded-host") or req.headers.get("host") or "kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run"
            base_url = f"https://{host}"
            greeting_text = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            escaped_greeting = xml_escape.escape(greeting_text)

            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN" voice="Polly.Aditi">{escaped_greeting}</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5">
    </Gather>
    <Say language="hi-IN" voice="Polly.Aditi">क्या आप कुछ पूछना चाहते हैं? कृपया बोलिए।</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")"""

new_twilio_voice = """        @web_app.api_route("/twilio/voice", methods=["GET", "POST"])
        async def twilio_voice(req: Request):
            import xml.sax.saxutils as xml_escape
            from fastapi.responses import Response
            host = req.headers.get("x-forwarded-host") or req.headers.get("host") or "kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run"
            base_url = f"https://{host}"
            # Default to Hindi, but could be extended with language detection from call context
            greeting_text = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            escaped_greeting = xml_escape.escape(greeting_text)

            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN" voice="Polly.Aditi">{escaped_greeting}</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5">
    </Gather>
    <Say language="hi-IN" voice="Polly.Aditi">क्या आप कुछ पूछना चाहते हैं? कृपया बोलिए।</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")"""

content = content.replace(old_twilio_voice, new_twilio_voice)

# Write back
with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Greeting patches applied successfully.")
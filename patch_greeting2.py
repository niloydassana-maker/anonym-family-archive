# -*- coding: utf-8 -*-
import re

with open(r"D:\anonym\modal_voice_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update /api/chat greeting logic
old1 = '''            # FAST GREETING INTERCEPT (Baba Law: natural clinic welcome, never reversed pronoun)
            clean_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम", "start", "शुरू"}
            if not clean_toks or clean_toks.issubset(greeting_set):
                full_reply = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            else:
                clauses = list(self.llm_stream_clauses(user_text, history=session_history))
                full_reply = " ".join(clauses).strip()
                if not full_reply:
                    full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"'''

new1 = '''            # FAST GREETING INTERCEPT (Baba Law: natural clinic welcome, never reversed pronoun)
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
                        full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"'''

content = content.replace(old1, new1)

# 2. Update greetings set in /turn
old2 = '''            greetings = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "प्रणाम", "हाय", "hi", "सुनिए", "हाँ", "हा", "ji", "जी"}

            def is_hallucination(text):'''

new2 = '''            greetings_hi = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "प्रणाम", "हाय", "hi", "सुनिए", "हाँ", "हा", "ji", "जी"}
            greetings_en = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "yes", "yeah", "yep"}
            greetings = greetings_hi | greetings_en

            def is_hallucination(text):'''

content = content.replace(old2, new2)

# 3. Update pure greeting check in stream_generator
old3 = '''            # FAST GREETING PATH (<600ms feel latency):
            # If caller says "hello", "hello hello", "नमस्ते", respond immediately with warm Hindi clinic greeting.
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            if clean_user_toks and clean_user_toks.issubset({"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}):
                is_pure_greeting = True'''

new3 = '''            # FAST GREETING PATH (<600ms feel latency):
            # If caller says "hello", "hello hello", "नमस्ते", respond immediately with warm bilingual clinic greeting.
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\\w\\u0900-\\u097f]+", " ", user_text.lower()).split())
            greeting_set_hi = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}
            greeting_set_en = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"}
            lang = self.detect_lang(user_text)
            if clean_user_toks and (clean_user_toks.issubset(greeting_set_hi) or clean_user_toks.issubset(greeting_set_en)):
                is_pure_greeting = True'''

content = content.replace(old3, new3)

# 4. Update fast greeting pieces
old4 = '''                if is_pure_greeting:
                    fast_pieces = [
                        "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                    ]'''

new4 = '''                if is_pure_greeting:
                    if lang == "en":
                        fast_pieces = [
                            "Sure, how can I help you today?"
                        ]
                    else:
                        fast_pieces = [
                            "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                        ]'''

content = content.replace(old4, new4)

with open(r"D:\anonym\modal_voice_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Greeting patches applied successfully.")
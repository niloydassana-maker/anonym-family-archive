import xml.sax.saxutils as xml_escape

PATCH_SCRIPT = """
import re

with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Pattern to match the old twilio_voice and twilio_turn
pattern = r'        @web_app\.api_route\("/twilio/voice", methods=\["GET", "POST"\]).*?        @web_app\.post\("/turn"\)'

replacement = '''        @web_app.api_route("/twilio/voice", methods=["GET", "POST"])
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
            return Response(content=twiml, media_type="application/xml")

        @web_app.api_route("/twilio/turn", methods=["GET", "POST"])
        async def twilio_turn(req: Request):
            import xml.sax.saxutils as xml_escape
            import asyncio
            from fastapi.responses import Response
            host = req.headers.get("x-forwarded-host") or req.headers.get("host") or "kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run"
            base_url = f"https://{host}"
            form_data = {}
            if req.method == "POST":
                try:
                    form_data = await req.form()
                except Exception:
                    pass
            speech_result = (form_data.get("SpeechResult") or req.query_params.get("SpeechResult") or "").strip()
            call_sid = (form_data.get("CallSid") or req.query_params.get("CallSid") or "twilio_default").strip()

            if not speech_result:
                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN" voice="Polly.Aditi">माफ़ कीजिए, आपकी आवाज़ सुनाई नहीं दी। क्या आप क्लिनिक या अपॉइंटमेंट के बारे में कुछ पूछना चाहते हैं?</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>
</Response>"""
                return Response(content=twiml, media_type="application/xml")

            now = time.time()
            if not hasattr(self, "sessions"):
                self.sessions = {}
            if call_sid not in self.sessions:
                self.sessions[call_sid] = {"history": [], "last_seen": now}
            sess = self.sessions[call_sid]
            if now - sess.get("last_seen", 0) > 300:
                sess["history"] = []
            sess["last_seen"] = now
            session_history = list(sess.get("history", []))

            def get_llm_reply():
                clauses = list(self.llm_stream_clauses(speech_result, history=session_history))
                reply = " ".join(clauses).strip()
                return reply or "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"

            full_reply = await asyncio.to_thread(get_llm_reply)

            sess["history"].append({"role": "user", "content": speech_result})
            sess["history"].append({"role": "assistant", "content": full_reply})
            sess["history"] = sess["history"][-8:]
            sess["last_seen"] = time.time()

            escaped_reply = xml_escape.escape(full_reply)
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN" voice="Polly.Aditi">{escaped_reply}</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5">
    </Gather>
    <Say language="hi-IN" voice="Polly.Aditi">क्या कोई और सहायता चाहिए?</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")

        @web_app.post("/turn")'''

new_code, count = re.subn(pattern, replacement, code, flags=re.DOTALL)
print(f"Replaced {count} matches")
if count == 1:
    with open('d:/anonym/modal_voice_service.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    print("Successfully patched modal_voice_service.py")
else:
    print("Match count was not 1, aborting write")
"""

with open('d:/anonym/patch_twilio_speed.py', 'w', encoding='utf-8') as f:
    f.write(PATCH_SCRIPT)
print("Wrote patch_twilio_speed.py")

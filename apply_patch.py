# -*- coding: utf-8 -*-
with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

v_start = None
t_end = None

for i, l in enumerate(lines):
    if '@web_app.api_route("/twilio/voice"' in l:
        v_start = i
    if v_start is not None and '@web_app.post("/turn")' in l:
        t_end = i
        break

print(f"Found block from line {v_start} to {t_end}")

if v_start is not None and t_end is not None:
    new_block = [
        '        @web_app.api_route("/twilio/voice", methods=["GET", "POST"])\n',
        '        async def twilio_voice(req: Request):\n',
        '            import xml.sax.saxutils as xml_escape\n',
        '            from fastapi.responses import Response\n',
        '            host = req.headers.get("x-forwarded-host") or req.headers.get("host") or "kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run"\n',
        '            base_url = f"https://{host}"\n',
        '            greeting_text = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"\n',
        '            escaped_greeting = xml_escape.escape(greeting_text)\n',
        '\n',
        '            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>\n',
        '<Response>\n',
        '    <Say language="hi-IN" voice="Polly.Aditi">{escaped_greeting}</Say>\n',
        '    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5">\n',
        '    </Gather>\n',
        '    <Say language="hi-IN" voice="Polly.Aditi">क्या आप कुछ पूछना चाहते हैं? कृपया बोलिए।</Say>\n',
        '    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>\n',
        '</Response>"""\n',
        '            return Response(content=twiml, media_type="application/xml")\n',
        '\n',
        '        @web_app.api_route("/twilio/turn", methods=["GET", "POST"])\n',
        '        async def twilio_turn(req: Request):\n',
        '            import xml.sax.saxutils as xml_escape\n',
        '            from fastapi.responses import Response\n',
        '            host = req.headers.get("x-forwarded-host") or req.headers.get("host") or "kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run"\n',
        '            base_url = f"https://{host}"\n',
        '            form_data = {}\n',
        '            if req.method == "POST":\n',
        '                try:\n',
        '                    form_data = await req.form()\n',
        '                except Exception:\n',
        '                    pass\n',
        '            speech_result = (form_data.get("SpeechResult") or req.query_params.get("SpeechResult") or "").strip()\n',
        '            call_sid = (form_data.get("CallSid") or req.query_params.get("CallSid") or "twilio_default").strip()\n',
        '\n',
        '            if not speech_result:\n',
        '                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>\n',
        '<Response>\n',
        '    <Say language="hi-IN" voice="Polly.Aditi">माफ़ कीजिए, आपकी आवाज़ सुनाई नहीं दी। क्या आप क्लिनिक या अपॉइंटमेंट के बारे में कुछ पूछना चाहते हैं?</Say>\n',
        '    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>\n',
        '</Response>"""\n',
        '                return Response(content=twiml, media_type="application/xml")\n',
        '\n',
        '            now = time.time()\n',
        '            if not hasattr(self, "sessions"):\n',
        '                self.sessions = {}\n',
        '            if call_sid not in self.sessions:\n',
        '                self.sessions[call_sid] = {"history": [], "last_seen": now}\n',
        '            sess = self.sessions[call_sid]\n',
        '            if now - sess.get("last_seen", 0) > 300:\n',
        '                sess["history"] = []\n',
        '            sess["last_seen"] = now\n',
        '            session_history = list(sess.get("history", []))\n',
        '\n',
        '            clauses = list(self.llm_stream_clauses(speech_result, history=session_history))\n',
        '            full_reply = " ".join(clauses).strip()\n',
        '            if not full_reply:\n',
        '                full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"\n',
        '\n',
        '            sess["history"].append({"role": "user", "content": speech_result})\n',
        '            sess["history"].append({"role": "assistant", "content": full_reply})\n',
        '            sess["history"] = sess["history"][-8:]\n',
        '            sess["last_seen"] = time.time()\n',
        '\n',
        '            escaped_reply = xml_escape.escape(full_reply)\n',
        '            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>\n',
        '<Response>\n',
        '    <Say language="hi-IN" voice="Polly.Aditi">{escaped_reply}</Say>\n',
        '    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5">\n',
        '    </Gather>\n',
        '    <Say language="hi-IN" voice="Polly.Aditi">क्या कोई और सहायता चाहिए?</Say>\n',
        '    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>\n',
        '</Response>"""\n',
        '            return Response(content=twiml, media_type="application/xml")\n',
        '\n'
    ]
    lines[v_start:t_end] = new_block
    with open('d:/anonym/modal_voice_service.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("SUCCESS: modal_voice_service.py updated with fast Polly Twilio handlers!")
else:
    print("FAILED to find block boundaries!")

import os

with open('d:/anonym/web_template.py', 'r', encoding='utf-8') as f:
    wt = f.read()

start = wt.find('WEB_DEMO_HTML = """')
end = wt.rfind('"""') + 3
html_def = wt[start:end]

with open('d:/anonym/modal_voice_service.py', 'r', encoding='utf-8') as f:
    mvs = f.read()

# 1. Insert WEB_DEMO_HTML after CLINIC_SYSTEM_PROMPT
prompt_marker = 'CLINIC_SYSTEM_PROMPT = """'
prompt_end = mvs.find('"""', mvs.find(prompt_marker) + len(prompt_marker)) + 3

mvs = mvs[:prompt_end] + "\n\n" + html_def + "\n" + mvs[prompt_end:]

# 2. Insert endpoints before @web_app.post("/turn")
endpoints_code = '''        def pcm_to_wav(pcm_bytes: bytes, sr: int = 24000) -> bytes:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm_bytes)
            return buf.getvalue()

        @web_app.get("/")
        def web_index():
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=WEB_DEMO_HTML)

        @web_app.post("/api/chat")
        async def api_chat(req: Request):
            from fastapi.responses import JSONResponse
            import uuid
            data = await req.json()
            user_text = (data.get("text") or "").strip()
            session_id = (data.get("session_id") or "web_doc_session").strip()

            if not user_text:
                return JSONResponse({"error": "No text provided"}, status_code=400)

            host = req.headers.get("x-forwarded-host") or req.headers.get("host") or "kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run"
            base_url = f"https://{host}"

            now = time.time()
            if not hasattr(self, "sessions"):
                self.sessions = {}
            if session_id not in self.sessions:
                self.sessions[session_id] = {"history": [], "last_seen": now}
            sess = self.sessions[session_id]
            if now - sess.get("last_seen", 0) > 600:
                sess["history"] = []
            sess["last_seen"] = now
            session_history = list(sess.get("history", []))

            clauses = list(self.llm_stream_clauses(user_text, history=session_history))
            full_reply = " ".join(clauses).strip()
            if not full_reply:
                full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"

            sess["history"].append({"role": "user", "content": user_text})
            sess["history"].append({"role": "assistant", "content": full_reply})
            sess["history"] = sess["history"][-8:]
            sess["last_seen"] = time.time()

            pcm = self.synthesize_pcm(full_reply, speed=TTS_DEFAULT_SPEED)
            wav_bytes = pcm_to_wav(pcm)
            audio_id = uuid.uuid4().hex
            if not hasattr(self, "audio_cache"):
                self.audio_cache = {}
            self.audio_cache[audio_id] = (wav_bytes, time.time())

            b64_audio = base64.b64encode(wav_bytes).decode("ascii")

            return JSONResponse({
                "reply": full_reply,
                "audio_url": f"{base_url}/twilio/audio/{audio_id}.wav",
                "audio_b64": b64_audio,
                "session_id": session_id
            })

        @web_app.get("/twilio/audio/{audio_id}.wav")
        def twilio_audio(audio_id: str):
            from fastapi.responses import Response
            if not hasattr(self, "audio_cache"):
                self.audio_cache = {}
            item = self.audio_cache.get(audio_id)
            if not item:
                return Response(status_code=404, content="Audio not found")
            return Response(
                content=item[0],
                media_type="audio/wav",
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Content-Disposition": f'inline; filename="{audio_id}.wav"'
                }
            )

        @web_app.api_route("/twilio/voice", methods=["GET", "POST"])
        async def twilio_voice(req: Request):
            import uuid
            from fastapi.responses import Response
            host = req.headers.get("x-forwarded-host") or req.headers.get("host") or "kunal-colab--kilo-voice-clinic-kilovoiceservice-web.modal.run"
            base_url = f"https://{host}"
            greeting_text = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            pcm = self.synthesize_pcm(greeting_text, speed=TTS_DEFAULT_SPEED)
            audio_id = uuid.uuid4().hex
            now = time.time()
            if not hasattr(self, "audio_cache"):
                self.audio_cache = {}
            stale_audio = [k for k, v in self.audio_cache.items() if now - v[1] > 600]
            for k in stale_audio:
                self.audio_cache.pop(k, None)
            self.audio_cache[audio_id] = (pcm_to_wav(pcm), now)

            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{base_url}/twilio/audio/{audio_id}.wav</Play>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5">
    </Gather>
    <Say language="hi-IN" voice="Polly.Aditi">क्या आप कुछ पूछना चाहते हैं? कृपया बोलिए।</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")

        @web_app.api_route("/twilio/turn", methods=["GET", "POST"])
        async def twilio_turn(req: Request):
            import uuid
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

            clauses = list(self.llm_stream_clauses(speech_result, history=session_history))
            full_reply = " ".join(clauses).strip()
            if not full_reply:
                full_reply = "जी, बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"

            sess["history"].append({"role": "user", "content": speech_result})
            sess["history"].append({"role": "assistant", "content": full_reply})
            sess["history"] = sess["history"][-8:]
            sess["last_seen"] = time.time()

            pcm = self.synthesize_pcm(full_reply, speed=TTS_DEFAULT_SPEED)
            audio_id = uuid.uuid4().hex
            if not hasattr(self, "audio_cache"):
                self.audio_cache = {}
            self.audio_cache[audio_id] = (pcm_to_wav(pcm), time.time())

            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{base_url}/twilio/audio/{audio_id}.wav</Play>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5">
    </Gather>
    <Say language="hi-IN" voice="Polly.Aditi">क्या कोई और सहायता चाहिए?</Say>
    <Gather input="speech" action="{base_url}/twilio/turn" language="hi-IN" speechTimeout="auto" timeout="5"/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")

'''

turn_marker = '        @web_app.post("/turn")'
if turn_marker in mvs:
    mvs = mvs.replace(turn_marker, endpoints_code + turn_marker, 1)
    with open('d:/anonym/modal_voice_service.py', 'w', encoding='utf-8') as f:
        f.write(mvs)
    print("SUCCESS: Embedded HTML and endpoints into modal_voice_service.py")
else:
    print("ERROR: turn_marker not found")

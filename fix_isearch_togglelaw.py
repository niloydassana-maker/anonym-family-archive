with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

def rep(old, new, name):
    global c
    n = c.count(old)
    if n != 1:
        raise SystemExit('ABORT: %s matched %d times. No changes written.' % (name, n))
    c = c.replace(old, new)
    print('patched: %s' % name)

rep(r'''    def llm_stream_clauses(self, user_text: str, history: list = None):
        lang = self.detect_lang(user_text)''', r'''    def llm_stream_clauses(self, user_text: str, history: list = None, lang_override: str = None):
        lang = lang_override if lang_override in ("hi", "en") else self.detect_lang(user_text)''', 'llm lang_override')

rep(r'''    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None):
        lang = self.detect_lang(user_text)
        system_prompt = CLINIC_SYSTEM_PROMPT if lang == "hi" else CLINIC_SYSTEM_PROMPT_EN''', r'''    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None, lang: str = None):
        lang = lang if lang in ("hi", "en") else self.detect_lang(user_text)
        system_prompt = CLINIC_SYSTEM_PROMPT if lang == "hi" else CLINIC_SYSTEM_PROMPT_EN''', 'llm prompt select')

rep(r'''        for clause in self._llm_api_clauses(user_text, hint, history=history):''', r'''        for clause in self._llm_api_clauses(user_text, hint, history=history, lang=lang):''', 'llm pass lang')

rep(r'''    def synthesize_pcm(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", postprocess: bool = True,
        collapse_pauses: bool = False, temperature: float = 0.65,
    ) -> bytes:
        chunks = list(self.synthesize_pcm_stream(text, speed=speed))''', r'''    def synthesize_pcm(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", postprocess: bool = True,
        collapse_pauses: bool = False, temperature: float = 0.65,
        lang: str = None,
    ) -> bytes:
        chunks = list(self.synthesize_pcm_stream(text, speed=speed, lang=lang))''', 'synthesize_pcm lang')

rep(r'''    def synthesize_pcm_stream(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", stream_chunk_size: int = 10,
        temperature: float = 0.65,
    ):''', r'''    def synthesize_pcm_stream(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", stream_chunk_size: int = 10,
        temperature: float = 0.65,
        lang: str = None,
    ):''', 'synthesize_pcm_stream lang param')

rep(r'''        if not text or not text.strip():
            return
        lang = self.detect_lang(text)
        if lang == "hi":''', r'''        if not text or not text.strip():
            return
        lang = lang if lang in ("hi", "en") else self.detect_lang(text)
        if lang == "hi":''', 'synthesize explicit wins')

rep(r'''            # STT
            user_text = direct_text
            stt_ms = 0''', r'''            # STT
            user_text = direct_text
            stt_ms = 0
            # TOGGLE LAW (Baba): explicit hi/en from toggle/header/query/JSON
            # rules the whole turn (STT+LLM+TTS+greeting+clarify). auto/absent
            # falls back to detection as before.
            _j_lang = j_dict.get("lang", "") if isinstance(j_dict, dict) else ""
            _req_lang = (req.headers.get("X-Voice-Lang", "") or req.query_params.get("lang", "") or _j_lang).strip().lower()
            if _req_lang in ("hi", "hi-in", "hindi"):
                turn_lang_req = "hi"
            elif _req_lang in ("en", "en-us", "english"):
                turn_lang_req = "en"
            else:
                turn_lang_req = "auto"''', 'turn_lang_req')

rep(r'''                    # Auto-detect language (supports both Hindi and English naturally)
                    j_lang = j.get("lang", "") if ("json" in content_type and "j" in locals() and isinstance(j, dict)) else ""
                    req_lang = (req.headers.get("X-Voice-Lang", "") or req.query_params.get("lang", "") or j_lang).strip().lower()
                    # Respect explicit overrides; auto means Whisper actually detects the
                    # spoken language. The old code forced every non-English request to hi,
                    # which damaged short English/Hinglish utterances from the phone.
                    if req_lang in ("hi", "hi-in", "hindi"):
                        whisper_lang = "hi"
                    elif req_lang in ("en", "en-us", "english"):
                        whisper_lang = "en"
                    else:
                        whisper_lang = None''', r'''                    # Toggle drives Whisper; auto/absent lets Whisper detect.
                    if turn_lang_req == "hi":
                        whisper_lang = "hi"
                    elif turn_lang_req == "en":
                        whisper_lang = "en"
                    else:
                        whisper_lang = None''', 'whisper toggle-driven')

rep(r'''                    user_text = " ".join([s.text for s in segments]).strip()
                    det_l = getattr(info, "language", "")
                    det_prob = getattr(info, "language_probability", None)''', r'''                    user_text = " ".join([s.text for s in segments]).strip()
                    det_l = getattr(info, "language", "")
                    det_prob = getattr(info, "language_probability", None)
                    turn_lang = turn_lang_req if turn_lang_req in ("hi", "en") else self.detect_lang(user_text)''', 'turn_lang resolve')

rep(r'''                    if (det_l in ("ur", "mr", "ne", "pa", "bn") or has_arabic) and whisper_lang != "en":''', r'''                    if (det_l in ("ur", "mr", "ne", "pa", "bn") or has_arabic) and turn_lang != "en":''', 'bengali guard toggle-aware')

rep(r'''                except Exception as e:
                    print(f"[TURN STT ERR] {e}", flush=True)
                    det_l = "error"
                    det_prob = None''', r'''                except Exception as e:
                    print(f"[TURN STT ERR] {e}", flush=True)
                    det_l = "error"
                    det_prob = None
                    turn_lang = turn_lang_req if turn_lang_req in ("hi", "en") else self.detect_lang(user_text)''', 'turn_lang except path')

rep(r'''            else:
                det_l = "text"
                det_prob = None''', r'''            else:
                det_l = "text"
                det_prob = None
                turn_lang = turn_lang_req if turn_lang_req in ("hi", "en") else self.detect_lang(user_text)''', 'turn_lang text path')

rep(r'''            turn_lang = self.detect_lang(user_text)
            if clean_user_toks and (clean_user_toks.issubset(_greet_hi) or clean_user_toks.issubset(_greet_en)):''', r'''            # turn_lang already resolved above: explicit toggle wins, else detected.
            if clean_user_toks and (clean_user_toks.issubset(_greet_hi) or clean_user_toks.issubset(_greet_en)):''', 'turn greeting uses toggle lang')

rep(r'''                if clarify:
                    _clar_lang = self.detect_lang(heard_raw) if heard_raw else "hi"''', r'''                if clarify:
                    _clar_lang = turn_lang''', 'clarify toggle lang')

rep(r'''                clauses = list(self.llm_stream_clauses(user_text, history=session_history))''', r'''                clauses = list(self.llm_stream_clauses(user_text, history=session_history, lang_override=lang))''', 'api_chat thread lang')

rep(r'''            pcm = self.synthesize_pcm(full_reply, speed=TTS_DEFAULT_SPEED)''', r'''            pcm = self.synthesize_pcm(full_reply, speed=TTS_DEFAULT_SPEED, lang=lang)''', 'api_chat tts lang')

rep(r'''                    for clause in self.llm_stream_clauses(user_text, history=session_history):''', r'''                    for clause in self.llm_stream_clauses(user_text, history=session_history, lang_override=turn_lang):''', 'turn llm lang')

rep(r'''                            for pcm_part in self.synthesize_pcm_stream(text, speed=turn_speed):''', r'''                            for pcm_part in self.synthesize_pcm_stream(text, speed=turn_speed, lang=turn_lang):''', 'turn tts lang')

rep(r'''                turn_event(
                    src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                    heard=user_text, reply=full_reply,
                    first_pcm_ms=t_first_pcm or total_ms, total_ms=total_ms,
                    llm_local=self.llm_local_name, tts_speed=turn_speed,
                    stt_language=det_l, stt_language_probability=det_prob,
                )''', r'''                turn_event(
                    src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                    heard=user_text, reply=full_reply,
                    first_pcm_ms=t_first_pcm or total_ms, total_ms=total_ms,
                    llm_local=self.llm_local_name, tts_speed=turn_speed,
                    stt_language=det_l, stt_language_probability=det_prob,
                    turn_lang=turn_lang,
                )''', 'turn_event lang field')

rep(r'''                            pcm = await asyncio.to_thread(self.synthesize_pcm, clarify_text, turn_speed)''', r'''                            pcm = await asyncio.to_thread(self.synthesize_pcm, clarify_text, turn_speed, lang=turn_lang)''', 'clarify tts lang')

with open(r'D:\anonym\modal_voice_service_isearch.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('TOGGLE LAW APPLIED')

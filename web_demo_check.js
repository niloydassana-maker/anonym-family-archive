
        const sessionId = "doc_web_" + Math.random().toString(36).substring(2, 9);
        const audioStore = {};
        let currentlyPlayingId = null;
        let isRecording = false;
        let liveMode = false;
        let assistantBusy = false;
        let micStream = null;
        let micContext = null;
        let micAnalyser = null;
        let vadTimer = null;
        let mediaRecorder = null;
        let recordedChunks = [];
        let captureStartedAt = 0;
        let speechCandidateAt = 0;
        let lastVoiceAt = 0;
        let noiseRms = 0;
        let speechDetected = false;
        let discardRecording = false;
        let currentLang = 'hi-IN'; // 'hi-IN' or 'en-IN'

        // Single shared HTML5 Audio Element to guarantee permanent iOS/Android autoplay
        const player = new Audio();
        let audioUnlocked = false;

        function unlockAudio() {
            if (!audioUnlocked) {
                // Play tiny silent wav buffer on first user touch/click
                player.src = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==';
                player.play().then(() => {
                    audioUnlocked = true;
                    player.pause();
                }).catch(() => {});
            }
        }

        // ---- i18n: every label follows the toggle (Baba order) ----
        var STR_EN = {
          heroSub:"Live Receptionist Demo \u2022 English Voice",
          doctorH2:"Dr. Anupam Ghosh / Dr. Lotika Purohit Clinic",
          doctorP:"AI voice assistant \u2014 appointments, clinic timings and general consultation",
          voiceTag:"🎙\uFE0F Magpie Leo (English)",
          greetText:"Hello! Welcome to Dr. Lotika Purohit's SugarDoctor Clinic. How can I help you today?",
          greetBtn:"Play greeting",
          thinkText:"AI is thinking and generating voice...",
          statusStart:"Start a conversation",
          stopLive:"Stop live conversation",
          startLive:"Start live conversation",
          answering:"Replying\u2026",
          listening:"Listening\u2026",
          listeningAgain:"Listening again\u2026",
          phType:"Speak in English or type...",
          phListen:"Listening... please speak...",
          playVoice:"Hear the voice",
          stopBtn:"Stop",
          micTitle:"Tap to speak",
          sendTitle:"Send",
          langTitle:"Change language",
          errMicStart:"Microphone did not start. Allow microphone for this site in the browser and try again.",
          errMicRecord:"Could not record from the mic. Please start again.",
          errMicAgain:"Mic recording did not start. Please tap the mic again.",
          errSend:"There was a problem sending the audio. Please speak again.",
          errNoReply:"Sorry, no reply was received.",
          errServer:"There was a problem reaching the server. Please try again.",
          errNoAudio:"The audio was not clear. Please speak again.",
          defaultReply:"Clinic reply",
          greetLoading:"Loading voice..."
        };
        function pageLang(){ return currentLang === 'hi-IN' ? 'hi' : 'en'; }
        function L(k){ if (pageLang() === 'en' && STR_EN[k] !== undefined) return STR_EN[k]; return null; }
        var __ORIG = null;
        function snapshotOrig(){
          if (__ORIG) return;
          function tx(id){ var e = document.getElementById(id); return e ? e.innerText : ''; }
          var tgl = document.getElementById('langToggleBtn');
          var ui = document.getElementById('userInput');
          var mb = document.getElementById('micBtn');
          var sb = document.getElementById('sendBtn');
          var gb = document.getElementById('btn_greeting');
          var gs = gb ? gb.querySelector('.btn-text') : null;
          __ORIG = {heroSub:tx('heroSub'), doctorH2:tx('doctorH2'), doctorP:tx('doctorP'),
            voiceTag:tx('voiceTag'), greetText:tx('greetText'),
            greetBtn:gs?gs.innerText:'', toggle:tgl?tgl.innerText:'',
            toggleTitle:tgl?tgl.title:'', micTitle:mb?mb.title:'', sendTitle:sb?sb.title:'',
            ph:ui?ui.placeholder:''};
        }
        function applyLang(){
          snapshotOrig();
          var en = (pageLang() === 'en');
          var o = __ORIG;
          function setT(id, v){ var e = document.getElementById(id); if (e) e.innerText = v; }
          if (document.documentElement) document.documentElement.lang = en ? 'en' : 'hi';
          setT('heroSub', en ? STR_EN.heroSub : o.heroSub);
          setT('doctorH2', en ? STR_EN.doctorH2 : o.doctorH2);
          setT('doctorP', en ? STR_EN.doctorP : o.doctorP);
          setT('voiceTag', en ? STR_EN.voiceTag : o.voiceTag);
          setT('greetText', en ? STR_EN.greetText : o.greetText);
          var tgl = document.getElementById('langToggleBtn');
          if (tgl) { tgl.className = 'lang-toggle-btn ' + (en ? 'active-en' : 'active-hi');
            tgl.innerText = en ? '🌐 English' : o.toggle;
            tgl.title = en ? STR_EN.langTitle : o.toggleTitle; }
          var mic = document.getElementById('micBtn'); if (mic) mic.title = en ? STR_EN.micTitle : o.micTitle;
          var snd = document.getElementById('sendBtn'); if (snd) snd.title = en ? STR_EN.sendTitle : o.sendTitle;
          var inp = document.getElementById('userInput');
          if (inp && !isRecording) inp.placeholder = en ? STR_EN.phType : o.ph;
          try { delete audioStore['greeting']; } catch (e) {}
          var chips = document.querySelectorAll('.chip');
          for (var i = 0; i < chips.length; i++) {
            var txt = chips[i].textContent || '';
            var isHi = /[\u0900-\u097F]/.test(txt);
            chips[i].style.display = ((en && !isHi) || (!en && isHi)) ? '' : 'none';
          }
          var labels = document.querySelectorAll('.play-btn .btn-text');
          for (var j = 0; j < labels.length; j++) {
            var b = labels[j].closest ? labels[j].closest('.play-btn') : null;
            var playing = b && b.classList.contains('playing');
            var kind = (b && b.getAttribute('data-kind')) || (b && b.id === 'btn_greeting' ? 'greet' : 'play');
            var txhi = (b && b.getAttribute('data-txhi')) || labels[j].innerText;
            labels[j].innerText = playing ? (en ? STR_EN.stopBtn : txhi) : (kind === 'greet' ? (en ? STR_EN.greetBtn : txhi) : (en ? STR_EN.playVoice : txhi));
          }
          updateLiveButton();
        }

        // Language toggle for Web Speech
        function toggleLang() {
            unlockAudio();
            if (currentLang === 'hi-IN') { currentLang = 'en-IN'; }
            else { currentLang = 'hi-IN'; }
            applyLang();
        }

        async function toggleMic() {
            unlockAudio();
            if (liveMode) {
                liveMode = false;
                stopLiveCapture();
                updateLiveButton();
                return;
            }
            liveMode = true;
            updateLiveButton();
            await startLiveListen();
        }

        function updateLiveButton() {
            var HI = {stopLive:"\u0932\u093e\u0907\u0935 \u092c\u093e\u0924\u091a\u0940\u0924 \u0930\u094b\u0915\u0947\u0902", startLive:"\u0932\u093e\u0907\u0935 \u092c\u093e\u0924\u091a\u0940\u0924 \u0936\u0941\u0930\u0942 \u0915\u0930\u0947\u0902", statusStart:"\u092c\u093e\u0924\u091a\u0940\u0924 \u0936\u0941\u0930\u0942 \u0915\u0930\u0947\u0902", answering:"\u091c\u0935\u093e\u092c \u0926\u0947 \u0930\u0939\u093e \u0939\u0948\u2026", listening:"\u0938\u0941\u0928 \u0930\u0939\u093e \u0939\u0948\u2026", listeningAgain:"\u092b\u093f\u0930 \u0938\u0941\u0928 \u0930\u0939\u093e \u0939\u0948\u2026"};
            const btn = document.getElementById('micBtn');
            btn.classList.toggle('live-mode', liveMode);
            btn.title = L(liveMode ? 'stopLive' : 'startLive') || (liveMode ? HI.stopLive : HI.startLive);
            btn.innerText = liveMode ? '\u23F9' : '🎤';
            const status = document.getElementById('liveStatus');
            if (status) {
                status.innerText = !liveMode ? (L('statusStart') || HI.statusStart) :
                    assistantBusy ? (L('answering') || HI.answering) :
                    isRecording ? (L('listening') || HI.listening) : (L('listeningAgain') || HI.listeningAgain);
            }
        }

        async function startLiveListen() {
            if (!liveMode || assistantBusy || isRecording) return;
            try {
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
                    throw new Error("इस ब्राउज़र में माइक्रोफ़ोन रिकॉर्डिंग उपलब्ध नहीं है।");
                }
                if (!micStream) {
                    micStream = await navigator.mediaDevices.getUserMedia({
                        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }
                    });
                    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                    micContext = new AudioContextClass({ latencyHint: 'interactive' });
                    await micContext.resume();
                    const source = micContext.createMediaStreamSource(micStream);
                    micAnalyser = micContext.createAnalyser();
                    micAnalyser.fftSize = 1024;
                    source.connect(micAnalyser);
                }
                startLiveCapture();
            } catch (e) {
                console.error("Live microphone capture failed:", e);
                liveMode = false;
                updateLiveButton();
                appendMessage(L('errMicStart') || "माइक्रोफ़ोन शुरू नहीं हुआ। ब्राउज़र में इस साइट के लिए माइक्रोफ़ोन की अनुमति दें और फिर प्रयास करें।", 'ai');
            }
        }

        function scheduleLiveListen(delay = 350) {
            if (!liveMode || assistantBusy) return;
            window.clearTimeout(window.liveListenTimer);
            window.liveListenTimer = window.setTimeout(() => startLiveListen(), delay);
        }

        function startLiveCapture() {
            if (!liveMode || assistantBusy || isRecording || !micStream || !micAnalyser) return;
            try {
                const formats = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'];
                const mimeType = formats.find(type => MediaRecorder.isTypeSupported(type));
                mediaRecorder = mimeType ? new MediaRecorder(micStream, { mimeType }) : new MediaRecorder(micStream);
                recordedChunks = [];
                captureStartedAt = performance.now();
                speechCandidateAt = 0;
                lastVoiceAt = 0;
                noiseRms = 0;
                speechDetected = false;
                discardRecording = false;
                mediaRecorder.ondataavailable = event => {
                    if (event.data && event.data.size) recordedChunks.push(event.data);
                };
                mediaRecorder.onerror = event => {
                    console.error("Microphone recorder error:", event.error || event);
                    stopLiveCapture(true);
                    if (liveMode) {
                        liveMode = false;
                        updateLiveButton();
                        appendMessage(L('errMicRecord') || "माइक से आवाज़ रिकॉर्ड नहीं हो सकी। कृपया दोबारा शुरू करें।", 'ai');
                    }
                };
                mediaRecorder.onstop = async () => {
                    window.clearInterval(vadTimer);
                    const wasSpeech = speechDetected;
                    const discard = discardRecording || !liveMode;
                    const chunks = recordedChunks;
                    recordedChunks = [];
                    mediaRecorder = null;
                    stopMic();
                    if (discard || !wasSpeech || !chunks.length) {
                        if (liveMode) scheduleLiveListen(250);
                        return;
                    }
                    try {
                        await processLiveAudio(new Blob(chunks, { type: chunks[0].type || 'audio/webm' }));
                    } catch (error) {
                        console.error("Live turn failed:", error);
                        appendMessage(L('errSend') || "आवाज़ भेजने में समस्या हुई। कृपया फिर से बोलें।", 'ai');
                        finishAssistantTurn();
                    }
                };
                mediaRecorder.start(200);
                isRecording = true;
                document.getElementById('micBtn').classList.add('recording');
                document.getElementById('userInput').placeholder = L('phListen') || "सुन रहा हूँ... बोलिए...";
                updateLiveButton();
                const samples = new Float32Array(micAnalyser.fftSize);
                vadTimer = window.setInterval(() => {
                    if (!isRecording || !mediaRecorder || mediaRecorder.state !== 'recording') return;
                    micAnalyser.getFloatTimeDomainData(samples);
                    let sum = 0;
                    for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
                    const rms = Math.sqrt(sum / samples.length);
                    const elapsed = performance.now() - captureStartedAt;
                    if (!speechDetected && elapsed < 500) noiseRms = Math.max(noiseRms, rms);
                    const threshold = Math.max(0.012, noiseRms * 2.8);
                    const now = performance.now();
                    if (rms >= threshold) {
                        if (!speechCandidateAt) speechCandidateAt = now;
                        if (!speechDetected && now - speechCandidateAt >= 160) speechDetected = true;
                        if (speechDetected) lastVoiceAt = now;
                    } else if (!speechDetected) {
                        speechCandidateAt = 0;
                    }
                    if (speechDetected && now - lastVoiceAt >= 850) {
                        mediaRecorder.stop();
                    } else if (elapsed >= 20000) {
                        mediaRecorder.stop();
                    }
                }, 80);
            } catch (e) {
                console.error("Could not start microphone recording:", e);
                liveMode = false;
                stopMic();
                updateLiveButton();
                appendMessage(L('errMicAgain') || "माइक रिकॉर्डिंग शुरू नहीं हुई। कृपया फिर से माइक दबाएँ।", 'ai');
            }
        }

        function stopMic() {
            isRecording = false;
            document.getElementById('micBtn').classList.remove('recording');
            document.getElementById('userInput').placeholder = currentLang === 'hi-IN' ? "यहाँ बोलें या टाइप करें..." : "Speak in English or type...";
            updateLiveButton();
        }

        function stopLiveCapture(discard = true) {
            window.clearInterval(vadTimer);
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                discardRecording = discard;
                mediaRecorder.stop();
            }
            if (micStream) {
                micStream.getTracks().forEach(track => track.stop());
                micStream = null;
            }
            if (micContext) {
                micContext.close().catch(() => {});
                micContext = null;
                micAnalyser = null;
            }
        }

        async function blobToWav16k(blob) {
            const decoded = await micContext.decodeAudioData(await blob.arrayBuffer());
            const input = decoded.getChannelData(0);
            const inputRate = decoded.sampleRate;
            const outputRate = 16000;
            const outputLength = Math.max(1, Math.floor(input.length * outputRate / inputRate));
            const pcm = new Int16Array(outputLength);
            for (let i = 0; i < outputLength; i++) {
                const pos = i * inputRate / outputRate;
                const left = Math.floor(pos);
                const fraction = pos - left;
                const a = input[Math.min(left, input.length - 1)] || 0;
                const b = input[Math.min(left + 1, input.length - 1)] || 0;
                const value = Math.max(-1, Math.min(1, a + (b - a) * fraction));
                pcm[i] = value < 0 ? value * 32768 : value * 32767;
            }
            const wav = new ArrayBuffer(44 + pcm.byteLength);
            const view = new DataView(wav);
            const write = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
            write(0, 'RIFF'); view.setUint32(4, 36 + pcm.byteLength, true); write(8, 'WAVE');
            write(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
            view.setUint16(22, 1, true); view.setUint32(24, outputRate, true);
            view.setUint32(28, outputRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
            write(36, 'data'); view.setUint32(40, pcm.byteLength, true);
            new Int16Array(wav, 44).set(pcm);
            return wav;
        }

        function parseLiveTurn(buffer) {
            const bytes = new Uint8Array(buffer);
            const newline = bytes.indexOf(10);
            if (newline < 0) throw new Error("सर्वर से turn header नहीं मिला।");
            const decoder = new TextDecoder();
            const header = JSON.parse(decoder.decode(bytes.subarray(0, newline)));
            let trailerEnd = bytes.length;
            while (trailerEnd > newline + 1 && bytes[trailerEnd - 1] === 10) trailerEnd--;
            let trailerStart = -1;
            let trailer = null;
            for (let i = trailerEnd - 1; i > newline; i--) {
                if (bytes[i] !== 123) continue;
                try {
                    const candidate = JSON.parse(decoder.decode(bytes.subarray(i, trailerEnd)));
                    if (candidate && candidate.end === true) {
                        trailerStart = i;
                        trailer = candidate;
                        break;
                    }
                } catch (_) {}
            }
            if (trailerStart < 0) throw new Error("turn trailer missing");
            return { header, trailer, pcm: bytes.slice(newline + 1, trailerStart) };
        }

        function pcm24kToWav(pcmBytes) {
            const wav = new ArrayBuffer(44 + pcmBytes.byteLength);
            const view = new DataView(wav);
            const write = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
            write(0, 'RIFF'); view.setUint32(4, 36 + pcmBytes.byteLength, true); write(8, 'WAVE');
            write(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
            view.setUint16(22, 1, true); view.setUint32(24, 24000, true);
            view.setUint32(28, 48000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
            write(36, 'data'); view.setUint32(40, pcmBytes.byteLength, true);
            new Uint8Array(wav, 44).set(pcmBytes);
            return wav;
        }

        async function processLiveAudio(blob) {
            assistantBusy = true;
            updateLiveButton();
            const thinkingId = appendThinking();
            try {
                const wav = await blobToWav16k(blob);
                const lang = currentLang === 'hi-IN' ? 'hi' : 'en';
                const response = await fetch(`/turn?speed=1.2&lang=${lang}&session_id=${encodeURIComponent(sessionId)}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'audio/wav', 'X-Session-ID': sessionId, 'X-Voice-Lang': lang },
                    body: wav
                });
                if (!response.ok) throw new Error(`सर्वर ने ${response.status} जवाब दिया।`);
                const parsed = parseLiveTurn(await response.arrayBuffer());
                removeThinking(thinkingId);
                const heard = parsed.trailer.heard || parsed.header.heard || '';
                if (heard) appendMessage(heard, 'user');
                if (parsed.pcm.byteLength) {
                    const turnId = 'live_' + Date.now();
                    const wavReply = pcm24kToWav(parsed.pcm);
                    audioStore[turnId] = URL.createObjectURL(new Blob([wavReply], { type: 'audio/wav' }));
                    appendMessage(parsed.trailer.reply || (L('defaultReply') || "क्लिनिक की ओर से जवाब"), 'ai', turnId);
                    playTurnAudio(turnId);
                } else {
                    appendMessage(L('errNoAudio') || "आवाज़ साफ़ नहीं आई। कृपया फिर से बोलें।", 'ai');
                    finishAssistantTurn();
                }
            } catch (error) {
                removeThinking(thinkingId);
                throw error;
            }
        }

        function handleInput() {
            const val = document.getElementById('userInput').value.trim();
            const btn = document.getElementById('sendBtn');
            if (val) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        }

        function handleKey(e) {
            if (e.key === 'Enter') {
                sendText();
            }
        }

        function askPreset(text) {
            unlockAudio();
            document.getElementById('userInput').value = text;
            handleInput();
            sendText();
        }

        async function sendText() {
            unlockAudio();
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text || assistantBusy) return;

            assistantBusy = true;
            updateLiveButton();
            if (isRecording && mediaRecorder && mediaRecorder.state === 'recording') {
                discardRecording = true;
                mediaRecorder.stop();
            }

            input.value = '';
            handleInput();

            // Append user message
            appendMessage(text, 'user');

            // Append thinking indicator
            const thinkingId = appendThinking();

            try {
                const lang = currentLang === 'hi-IN' ? 'hi' : 'en';
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        session_id: sessionId,
                        lang: lang
                    })
                });

                const data = await res.json();
                removeThinking(thinkingId);

                if (data.reply) {
                    const turnId = 'turn_' + Date.now();
                    // Prefer direct audio_url to avoid huge data URI overhead
                    audioStore[turnId] = data.audio_url || ('data:audio/wav;base64,' + data.audio_b64);
                    appendMessage(data.reply, 'ai', turnId);
                    // Automatic playback of response
                    playTurnAudio(turnId);
                } else {
                    appendMessage(L('errNoReply') || "माफ़ कीजिए, कोई उत्तर नहीं मिल सका।", 'ai');
                    finishAssistantTurn();
                }
            } catch (err) {
                console.error("Chat API error:", err);
                removeThinking(thinkingId);
                appendMessage(L('errServer') || "सर्वर से संपर्क करने में समस्या हुई। कृपया दोबारा प्रयास करें।", 'ai');
                finishAssistantTurn();
            }
        }

        function finishAssistantTurn() {
            assistantBusy = false;
            updateLiveButton();
            scheduleLiveListen();
        }

        function appendMessage(text, role, turnId) {
            const chat = document.getElementById('chat');
            const div = document.createElement('div');
            div.className = `chat-bubble ${role}`;

            let html = `<p>${text}</p>`;
            if (role === 'ai' && turnId) {
                html += `
                    <div class="audio-play-row">
                        <button class="play-btn" data-kind="play" data-txhi="वॉयस सुनें" id="btn_${turnId}" onclick="playTurnAudio('${turnId}')">
                            <span class="btn-icon">▶</span>
                            <span class="btn-text">${L('playVoice') || "वॉयस सुनें"}</span>
                        </button>
                        <div class="wave-bars" style="display:none;" id="wave_${turnId}">
                            <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
                        </div>
                    </div>
                `;
            }
            div.innerHTML = html;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function appendThinking() {
            const chat = document.getElementById('chat');
            const id = "think_" + Date.now();
            const div = document.createElement('div');
            div.id = id;
            div.className = "chat-bubble ai";
            div.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px;">
                    <div class="pulse-dot" style="background:#06B6D4;"></div>
                    <span style="font-size:0.85rem; color:#9CA3AF;">${L('thinkText') || "एआई सोच रहा है और आवाज़ बना रहा है..."}</span>
                </div>
            `;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
            return id;
        }

        function removeThinking(id) {
            const el = document.getElementById(id);
            if (el) el.remove();
        }

        function updatePlayBtn(turnId, isPlaying) {
            const btn = document.getElementById('btn_' + turnId);
            const wave = document.getElementById('wave_' + turnId);
            if (btn) {
                const icon = btn.querySelector('.btn-icon');
                const label = btn.querySelector('.btn-text');
                if (isPlaying) {
                    btn.classList.add('playing');
                    if (icon) icon.innerText = '⏸';
                    if (label) label.innerText = L('stopBtn') || 'रोकें';
                } else {
                    btn.classList.remove('playing');
                    if (icon) icon.innerText = '▶';
                    if (label) label.innerText = L('playVoice') || 'वॉयस सुनें';
                }
            }
            if (wave) {
                wave.style.display = isPlaying ? 'inline-flex' : 'none';
            }
        }

        function playTurnAudio(turnId) {
            unlockAudio();
            const src = audioStore[turnId];
            if (!src) return;

            // If this turn is already playing, pause it
            if (currentlyPlayingId === turnId && !player.paused) {
                player.pause();
                updatePlayBtn(turnId, false);
                currentlyPlayingId = null;
                finishAssistantTurn();
                return;
            }

            // If another turn was playing, stop it
            if (currentlyPlayingId && currentlyPlayingId !== turnId) {
                updatePlayBtn(currentlyPlayingId, false);
            }

            currentlyPlayingId = turnId;
            player.src = src;
            updatePlayBtn(turnId, true);

            player.onended = () => {
                updatePlayBtn(turnId, false);
                currentlyPlayingId = null;
                finishAssistantTurn();
            };

            player.onerror = (e) => {
                console.error("Audio playback error:", e);
                updatePlayBtn(turnId, false);
                currentlyPlayingId = null;
                finishAssistantTurn();
            };

            player.play().catch(e => {
                console.warn("Autoplay deferred until explicit click:", e);
                updatePlayBtn(turnId, false);
                finishAssistantTurn();
            });
        }

        function playGreeting() {
            unlockAudio();
            const turnId = 'greeting';
            if (audioStore[turnId]) {
                playTurnAudio(turnId);
                return;
            }

            const btn = document.getElementById('btn_greeting');
            if (btn) {
                const label = btn.querySelector('.btn-text');
                if (label) label.innerText = L('greetLoading') || 'आवाज़ लोड हो रही है...';
            }

            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: 'hello',
                        lang: (currentLang === 'hi-IN' ? 'hi' : 'en'),
                    session_id: 'greeting_warm'
                })
            })
            .then(r => r.json())
            .then(data => {
                audioStore[turnId] = data.audio_url || ('data:audio/wav;base64,' + data.audio_b64);
                // Greeting is lowest priority: never hijack a newer/active turn (overlap guard).
                if (assistantBusy || (currentlyPlayingId && currentlyPlayingId !== turnId && !player.paused)) { updatePlayBtn(turnId, false); return; }
                playTurnAudio(turnId);
            })
            .catch(err => {
                console.error("Greeting fetch error:", err);
                if (btn) {
                    const label = btn.querySelector('.btn-text');
                    if (label) label.innerText = L('greetBtn') || 'नमस्ते वॉयस सुनें';
                }
            });
        }
    
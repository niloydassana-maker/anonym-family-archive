# -*- coding: utf-8 -*-
"""
SugarDoctor AI Clinic Receptionist - Interactive Web Demo
Designed for Dr. Anupam Ghosh / Dr. Lotika Purohit
Mobile-first, responsive, Web Speech API & HTML5 Audio
v2: AudioContext pre-unlock, AudioStore map, Dual-language Mic (Hi/En), Corrected Hindi Receptionist Cadence
"""

WEB_DEMO_HTML = """<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SugarDoctor AI Receptionist | Live Interactive Demo</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0B0F19;
            --card-bg: rgba(17, 24, 39, 0.85);
            --card-border: rgba(31, 41, 55, 0.7);
            --accent-emerald: #10B981;
            --accent-cyan: #06B6D4;
            --accent-blue: #3B82F6;
            --text-primary: #F9FAFB;
            --text-secondary: #9CA3AF;
            --user-bubble: #1E3A8A;
            --ai-bubble: #1F2937;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'Inter', 'Noto Sans Devanagari', -apple-system, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(6, 182, 212, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.12) 0%, transparent 40%);
        }

        /* HEADER */
        header {
            padding: 0.9rem 1.25rem;
            background: rgba(11, 15, 25, 0.92);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
        }

        .brand-text h1 {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            background: linear-gradient(to right, #FFF, #A7F3D0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-text p {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34D399;
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: #10B981;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        /* MAIN CONTAINER */
        main {
            flex: 1;
            max-width: 760px;
            width: 100%;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            padding: 0.75rem 1rem;
            gap: 0.75rem;
        }

        /* CLINIC HERO CARD */
        .clinic-hero {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 0.85rem 1.15rem;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
        }

        .doctor-info h2 {
            font-size: 0.95rem;
            font-weight: 600;
            color: #E2E8F0;
        }

        .doctor-info p {
            font-size: 0.78rem;
            color: var(--text-secondary);
        }

        .model-tags {
            display: flex;
            gap: 0.4rem;
            flex-wrap: wrap;
        }

        .tag {
            font-size: 0.7rem;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #CBD5E1;
        }

        /* CHAT WINDOW */
        .chat-container {
            flex: 1;
            min-height: 380px;
            max-height: 520px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
            padding: 0.5rem 0.25rem;
            scrollbar-width: thin;
            scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
        }

        .chat-bubble {
            max-width: 88%;
            padding: 0.85rem 1.15rem;
            border-radius: 18px;
            line-height: 1.55;
            font-size: 0.92rem;
            animation: fadeIn 0.25s ease-out;
            position: relative;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .chat-bubble.ai {
            align-self: flex-start;
            background: var(--ai-bubble);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-bottom-left-radius: 4px;
        }

        .chat-bubble.user {
            align-self: flex-end;
            background: linear-gradient(135deg, #1D4ED8, #2563EB);
            color: #FFF;
            border-bottom-right-radius: 4px;
        }

        .audio-play-row {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-top: 0.55rem;
            padding-top: 0.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .play-btn {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #34D399;
            padding: 0.35rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .play-btn:hover {
            background: rgba(16, 185, 129, 0.35);
            transform: scale(1.02);
        }

        .play-btn.playing {
            background: rgba(239, 68, 68, 0.2);
            border-color: rgba(239, 68, 68, 0.4);
            color: #F87171;
        }

        .audio-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        /* WAVEFORM ANIMATION */
        .wave-bars {
            display: inline-flex;
            align-items: center;
            gap: 3px;
            height: 14px;
        }

        .wave-bar {
            width: 3px;
            background-color: #34D399;
            border-radius: 2px;
            animation: wave 1s ease-in-out infinite;
        }

        .wave-bar:nth-child(2) { animation-delay: 0.2s; }
        .wave-bar:nth-child(3) { animation-delay: 0.4s; }
        .wave-bar:nth-child(4) { animation-delay: 0.1s; }

        @keyframes wave {
            0%, 100% { height: 4px; }
            50% { height: 14px; }
        }

        /* PRESET CHIPS */
        .preset-section {
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.4rem;
            scrollbar-width: none;
        }

        .preset-section::-webkit-scrollbar {
            display: none;
        }

        .chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: #E2E8F0;
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.2s;
        }

        .chip:hover {
            background: rgba(6, 182, 212, 0.15);
            border-color: rgba(6, 182, 212, 0.4);
            color: #A5F3FC;
        }

        /* INPUT CONTROL BAR */
        .controls-container {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 0.5rem 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }

        .lang-toggle-btn {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #9CA3AF;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.35rem 0.55rem;
            border-radius: 12px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .lang-toggle-btn.active-hi {
            background: rgba(16, 185, 129, 0.15);
            border-color: rgba(16, 185, 129, 0.3);
            color: #34D399;
        }

        .lang-toggle-btn.active-en {
            background: rgba(59, 130, 246, 0.15);
            border-color: rgba(59, 130, 246, 0.3);
            color: #60A5FA;
        }

        .mic-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-emerald));
            border: none;
            color: #FFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(6, 182, 212, 0.4);
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .mic-btn:hover {
            transform: scale(1.05);
        }

        .mic-btn.recording {
            background: #EF4444;
            box-shadow: 0 0 16px #EF4444;
            animation: pulse-red 1.5s infinite;
        }

        @keyframes pulse-red {
            0% { transform: scale(0.98); }
            50% { transform: scale(1.08); }
            100% { transform: scale(0.98); }
        }

        .text-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-primary);
            font-size: 0.95rem;
            font-family: inherit;
        }

        .text-input::placeholder {
            color: #6B7280;
        }

        .send-btn {
            background: rgba(255, 255, 255, 0.08);
            border: none;
            color: #9CA3AF;
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .send-btn.active {
            background: var(--accent-blue);
            color: #FFF;
        }

        /* FOOTER */
        footer {
            text-align: center;
            padding: 0.6rem 1rem;
            font-size: 0.72rem;
            color: #6B7280;
        }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <div class="brand-icon">🩺</div>
            <div class="brand-text">
                <h1>SugarDoctor AI Clinic</h1>
                <p>Live Receptionist Demo • हिन्दी Voice</p>
            </div>
        </div>
        <div class="status-badge">
            <div class="pulse-dot"></div>
            <span>24/7 Live</span>
        </div>
    </header>

    <main>
        <div class="clinic-hero">
            <div class="doctor-info">
                <h2>डॉक्टर अनुपम घोष / डॉक्टर लोटिका पुरोहित क्लिनिक</h2>
                <p>AI वॉयस असिस्टेंट — अपॉइंटमेंट, क्लिनिक टाइमिंग और सामान्य परामर्श</p>
            </div>
            <div class="model-tags">
                <span class="tag">⚡ Nemotron-120B</span>
                <span class="tag">🎙️ Magpie Leo (Hindi)</span>
                <span class="tag">⏱️ &lt;1.2s Real-time</span>
            </div>
        </div>

        <div class="chat-container" id="chat">
            <div class="chat-bubble ai" id="bubble_greeting">
                <p>नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?</p>
                <div class="audio-play-row">
                    <button class="play-btn" id="btn_greeting" onclick="playGreeting()">
                        <span class="btn-icon">▶</span>
                        <span class="btn-text">नमस्ते वॉयस सुनें</span>
                    </button>
                    <div class="wave-bars" style="display:none;" id="wave_greeting">
                        <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="preset-section">
            <div class="chip" onclick="askPreset('क्लिनिक की टाइमिंग क्या है?')">🩺 क्लिनिक टाइमिंग</div>
            <div class="chip" onclick="askPreset('डॉक्टर से बात करनी है')">👨‍⚕️ डॉक्टर से बात करनी है</div>
            <div class="chip" onclick="askPreset('कल दोपहर 3 बजे अपॉइंटमेंट मिल सकता है?')">📅 कल अपॉइंटमेंट</div>
            <div class="chip" onclick="askPreset('शुगर चेकअप की क्या फीस है?')">💉 चेकअप फीस</div>
            <div class="chip" onclick="askPreset('क्लिनिक का पता कहाँ है?')">📍 क्लिनिक का पता</div>
            <div class="chip" onclick="askPreset('क्या डॉक्टर साहब ऑनलाइन परामर्श भी देते हैं?')">🌐 ऑनलाइन कंसल्टेशन</div>
        </div>

        <div class="controls-container">
            <button id="langToggleBtn" class="lang-toggle-btn active-hi" onclick="toggleLang()" title="भाषा बदलें">🌐 हिन्दी</button>
            <button class="mic-btn" id="micBtn" onclick="toggleMic()" title="बोलने के लिए दबाएँ">🎤</button>
            <input type="text" class="text-input" id="userInput" placeholder="यहाँ बोलें या टाइप करें..." onkeypress="handleKey(event)" oninput="handleInput()">
            <button class="send-btn" id="sendBtn" onclick="sendText()" title="भेजें">➔</button>
        </div>
    </main>

    <footer>
        SugarDoctor Telehealth Suite • Powered by NVIDIA Cloud & Modal Serverless • Zero Client Footprint
    </footer>

    <script>
        const sessionId = "doc_web_" + Math.random().toString(36).substring(2, 9);
        const audioStore = {};
        let currentlyPlayingId = null;
        let isRecording = false;
        let recognition = null;
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

        // Language toggle for Web Speech
        function toggleLang() {
            unlockAudio();
            const btn = document.getElementById('langToggleBtn');
            if (currentLang === 'hi-IN') {
                currentLang = 'en-IN';
                btn.className = 'lang-toggle-btn active-en';
                btn.innerText = '🌐 English';
                document.getElementById('userInput').placeholder = "Speak in English or type...";
            } else {
                currentLang = 'hi-IN';
                btn.className = 'lang-toggle-btn active-hi';
                btn.innerText = '🌐 हिन्दी';
                document.getElementById('userInput').placeholder = "यहाँ बोलें या टाइप करें...";
            }
            if (recognition) {
                recognition.lang = currentLang;
            }
        }

        // Init Web Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = currentLang;

            recognition.onstart = () => {
                isRecording = true;
                document.getElementById('micBtn').classList.add('recording');
                document.getElementById('userInput').placeholder = "सुन रहा हूँ... बोलिए...";
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                if (transcript && transcript.trim()) {
                    document.getElementById('userInput').value = transcript.trim();
                    handleInput();
                    sendText();
                }
            };

            recognition.onerror = (e) => {
                console.warn("Speech recognition error:", e);
                stopMic();
                if (e.error === 'not-allowed') {
                    alert("माइक्रोफ़ोन की अनुमति नहीं मिली। कृपया ब्राउज़र सेटिंग्स में माइक्रोफ़ोन की अनुमति दें!");
                }
            };

            recognition.onend = () => {
                stopMic();
            };
        }

        function toggleMic() {
            unlockAudio();
            if (!recognition) {
                alert("आपके ब्राउज़र में स्पीच रिकग्निशन सपोर्ट नहीं है। कृपया लिखकर पूछें!");
                return;
            }
            if (isRecording) {
                recognition.stop();
            } else {
                try {
                    recognition.lang = currentLang;
                    recognition.start();
                } catch(e) {
                    console.error("Mic start failed:", e);
                }
            }
        }

        function stopMic() {
            isRecording = false;
            document.getElementById('micBtn').classList.remove('recording');
            document.getElementById('userInput').placeholder = currentLang === 'hi-IN' ? "यहाँ बोलें या टाइप करें..." : "Speak in English or type...";
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
            if (!text) return;

            input.value = '';
            handleInput();

            // Append user message
            appendMessage(text, 'user');

            // Append thinking indicator
            const thinkingId = appendThinking();

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        session_id: sessionId
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
                    appendMessage("माफ़ कीजिए, कोई उत्तर नहीं मिल सका।", 'ai');
                }
            } catch (err) {
                console.error("Chat API error:", err);
                removeThinking(thinkingId);
                appendMessage("सर्वर से संपर्क करने में समस्या हुई। कृपया दोबारा प्रयास करें।", 'ai');
            }
        }

        function appendMessage(text, role, turnId) {
            const chat = document.getElementById('chat');
            const div = document.createElement('div');
            div.className = `chat-bubble ${role}`;
            
            let html = `<p>${text}</p>`;
            if (role === 'ai' && turnId) {
                html += `
                    <div class="audio-play-row">
                        <button class="play-btn" id="btn_${turnId}" onclick="playTurnAudio('${turnId}')">
                            <span class="btn-icon">▶</span>
                            <span class="btn-text">वॉयस सुनें</span>
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
                    <span style="font-size:0.85rem; color:#9CA3AF;">एआई सोच रहा है और आवाज़ बना रहा है...</span>
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
                    if (label) label.innerText = 'रोकें';
                } else {
                    btn.classList.remove('playing');
                    if (icon) icon.innerText = '▶';
                    if (label) label.innerText = 'वॉयस सुनें';
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
            };

            player.onerror = (e) => {
                console.error("Audio playback error:", e);
                updatePlayBtn(turnId, false);
                currentlyPlayingId = null;
            };

            player.play().catch(e => {
                console.warn("Autoplay deferred until explicit click:", e);
                updatePlayBtn(turnId, false);
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
                if (label) label.innerText = 'आवाज़ लोड हो रही है...';
            }

            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: 'hello',
                    session_id: 'greeting_warm'
                })
            })
            .then(r => r.json())
            .then(data => {
                audioStore[turnId] = data.audio_url || ('data:audio/wav;base64,' + data.audio_b64);
                playTurnAudio(turnId);
            })
            .catch(err => {
                console.error("Greeting fetch error:", err);
                if (btn) {
                    const label = btn.querySelector('.btn-text');
                    if (label) label.innerText = 'नमस्ते वॉयस सुनें';
                }
            });
        }
    </script>
</body>
</html>
"""

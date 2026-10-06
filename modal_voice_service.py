import sys
import os
import io
import re
import time
import json
import base64
import wave
import urllib.request
from contextlib import nullcontext
import numpy as np
from collections import deque

# Force UTF-8 on Windows consoles
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import modal

app = modal.App("kilo-voice-clinic")

# Production Container Image with local reference audio baked in
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")
    .pip_install(
        "click",
        "faster-whisper",
        "fastapi[standard]",
        "requests",
        "scipy",
        "numpy",
    )
)

# Spoken Hindi receptionist prompt: natural, warm North Indian cadence without canned wording.
CLINIC_SYSTEM_PROMPT = """आप 'शुगरडॉक्टर क्लिनिक' के फोन सहायक हैं। आपकी बोली सहज, गर्मजोशी भरी, और उत्तर भारतीय हिंदी जैसी होनी चाहिए—जैसे कोई समझदार इंसान फोन पर बात करता है, न कि कोई स्क्रिप्ट पढ़ता हुआ रोबोट।
क्लिनिक की महत्वपूर्ण जानकारी:
- मुख्य चिकित्सक: डॉक्टर लोटिका पुरोहित
- समय: सुबह नौ बजे से दोपहर दो बजे तक, और शाम पांच बजे से रात आठ बजे तक (सोमवार से शनिवार, रविवार बंद)
- परामर्श शुल्क: बिल्कुल निशुल्क (मुफ्त परामर्श)

अति-महत्वपूर्ण नियम:
1. देवनागरी हिंदी में बोलें। अंग्रेजी अक्षर न लिखें; जरूरत हो तो परिचित शब्द देवनागरी में लिखें।
2. समय और संख्याओं को केवल हिंदी शब्दों में ही लिखें (जैसे: नौ बजे, दो बजे, पांच बजे, आठ बजे, निशुल्क)। कभी भी अंक (digits जैसे 9:00, 2, 5 आदि) बिल्कुल न लिखें।
3. पहले कॉलर की बात का सीधा जवाब दें। आम तौर पर एक या दो छोटे वाक्य काफी हैं; सवाल के हिसाब से स्वाभाविक रूप से कम-ज्यादा बोलें।
4. बातचीत में हल्की मानवीय गर्मजोशी रखें। जरूरत के मुताबिक कभी "जी", "अच्छा", या "ज़रूर" कहें, मगर हर जवाब में वही तकिया-कलाम न दोहराएँ। प्रश्न को शब्दशः न दोहराएँ और स्वागत वाली तय पंक्ति हर बार न बोलें।
5. एक ही वाक्यांश बार-बार इस्तेमाल न करें। सहज और साफ बोलें, जरूरत से ज्यादा औपचारिक या उत्साही न बनें।
6. हर वाक्य को पूर्ण विराम (।) या प्रश्नवाचक चिह्न (?) पर समाप्त करें।
7. मार्कडाउन, बुलेट या इमोजी न लिखें।
8. अपने बारे में पूछने पर बताएं कि आप क्लिनिक के फोन सहायक हैं। मॉडल या निर्माता का नाम न बताएं।
9. क्लिनिक से बाहर की मांग पर बात न गढ़ें; साफ कहें कि आप क्लिनिक और अपॉइंटमेंट में मदद कर सकते हैं।
10. अपॉइंटमेंट मांगे जाने पर बुकिंग पूरी होने का दावा न करें; नाम और सुविधाजनक समय पूछें।
11. कॉलर का स्वागत करते समय हमेशा कहें: 'मैं आपकी क्या सहायता कर सकता हूँ?'। कभी भी 'आप कैसे मदद कर सकते हैं' न कहें!
12. कॉलर अंग्रेजी या हिंग्लिश में पूछे (जैसे 'I want to talk to a doctor' या 'डॉक्टर से बात करनी है'), तो सहजता से देवनागरी हिंदी में कहें: 'हाँ, बिल्कुल। आप डॉक्टर लोटिका पुरोहित से परामर्श ले सकते हैं। क्या आप अपॉइंटमेंट लेना चाहते हैं?'।
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
            <span id="liveStatus">बातचीत शुरू करें</span>
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
            const btn = document.getElementById('micBtn');
            btn.classList.toggle('live-mode', liveMode);
            btn.title = liveMode ? "लाइव बातचीत रोकें" : "लाइव बातचीत शुरू करें";
            btn.innerText = liveMode ? '⏹' : '🎤';
            const status = document.getElementById('liveStatus');
            if (status) {
                status.innerText = !liveMode ? 'बातचीत शुरू करें' :
                    assistantBusy ? 'जवाब दे रहा है…' :
                    isRecording ? 'सुन रहा है…' : 'फिर सुन रहा है…';
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
                appendMessage("माइक्रोफ़ोन शुरू नहीं हुआ। ब्राउज़र में इस साइट के लिए माइक्रोफ़ोन की अनुमति दें और फिर प्रयास करें।", 'ai');
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
                        appendMessage("माइक से आवाज़ रिकॉर्ड नहीं हो सकी। कृपया दोबारा शुरू करें।", 'ai');
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
                        appendMessage("आवाज़ भेजने में समस्या हुई। कृपया फिर से बोलें।", 'ai');
                        finishAssistantTurn();
                    }
                };
                mediaRecorder.start(200);
                isRecording = true;
                document.getElementById('micBtn').classList.add('recording');
                document.getElementById('userInput').placeholder = "सुन रहा हूँ... बोलिए...";
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
                appendMessage("माइक रिकॉर्डिंग शुरू नहीं हुई। कृपया फिर से माइक दबाएँ।", 'ai');
            }
        }

        function stopMic() {
            isRecording = false;
            document.getElementById('micBtn').classList.remove('recording');
            document.getElementById('userInput').placeholder = "यहाँ बोलें या टाइप करें...";
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
            if (trailerStart < 0) if (end < 0) throw new Error("सर्वर का turn पूरा नहीं हुआ।");
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
                const lang = 'hi';
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
                    appendMessage(parsed.trailer.reply || "क्लिनिक की ओर से जवाब", 'ai', turnId);
                    playTurnAudio(turnId);
                } else {
                    appendMessage("आवाज़ साफ़ नहीं आई। कृपया फिर से बोलें।", 'ai');
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
                    finishAssistantTurn();
                }
            } catch (err) {
                console.error("Chat API error:", err);
                removeThinking(thinkingId);
                appendMessage("सर्वर से संपर्क करने में समस्या हुई। कृपया दोबारा प्रयास करें।", 'ai');
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


# Keep conversational inference on the hosted provider. The Modal CPU container is reserved
# for Whisper and XTTS so LLM weights cannot contend with speech synthesis VRAM.
VOICE_LLM_PROVIDER = "NVIDIA NIM"
VOICE_LLM_MODEL = "nvidia/nemotron-3-super-120b-a12b"
TTS_DEFAULT_SPEED = 1.2
TTS_MODEL = "magpie-tts-multilingual"
TTS_VOICE = "Magpie-Multilingual.HI-IN.Leo"
TTS_RATE_HZ = 22050
TTS_NVCF_URL = "https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com/v1/audio/synthesize_online"

HINDI_NUMBERS = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पांच",
    6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह",
    16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस",
    26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    31: "इकतीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस",
    36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चवालीस", 45: "पैंतालीस",
    46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन",
    56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ",
    66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर",
    76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उन्नासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी",
    86: "छियासी", 87: "सत्तासी", 88: "अठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे",
    96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे", 100: "सौ"
}

def num_to_hindi(n: int) -> str:
    if n in HINDI_NUMBERS:
        return HINDI_NUMBERS[n]
    return " ".join(HINDI_NUMBERS.get(int(d), d) for d in str(n))

def sanitize_hindi_for_xtts(text: str) -> str:
    if not text:
        return ""
    # Map common English clinic words to pure Devanagari Hindi
    subs = [
        (r"(?i)\bsugardoctor\s*clinic\b", "शुगरडॉक्टर क्लिनिक"),
        (r"(?i)\bsugardoctor\b", "शुगरडॉक्टर"),
        (r"(?i)\bclinic\b", "क्लिनिक"),
        (r"(?i)\bdr\.?\s*lotika\s*purohit\b", "डॉक्टर लोटिका पुरोहित"),
        (r"(?i)\bdr\.?\s*lotika\b", "डॉक्टर लोटिका"),
        (r"(?i)\bdr\.?\b", "डॉक्टर"),
        (r"(?i)\blotika\b", "लोटिका"),
        (r"(?i)\bpurohit\b", "पुरोहित"),
        (r"(?i)\bhello\b", "नमस्ते"),
        (r"(?i)\bhi\b", "नमस्ते"),
        (r"(?i)\bfree\b", "निशुल्क"),
        (r"(?i)\bconsultation\b", "परामर्श"),
        (r"(?i)\bappointment\b", "परामर्श"),
        (r"(?i)\bdoctor\b", "डॉक्टर"),
    ]
    for pat, rep in subs:
        text = re.sub(pat, rep, text)

    # Convert Devanagari digits to ASCII digits
    dev_digits = str.maketrans("०१२३४५६७८९", "0123456789")
    text = text.translate(dev_digits)
    # Expand times like 9:00 -> नौ, 9:30 -> नौ बजकर तीस मिनट
    text = re.sub(r'(\d+):00', lambda m: num_to_hindi(int(m.group(1))), text)
    text = re.sub(r'(\d+):(\d+)', lambda m: num_to_hindi(int(m.group(1))) + " बजकर " + num_to_hindi(int(m.group(2))) + " मिनट", text)
    # Expand all remaining digits to Hindi words (prevents num2words NotImplementedError)
    text = re.sub(r'\b\d+\b', lambda m: num_to_hindi(int(m.group(0))), text)
    text = re.sub(r'\d', lambda m: num_to_hindi(int(m.group(0))), text)

    # Strip any remaining Latin letters (so XTTS is NEVER tricked into English phonemizer / American accent)
    text = re.sub(r"[a-zA-Z]+", "", text)
    # Strip colons, dashes, markdown and noise
    text = re.sub(r'[:\-–—]+', ' ', text)
    text = text.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def provider_api_keys():
    # Modal injects secrets into the serving container, not the local deploy CLI.
    return [k.strip() for k in os.environ.get("NVIDIA_API_KEYS", "").split(",") if k.strip()]

@app.cls(
    # CPU-ONLY deployment (2026-10-06 Baba order: "shift isearch modal completely
    # to cpu, currently stt uses gpu shift it to cpu"). Whisper is the only GPU
    # consumer in this service (LLM + TTS are hosted NVIDIA NIM/NVCF), so no GPU
    # is allocated at all. cpu=4 / memory=8GiB sized for faster-whisper
    # large-v3-turbo int8 on CPU.
    cpu=4,
    memory=8192,
    image=image,
    scaledown_window=300,  # Keep warm for 5 minutes of idle conversation
    timeout=600,
    secrets=[modal.Secret.from_name("nvidia-voice-inference")],
)
class KiloVoiceService:
    @modal.enter()
    def setup(self):
        import os
        from faster_whisper import WhisperModel

        os.environ["COQUI_TOS_AGREED"] = "1"
        self.device = "cpu"
        print("[MODAL CPU] Initializing Kilo Voice Engine on cpu (no GPU allocated)...", flush=True)

        # 2026-10-06 CPU shift: the CUDA cublas/cudnn RTLD_GLOBAL preload that
        # used to live here is gone -- there is no GPU in this container.

        # Hindi synthesis uses NVIDIA's Hindi-capable Magpie model through NVCF.
        # XTTS-v2's published language list does not include Hindi; round-trip
        # checks confirmed its streamed Hindi output was frequently unintelligible.
        print(f"[TTS PROVIDER] NVIDIA NIM / {TTS_MODEL} / {TTS_VOICE}", flush=True)

        # Load Faster-Whisper on CPU. int8 is the standard CPU compute type for
        # ctranslate2: ~2x faster than float32 with negligible accuracy loss on
        # large-v3-turbo.
        print("[MODAL CPU] Loading Faster-Whisper large-v3-turbo (device=cpu, compute_type=int8)...")
        self.whisper = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
        dummy_pcm = np.zeros(16000, dtype=np.float32)
        list(self.whisper.transcribe(dummy_pcm, beam_size=1)[0])
        print("[MODAL CPU] Faster-Whisper CPU int8 validated successfully!", flush=True)

        # Warm the provider route at boot and fail early if API credentials or
        # Hindi synthesis are unavailable. The phone still owns its instant filler.
        print("[TTS PROVIDER] Running Hindi pre-warm...")
        _warm = self.synthesize_pcm("नमस्ते।", speed=TTS_DEFAULT_SPEED)
        try:
            _pk = int(np.abs(np.frombuffer(_warm, dtype=np.int16)).max()) if _warm else 0
            print(f"[TTS PROVIDER] pre-warm peak={_pk} bytes={len(_warm)}", flush=True)
            if _pk < 3000:
                raise RuntimeError(f"pre-warm audio peak {_pk} is dead - refusing to serve a broken voice")
        except Exception as e:
            print(f"[MODAL CPU] PRE-WARM GATE FAILED: {e}", flush=True)
            raise

        # Provider-only inference: NVIDIA hosts both Nemotron text and Magpie TTS;
        # this container is CPU-only: Whisper STT runs on cpu, LLM/TTS are hosted.
        self.llm_local = None
        self.llm_local_name = None
        self.sessions = {}
        print(f"[LLM PROVIDER] {VOICE_LLM_PROVIDER} / {VOICE_LLM_MODEL}", flush=True)

        print("[MODAL CPU] Warm-up complete! Serverless engine ready.")

    def detect_lang(self, text: str) -> str:
        # HINDI ONLY (stable)
        return "hi"

    def llm_stream_clauses(self, user_text: str, history: list = None):
        hint = "Reply in simple spoken Hindi, Devanagari script."
        t0 = time.time()
        emitted = 0
        for clause in self._llm_api_clauses(user_text, hint, history=history):
            clause = sanitize_hindi_for_xtts(clause)
            if not clause:
                continue
            if emitted and len(re.sub(r"[^\w\u0900-\u097f]+", "", clause)) <= 1:
                print(f"[LLM PROVIDER TAIL DROPPED] orphan fragment='{clause}'", flush=True)
                continue
            emitted += 1
            if emitted == 1:
                print(f"[LLM PROVIDER FIRST CLAUSE] {int((time.time()-t0)*1000)}ms model={VOICE_LLM_MODEL} text='{clause[:100]}'", flush=True)
            yield clause
        print(f"[LLM PROVIDER STREAM] {time.time()-t0:.2f}s clauses={emitted}", flush=True)

    def _llm_api_clauses(self, user_text: str, hint: str, history: list = None):
        messages = [
            {"role": "system", "content": CLINIC_SYSTEM_PROMPT + "\n" + hint},
        ]
        if history:
            # Latency guard: cap history to last 6 messages (~200 tokens) so prefill latency overhead is <15ms
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": user_text})
        payload = {
            "model": VOICE_LLM_MODEL,
            "messages": messages,
            "max_tokens": 90,
            "temperature": 0.45,
            "top_p": 0.9,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        data = json.dumps(payload).encode("utf-8")

        keys = provider_api_keys()
        if not keys:
            raise RuntimeError("Modal secret nvidia-voice-inference must provide NVIDIA_API_KEYS")
        for key in keys:
            buf = ""
            emitted = False
            key_t0 = time.time()
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    first_token = True
                    punct = ("।", ".", "?", "!", "\n", ";")
                    for line in resp:
                        line = line.decode("utf-8", errors="replace").strip()
                        if not line.startswith("data: ") or line[6:].strip() == "[DONE]":
                            continue
                        try:
                            j = json.loads(line[6:])
                            choices = j.get("choices") or []
                            delta = choices[0].get("delta", {}).get("content") or "" if choices else ""
                        except Exception:
                            continue
                        delta = delta.replace("*", "").replace("#", "").replace("<think>", "").replace("</think>", "")
                        if not delta:
                            continue
                        if first_token:
                            print(f"[LLM PROVIDER FIRST TOKEN] {int((time.time()-key_t0)*1000)}ms model={VOICE_LLM_MODEL}", flush=True)
                            first_token = False
                        buf += delta
                        while buf:
                            stops = [buf.find(mark) for mark in punct if buf.find(mark) >= 0]
                            if not stops:
                                break
                            cut = min(stops) + 1
                            part, buf = buf[:cut].strip(), buf[cut:].lstrip()
                            if part:
                                emitted = True
                                yield part
                    if buf.strip():
                        part = buf.strip()
                        if part[-1] not in "।.!?":
                            part += "।"
                        emitted = True
                        yield part
                    return
            except Exception as e:
                if emitted:
                    print(f"[LLM PROVIDER PARTIAL] {type(e).__name__}; retaining streamed text without retry", flush=True)
                    if buf.strip():
                        part = buf.strip()
                        if part[-1] not in "।.!?":
                            part += "।"
                        yield part
                    return
                print(f"[LLM STREAM FAIL] {e}, trying next provider key...", flush=True)
                continue

        if user_text and self.detect_lang(user_text) == "hi":
            yield "नमस्ते! मैं डॉक्टर लोटिका के क्लिनिक से बोल रहा हूँ।"
            yield "बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
        else:
            yield "Hello, this is Sugardoctor Clinic. How can I help you today?"

    def trim_sil(self, a, sr=24000, lead_ms=25, tail_ms=80):
        if a.size == 0:
            return a
        peak = float(np.max(np.abs(a)))
        thr = max(0.003, 0.015 * peak)
        idx = np.flatnonzero(np.abs(a) > thr)
        if idx.size == 0:
            return a
        s = max(int(idx[0]) - int(sr * lead_ms / 1000), 0)
        e = min(int(idx[-1]) + int(sr * tail_ms / 1000) + 1, a.size)
        return a[s:e]

    def collapse_silence(self, arr, sr=24000, frame_ms=10, quiet_pct=0.08, keep_ms=70, min_run_ms=120):
        """Frame-based RMS silence collapse: cuts long dead pauses between words down to 70ms."""
        if arr.size == 0:
            return arr, 0.0
        frame_len = int(sr * frame_ms / 1000)
        num_frames = len(arr) // frame_len
        if num_frames == 0:
            return arr, 0.0

        rms = np.array([np.sqrt(np.mean(arr[i*frame_len:(i+1)*frame_len]**2)) for i in range(num_frames)])
        peak_rms = float(np.max(rms)) or 1.0
        thresh = quiet_pct * peak_rms

        quiet_frames = rms < thresh
        keep_frames = max(int(keep_ms / frame_ms), 1)

        out_frames = []
        run_len = 0

        for idx, q in enumerate(quiet_frames):
            chunk = arr[idx*frame_len : (idx+1)*frame_len]
            if q:
                run_len += 1
                if run_len <= keep_frames:
                    out_frames.append(chunk)
            else:
                run_len = 0
                out_frames.append(chunk)

        if num_frames * frame_len < len(arr):
            out_frames.append(arr[num_frames * frame_len:])

        res = np.concatenate(out_frames)
        removed_s = (len(arr) - len(res)) / float(sr)
        return res, removed_s

    def synthesize_pcm(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", postprocess: bool = True,
        collapse_pauses: bool = False, temperature: float = 0.65,
    ) -> bytes:
        chunks = list(self.synthesize_pcm_stream(text, speed=speed))
        pcm = b"".join(chunks)
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        if postprocess and samples.size:
            samples = self.trim_sil(samples, 24000, lead_ms=20, tail_ms=60)
        if collapse_pauses and samples.size:
            samples, _ = self.collapse_silence(samples, 24000, frame_ms=10,
                                                quiet_pct=0.08, keep_ms=180, min_run_ms=300)
        out = np.clip(samples, -1.0, 1.0)
        result = (out * 32767.0).astype(np.int16).tobytes()
        duration = len(result) / 48000.0
        print(f"[NVIDIA MAGPIE TTS] wall_pcm={duration:.2f}s bytes={len(result)} "
              f"speed={speed:.2f} provider={TTS_MODEL} voice={TTS_VOICE}", flush=True)
        return result

    def synthesize_pcm_stream(
        self, text: str, speed: float = TTS_DEFAULT_SPEED,
        precision: str = "provider", stream_chunk_size: int = 10,
        temperature: float = 0.65,
    ):
        """Stream Hindi LPCM from NVIDIA Magpie and apply pitch-preserving tempo."""
        import subprocess
        import threading
        import uuid

        if not text or not text.strip():
            return
        clean_text = sanitize_hindi_for_xtts(text)
        language_code = "hi-IN"
        voice = TTS_VOICE
        if clean_text[-1] not in "।.!?":
            clean_text += "।"
        speed = min(1.5, max(0.8, float(speed)))
        boundary = "----KiloVoice" + uuid.uuid4().hex
        fields = {
            "text": clean_text,
            "language": language_code,
            "voice": voice,
            "encoding": "LINEAR_PCM",
            "sample_rate_hz": str(TTS_RATE_HZ),
        }
        multipart = bytearray()
        for name, value in fields.items():
            multipart.extend((f"--{boundary}\r\n"
                              f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                              f"{value}\r\n").encode("utf-8"))
        multipart.extend(f"--{boundary}--\r\n".encode("ascii"))
        keys = provider_api_keys()
        if not keys:
            raise RuntimeError("Modal secret nvidia-voice-inference must provide NVIDIA_API_KEYS")

        response = None
        errors = []
        for key in keys:
            req = urllib.request.Request(
                TTS_NVCF_URL,
                data=bytes(multipart),
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Accept": "audio/pcm",
                },
                method="POST",
            )
            try:
                response = urllib.request.urlopen(req, timeout=45)
                break
            except Exception as exc:
                code = getattr(exc, "code", "network")
                errors.append(str(code))
        if response is None:
            raise RuntimeError("NVIDIA Magpie TTS request failed across provider keys: "
                               + ",".join(errors))

        # The NVIDIA endpoint streams signed 16-bit mono LPCM at 22.05 kHz.
        # ffmpeg's atempo filter applies the requested pace while preserving
        # pitch, then resamples to the phone's existing 24 kHz PCM contract.
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "s16le", "-ar", str(TTS_RATE_HZ), "-ac", "1", "-i", "pipe:0",
            "-af", f"atempo={speed:.4f}", "-ar", "24000", "-ac", "1",
            "-f", "s16le", "pipe:1",
        ]
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, bufsize=0)
        pump_error = []
        provider_bytes = 0

        def pump_provider():
            nonlocal provider_bytes
            try:
                with response:
                    while True:
                        part = response.read(4096)
                        if not part:
                            break
                        provider_bytes += len(part)
                        proc.stdin.write(part)
                        proc.stdin.flush()
            except Exception as exc:
                pump_error.append(exc)
            finally:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

        pump = threading.Thread(target=pump_provider, name="magpie-provider-stream", daemon=True)
        t0 = time.time()
        pump.start()
        output_bytes = 0
        first_ms = None
        stream_completed = False
        try:
            while True:
                part = proc.stdout.read(8192)
                if not part:
                    stream_completed = True
                    break
                output_bytes += len(part)
                if first_ms is None:
                    first_ms = int((time.time() - t0) * 1000)
                    print(f"[NVIDIA MAGPIE FIRST PCM] {first_ms}ms voice={voice} "
                          f"lang={language_code} tempo={speed:.2f}", flush=True)
                yield part
        finally:
            if not stream_completed:
                try:
                    response.close()
                except Exception:
                    pass
                if proc.poll() is None:
                    proc.kill()
            pump.join(timeout=10)
            if proc.poll() is None:
                proc.wait(timeout=10)
        stderr = proc.stderr.read().decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 or output_bytes == 0:
            detail = stderr or (str(pump_error[0]) if pump_error else "no output")
            raise RuntimeError(f"Magpie/ffmpeg synthesis failed: {detail[:300]}")
        audio_s = output_bytes / 48000.0
        wall_ms = int((time.time() - t0) * 1000)
        print(f"[NVIDIA MAGPIE STREAM] wall={wall_ms}ms provider_bytes={provider_bytes} "
              f"audio={audio_s:.2f}s out_bytes={output_bytes} speed={speed:.2f}", flush=True)

    @modal.asgi_app()
    def web(self):
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, StreamingResponse

        web_app = FastAPI(title="Kilo Voice Clinic - Modal CPU Production")

        self.turn_events = deque(maxlen=25)
        self.last_audio = b""  # AUDIO EVIDENCE (2026-10-05): keep the most recent
        # uploaded utterance in memory so the house can pull exactly what the seat
        # heard. This is what settles "phone sends good audio vs phone sends noise".

        def turn_event(**kw):
            ev = {
                "ts": time.strftime("%H:%M:%S", time.localtime()),
                "llm_provider": VOICE_LLM_PROVIDER,
                "llm_model": VOICE_LLM_MODEL,
            }
            ev.update(kw)
            self.turn_events.append(ev)

        @web_app.get("/lastturns")
        def lastturns():
            return json.dumps(list(self.turn_events))

        @web_app.get("/last_audio")
        def last_audio():
            from fastapi.responses import Response
            return Response(content=self.last_audio, media_type="audio/wav")

        @web_app.get("/health")
        def health():
            return {
                "ok": True,
                "engine": "kilo-voice-modal-cpu-whisper-nvidia-tts",
                "gpu": None,
                "stt_device": str(self.device),
                "stt_compute_type": "int8",
                "voice": TTS_VOICE,
                "speed": TTS_DEFAULT_SPEED,
                "llm_local": self.llm_local_name,
                "llm_provider": VOICE_LLM_PROVIDER,
                "llm_model": VOICE_LLM_MODEL,
                "tts_provider": "NVIDIA NIM",
                "tts_model": TTS_MODEL,
                "tts_voice": TTS_VOICE,
                "tts_stream_api": True,
                "tts_output_sample_rate_hz": 24000,
                "tts_tempo_pitch_preserving": TTS_DEFAULT_SPEED,
                "phone_local_filler_bytes": 0,
                "phone_local_greeting": False,
                "stt_language_mode": "Whisper auto-detect unless explicit hi/en",
                "conversation_cache": True,
                "active_sessions": len(getattr(self, "sessions", {})),
            }

        @web_app.post("/say")
        async def say(req: Request):
            data = await req.json()
            text = data.get("text", "")
            speed = float(data.get("speed", TTS_DEFAULT_SPEED))
            # Keep accepting legacy probe fields while the phone transitions to Magpie.
            precision = str(data.get("precision", "provider"))
            postprocess = bool(data.get("postprocess", True))
            collapse_pauses = bool(data.get("collapse_pauses", False))
            speed = min(1.5, max(0.8, speed))
            if not text:
                return JSONResponse({"error": "No text provided"}, status_code=400)
            
            t0 = time.time()
            pcm = self.synthesize_pcm(text, speed, precision=precision, postprocess=postprocess,
                                      collapse_pauses=collapse_pauses)
            gen_ms = int((time.time() - t0) * 1000)
            audio_s = len(pcm) / 2 / 24000
            rtf = gen_ms / 1000.0 / max(audio_s, 0.01)

            return StreamingResponse(
                io.BytesIO(pcm),
                media_type="audio/pcm",
                headers={
                    "X-Gen-Ms": str(gen_ms),
                    "X-Sample-Rate": "24000",
                    "X-Channels": "1",
                    "X-Audio-Duration-S": f"{audio_s:.3f}",
                    "X-RTF": f"{rtf:.3f}",
                    "X-TTS-Speed": str(speed),
                    "X-TTS-Provider": "NVIDIA NIM",
                    "X-TTS-Model": TTS_MODEL,
                    "X-TTS-Voice": TTS_VOICE,
                    "X-TTS-Postprocess": str(postprocess).lower(),
                    "X-TTS-Trim-Edges": str(postprocess).lower(),
                    "X-TTS-Collapse-Pauses": str(collapse_pauses).lower(),
                }
            )

        def pcm_to_wav(pcm_bytes: bytes, sr: int = 24000) -> bytes:
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

            # FAST GREETING INTERCEPT (Baba Law: natural clinic welcome, never reversed pronoun)
            clean_toks = set(re.sub(r"[^\w\u0900-\u097f]+", " ", user_text.lower()).split())
            greeting_set = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम", "start", "शुरू"}
            if not clean_toks or clean_toks.issubset(greeting_set):
                full_reply = "नमस्ते! डॉक्टर लोटिका पुरोहित के शुगरडॉक्टर क्लिनिक में आपका स्वागत है। बताइए, मैं आपकी क्या सहायता कर सकता हूँ?"
            else:
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

        @web_app.post("/turn")
        async def turn(req: Request):
            import re
            t_turn0 = time.time()
            content_type = req.headers.get("content-type", "")
            no_fill = req.query_params.get("no_fill", "0") == "1"
            try:
                turn_speed = float(req.query_params.get("speed", TTS_DEFAULT_SPEED))
            except ValueError:
                turn_speed = TTS_DEFAULT_SPEED
            turn_speed = min(1.5, max(0.8, turn_speed))
            src = req.headers.get("user-agent", "?")[:40]

            body = await req.body()
            user_audio_bytes = b""
            if "json" in content_type:
                try:
                    j = json.loads(body.decode("utf-8"))
                    audio_b64 = j.get("b64") or j.get("audio_b64") or ""
                    user_audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
                    direct_text = (j.get("text", "") or j.get("user_text", "")).strip()
                except Exception as e:
                    print(f"[TURN JSON ERR] {e}")
                    direct_text = ""
            else:
                user_audio_bytes = body
                direct_text = ""

            # SESSION & CALL IDENTIFICATION (Twilio CallSid or client session)
            j_dict = j if ("json" in content_type and "j" in locals() and isinstance(j, dict)) else {}
            session_id = (
                req.headers.get("X-Call-Sid") or
                req.headers.get("X-Twilio-CallSid") or
                req.headers.get("X-Session-ID") or
                req.headers.get("X-Caller-ID") or
                req.query_params.get("CallSid") or
                req.query_params.get("call_sid") or
                req.query_params.get("session_id") or
                req.query_params.get("caller") or
                j_dict.get("call_sid") or
                j_dict.get("session_id") or
                (getattr(req.client, "host", None) if hasattr(req, "client") and req.client else "default_session")
            )
            reset_session = req.query_params.get("reset", "0") == "1" or j_dict.get("reset") is True

            now = time.time()
            if not hasattr(self, "sessions"):
                self.sessions = {}
            stale_keys = [k for k, v in self.sessions.items() if now - v.get("last_seen", 0) > 600]
            for k in stale_keys:
                self.sessions.pop(k, None)

            if reset_session or session_id not in self.sessions:
                self.sessions[session_id] = {"history": [], "last_seen": now}

            sess = self.sessions[session_id]
            # 5-minute idle timeout: clear history for a new phone call
            if now - sess.get("last_seen", 0) > 300:
                sess["history"] = []
            sess["last_seen"] = now
            session_history = list(sess.get("history", []))

            # STT
            user_text = direct_text
            stt_ms = 0
            if user_audio_bytes:
                t_stt0 = time.time()
                try:
                    with wave.open(io.BytesIO(user_audio_bytes), "rb") as wf:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        sr = wf.getframerate()
                        frames = wf.readframes(wf.getnframes())
                    
                    if sampwidth == 2:
                        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    else:
                        samples = np.frombuffer(frames, dtype=np.float32)
                    if channels > 1:
                        samples = samples.reshape(-1, channels).mean(axis=1)
                    
                    if sr != 16000:
                        from scipy.signal import resample
                        target_len = int(len(samples) * 16000 / sr)
                        samples = resample(samples, target_len).astype(np.float32)
                    else:
                        samples = np.ascontiguousarray(samples, dtype=np.float32)

                    # DIGITAL AGC (Baba 2026-10-05): Normalize incoming audio to boost faint phone mics
                    max_amp = float(np.abs(samples).max()) if len(samples) else 0.0
                    if 0.0025 <= max_amp < 0.6:
                        # AEC/NS can leave detected handset speech below 2.5% full scale.
                        # Boost it before Whisper, retaining VAD and transcript noise gates.
                        gain = min(12.0, 0.65 / max_amp)
                        samples = np.ascontiguousarray(samples * gain, dtype=np.float32)

                    # Auto-detect language (supports both Hindi and English naturally)
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
                        whisper_lang = None

                    # STT QUALITY (RCA-1 fix #2, Baba 2026-10-05): beam_size=1 (greedy)
                    # invents words on accented Hinglish ("वेगारी", "प्रूट" receipts).
                    # beam 5 gives real alternatives. The initial_prompt biases Hindi
                    # decoding toward clinic vocabulary instead of Bengali phonetics.
                    _stt_kw = dict(
                        beam_size=5,
                        vad_filter=False,
                        without_timestamps=True,
                        condition_on_previous_text=False,
                        temperature=0.0,
                        repetition_penalty=1.2,
                        no_repeat_ngram_size=3,
                        initial_prompt=(
                            "नमस्ते, हेलो। डॉक्टर, क्लिनिक, अपॉइंटमेंट, टाइमिंग।"
                            if whisper_lang == "hi" else None
                        ),
                    )

                    segments, info = self.whisper.transcribe(
                        samples,
                        language=whisper_lang,
                        **_stt_kw
                    )
                    user_text = " ".join([s.text for s in segments]).strip()
                    det_l = getattr(info, "language", "")
                    det_prob = getattr(info, "language_probability", None)
                    has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in user_text)
                    # bn = Bengali (Baba's mother tongue leaks into auto-detect and Whisper
                    # then outputs Bengali phonetics in Devanagari = "gibberish" Hindi).
                    if (det_l in ("ur", "mr", "ne", "pa", "bn") or has_arabic) and whisper_lang != "en":
                        # re-transcribe forced to clean Hindi Devanagari
                        segments, info = self.whisper.transcribe(
                            samples,
                            language="hi",
                            **_stt_kw
                        )
                        user_text = " ".join([s.text for s in segments]).strip()
                        det_l = getattr(info, "language", "hi")
                        det_prob = getattr(info, "language_probability", None)
                except Exception as e:
                    print(f"[TURN STT ERR] {e}", flush=True)
                    det_l = "error"
                    det_prob = None
            else:
                det_l = "text"
                det_prob = None
            if user_audio_bytes:
                stt_ms = int((time.time() - t_stt0) * 1000)

            # AUDIO RECEIPT (2026-10-05): "Whisper hears 'you'" can mean two very
            # different faults - a bad model, or a near-silent upload. Log the actual
            # signal level so the question is answered by measurement, not guesswork.
            sig_dur = sig_peak = sig_rms = 0
            try:
                if user_audio_bytes:
                    # keep this utterance for the /last_audio evidence lane (bounded)
                    self.last_audio = user_audio_bytes[:320044]
                    with wave.open(io.BytesIO(user_audio_bytes), "rb") as wf:
                        _ch = wf.getnchannels(); _sr = wf.getframerate(); _sw = wf.getsampwidth()
                        _fr = wf.readframes(wf.getnframes())
                    if _sw == 2:
                        _a = np.frombuffer(_fr, dtype=np.int16).astype(np.float32)
                        if _ch > 1:
                            _a = _a.reshape(-1, _ch).mean(axis=1)
                        sig_dur = round(len(_a) / max(_sr, 1), 2)
                        sig_peak = int(np.abs(_a).max()) if len(_a) else 0
                        sig_rms = int(np.sqrt(((_a ** 2).mean()))) if len(_a) else 0
            except Exception as _e:
                print(f"[SIG ERR] {_e}", flush=True)

            print(f"[TURN RECEIVED] src={src} bytes={len(user_audio_bytes)} dur={sig_dur}s peak={sig_peak} rms={sig_rms} | STT: {stt_ms}ms | Heard: '{user_text}' | LLM_local={bool(self.llm_local)}", flush=True)

            greetings = {"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "प्रणाम", "हाय", "hi", "सुनिए", "हाँ", "हा", "ji", "जी"}

            def is_hallucination(text):
                t = (text or "").lower()
                # 1. Any Cyrillic/Russian character is an automatic Whisper hallucination on noise
                if any("\u0400" <= ch <= "\u04FF" for ch in t):
                    return True
                clean = re.sub(r"[^\w\u0900-\u097f]+", " ", t)
                toks = [w for w in clean.split() if w]
                if not toks:
                    return True

                # WHITELIST: Greetings and affirmations must NEVER be flagged as hallucinations!
                if set(toks).issubset(greetings) or any(w in greetings for w in toks):
                    return False

                # 2. English & noise words that Whisper emits on background hum/noise or speaker bleed
                noise_words = {
                    "you", "oh", "i", "the", "a", "an", "to", "it", "thank", "thanks", "bye",
                    "झाल", "झाला", "झाली", "झाले", "क्लिका", "कळिका", "टिक", "हूँ", "हूं"
                }
                if len(toks) == 1 and toks[0] in noise_words:
                    return True
                if len(toks) == 2 and (
                    set(toks).issubset({"thank", "you"}) or
                    set(toks).issubset({"कर", "दो"}) or
                    set(toks).issubset({"टिक", "टिक"}) or
                    all(w in noise_words for w in toks)
                ):
                    return True

                # 3. Repeated single token hallucination (e.g. "you you you...")
                collapsed = [toks[0]]
                for w in toks[1:]:
                    if w != collapsed[-1]:
                        collapsed.append(w)
                if len(collapsed) == 1 and len(toks) > 2:
                    return True
                if len(toks) >= 6 and len(set(toks)) <= 2:
                    return True
                if len(toks) >= 8 and len(set(toks)) / float(len(toks)) < 0.3:
                    return True
                return False

            # keep what Whisper REALLY heard for the receipt (before the gate edits it)
            heard_raw = user_text

            drop_reason = ""
            if is_hallucination(user_text):
                drop_reason = "whisper_noise_or_hallucination"
                user_text = ""
            elif user_audio_bytes and sig_peak < 100 and user_text:
                clean = re.sub(r"[^\w\u0900-\u097f]+", " ", user_text.lower())
                toks = [w for w in clean.split() if w]
                if not any(w in greetings for w in toks):
                    drop_reason = "low_signal_peak"
                    print(f"[TURN DROPPED] sig_peak={sig_peak} below speech threshold (100), dropping transcript.", flush=True)
                    user_text = ""

            # ECHO GUARD: Only suppress if caller's audio is an echo of our own outgoing sentence
            _echo = False
            _heard_l = (user_text or "").lower().strip()
            if _heard_l and len(_heard_l) >= 8:
                try:
                    for _r in list(getattr(self, "_recent_replies", [])):
                        _rl = (_r or "").lower().strip()
                        if _rl and (_heard_l in _rl or _rl in _heard_l):
                            _echo = True
                            break
                except Exception:
                    _echo = False

            if _echo:
                print(f"[TURN ECHO] own audio came back as '{user_text}' - refusing to answer it.", flush=True)
                turn_event(src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                           heard=heard_raw, reply="", echo=True,
                           llm_local=self.llm_local_name)

                async def echo_stream():
                    hdr = json.dumps({"cid": "turn", "heard": heard_raw,
                                      "stt_ms": stt_ms, "sr": 24000,
                                      "echo": True}) + "\n"
                    yield hdr.encode("utf-8")
                    trailer = json.dumps({"end": True, "heard": heard_raw,
                                          "reply": "", "echo": True,
                                          "stt_ms": stt_ms,
                                          "total_ms": int((time.time() - t_turn0) * 1000)}) + "\n"
                    yield trailer.encode("utf-8")

                return StreamingResponse(
                    echo_stream(), media_type="application/octet-stream",
                    headers={"X-Sample-Rate": "24000", "X-Channels": "1"})

            if not user_text:
                # If the handset has already captured a speech-length segment with
                # measurable energy, a Whisper noise/hallucination rejection must
                # not become silent dead air. Ask for one repeat in the same Magpie
                # voice. Truly empty/very quiet or sub-second uploads remain silent;
                # echo turns are handled by the separate echo guard above.
                if not drop_reason:
                    drop_reason = "empty_transcript"
                clarify = bool(user_audio_bytes) and sig_dur >= 0.9 and sig_peak >= 180 and sig_rms >= 24
                if clarify:
                    clarify_text = "माफ़ कीजिए, आपकी आवाज़ साफ़ नहीं आई। कृपया एक बार फिर कहिए।"
                    print(f"[TURN CLARIFY] reason={drop_reason} dur={sig_dur}s peak={sig_peak} rms={sig_rms}", flush=True)

                    async def clarify_stream():
                        import asyncio
                        t_clarify = time.time()
                        hdr = json.dumps({"cid": "turn", "heard": heard_raw, "stt_ms": stt_ms,
                                          "sr": 24000, "clarification": True}) + "\n"
                        yield hdr.encode("utf-8")
                        pcm = b""
                        try:
                            pcm = await asyncio.to_thread(self.synthesize_pcm, clarify_text, turn_speed)
                            if pcm:
                                if not hasattr(self, "_recent_replies"):
                                    self._recent_replies = deque(maxlen=5)
                                self._recent_replies.append(clarify_text)
                                yield pcm
                        except Exception as e:
                            print(f"[TURN CLARIFY TTS FAIL] {type(e).__name__}: {e}", flush=True)
                        total_ms = int((time.time() - t_turn0) * 1000)
                        first_pcm_ms = int((time.time() - t_clarify) * 1000) if pcm else None
                        turn_event(src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                                   heard=heard_raw, reply=clarify_text if pcm else "",
                                   clarification=True, empty=not bool(pcm), drop_reason=drop_reason,
                                   signal_peak=sig_peak, signal_rms=sig_rms,
                                   first_pcm_ms=first_pcm_ms, total_ms=total_ms,
                                   llm_local=self.llm_local_name, tts_speed=turn_speed)
                        trailer = json.dumps({"end": True, "heard": heard_raw,
                                              "reply": clarify_text if pcm else "",
                                              "clarification": True, "empty": not bool(pcm),
                                              "first_pcm_ms": first_pcm_ms, "stt_ms": stt_ms,
                                              "total_ms": total_ms}) + "\n"
                        yield trailer.encode("utf-8")

                    return StreamingResponse(
                        clarify_stream(), media_type="application/octet-stream",
                        headers={"X-Sample-Rate": "24000", "X-Channels": "1",
                                 "X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

                print(f"[TURN DROPPED] empty/quiet segment raw='{heard_raw}' dur={sig_dur}s peak={sig_peak} rms={sig_rms}; no clarification audio", flush=True)
                turn_event(src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                           heard=heard_raw, reply="", empty=True, drop_reason=drop_reason,
                           signal_peak=sig_peak, signal_rms=sig_rms, signal_duration=sig_dur,
                           llm_local=self.llm_local_name)

                async def empty_stream():
                    hdr = json.dumps({"cid": "turn", "heard": heard_raw, "stt_ms": stt_ms,
                                      "sr": 24000, "empty": True, "drop_reason": drop_reason}) + "\n"
                    yield hdr.encode("utf-8")
                    trailer = json.dumps({"end": True, "heard": heard_raw, "reply": "", "empty": True,
                                          "drop_reason": drop_reason}) + "\n"
                    yield trailer.encode("utf-8")

                return StreamingResponse(
                    empty_stream(), media_type="application/octet-stream",
                    headers={"X-Sample-Rate": "24000", "X-Channels": "1"})

            # FAST GREETING PATH (<600ms feel latency):
            # If caller says "hello", "hello hello", "नमस्ते", respond immediately with warm Hindi clinic greeting.
            is_pure_greeting = False
            clean_user_toks = set(re.sub(r"[^\w\u0900-\u097f]+", " ", user_text.lower()).split())
            if clean_user_toks and clean_user_toks.issubset({"hello", "हेलो", "हलो", "नमस्ते", "नमस्कार", "हाय", "hi", "सुनिए", "प्रणाम"}):
                is_pure_greeting = True

            async def stream_generator():
                import asyncio
                import queue
                import threading

                async def stream_tts(text):
                    pieces = queue.Queue(maxsize=2)
                    stopped = threading.Event()
                    finished = object()

                    def put_item(item):
                        while not stopped.is_set():
                            try:
                                pieces.put(item, timeout=0.1)
                                return True
                            except queue.Full:
                                continue
                        return False

                    def produce():
                        try:
                            for pcm_part in self.synthesize_pcm_stream(text, speed=turn_speed):
                                if not put_item(pcm_part):
                                    return
                        except Exception as e:
                            put_item(e)
                        finally:
                            put_item(finished)

                    worker = threading.Thread(target=produce, daemon=True)
                    worker.start()
                    try:
                        while True:
                            item = await asyncio.to_thread(pieces.get)
                            if item is finished:
                                break
                            if isinstance(item, Exception):
                                raise item
                            yield item
                    finally:
                        stopped.set()

                # 1. Header line for BridgeService
                hdr = json.dumps({"cid": "turn", "heard": user_text, "stt_ms": stt_ms, "sr": 24000}) + "\n"
                yield hdr.encode("utf-8")
                await asyncio.sleep(0.001)

                # 2. Pipelined clause streaming: as clauses are ready, synthesize & yield immediately
                total_spoken = []
                t_first_pcm = None

                if is_pure_greeting:
                    fast_pieces = [
                        "जी, बताइए, मैं आपकी कैसे मदद करूँ?"
                    ]
                    for fast_clause in fast_pieces:
                        total_spoken.append(fast_clause)
                        async for pcm in stream_tts(fast_clause):
                            if not pcm:
                                continue
                            if t_first_pcm is None:
                                t_first_pcm = int((time.time() - t_turn0) * 1000)
                                print(f"[STREAM FIRST AUDIO FAST GREETING] {t_first_pcm}ms | Piece: '{fast_clause}'", flush=True)
                            yield pcm
                            await asyncio.sleep(0.001)
                else:
                    for clause in self.llm_stream_clauses(user_text, history=session_history):
                        clause_clean = clause.strip()
                        if not clause_clean:
                            continue
                        total_spoken.append(clause_clean)
                        async for pcm in stream_tts(clause_clean):
                            if not pcm:
                                continue
                            if t_first_pcm is None:
                                t_first_pcm = int((time.time() - t_turn0) * 1000)
                                print(f"[STREAM FIRST AUDIO] {t_first_pcm}ms | Piece: '{clause_clean}'", flush=True)
                            yield pcm
                            await asyncio.sleep(0.001)

                full_reply = " ".join(total_spoken)
                if not hasattr(self, "_recent_replies"):
                    self._recent_replies = deque(maxlen=5)
                if full_reply:
                    self._recent_replies.append(full_reply)
                    sess["history"].append({"role": "user", "content": user_text})
                    sess["history"].append({"role": "assistant", "content": full_reply})
                    # Sliding window: keep max 8 messages (4 user-assistant pairs) to protect latency
                    sess["history"] = sess["history"][-8:]
                    sess["last_seen"] = time.time()

                total_ms = int((time.time() - t_turn0) * 1000)
                turn_event(
                    src=src, bytes=len(user_audio_bytes), stt_ms=stt_ms,
                    heard=user_text, reply=full_reply,
                    first_pcm_ms=t_first_pcm or total_ms, total_ms=total_ms,
                    llm_local=self.llm_local_name, tts_speed=turn_speed,
                    stt_language=det_l, stt_language_probability=det_prob,
                )
                trailer = json.dumps({
                    "end": True,
                    "heard": user_text,
                    "reply": full_reply,
                    "first_pcm_ms": t_first_pcm or total_ms,
                    "stt_ms": stt_ms,
                    "total_ms": total_ms,
                    "session_id": str(session_id),
                    "history_turns": len(sess.get("history", [])) // 2,
                }) + "\n"
                yield trailer.encode("utf-8")

            return StreamingResponse(
                stream_generator(),
                media_type="application/octet-stream",
                headers={
                    "X-Sample-Rate": "24000",
                    "X-Channels": "1",
                    "X-Accel-Buffering": "no",
                    "Cache-Control": "no-cache"
                }
            )

        return web_app

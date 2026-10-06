with open(r'D:\anonym\modal_voice_service_isearch.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add English preset chips in HTML
old_chips = '''        <div class="preset-section">
            <div class="chip" onclick="askPreset('क्लिनिक की टाइमिंग क्या है?')">🩺 क्लिनिक टाइमिंग</div>
            <div class="chip" onclick="askPreset('डॉक्टर से बात करनी है')">👨‍⚕️ डॉक्टर से बात करनी है</div>
            <div class="chip" onclick="askPreset('कल दोपहर 3 बजे अपॉइंटमेंट मिल सकता है?')">📅 कल अपॉइंटमेंट</div>
            <div class="chip" onclick="askPreset('शुगर चेकअप की क्या फीस है?')">💉 चेकअप फीस</div>
            <div class="chip" onclick="askPreset('क्लिनिक का पता कहाँ है?')">📍 क्लिनिक का पता</div>
            <div class="chip" onclick="askPreset('क्या डॉक्टर साहब ऑनलाइन परामर्श भी देते हैं?')">🌐 ऑनलाइन कंसल्टेशन</div>
        </div>'''

new_chips = '''        <div class="preset-section">
            <div class="chip" onclick="askPreset('क्लिनिक की टाइमिंग क्या है?')">🩺 क्लिनिक टाइमिंग</div>
            <div class="chip" onclick="askPreset('डॉक्टर से बात करनी है')">👨‍⚕️ डॉक्टर से बात करनी है</div>
            <div class="chip" onclick="askPreset('कल दोपहर 3 बजे अपॉइंटमेंट मिल सकता है?')">📅 कल अपॉइंटमेंट</div>
            <div class="chip" onclick="askPreset('शुगर चेकअप की क्या फीस है?')">💉 चेकअप फीस</div>
            <div class="chip" onclick="askPreset('क्लिनिक का पता कहाँ है?')">📍 क्लिनिक का पता</div>
            <div class="chip" onclick="askPreset('क्या डॉक्टर साहब ऑनलाइन परामर्श भी देते हैं?')">🌐 ऑनलाइन कंसल्टेशन</div>
            <div class="chip" onclick="askPreset('What are the clinic timings?')">🩺 Clinic Timings</div>
            <div class="chip" onclick="askPreset('I need to talk to the doctor')">👨‍⚕️ Talk to Doctor</div>
            <div class="chip" onclick="askPreset('Can I book an appointment for tomorrow at 3 PM?')">📅 Book Appointment</div>
            <div class="chip" onclick="askPreset('What is the sugar checkup fee?')">💉 Checkup Fee</div>
            <div class="chip" onclick="askPreset('Where is the clinic located?')">📍 Clinic Address</div>
            <div class="chip" onclick="askPreset('Do you offer online consultation?')">🌐 Online Consultation</div>
        </div>'''

c = c.replace(old_chips, new_chips)

# 2. Add language toggle button in controls
old_controls = '''        <div class="controls-container">
            <button class="mic-btn" id="micBtn" onclick="toggleMic()" title="बोलने के लिए दबाएँ">🎤</button>
            <input type="text" class="text-input" id="userInput" placeholder="यहाँ बोलें या टाइप करें..." onkeypress="handleKey(event)" oninput="handleInput()">
            <button class="send-btn" id="sendBtn" onclick="sendText()" title="भेजें">➔</button>
        </div>'''

new_controls = '''        <div class="controls-container">
            <button id="langToggleBtn" class="lang-toggle-btn active-hi" onclick="toggleLang()" title="भाषा बदलें">🌐 हिन्दी</button>
            <button class="mic-btn" id="micBtn" onclick="toggleMic()" title="बोलने के लिए दबाएँ">🎤</button>
            <input type="text" class="text-input" id="userInput" placeholder="यहाँ बोलें या टाइप करें..." onkeypress="handleKey(event)" oninput="handleInput()">
            <button class="send-btn" id="sendBtn" onclick="sendText()" title="भेजें">➔</button>
        </div>'''

c = c.replace(old_controls, new_controls)

# 3. Add language toggle JS variable and function
old_js_vars = '''let discardRecording = false;

        // Single shared HTML5 Audio Element to guarantee permanent iOS/Android autoplay
        const player = new Audio()'''

new_js_vars = '''let discardRecording = false;
        let currentLang = 'hi-IN'; // 'hi-IN' or 'en-IN'

        // Single shared HTML5 Audio Element to guarantee permanent iOS/Android autoplay
        const player = new Audio()'''

c = c.replace(old_js_vars, new_js_vars)

# 4. Add toggleLang function
old_unlock = '''        function unlockAudio() {
            if (!audioUnlocked) {
                // Play tiny silent wav buffer on first user touch/click
                player.src = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==';
                player.play().then(() => {
                    audioUnlocked = true;
                    player.pause();
                }).catch(() => {});
            }
        }

        async function toggleMic() {'''

new_unlock = '''        function unlockAudio() {
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
        }

        async function toggleMic() {'''

c = c.replace(old_unlock, new_unlock)

# 5. Update stopMic to use currentLang
old_stopmic = '''function stopMic() {
            isRecording = false;
            document.getElementById('micBtn').classList.remove('recording');
            document.getElementById('userInput').placeholder = "यहाँ बोलें या टाइप करें...";
            updateLiveButton();
        }'''

new_stopmic = '''function stopMic() {
            isRecording = false;
            document.getElementById('micBtn').classList.remove('recording');
            document.getElementById('userInput').placeholder = currentLang === 'hi-IN' ? "यहाँ बोलें या टाइप करें..." : "Speak in English or type...";
            updateLiveButton();
        }'''

c = c.replace(old_stopmic, new_stopmic)

# 6. Update processLiveAudio to use currentLang
old_process = '''        async function processLiveAudio(blob) {
            assistantBusy = true;
            updateLiveButton();
            const thinkingId = appendThinking();
            try {
                const wav = await blobToWav16k(blob);
                const lang = 'hi';
                const response = await fetch(`/turn?speed=1.2&lang=${lang}&session_id=${encodeURIComponent(sessionId)}`, {'''

new_process = '''        async function processLiveAudio(blob) {
            assistantBusy = true;
            updateLiveButton();
            const thinkingId = appendThinking();
            try {
                const wav = await blobToWav16k(blob);
                const lang = currentLang === 'hi-IN' ? 'hi' : 'en';
                const response = await fetch(`/turn?speed=1.2&lang=${lang}&session_id=${encodeURIComponent(sessionId)}`, {'''

c = c.replace(old_process, new_process)

# 6. Update sendText to use currentLang
old_sendtext = '''        async function sendText() {
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
                });'''

new_sendtext = '''        async function sendText() {
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
                });'''

c = c.replace(old_sendtext, new_sendtext)

# Write back
with open(r"D:\anonym\modal_voice_service_isearch.py", "w", encoding="utf-8") as f:
    f.write(c)

print("JavaScript patches applied for isearch-xsolve")
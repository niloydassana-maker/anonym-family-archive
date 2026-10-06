# -*- coding: utf-8 -*-
"""EN-mode i18n FINAL: all content-anchored, Hindi extracted, single write."""
import json
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

DEV = r'[\u0900-\u097F]'

def rep(pat, repl, name):
    global src
    found = re.findall(pat, src)
    if len(found) != 1:
        raise SystemExit('ABORT %s: matched %d (want 1)' % (name, len(found)))
    src = re.sub(pat, repl, src, count=1)
    print('patched: %s' % name, flush=True)

def jq(s):
    return json.dumps(s, ensure_ascii=True)

# ---------- A. updateLiveButton ----------
m = re.search(r"        function updateLiveButton\(\) \{\n(?:.*\n)*?        \}\n", src)
if not m:
    raise SystemExit('ABORT find updateLiveButton')
old_fn = m.group(0)
dq_hi = [x for x in re.findall(r'"([^"]*)"', old_fn) if re.search(DEV, x)]
sq_hi = [x for x in re.findall(r"'([^']*)'", old_fn) if re.search(DEV, x)]
if len(dq_hi) != 2 or len(sq_hi) != 4:
    raise SystemExit('ABORT ulb literals dq=%d sq=%d' % (len(dq_hi), len(sq_hi)))
HI_stop, HI_start = dq_hi
HI_s0, HI_s1, HI_s2, HI_s3 = sq_hi
new_fn = (
    "        function updateLiveButton() {\n"
    "            var HI = {stopLive:%s, startLive:%s, statusStart:%s, answering:%s, listening:%s, listeningAgain:%s};\n"
    "            const btn = document.getElementById('micBtn');\n"
    "            btn.classList.toggle('live-mode', liveMode);\n"
    "            btn.title = L(liveMode ? 'stopLive' : 'startLive') || (liveMode ? HI.stopLive : HI.startLive);\n"
    "            btn.innerText = liveMode ? '\\u23F9' : '\\uD83C\\uDFA4';\n"
    "            const status = document.getElementById('liveStatus');\n"
    "            if (status) {\n"
    "                status.innerText = !liveMode ? (L('statusStart') || HI.statusStart) :\n"
    "                    assistantBusy ? (L('answering') || HI.answering) :\n"
    "                    isRecording ? (L('listening') || HI.listening) : (L('listeningAgain') || HI.listeningAgain);\n"
    "            }\n"
    "        }\n"
) % (jq(HI_stop), jq(HI_start), jq(HI_s0), jq(HI_s1), jq(HI_s2), jq(HI_s3))
src = src.replace(old_fn, new_fn, 1)
print('patched: updateLiveButton', flush=True)

# ---------- B. toggle block + STR insert ----------
lines = src.split('\n')
si = next(i for i, l in enumerate(lines) if l.strip() == '// Language toggle for Web Speech')
ti = next(i for i, l in enumerate(lines) if 'async function toggleMic() {' in l)
seg = lines[si:ti]
if not any('function toggleLang()' in l for l in seg):
    raise SystemExit('ABORT toggle fn missing')
ej = max(i for i in range(si, ti) if lines[i] == '        }')
new_toggle = [
    "        // Language toggle for Web Speech",
    "        function toggleLang() {",
    "            unlockAudio();",
    "            if (currentLang === 'hi-IN') { currentLang = 'en-IN'; }",
    "            else { currentLang = 'hi-IN'; }",
    "            applyLang();",
    "        }",
]
lines[si:ej + 1] = new_toggle
src = '\n'.join(lines)
print('patched: toggleLang', flush=True)

STR = '''        // ---- i18n: every label follows the toggle (Baba order) ----
        var STR_EN = {
          heroSub:"Live Receptionist Demo \\u2022 English Voice",
          doctorH2:"Dr. Anupam Ghosh / Dr. Lotika Purohit Clinic",
          doctorP:"AI voice assistant \\u2014 appointments, clinic timings and general consultation",
          voiceTag:"\\uD83C\\uDFA9\\uFE0F Magpie Leo (English)",
          greetText:"Hello! Welcome to Dr. Lotika Purohit's SugarDoctor Clinic. How can I help you today?",
          greetBtn:"Play greeting",
          thinkText:"AI is thinking and generating voice...",
          statusStart:"Start a conversation",
          stopLive:"Stop live conversation",
          startLive:"Start live conversation",
          answering:"Replying\\u2026",
          listening:"Listening\\u2026",
          listeningAgain:"Listening again\\u2026",
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
            tgl.innerText = en ? '\\uD83C\\uDF10 English' : o.toggle;
            tgl.title = en ? STR_EN.langTitle : o.toggleTitle; }
          var mic = document.getElementById('micBtn'); if (mic) mic.title = en ? STR_EN.micTitle : o.micTitle;
          var snd = document.getElementById('sendBtn'); if (snd) snd.title = en ? STR_EN.sendTitle : o.sendTitle;
          var inp = document.getElementById('userInput');
          if (inp && !isRecording) inp.placeholder = en ? STR_EN.phType : o.ph;
          try { delete audioStore['greeting']; } catch (e) {}
          var chips = document.querySelectorAll('.chip');
          for (var i = 0; i < chips.length; i++) {
            var txt = chips[i].textContent || '';
            var isHi = /[\\u0900-\\u097F]/.test(txt);
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

'''
src = src.replace('        // Language toggle for Web Speech',
                  STR + '        // Language toggle for Web Speech', 1)
print('inserted: STR block', flush=True)

with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('WROTE PART A (toggle+STR). Part B follows.')

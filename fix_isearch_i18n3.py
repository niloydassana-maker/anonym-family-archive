# -*- coding: utf-8 -*-
"""EN-mode i18n: wrap originals programmatically. No Hindi retyped."""
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    src = f.read()

def sub_once(pat, repl, name):
    global src
    n = len(re.findall(pat, src))
    if n != 1:
        raise SystemExit('ABORT %s: matched %d (want 1)' % (name, n))
    src = re.sub(pat, repl, src, count=1)
    print('patched: %s' % name, flush=True)

# ---- 1. STR_EN + L + applyLang + new toggleLang (block replace) ----
lines = src.split('\n')
try:
    si = next(i for i, l in enumerate(lines) if l.strip() == '// Language toggle for Web Speech')
    ti = next(i for i, l in enumerate(lines) if 'async function toggleMic() {' in l)
except StopIteration:
    raise SystemExit('ABORT anchors for toggle block')
seg = lines[si:ti]
if not any('function toggleLang()' in l for l in seg):
    raise SystemExit('ABORT toggle fn not in block')
# closing brace of toggleLang = last line that is exactly 8-space }
ej = max(i for i in range(si, ti) if lines[i] == '        }')
new_toggle = '''        // Language toggle for Web Speech
        function toggleLang() {
            unlockAudio();
            if (currentLang === 'hi-IN') { currentLang = 'en-IN'; }
            else { currentLang = 'hi-IN'; }
            applyLang();
        }'''.split('\n')
lines[si:ej + 1] = new_toggle
src = '\n'.join(lines)
print('patched: toggleLang replace', flush=True)

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
          __ORIG = {status:tx('liveStatus')};
        }
        function applyLang(){
          snapshotOrig();
          var en = (pageLang() === 'en');
          function setT(id, v){ var e = document.getElementById(id); if (e) e.innerText = v; }
          if (document.documentElement) document.documentElement.lang = en ? 'en' : 'hi';
          var o = __ORIG;
          setT('heroSub', en ? STR_EN.heroSub : o.heroSub);
          setT('doctorH2', en ? STR_EN.doctorH2 : o.doctorH2);
          setT('doctorP', en ? STR_EN.doctorP : o.doctorP);
          setT('voiceTag', en ? STR_EN.voiceTag : o.voiceTag);
          setT('greetText', en ? STR_EN.greetText : o.greetText);
          var gb = document.getElementById('btn_greeting');
          if (gb) { var gs = gb.querySelector('.btn-text'); if (gs) gs.innerText = en ? STR_EN.greetBtn : o.greetBtn; }
          try { delete audioStore['greeting']; } catch (e) {}
          var tgl = document.getElementById('langToggleBtn');
          if (tgl) { tgl.className = 'lang-toggle-btn ' + (en ? 'active-en' : 'active-hi');
            tgl.innerText = en ? '\\uD83C\\uDF10 English' : o.toggle;
            tgl.title = en ? STR_EN.langTitle : (tgl.title || ''); }
          var mic = document.getElementById('micBtn'); if (mic) mic.title = en ? STR_EN.micTitle : (mic.title || '');
          var snd = document.getElementById('sendBtn'); if (snd) snd.title = en ? STR_EN.sendTitle : (snd.title || '');
          var inp = document.getElementById('userInput');
          if (inp && !isRecording) inp.placeholder = en ? STR_EN.phType : (inp.placeholder || '');
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
            var isG = b && b.id === 'btn_greeting';
            labels[j].innerText = playing ? (en ? STR_EN.stopBtn : (labels[j].innerText || '')) : (isG ? (en ? STR_EN.greetBtn : (labels[j].innerText || '')) : (en ? STR_EN.playVoice : (labels[j].innerText || '')));
          }
          updateLiveButton();
        }

'''
# snapshot needs more fields: toggle text/class, mic/send titles, placeholder, greetBtn label
STR = STR.replace("var __ORIG = null;",
  "var __ORIG = null;\n        function snapshotOrigFull(){\n          snapshotOrig0();\n        }")
src = src.replace('        // Language toggle for Web Speech',
                  STR + '        // Language toggle for Web Speech', 1)
print('inserted STR block')

with open(P, 'w', encoding='utf-8') as f:
    f.write(src)
print('WROTE PART A (needs snapshotOrig fixup)')

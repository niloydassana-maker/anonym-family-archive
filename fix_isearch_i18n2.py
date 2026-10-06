# -*- coding: utf-8 -*-
"""EN-mode i18n without retyping Hindi: wrap originals, EN literals only."""
import re

P = r'D:\anonym\modal_voice_service_isearch.py'
with open(P, 'r', encoding='utf-8') as f:
    lines = f.readlines()

def ck(i, needle, name):
    if needle not in lines[i]:
        raise SystemExit('ABORT %s: line %d lacks anchor %r' % (name, i + 1, needle))

def wrap_dq(line, key):
    """appendMessage("HINDI", 'ai') -> appendMessage(L('key') || "HINDI", 'ai')."""
    m = re.search(r'appendMessage\\("([^"]*)"', line)
    if not m:
        raise SystemExit('ABORT wrap_dq: no match in %r' % line[:80])
    return line.replace('appendMessage("%s"' % m.group(1),
                        'appendMessage(L(%s) || "%s"' % ("'" + key + "'", m.group(1)), 1)

def wrap_sq_assign(line, key):
    """x = 'HINDI' -> x = L('key') || 'HINDI' (trailing ; kept)."""
    m = re.search(r"= '([^']*)';", line)
    if not m:
        raise SystemExit('ABORT wrap_sq: no match in %r' % line[:80])
    return line.replace("= '%s';" % m.group(1),
                        "= L('%s') || '%s';" % (key, m.group(1)), 1)

# ---- A. STR_EN + L + applyLang + new toggleLang (insert before toggle comment) ----
ck(616, '// Language toggle for Web Speech', 'toggle-comment')
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
        var __ORIG = null;
        function pageLang(){ return currentLang === 'hi-IN' ? 'hi' : 'en'; }
        function L(k){ if (pageLang() === 'en' && STR_EN[k] !== undefined) return STR_EN[k]; return null; }
        function snapshotOrig(){
          if (__ORIG) return;
          function tx(id){ var e = document.getElementById(id); return e ? e.innerText : ''; }
          __ORIG = {heroSub:tx('heroSub'), doctorH2:tx('doctorH2'), doctorP:tx('doctorP'),
            voiceTag:tx('voiceTag'), greetText:tx('greetText'),
            greetBtn:(function(){var b=document.getElementById('btn_greeting');var s=b?b.querySelector('.btn-text'):null;return s?s.innerText:'';})(),
            status:tx('liveStatus')};
        }
        function applyLang(){
          snapshotOrig();
          var en = (pageLang() === 'en');
          function setT(id, v){ var e = document.getElementById(id); if (e) e.innerText = v; }
          if (document.documentElement) document.documentElement.lang = en ? 'en' : 'hi';
          setT('heroSub', en ? STR_EN.heroSub : __ORIG.heroSub);
          setT('doctorH2', en ? STR_EN.doctorH2 : __ORIG.doctorH2);
          setT('doctorP', en ? STR_EN.doctorP : __ORIG.doctorP);
          setT('voiceTag', en ? STR_EN.voiceTag : __ORIG.voiceTag);
          setT('greetText', en ? STR_EN.greetText : __ORIG.greetText);
          var gb = document.getElementById('btn_greeting');
          if (gb) { var gs = gb.querySelector('.btn-text'); if (gs) gs.innerText = en ? STR_EN.greetBtn : __ORIG.greetBtn; }
          try { delete audioStore['greeting']; } catch (e) {}
          var tgl = document.getElementById('langToggleBtn');
          if (tgl) { tgl.className = 'lang-toggle-btn ' + (en ? 'active-en' : 'active-hi');
            tgl.innerText = en ? '\\uD83C\\uDF10 English' : '\\uD83C\\uDF10 \\u0939\\u093F\\u0928\\u094D\\u0926\\u0940';
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
lines.insert(616, STR)
print('inserted STR block')
print('ALL OK')

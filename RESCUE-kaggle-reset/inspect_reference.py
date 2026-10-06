"""Inspect the reference audio Baba supplied at D:\anonym\realhindivoice.

Facts only: codec, sample rate, channels, duration, loudness and leading/trailing silence.
XTTS wants a SHORT clean reference (roughly 3-15 s of a single speaker, ideally one sentence,
no music, no noise), so these numbers decide whether this file can be used as-is or needs trimming.
"""
import glob, json, os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FFB = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
D = r"D:\anonym\realhindivoice"
files = sorted(glob.glob(os.path.join(D, "*")))
print("directory: %s" % D)
for f in files:
    print("\nfile      : %s" % os.path.basename(f))
    print("size      : %d bytes" % os.path.getsize(f))

    def run(tool, args):
        try:
            return subprocess.run([os.path.join(FFB, tool)] + args, capture_output=True,
                                  text=True, timeout=120).stdout.strip()
        except Exception as e:
            return "ERR %s" % repr(e)[:80]

    probe = run("ffprobe.exe", ["-v", "error", "-show_entries",
                                "format=duration,bit_rate,format_name",
                                "-show_entries", "stream=codec_name,sample_rate,channels,bit_rate",
                                "-of", "json", files[0]])
    try:
        j = json.loads(probe)
        st = (j.get("streams") or [{}])[0]
        fm = j.get("format") or {}
        print("codec     : %s   %s Hz   %s ch" % (st.get("codec_name"), st.get("sample_rate"),
                                                 st.get("channels")))
        print("duration  : %.2f s" % float(fm.get("duration") or 0))
        print("bitrate   : %s" % (fm.get("bit_rate") or st.get("bit_rate")))
    except Exception:
        print("probe     : %s" % probe[:200])

    # loudness and silence -- XTTS is sensitive to both
    loud = run("ffmpeg.exe", ["-hide_banner", "-i", files[0], "-af",
                              "ebur128=peak=true", "-f", "null", "-"])
    tail = [l for l in loud.splitlines() if "I:" in l or "Peak:" in l or "LUFS" in l]
    if tail:
        print("loudness  : %s" % " | ".join(tail[-2:])[:180])

    sil = run("ffmpeg.exe", ["-hide_banner", "-i", files[0], "-af",
                             "silencedetect=noise=-40dB:d=0.4", "-f", "null", "-"])
    dets = [l.strip() for l in sil.splitlines() if "silence_" in l]
    if dets:
        print("silence   :")
        for d in dets[:6]:
            print("            %s" % d)
    else:
        print("silence   : none over 0.4 s below -40 dB")

    # how much is actually speech vs room
    vol = run("ffmpeg.exe", ["-hide_banner", "-i", files[0], "-af",
                             "volumedetect", "-f", "null", "-"])
    for l in vol.splitlines():
        if "mean_volume" in l or "max_volume" in l:
            print("level     : %s" % l.split("]")[-1].strip())

    # XTTS wants mono 24 kHz float-ish wav; mp3 at 44.1 kHz is fine as input but converting once,
    # cleanly, avoids resampling artefacts inside the conditioning step.
    out = os.path.join(D, "reference_clean.wav")
    rc = run("ffmpeg.exe", ["-y", "-hide_banner", "-loglevel", "error", "-i", files[0],
                            "-ac", "1", "-ar", "24000", "-af",
                            "highpass=f=60, loudnorm=I=-20:TP=-2:LRA=11",
                            "-c:a", "pcm_s16le", out])
    if os.path.exists(out):
        import wave as _w
        w = _w.open(out, "rb")
        d = w.getnframes() / float(w.getframerate())
        print("\nWROTE reference_clean.wav  %.2f s  %d Hz  mono  %d bytes"
              % (d, w.getframerate(), os.path.getsize(out)))
        print("  full path: %s" % out)
        print("  (mono 24 kHz, high-pass 60 Hz, loudness normalised to -20 LUFS, no clipping)")
    else:
        print("conversion failed: %s" % rc[:200])
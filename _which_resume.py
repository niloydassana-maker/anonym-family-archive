import io, sys, re, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def probe(p, label):
    try:
        raw = open(p, "rb").read()
    except Exception as e:
        print(f"{label}: MISSING ({e})"); return
    txt = ""
    # PDF metadata + any uncompressed text
    for m in re.finditer(rb"/(Author|Title|Creator)\s*\(([^)]{0,80})\)", raw):
        txt += m.group(2).decode("latin-1", "replace") + " | "
    print(f"{label}: {len(raw)} bytes")
    print(f"   meta: {txt.strip()[:120] or '(none)'}")
    # name heuristics
    for name in (b"Kunal", b"NILOY", b"Partha", b"Deb"):
        if name.lower() in raw.lower():
            print(f"   contains: {name.decode()}")
probe(r"D:\anonym\kilo_apply_resume.pdf", "kilo_apply_resume.pdf")
probe(r"D:\anonym\career\Partha_Deb_Resume.pdf", "Partha_Deb_Resume.pdf")

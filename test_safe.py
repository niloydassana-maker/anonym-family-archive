import subprocess

SERIAL = "10BE8135QM001KK"
ADB = r"D:\anonym\platform-tools\adb.exe"

def make_adb_safe(text):
    text = text.replace(' ', '%s')
    for s in ['\\', '"', "'", '(', ')', '&', ';', '<', '>', '|', '*', '?', '`', '$']:
        text = text.replace(s, '\\' + s)
    return text

msg = "Saw you're Open to Work. Built job automation applying to perfect-fit roles on LinkedIn/Naukri/Foundit while laptop idles (Rs 499 setup). Demo: https://drive.google.com/file/d/1ToXMovfWEuqRBBRwyJpNxbgUVfQMoAOl/view?usp=sharing. Happy to share more if you accept. - Kunal"
safe = make_adb_safe(msg)
print("Safe string:", safe)

# Run echo on adb shell
r = subprocess.run([ADB, "-s", SERIAL, "shell", f"echo {safe}"], capture_output=True, text=True)
print("ADB shell echo output:", r.stdout.strip())
print("Stderr:", r.stderr.strip())

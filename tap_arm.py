import subprocess, re
adb = 'D:/anonym/platform-tools/adb.exe'
s = '10BE8135QM001KK'
subprocess.run([adb, '-s', s, 'shell', 'uiautomator', 'dump', '/data/local/tmp/dump.xml'])
xml = subprocess.check_output([adb, '-s', s, 'shell', 'cat', '/data/local/tmp/dump.xml'], encoding='utf-8', errors='ignore')
m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*text="ARM THE BRIDGE"', xml)
if not m:
    m = re.search(r'text="ARM THE BRIDGE"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
if m:
    x1, y1, x2, y2 = map(int, m.groups())
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    print(f'BUTTON CENTER: {cx} {cy}')
    subprocess.run([adb, '-s', s, 'shell', 'input', 'tap', str(cx), str(cy)])
    print('TAPPED!')
else:
    print('BUTTON NOT FOUND IN XML, length:', len(xml))

import ctypes
import subprocess

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

hwnd = u32.GetOpenClipboardWindow()
print(f"Clipboard locked by HWND: {hwnd}")
if hwnd:
    pid = ctypes.c_ulong()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    print(f"Locked by PID: {pid.value}")
    try:
        out = subprocess.check_output(f'tasklist /fi "PID eq {pid.value}"', shell=True).decode()
        print(out)
    except Exception as e:
        print(e)
else:
    print("Clipboard is not locked by any window.")

if u32.OpenClipboard(None):
    print("Successfully opened clipboard!")
    u32.EmptyClipboard()
    u32.CloseClipboard()
    print("Emptied and closed clipboard successfully.")
else:
    print("Failed to open clipboard, error code:", k32.GetLastError())

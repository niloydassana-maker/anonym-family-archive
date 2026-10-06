import ctypes
from ctypes import wintypes

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

k32.GlobalAlloc.restype = wintypes.HGLOBAL
k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
k32.GlobalLock.restype = wintypes.LPVOID
k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
k32.GlobalUnlock.restype = wintypes.BOOL
k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
u32.SetClipboardData.restype = wintypes.HANDLE
u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

GMEM_MOVEABLE = 0x0002
CF_UNICODETEXT = 13

def copy_text_to_clipboard(text: str):
    if not u32.OpenClipboard(None):
        print("Failed to open clipboard")
        return False
    try:
        u32.EmptyClipboard()
        data = text.encode('utf-16le') + b'\x00\x00'
        h_mem = k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h_mem:
            print("Failed GlobalAlloc")
            return False
        p_mem = k32.GlobalLock(h_mem)
        if not p_mem:
            print("Failed GlobalLock")
            return False
        ctypes.memmove(p_mem, data, len(data))
        k32.GlobalUnlock(h_mem)
        if not u32.SetClipboardData(CF_UNICODETEXT, h_mem):
            print("Failed SetClipboardData")
            return False
        print("Text successfully copied to Windows clipboard!")
        return True
    finally:
        u32.CloseClipboard()

if __name__ == "__main__":
    with open(r"D:\anonym\Email_Draft_To_Aveek.md", "r", encoding="utf-8") as f:
        content = f.read()
    copy_text_to_clipboard(content)

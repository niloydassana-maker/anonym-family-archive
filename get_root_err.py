# -*- coding: utf-8 -*-
import urllib.request
import urllib.error

try:
    with urllib.request.urlopen(
        "https://isearch-xsolve--kilo-voice-clinic-kilovoiceservice-web.modal.run/",
        timeout=60,
    ) as resp:
        print("STATUS", resp.status)
        print("HEADERS", dict(resp.headers))
        body = resp.read()
        print("LEN", len(body))
        open(r"D:\anonym\root_body.bin", "wb").write(body)
except urllib.error.HTTPError as e:
    print("HTTP", e.code)
    print("HEADERS", dict(e.headers))
    body = e.read()
    print("LEN", len(body))
    open(r"D:\anonym\root_body.bin", "wb").write(body)
print("done")

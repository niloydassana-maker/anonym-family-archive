import socket
from concurrent.futures import ThreadPoolExecutor

TARGET = "172.23.85.117"
LO, HI = 32768, 61000

def probe(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        if s.connect_ex((TARGET, port)) == 0:
            return port
    finally:
        s.close()
    return None

open_ports = []
with ThreadPoolExecutor(max_workers=800) as ex:
    for r in ex.map(probe, range(LO, HI + 1)):
        if r:
            open_ports.append(r)

print("OPEN:", open_ports)

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import socket

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8767))
s.listen(1)
s.settimeout(20)
print("listening", flush=True)
try:
    conn, addr = s.accept()
    data = conn.recv(2000)
    print("got", data[:300], flush=True)
    conn.close()
except Exception as e:
    print("fail", type(e).__name__, e, flush=True)

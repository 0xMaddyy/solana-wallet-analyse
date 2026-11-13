import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import time
import urllib.request

URL = "https://public.rpc.solanavibestation.com"
sigs = [s["signature"] for s in json.load(open("2h6d_sigs.json"))][:8]
body = json.dumps([
    {"jsonrpc": "2.0", "id": i, "method": "getTransaction",
     "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}]}
    for i, sig in enumerate(sigs)
]).encode()
t = time.time()
req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as r:
    out = json.loads(r.read())
print("sec", round(time.time() - t, 2), "n", len(out) if isinstance(out, list) else type(out))
if isinstance(out, list):
    for item in out:
        tx = item.get("result") or {}
        msg = (tx.get("transaction") or {}).get("message") or {}
        print(item.get("id"), item.get("error"), tx.get("slot"), [i.get("programId", "")[:6] for i in msg.get("instructions") or []][:6])

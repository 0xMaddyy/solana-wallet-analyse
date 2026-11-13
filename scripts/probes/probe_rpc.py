import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import os
import urllib.request

WALLET = "2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf"
urls = [
    os.environ.get("SNO_RPC_URL") or os.environ.get("HELIUS_RPC_URL") or "",
    "https://api.mainnet-beta.solana.com",
]
body = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
    "params": [WALLET, {"limit": 1}],
}).encode()
for url in urls:
    if not url:
        print("(skip empty SNO_RPC_URL)")
        continue
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read())
        print(url[:40], "ok", "error" in out, str(out)[:180])
    except Exception as e:
        print(url[:40], type(e).__name__, e)

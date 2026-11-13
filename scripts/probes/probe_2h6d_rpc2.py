import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import time
import urllib.request

sig = json.load(open("2h6d_sigs.json"))[0]["signature"]
urls = [
    "https://api.mainnet-beta.solana.com",
    "https://rpc.ankr.com/solana",
    "https://solana.drpc.org",
]
body = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
    "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}],
}).encode()
time.sleep(8)
for u in urls:
    t0 = time.time()
    try:
        req = urllib.request.Request(u, data=body, headers={"Content-Type": "application/json"})
        raw = urllib.request.urlopen(req, timeout=40).read()
        out = json.loads(raw)
        ok = "result" in out and out["result"]
        print(f"{u} {time.time()-t0:.1f}s ok={bool(ok)} err={out.get('error')}")
        if ok:
            msg = out["result"]["transaction"]["message"]
            print(" programs", [ix["programId"][:12] for ix in msg["instructions"]])
    except Exception as e:
        print(u, type(e).__name__, getattr(e, "code", ""), str(e)[:80])
    time.sleep(2)

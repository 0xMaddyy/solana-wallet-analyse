import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc, RPC
import urllib.request
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

def call(params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTransactionsForAddress", "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.loads(r.read())
    if "error" in out:
        print("ERR", str(out["error"])[:250])
        return None
    return out["result"]

res = call([PUMP, {"limit": 1, "sortOrder": "asc", "filters": {"slot": {"gte": 459024009, "lt": 459024100}}}])
if res:
    print("keys", res.keys(), "n", len(res.get("data") or []))
    item = res["data"][0]
    print("item keys", item.keys())
    print(json.dumps(item)[:2000])

print("--- details signatures")
res2 = call([PUMP, {"limit": 2, "transactionDetails": "signatures", "sortOrder": "asc", "filters": {"slot": {"gte": 459024009, "lt": 459024050}}}])
if res2:
    print(json.dumps(res2["data"][0])[:800])

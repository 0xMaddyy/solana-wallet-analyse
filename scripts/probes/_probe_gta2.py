import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc, RPC
import urllib.request

PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

def try_rpc(params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTransactionsForAddress", "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    if "error" in out:
        print("ERR", out["error"].get("message", "")[:300])
        return
    res = out["result"]
    print("OK", type(res).__name__, (list(res)[:8] if isinstance(res, dict) else str(res)[:200]))

print("--- one arg")
try_rpc([PUMP])
print("--- limit only")
try_rpc([PUMP, {"limit": 2}])
print("--- sigs")
page = rpc("getSignaturesForAddress", [PUMP, {"limit": 1000}])
print("page", len(page), "slot", page[-1]["slot"], "->", page[0]["slot"], "span", page[0]["slot"] - page[-1]["slot"])

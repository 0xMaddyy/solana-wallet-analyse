import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import RPC
import urllib.request
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

def call(details):
    params = [PUMP, {
        "limit": 1,
        "sortOrder": "asc",
        "transactionDetails": details,
        "filters": {"slot": {"gte": 459024009, "lt": 459024020}, "status": "succeeded"},
    }]
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTransactionsForAddress", "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read()
    out = json.loads(raw)
    if "error" in out:
        print(details, "ERR", str(out["error"])[:200])
        return
    item = out["result"]["data"][0]
    print(details, "bytes", len(raw), "keys", list(item)[:12])
    # signer hints
    blob = json.dumps(item)
    print(blob[:400])

for d in ("accounts", "full"):
    call(d)

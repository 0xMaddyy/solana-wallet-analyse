import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import time
import urllib.request
from sno.analyze import RPC

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"

def call(cfg):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTransactionsForAddress", "params": [ADDR, cfg]}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.loads(r.read())
    if "error" in out:
        print("sec", round(time.time() - t, 2), "ERR", out["error"].get("message", "")[:200])
        return
    data = out["result"].get("data") or []
    print("sec", round(time.time() - t, 2), "n", len(data), "keys", list(data[0])[:8] if data else None)

call({
    "limit": 50,
    "sortOrder": "asc",
    "transactionDetails": "full",
    "encoding": "json",
    "filters": {"status": "succeeded", "slot": {"gte": 459024095, "lt": 459421250}},
})

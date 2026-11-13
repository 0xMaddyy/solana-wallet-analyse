import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request
from sno.analyze import RPC

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"
token = None
signed = 0
total = 0
signers = {}
for i in range(6):
    cfg = {
        "limit": 50,
        "sortOrder": "asc",
        "transactionDetails": "full",
        "encoding": "json",
        "filters": {"status": "succeeded", "slot": {"gte": 459023999, "lt": 459421250}},
    }
    if token:
        cfg["paginationToken"] = token
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTransactionsForAddress", "params": [ADDR, cfg]}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        res = json.loads(r.read())["result"]
    for item in res["data"]:
        msg = item["transaction"]["message"]
        n = msg["header"]["numRequiredSignatures"]
        pubs = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"][:n]]
        fee = pubs[0]
        signers[fee] = signers.get(fee, 0) + 1
        total += 1
        if ADDR in pubs:
            signed += 1
    token = res.get("paginationToken")
    print("page", i, "total", total, "signed", signed)
    if not token:
        break
top = sorted(signers.items(), key=lambda kv: -kv[1])[:8]
print("top signers")
for s, n in top:
    print(n, s)

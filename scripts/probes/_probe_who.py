import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"
res = rpc("getTransactionsForAddress", [ADDR, {
    "limit": 5,
    "sortOrder": "asc",
    "filters": {"status": "succeeded", "slot": {"gte": 459024095, "lt": 459024400}},
}])
data = res.get("data") or []
print("succeeded n", len(data), "token", res.get("paginationToken"))
if not data:
    res = rpc("getTransactionsForAddress", [ADDR, {
        "limit": 3,
        "sortOrder": "asc",
        "filters": {"slot": {"gte": 459024095, "lt": 459024200}},
    }])
    data = res.get("data") or []
    print("any n", len(data))
sig = data[0]["signature"]
tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
keys = tx["transaction"]["message"]["accountKeys"]
pubs = [k["pubkey"] if isinstance(k, dict) else k for k in keys]
signers = [k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")]
print("signers", signers)
print("addr index", pubs.index(ADDR) if ADDR in pubs else None, "nkeys", len(pubs))
print("err", tx["meta"]["err"], "slot", tx["slot"])

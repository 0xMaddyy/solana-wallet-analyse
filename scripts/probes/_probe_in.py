import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request
from sno.analyze import RPC, rpc

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"

def call(filters, details=None):
    cfg = {"limit": 10, "sortOrder": "asc", "filters": filters}
    if details:
        cfg["transactionDetails"] = details
        cfg["encoding"] = "json"
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTransactionsForAddress", "params": [ADDR, cfg]}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.loads(r.read())
    if "error" in out:
        print("ERR", out["error"].get("message", "")[:220])
        return None
    data = out["result"].get("data") or []
    print("n", len(data), "token", bool(out["result"].get("paginationToken")), "slot", data[0]["slot"] if data else None)
    return data

data = call({
    "status": "succeeded",
    "slot": {"gte": 459023999, "lt": 459421250},
    "tokenTransfer": {"direction": "in"},
})
if data:
    sig = data[0]["signature"]
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    keys = tx["transaction"]["message"]["accountKeys"]
    signers = [k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")]
    print("signer", signers[0], "match", signers[0] == ADDR)

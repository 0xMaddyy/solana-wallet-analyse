import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request
from sno.analyze import RPC

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"
body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTransactionsForAddress", "params": [ADDR, {
    "limit": 1,
    "sortOrder": "asc",
    "transactionDetails": "full",
    "encoding": "jsonParsed",
    "maxSupportedTransactionVersion": 1,
    "filters": {"status": "succeeded", "slot": {"gte": 459023999, "lt": 459421250}},
}]}).encode()
req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=90) as r:
    item = json.loads(r.read())["result"]["data"][0]
msg = item["transaction"]["message"]
keys = msg["accountKeys"]
pubs = [k["pubkey"] if isinstance(k, dict) else k for k in keys]
print("index", pubs.index(ADDR), "n", len(pubs))
for ix in msg["instructions"]:
    accs = ix.get("accounts") or []
    if ADDR in accs or (isinstance(accs, list) and any(pubs[i] == ADDR for i in accs if isinstance(i, int) and i < len(pubs))):
        print("ix program", ix.get("programId"), "parsed", str(ix.get("parsed"))[:300])
print("inner")
for grp in (item.get("meta") or {}).get("innerInstructions") or []:
    for ix in grp.get("instructions") or []:
        accs = ix.get("accounts") or []
        hit = ADDR in accs
        if not hit and accs and isinstance(accs[0], int):
            hit = any(i < len(pubs) and pubs[i] == ADDR for i in accs)
        if hit:
            print(" inner", ix.get("programId"), str(ix.get("parsed"))[:250])

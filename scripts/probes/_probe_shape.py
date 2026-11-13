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
    "limit": 20,
    "sortOrder": "asc",
    "transactionDetails": "full",
    "encoding": "json",
    "filters": {"status": "succeeded", "slot": {"gte": 459024095, "lt": 459421250}},
}]}).encode()
req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=90) as r:
    data = json.loads(r.read())["result"]["data"]
item = data[0]
msg = item["transaction"]["message"]
print("msg keys", msg.keys())
k0 = msg["accountKeys"][0]
print("key0 type", type(k0).__name__, str(k0)[:200])
print("header", msg.get("header"))
matched = 0
for item in data:
    msg = item["transaction"]["message"]
    keys = msg["accountKeys"]
    n = msg["header"]["numRequiredSignatures"]
    pubs = []
    for k in keys[:n]:
        pubs.append(k["pubkey"] if isinstance(k, dict) else k)
    if ADDR in pubs:
        matched += 1
print("signed by addr", matched, "of", len(data))

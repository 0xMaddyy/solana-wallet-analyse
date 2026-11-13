import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request
from sno.analyze import RPC

ADDR = "8HFagtU2YAGxhWRPuFQ9Jrj5K387vQpUUTB7goHpump"
START = 1780272000  # 2026-06-01 UTC
END = 1792540800    # 2026-10-21 UTC

def call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]

info = call("getAccountInfo", [ADDR, {"encoding": "jsonParsed"}])
val = info["value"]
print("exists", bool(val), "lamports", None if not val else val["lamports"], "owner", None if not val else val["owner"])

res = call("getTransactionsForAddress", [ADDR, {
    "limit": 1000,
    "sortOrder": "asc",
    "filters": {"blockTime": {"gte": START, "lt": END}, "status": "succeeded"},
}])
data = res.get("data") or []
print("page", len(data), "token", bool(res.get("paginationToken")))
if data:
    print("first", data[0]["slot"], data[0]["blockTime"], "last", data[-1]["slot"], data[-1]["blockTime"])

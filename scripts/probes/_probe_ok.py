import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time
from sno.analyze import rpc

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"
opts = {
    "limit": 1000,
    "sortOrder": "asc",
    "filters": {"status": "succeeded", "slot": {"gte": 459023999, "lt": 459421250}},
}
token = None
total = 0
for i in range(5):
    if token:
        opts["paginationToken"] = token
    t = time.time()
    res = rpc("getTransactionsForAddress", [ADDR, opts])
    data = res.get("data") or []
    token = res.get("paginationToken")
    total += len(data)
    print("page", i, "n", len(data), "slots", data[0]["slot"] if data else None, "->", data[-1]["slot"] if data else None,
          "sec", round(time.time() - t, 2), "token", bool(token))
    if not token or len(data) < 1000:
        break
print("total", total)

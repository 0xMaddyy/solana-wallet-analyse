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
    "filters": {"slot": {"gte": 459023999, "lt": 459421250}},
}
t = time.time()
res = rpc("getTransactionsForAddress", [ADDR, opts])
data = res.get("data") or []
token = res.get("paginationToken")
print("page1", len(data), data[0]["slot"], data[-1]["slot"], "token", str(token)[:80], "sec", round(time.time() - t, 2))
opts["paginationToken"] = token
t = time.time()
res2 = rpc("getTransactionsForAddress", [ADDR, opts])
data2 = res2.get("data") or []
print("page2", len(data2), (data2[0]["slot"] if data2 else None), (data2[-1]["slot"] if data2 else None),
      "same", data2[0]["signature"] == data[0]["signature"] if data2 else None,
      "token", str(res2.get("paginationToken"))[:80], "sec", round(time.time() - t, 2))

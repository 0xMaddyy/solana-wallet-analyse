import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time
from sno.analyze import rpc

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"
GTE, LT = 459023999, 459421250
t = time.time()
res = rpc("getTransactionsForAddress", [ADDR, {
    "limit": 1000,
    "sortOrder": "asc",
    "filters": {"slot": {"gte": GTE, "lt": LT}},
}])
print("n", len(res.get("data") or []), "token", bool(res.get("paginationToken")), "sec", round(time.time() - t, 2))

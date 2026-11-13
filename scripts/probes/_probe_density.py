import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time
from sno.analyze import rpc
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
LO, HI = 459024009, 459025009  # 1000 slots
token = None
n = 0
adj = 0
t0 = time.time()
pages = 0
prev = None
while True:
    cfg = {"limit": 1000, "sortOrder": "asc", "filters": {"slot": {"gte": LO, "lt": HI}}}
    if token:
        cfg["paginationToken"] = token
    res = rpc("getTransactionsForAddress", [PUMP, cfg])
    pages += 1
    data = res["data"]
    if not data:
        break
    for s in data:
        n += 1
        if prev and prev["slot"] == s["slot"] and s["transactionIndex"] == prev["transactionIndex"] + 1:
            adj += 1
        prev = s
    token = res.get("paginationToken")
    if not token or data[-1]["slot"] >= HI:
        break
print(f"txs {n} adjacent pairs {adj} pages {pages} sec {time.time()-t0:.1f}")

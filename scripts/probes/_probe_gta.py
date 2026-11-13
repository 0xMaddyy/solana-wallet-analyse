import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
res = rpc("getTransactionsForAddress", [PUMP, {
    "transactionDetails": "accounts",
    "encoding": "json",
    "limit": 5,
    "sortOrder": "asc",
    "filters": {"slot": {"gte": 459024009, "lte": 459024200}},
}])
print(type(res), res.keys() if isinstance(res, dict) else None)
data = res.get("data") or res.get("transactions") or res
if isinstance(res, dict):
    print("top", {k: (len(v) if hasattr(v, "__len__") and not isinstance(v, str) else v) for k, v in res.items()})
item = (res.get("data") or [None])[0]
print("item type", type(item))
if isinstance(item, dict):
    print("item keys", item.keys())
    print(json.dumps(item)[:1500])

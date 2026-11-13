import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"
res = rpc("getTransactionsForAddress", [ADDR, {
    "limit": 1,
    "sortOrder": "asc",
    "transactionDetails": "accounts",
    "encoding": "json",
    "filters": {"status": "succeeded", "slot": {"gte": 459024095, "lt": 459024200}},
}])
item = res["data"][0]
print(item.keys())
print(json.dumps(item)[:1500])

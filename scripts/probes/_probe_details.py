import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc

ADDR = "5hAgYC8TJCcEZV7LTXAzkTrm7YL29YXyQQJPCNrG84zM"
base = {"limit": 2, "sortOrder": "asc", "filters": {"slot": {"gte": 459024095, "lt": 459024200}}}
for details in ("accounts", "full"):
    cfg = dict(base)
    cfg["transactionDetails"] = details
    cfg["encoding"] = "json"
    try:
        res = rpc("getTransactionsForAddress", [ADDR, cfg])
    except Exception as e:
        print(details, "ERR", str(e)[:200])
        continue
    item = (res.get("data") or [None])[0]
    print(details, "keys", list(item)[:12] if isinstance(item, dict) else type(item))
    print(json.dumps(item)[:500])

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
SLOT = 459226783
b = rpc("getBlock", [SLOT, {"transactionDetails": "accounts", "rewards": False,
                            "maxSupportedTransactionVersion": 1, "encoding": "json"}])
print("ntx", len(b["transactions"]))
hits = 0
for i, tx in enumerate(b["transactions"]):
    meta = tx["meta"]
    if not meta.get("postTokenBalances"):
        continue
    hits += 1
    if hits == 1:
        print("sample post", meta["postTokenBalances"][0])
print("txs with token balances", hits)
# known bot buy around index 643
for i in (641, 642, 643, 644):
    tx = b["transactions"][i]
    keys = tx["transaction"]["accountKeys"]
    signer = next(k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer"))
    mints = []
    for row in tx["meta"].get("postTokenBalances") or []:
        if row.get("owner") == signer:
            mints.append(row["mint"][:8])
    print(i, signer[:8], "err", bool(tx["meta"].get("err")), "mints", mints[:4], "pump", any((k.get("pubkey") if isinstance(k, dict) else k) == PUMP for k in keys))

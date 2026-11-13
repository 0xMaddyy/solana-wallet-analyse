import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from datetime import datetime, timezone
from sno.analyze import rpc

START = int(datetime(2026, 10, 20, tzinfo=timezone.utc).timestamp())
END = START + 86400

def slot_at(ts):
    lo, hi = 450_000_000, 470_000_000
    while lo < hi:
        mid = (lo + hi) // 2
        bt = rpc("getBlockTime", [mid])
        if bt is None or bt < ts:
            lo = mid + 1
        else:
            hi = mid
    return lo

s0 = slot_at(START)
s1 = slot_at(END)
print("slots", s0, s1, "span", s1 - s0)

b = rpc("getBlock", [s0 + 5000, {"transactionDetails": "accounts", "rewards": False,
                                 "maxSupportedTransactionVersion": 1, "encoding": "json"}])
print("keys", b.keys() if b else None, "ntx", len(b["transactions"]) if b else None)
if b and b["transactions"]:
    tx = b["transactions"][100] if len(b["transactions"]) > 100 else b["transactions"][0]
    print("meta keys", tx["meta"].keys())
    print("err", tx["meta"].get("err"))
    pt = tx["meta"].get("preTokenBalances")
    print("pre sample", (pt or [None])[0])
    ak = tx["transaction"]["accountKeys"]
    print("nkeys", len(ak), "pump prog", any((k.get("pubkey") if isinstance(k, dict) else k) == "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" for k in ak))

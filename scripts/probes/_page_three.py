import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from datetime import datetime, timezone
from sno.analyze import rpc

PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
START = int(datetime(2026, 10, 20, tzinfo=timezone.utc).timestamp())
END = START + 86400
WALLETS = [
    "FfW5e8gKJfgaZPog6DiJoW6Kif6Fb23CokWprRhHVjV1",
    "CRjYEJowq4YaPUSkJsJResF6Hu5ko4GiB4PX9jmX7CrE",
    "D1gszVJ9vvAdrfaAWcYU745WKywKR8C16hFeyPjY8dJg",
]

def page(addr):
    out, before = [], None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        batch = rpc("getSignaturesForAddress", [addr, opts])
        if not batch:
            break
        for s in batch:
            bt = s.get("blockTime")
            if bt is None or bt >= END or bt < START:
                continue
            out.append(s)
        before = batch[-1]["signature"]
        last = batch[-1].get("blockTime") or 0
        if last < START or len(batch) < 1000:
            break
    return out

for w in WALLETS:
    rows = page(w)
    ok = sum(1 for s in rows if not s.get("err"))
    fail = len(rows) - ok
    slots = len({s["slot"] for s in rows})
    print(f"{w[:8]} txs {len(rows)} ok {ok} fail {fail} slots {slots}", flush=True)

# token balances present?
b = rpc("getBlock", [459226783, {"transactionDetails": "accounts", "rewards": False,
                                 "maxSupportedTransactionVersion": 1, "encoding": "json"}])
meta = b["transactions"][0]["meta"]
print("meta", sorted(meta.keys()))
print("pre", (meta.get("preTokenBalances") or [None])[0])
print("post", (meta.get("postTokenBalances") or [None])[0])

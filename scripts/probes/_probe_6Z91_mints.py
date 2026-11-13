"""Estimate unique mints / buy count for 6Z91 via signature pages (fast)."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from sno.analyze import rpc

WALLET = "6Z91Dgiz9E44bMW11rQuMBjt1NwwPoQGXFNZieGfVtAb"
# just count total succeeded sigs in range via getSignaturesForAddress
START = 1761724800  # 2026-10-29 approx - use first funding from profit file
# better: paginate getSignaturesForAddress
n = 0
before = None
while True:
    opts = {"limit": 1000}
    if before:
        opts["before"] = before
    page = rpc("getSignaturesForAddress", [WALLET, opts]) or []
    if not page:
        break
    n += len(page)
    before = page[-1]["signature"]
    if n >= 5000:
        break
print("sigs sampled", n, "last slot", page[-1]["slot"] if page else None)

# full detail sample of 200 for mint uniqueness
res = rpc("getTransactionsForAddress", [WALLET, {
    "limit": 200,
    "sortOrder": "desc",
    "transactionDetails": "full",
    "encoding": "json",
    "maxSupportedTransactionVersion": 1,
    "filters": {"status": "succeeded"},
}])
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
buys = sells = 0
mints = Counter()
for item in res.get("data") or []:
    meta = item["meta"]
    pre, post = {}, {}
    for row in meta.get("preTokenBalances") or []:
        if row.get("owner") == WALLET:
            pre[row["mint"]] = pre.get(row["mint"], 0) + int(row["uiTokenAmount"]["amount"])
    for row in meta.get("postTokenBalances") or []:
        if row.get("owner") == WALLET:
            post[row["mint"]] = post.get(row["mint"], 0) + int(row["uiTokenAmount"]["amount"])
    for m in set(pre) | set(post):
        if m in (WSOL, USDC):
            continue
        d = post.get(m, 0) - pre.get(m, 0)
        if d > 0:
            buys += 1
            mints[m] += 1
        elif d < 0:
            sells += 1
print(f"in 200 txs: buys {buys} sells {sells} unique buy-mints {len(mints)}")

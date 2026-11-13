"""Scan each backrun block for bot txs touching the same mint that sit before (or after) the target tx."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import rpc

CSV, PREFIX = sys.argv[1], sys.argv[2]
rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8-sig")) if r["buyer_wallet"].startswith(PREFIX)]


def scan(r):
    blk = rpc("getBlock", [int(r["slot"]), {"transactionDetails": "accounts", "rewards": False,
                                            "maxSupportedTransactionVersion": 1}])
    sigs = [t["transaction"]["signatures"][0] for t in blk["transactions"]]
    ti = sigs.index(r["target_tx"])
    ahead, after = [], 0
    for i, t in enumerate(blk["transactions"]):
        keys = t["transaction"]["accountKeys"]
        if keys[0]["pubkey"] != r["buyer_wallet"] or r["mint"] not in [k["pubkey"] for k in keys]:
            continue
        if i < ti:
            ahead.append((ti - i, "FAIL" if t["meta"]["err"] else "ok", str(t["meta"]["err"])))
        elif i > ti and t["meta"]["err"]:
            after += 1
    return ahead, after


with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(scan, rows))
c = Counter()
errs = Counter()
for ahead, after in res:
    c["backruns"] += 1
    c["with_bot_tx_ahead"] += bool(ahead)
    c["failed_ahead"] += sum(a[1] == "FAIL" for a in ahead)
    c["ok_ahead"] += sum(a[1] == "ok" for a in ahead)
    c["failed_after"] += after
    errs.update(a[2] for a in ahead)
print(PREFIX, dict(c))
print("  errors ahead:", errs.most_common(4))

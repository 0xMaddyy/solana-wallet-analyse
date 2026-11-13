"""Compare how the Oct 8 pair bots and the Oct 13 single-wallet bots execute backruns."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import os
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime

from sno.analyze import rpc

LH = "L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
DAYS = {
    "oct8": ("backruns_oct8.blockorder.csv", lambda b: f"multi_{b[:8]}.jsonl"),
    "oct13": ("backruns_oct13.full.csv", lambda b: f"multi_oct13_{b[:8]}.jsonl"),
}


def secs(a, b):
    f = "%Y-%m-%d %H:%M:%S"
    return (datetime.strptime(b, f) - datetime.strptime(a, f)).total_seconds()


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


for day, (path, cache) in DAYS.items():
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    print(f"\n===== {day}: {len(rows)} backruns")
    hold = [secs(r["time_utc"], r["last_sell_utc"]) for r in rows if r["last_sell_utc"]]
    print(f"hold time s: p10 {q(hold, .1)}  median {q(hold, .5)}  p90 {q(hold, .9)}  same-second {sum(h == 0 for h in hold)}")
    print("sell_count:", Counter(r["sell_count"] for r in rows).most_common(4))
    buy = [float(r["buy_sol"]) for r in rows]
    print(f"buy_sol: median {st.median(buy):.3f}  p10 {q(buy, .1):.3f}  p90 {q(buy, .9):.3f}")
    prof = defaultdict(list)
    for r in rows:
        prof[r["bot_route"]].append(float(r["trade_profit_sol"]))
    for k, v in prof.items():
        print(f"route {k:12s} n {len(v):5d}  profit {sum(v):+8.2f}  median {st.median(v):+.4f}  win {sum(x > 0 for x in v) / len(v):.0%}")
    pf = [float(r["bot_priority_fee_sol"]) for r in rows]
    print(f"priority fee SOL: median {st.median(pf):.5f}  p90 {q(pf, .9):.5f}")
    print("bot_swqos:", Counter(r["bot_swqos"] for r in rows).most_common(6))

    recs = {}
    for b in {r["buyer_wallet"] for r in rows}:
        if os.path.exists(cache(b)):
            for l in open(cache(b)):
                t = json.loads(l)
                recs[t["sig"]] = t
    lh = progs = Counter()
    lh = sum(1 for r in rows if LH in recs.get(r["bot_tx"], {}).get("programs", []))
    progs = Counter(p for r in rows for p in recs.get(r["bot_tx"], {}).get("programs", [])
                    if p not in (LH, PUMP) and not p.startswith(("ComputeBudget", "1111", "AToken", "Token")))
    print(f"bot buys with Lighthouse: {lh}/{len(rows)}; other top-level programs: {progs.most_common(4)}")
    nsig = Counter(recs.get(r["bot_tx"], {}).get("n_sigs") for r in rows)
    print("signatures per bot tx:", dict(nsig))

    # failure rate (Oct 8 cache keeps failed txs; Oct 13 cache holds successes only)
    allc = Counter()
    for t in recs.values():
        allc["failed" if t.get("err") else "ok"] += 1
    print("cached txs:", dict(allc))

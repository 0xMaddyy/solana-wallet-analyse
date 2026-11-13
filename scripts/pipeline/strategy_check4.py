"""Target buy size (SOL spent by the target signer) for Oct 8 vs Oct 13 backruns."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import rpc


def spent(tx):
    keys = [k["pubkey"] for k in tx["transaction"]["message"]["accountKeys"]]
    m = tx["meta"]
    return (m["preBalances"][0] - m["postBalances"][0]) / 1e9


def q(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p * len(xs)))], 3)


cache = {}
for l in open("target_txs.jsonl"):
    rec = json.loads(l)
    cache[rec["sig"]] = rec["tx"]

for name, path in (("oct8", "backruns_oct8.blockorder.csv"), ("oct13", "backruns_oct13.full.csv")):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    todo = [r["target_tx"] for r in rows if r["target_tx"] not in cache]
    with ThreadPoolExecutor(10) as ex:
        for sig, tx in zip(todo, ex.map(lambda s: rpc("getTransaction", [s, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}]), todo)):
            cache[sig] = tx
    t = [spent(cache[r["target_tx"]]) for r in rows]
    b = [float(r["buy_sol"]) for r in rows]
    ratio = [bb / tt for bb, tt in zip(b, t) if tt > 0.01]
    print(f"{name}: target buy SOL p10 {q(t, .1)} median {q(t, .5)} p90 {q(t, .9)}; "
          f"share of targets >= 1 SOL {sum(x >= 1 for x in t) / len(t):.0%}; bot/target size median {q(ratio, .5)}")
    big = sorted(zip(t, (float(r['trade_profit_sol']) for r in rows)))
    half = len(big) // 2
    print(f"   profit on smaller-half targets {sum(p for _, p in big[:half]):+.2f}, larger-half {sum(p for _, p in big[half:]):+.2f}")

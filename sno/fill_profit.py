import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from sno.multi_fetch import CSV, END_LABEL, PAIRS, TAG, out_path
from sno.multi_report import block_sigs, pair_mints, pair_sol
from sno.paths import RESULTS

POS_CACHE = str(RESULTS / f"block_pos_{TAG}.json")
block_pos = json.load(open(POS_CACHE)) if os.path.exists(POS_CACHE) else {}


def in_block_order(txs):
    """Sort by slot, then by position inside the block (bots often buy and sell in the same block)."""
    counts = Counter(t["slot"] for t in txs)
    shared = sorted({t["slot"] for t in txs if counts[t["slot"]] > 1 and t["sig"] not in block_pos.get(str(t["slot"]), {})})
    mine = {t["sig"] for t in txs}
    with ThreadPoolExecutor(10) as ex:
        for s, sigs in zip(shared, ex.map(block_sigs, shared)):
            block_pos.setdefault(str(s), {}).update({sig: i for i, sig in enumerate(sigs) if sig in mine})
    if shared:
        json.dump(block_pos, open(POS_CACHE, "w"))
    return sorted(txs, key=lambda t: (t["slot"], block_pos.get(str(t["slot"]), {}).get(t["sig"], 0)))


path = sys.argv[1] if len(sys.argv) > 1 else CSV
out = sys.argv[2] if len(sys.argv) > 2 else path


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


lots = {}
position = {}
issues = defaultdict(int)
for buyer, seller in PAIRS:
    pair = {buyer, seller}
    txs = [json.loads(l) for l in open(out_path(buyer))]
    txs = in_block_order([t for t in txs if not t.get("missing") and t["err"] is None])
    open_lots = defaultdict(list)
    mint_sol = defaultdict(int)
    for t in txs:
        mints = pair_mints(t, pair)
        if not mints:
            continue
        s = pair_sol(t, pair)
        paid_for = [m for m, d in mints.items() if (d < 0) == (s > 0)] or list(mints)
        for m, d in mints.items():
            share = s / len(paid_for) if m in paid_for else 0
            mint_sol[m] += share
            if d > 0:
                if share >= 0:
                    issues["tokens received without paying SOL"] += 1
                lot = {"sig": t["sig"], "tokens": d, "cost": -share, "sold": 0, "proceeds": 0.0, "sells": []}
                open_lots[m].append(lot)
                lots[(buyer, t["sig"], m)] = lot
                continue
            left = -d
            for lot in open_lots[m]:
                take = min(left, lot["tokens"] - lot["sold"])
                if take <= 0:
                    continue
                lot["sold"] += take
                lot["proceeds"] += share * take / -d
                lot["sells"].append((t["sig"], t["blockTime"]))
                left -= take
                if left == 0:
                    break
            open_lots[m] = [l for l in open_lots[m] if l["sold"] < l["tokens"]]
            if left:
                issues["sold tokens with no matching buy in window"] += 1
    for m, v in mint_sol.items():
        position[(buyer, m)] = v

rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
cols = list(rows[0])
for c in ("position_profit_sol", "sell_count", "last_sell_tx", "last_sell_utc"):
    if c not in cols:
        cols.append(c)
check = defaultdict(lambda: [0.0, 0])
for r in rows:
    lot = lots.get((r["buyer_wallet"], r["bot_tx"], r["mint"]))
    if lot is None:
        issues["CSV row with no buy lot"] += 1
        continue
    profit = (lot["proceeds"] - lot["cost"]) / 1e9
    unsold = 1 - lot["sold"] / lot["tokens"]
    r["trade_profit_sol"] = round(profit, 6)
    r["trade_status"] = "closed" if unsold < 1e-9 else f"open at {END_LABEL} ({unsold:.0%} unsold)"
    r["position_profit_sol"] = round(position[(r["buyer_wallet"], r["mint"])] / 1e9, 6)
    r["sell_count"] = len({s for s, _ in lot["sells"]})
    r["last_sell_tx"] = lot["sells"][-1][0] if lot["sells"] else ""
    r["last_sell_utc"] = utc(lot["sells"][-1][1]) if lot["sells"] else ""

for (buyer, sig, m), lot in lots.items():
    c = check[(buyer, m)]
    c[0] += lot["proceeds"] - lot["cost"]
    c[1] += lot["tokens"] - lot["sold"]
mismatch = [(k, v[0], position[k]) for k, v in check.items() if v[1] == 0 and abs(v[0] - position[k]) > 1000]
print("positions fully closed whose per-buy sum != position total:", len(mismatch))
for k, a, b in mismatch[:10]:
    print("  ", k[0][:8], k[1][:8], a / 1e9, b / 1e9)
print("issues:", dict(issues))

with open(out, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print("\n== per pair (backrun buys only)")
for buyer, _ in PAIRS:
    rs = [r for r in rows if r["buyer_wallet"] == buyer and r["trade_profit_sol"] != ""]
    p = sum(float(r["trade_profit_sol"]) for r in rs)
    wins = sum(1 for r in rs if float(r["trade_profit_sol"]) > 0)
    op = sum(1 for r in rs if r["trade_status"] != "closed")
    print(f"  {buyer[:8]}  rows {len(rs):4d}  profit {p:+9.3f} SOL  win {wins / max(len(rs), 1) * 100:5.1f}%  open {op}")
print("  total", round(sum(float(r["trade_profit_sol"]) for r in rows if r["trade_profit_sol"] != ""), 3))
print("  empty trade_profit_sol:", sum(1 for r in rows if r["trade_profit_sol"] == ""))

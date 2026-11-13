"""Summarize gate_6gY1_oct16.csv and spot-check 'no recent target'."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter, defaultdict

rows = list(csv.DictReader(open("gate_6gY1_oct16.csv", encoding="utf-8-sig")))
print("rows", len(rows), "from", rows[0]["time_utc"], "to", rows[-1]["time_utc"])
closed = [r for r in rows if r["trade_status"] == "closed"]
open_ = [r for r in rows if r["trade_status"] != "closed"]
print("closed", len(closed), "other", len(open_))

def f(r, k):
    return float(r[k]) if r[k] != "" else None

profits = sorted(f(r, "trade_profit_sol") for r in closed)
s = sum(profits)
print(f"profit {s:+.3f} win {sum(p > 0 for p in profits) / len(profits):.1%}")
for q in (0.5, 0.9, 0.99):
    print(f"  p{int(q*100)} {profits[int(q * (len(profits) - 1))]:+.4f}")
top = sorted(closed, key=lambda r: -f(r, "trade_profit_sol"))[:8]
print("top", [(r["wallet"][:6], r["sniping_type"], r["trade_profit_sol"], r["buy_sol"]) for r in top])
print("top8 share", sum(f(r, "trade_profit_sol") for r in top))
# profit if we drop the best 1%
cut = profits[: int(len(profits) * 0.99)]
print("without top 1%", sum(cut))

print("platforms", Counter(r["target_platform"] for r in rows if r["target_platform"]).most_common(8))
pos = [int(r["positions_after_target"]) for r in rows if r["sniping_type"] == "copy same block" and r["positions_after_target"]]
pos.sort()
if pos:
    print("same-block gap pos median", pos[len(pos)//2], "p90", pos[int(len(pos)*0.9)], "n", len(pos), "backrun-like <=3", sum(p <= 3 for p in pos))
gaps = [int(r["slots_after_target"]) for r in rows if r["sniping_type"] == "copy later slot" and r["slots_after_target"]]
gaps.sort()
if gaps:
    print("later-slot gap median", gaps[len(gaps)//2], "p90", gaps[int(len(gaps)*0.9)])
holds = sorted(int(r["hold_seconds"]) for r in closed if r["hold_seconds"] != "")
print("hold median", holds[len(holds)//2], "p90", holds[int(len(holds)*0.9)])
buys = sorted(float(r["buy_sol"]) for r in rows)
print("buy median", buys[len(buys)//2], "p90", buys[int(len(buys)*0.9)])
print("deadline", Counter(
    (int(r["gate_deadline_slot"]) - int(r["slot"])) if r["gate_deadline_slot"] else None for r in rows
).most_common(4))

# same mint bought by how many wallets
mints = defaultdict(set)
for r in rows:
    mints[r["mint"]].add(r["wallet"])
sizes = sorted(len(v) for v in mints.values())
print("mints", len(mints), "wallets-per-mint median", sizes[len(sizes)//2], "max", sizes[-1],
      "shared", sum(1 for v in mints.values() if len(v) > 1))

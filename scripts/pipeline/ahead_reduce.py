"""Keep only the earliest failed copy per target tx and add how many copies landed before that target."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import sys
from collections import Counter

# usage: ahead_reduce.py [all_copies.csv] [first.csv]
SRC = sys.argv[1] if len(sys.argv) > 1 else "failed_copies_before_target.csv"
PATH = sys.argv[2] if len(sys.argv) > 2 else "failed_copies_before_target.first.csv"
rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
counts = Counter(r["target_tx"] for r in rows)
earliest = {}
for r in sorted(rows, key=lambda r: (int(r["copy_slot"]), int(r["copy_index"]))):
    earliest.setdefault(r["target_tx"], r)

cols = list(rows[0]) if rows else [
    "bot_wallet", "target_wallet", "mint", "target_tx", "target_slot", "target_index",
    "bot_backrun_tx", "bot_backrun_index", "copy_tx", "copy_slot", "copy_index",
    "slots_before_target", "positions_before_target", "status", "error", "fee_sol",
    "references_target_wallet",
]
cols.insert(cols.index("copy_tx"), "txs_count")
out = []
for t, r in earliest.items():
    r["txs_count"] = counts[t]
    out.append(r)
out.sort(key=lambda r: (r["bot_wallet"], int(r["target_slot"])))
with open(PATH, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(out)
print(len(rows), "->", len(out), "rows; txs_count total", sum(counts.values()))

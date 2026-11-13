import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter, defaultdict
from pathlib import Path

BOT = "9qz7"
named = [r["target_wallet"] for r in csv.DictReader(open("target_wallets_named.csv", encoding="utf-8-sig"))]
want = set(named)

def bucket(p):
    pl = p.lower()
    if pl.startswith("axiom"):
        return "axiom"
    if pl.startswith("gmgn"):
        return "gmgn"
    if "terminal" in pl or "padre" in pl:
        return "terminal"
    return "other"

plats = defaultdict(Counter)
for day in (12, 13, 14, 15, 16, 17, 18, 19, 20, 21):
    for row in csv.DictReader(open(f"backruns_oct{day}.csv", encoding="utf-8-sig", newline="")):
        if row["buyer_wallet"].startswith(BOT):
            continue
        w = row["target_wallet"]
        if w in want:
            plats[w][bucket(row["target_platform"])] += 1

only_other = 0
mixed = 0
other_kinds = Counter()
for w, c in plats.items():
    if "other" not in c:
        continue
    keys = set(c) - {"other"}
    if not keys:
        only_other += 1
    else:
        mixed += 1
    other_kinds[tuple(sorted(keys)) or ("only other",)] += 1
print("only_other", only_other, "mixed_with_three", mixed)
print("other plus", other_kinds.most_common(12))

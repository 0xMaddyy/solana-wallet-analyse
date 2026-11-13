import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter, defaultdict
from pathlib import Path

BOT = "9qz7cWBqYBP2TnGfzMmxX64G4PQip7HtogjPBBnMhWpw"
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
rows_n = 0
for day in (12, 13, 14, 15, 16, 17, 18, 19, 20, 21):
    path = Path(f"backruns_oct{day}.csv")
    for row in csv.DictReader(path.open(encoding="utf-8-sig", newline="")):
        if row["buyer_wallet"].startswith("9qz7"):
            continue
        w = row["target_wallet"]
        if w not in want:
            continue
        plats[w][row["target_platform"]] += 1
        rows_n += 1

only = Counter()
any_other = Counter()
mixed = 0
missing = [w for w in named if w not in plats]
for w, c in plats.items():
    buckets = {bucket(p) for p in c}
    if buckets <= {"axiom", "gmgn", "terminal"} and buckets:
        if len(buckets) == 1:
            only[next(iter(buckets))] += 1
        else:
            mixed += 1
            only["mix of axiom/gmgn/terminal"] += 1
    else:
        any_other["has other"] += 1

print("named", len(named), "with_trades", len(plats), "missing", len(missing), "rows", rows_n)
print("exclusive buckets", only)
print("mixed_three", mixed)
print("has_other_wallets", any_other["has other"])

plat_wallets = Counter()
plat_rows = Counter()
for w, c in plats.items():
    for p, n in c.items():
        plat_wallets[p] += 1
        plat_rows[p] += n
print("\nplatform wallets / trades")
for p, n in plat_wallets.most_common():
    print(f"  {n:4d} wallets  {plat_rows[p]:4d} trades  {p}")

print("\nwallets with a non axiom/gmgn/terminal trade")
other_w = []
for w, c in plats.items():
    bad = {p: n for p, n in c.items() if bucket(p) == "other"}
    if bad:
        other_w.append((w, dict(c)))
print("count", len(other_w))
for w, c in other_w[:40]:
    print(w, c)

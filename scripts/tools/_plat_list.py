import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter, defaultdict

BOT = "9qz7"
named = {
    r["target_wallet"]: r
    for r in csv.DictReader(open("target_wallets_named.csv", encoding="utf-8-sig"))
}

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
        if w in named:
            plats[w][row["target_platform"]] += 1

rows = []
for w, c in plats.items():
    buckets = {bucket(p) for p in c}
    if "other" not in buckets:
        continue
    group = "mixed" if buckets - {"other"} else "none"
    info = named[w]
    rows.append({
        "group": group,
        "target_wallet": w,
        "solscan_name": info.get("solscan_name", ""),
        "orb_name": info.get("orb_name", ""),
        "platforms": "; ".join(f"{p} x{n}" for p, n in c.most_common()),
    })
rows.sort(key=lambda r: (r["group"] != "mixed", r["platforms"], r["target_wallet"]))
with open("target_wallets_other_routers.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, ["group", "target_wallet", "solscan_name", "orb_name", "platforms"], lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print("wrote", len(rows), "mixed", sum(1 for r in rows if r["group"] == "mixed"), "none", sum(1 for r in rows if r["group"] == "none"))

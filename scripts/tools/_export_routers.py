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

# Longer prefixes first so a platform string hits one label.
MATCHES = [
    ("direct pump.fun", "Direct pump.fun"),
    ("LanMV9sAd7w", "Raydium LaunchLab"),
    ("4KRSet9Y", "4KRSet9Y"),
    ("m9obQHAPy", "m9obQHAPy"),
    ("6gY1osmP4", "6gY1osmP4"),
    ("proVF4pMX", "proVF4pMX"),
    ("CAMMCzo5", "CAMMCzo5"),
    ("41Pr4XqE", "41Pr4Xqe"),
    ("9nADhRkM", "9nADhRkM"),
    ("B5wU3wug", "B5wU3wug"),
    ("HDk4dSrL", "HDk4dSrL"),
]

def labels_for(platform):
    return [name for needle, name in MATCHES if needle in platform]

plats = defaultdict(Counter)
for day in (12, 13, 14, 15, 16, 17, 18, 19, 20, 21):
    for row in csv.DictReader(open(f"backruns_oct{day}.csv", encoding="utf-8-sig", newline="")):
        if row["buyer_wallet"].startswith(BOT):
            continue
        w = row["target_wallet"]
        if w in named:
            plats[w][row["target_platform"]] += 1

rows = []
cat_counts = Counter()
for w, c in plats.items():
    hit = []
    for platform in c:
        for name in labels_for(platform):
            if name not in hit:
                hit.append(name)
    if not hit:
        continue
    for name in hit:
        cat_counts[name] += 1
    info = named[w]
    rows.append({
        "target_wallet": w,
        "solscan_name": info.get("solscan_name", ""),
        "orb_name": info.get("orb_name", ""),
        "matched": "; ".join(hit),
        "platforms": "; ".join(f"{p} x{n}" for p, n in c.most_common()),
    })
rows.sort(key=lambda r: (r["matched"], r["target_wallet"]))
out = "target_wallets_direct_launchlab_routers.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as fh:
    writer = csv.DictWriter(
        fh,
        ["target_wallet", "solscan_name", "orb_name", "matched", "platforms"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
print("wallets", len(rows))
for name, _ in MATCHES:
    label = dict(MATCHES)[name]
    print(f"  {cat_counts[label]:4d}  {label}")

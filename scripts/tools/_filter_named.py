import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
from pathlib import Path

BOT = "9qz7cWBqYBP2TnGfzMmxX64G4PQip7HtogjPBBnMhWpw"
days = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
keep = set()
drop_9qz7 = set()
for day in days:
    path = Path(f"backruns_oct{day}.csv")
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            wallet = row["target_wallet"].strip()
            if not wallet:
                continue
            buyer = row["buyer_wallet"].strip()
            if buyer == BOT or buyer.startswith("9qz7cWBq"):
                drop_9qz7.add(wallet)
            else:
                keep.add(wallet)

keep -= drop_9qz7

src = Path("target_wallets_named.csv")
with src.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = [r for r in rows if r["target_wallet"] in keep]
missing = keep - {r["target_wallet"] for r in rows}
print("kept_from_backruns", len(keep))
print("dropped_9qz7_targets", len(drop_9qz7))
print("named_rows_in", len(rows))
print("named_rows_out", len(out_rows))
print("missing_from_named", len(missing))
if missing:
    print("missing_sample", sorted(missing)[:5])

with src.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=["target_wallet", "solscan_name", "orb_name"],
        lineterminator="\n",
    )
    w.writeheader()
    for row in out_rows:
        w.writerow(row)

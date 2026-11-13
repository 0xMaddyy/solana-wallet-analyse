import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from pathlib import Path

days = [12, 14, 15, 16, 17, 18, 19, 20, 21]
fields = [
    "day",
    "bot_wallet",
    "target_wallet",
    "mint",
    "target_tx",
    "target_slot",
    "target_index",
    "bot_backrun_tx",
    "bot_backrun_index",
    "txs_count",
    "leader",
    "leader_region",
    "leader_client_type",
    "target_leader",
    "copy_tx",
    "copy_slot",
    "copy_index",
    "slots_before_target",
    "positions_before_target",
    "status",
    "error",
    "fee_sol",
    "references_target_wallet",
]
out = Path("failed_copies_before_target_oct12_21.first.csv")
counts = {}
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for day in days:
        path = Path(f"failed_copies_before_target_oct{day}.first.csv")
        with path.open(encoding="utf-8-sig", newline="") as src:
            rows = list(csv.DictReader(src))
        for row in rows:
            row["day"] = f"2026-10-{day:02d}"
            row.setdefault("target_leader", "")
            w.writerow(row)
        counts[day] = len(rows)
print(counts)
print("total", sum(counts.values()))

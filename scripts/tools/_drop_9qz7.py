import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from pathlib import Path

BOT = "9qz7cWBqYBP2TnGfzMmxX64G4PQip7HtogjPBBnMhWpw"
files = [
    "failed_copies_before_target_oct12_21.first.csv",
    "failed_copies_before_target_oct12.csv",
    "failed_copies_before_target_oct12.first.csv",
    "failed_copies_before_target_oct14.csv",
    "failed_copies_before_target_oct14.first.csv",
    "failed_copies_before_target_oct15.csv",
    "failed_copies_before_target_oct15.first.csv",
    "failed_copies_before_target_oct16.csv",
    "failed_copies_before_target_oct16.first.csv",
    "failed_copies_before_target_oct17.csv",
    "failed_copies_before_target_oct17.first.csv",
    "failed_copies_before_target_oct18.csv",
    "failed_copies_before_target_oct18.first.csv",
    "failed_copies_before_target_oct19.csv",
    "failed_copies_before_target_oct19.first.csv",
    "failed_copies_before_target_oct20.csv",
    "failed_copies_before_target_oct20.first.csv",
    "failed_copies_before_target_oct21.csv",
    "failed_copies_before_target_oct21.first.csv",
]

for name in files:
    path = Path(name)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    kept = []
    dropped = 0
    other_col = 0
    for row in rows:
        hit_bot = row.get("bot_wallet", "").strip() == BOT
        hit_any = any((v or "").strip() == BOT for v in row.values())
        if hit_any:
            dropped += 1
            if hit_any and not hit_bot:
                other_col += 1
            continue
        kept.append(row)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)
    print(f"{name}: {len(rows)} -> {len(kept)} removed {dropped} other_col {other_col}")

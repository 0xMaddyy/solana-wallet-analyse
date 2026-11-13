import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from pathlib import Path
from collections import Counter

for d in range(22, 27):
    br = Path(f"backruns_oct{d}.csv")
    full = Path(f"failed_copies_before_target_oct{d}.csv")
    first = Path(f"failed_copies_before_target_oct{d}.first.csv")
    if not full.exists():
        print(f"oct{d}: not ready")
        continue
    rows = list(csv.DictReader(full.open(encoding="utf-8-sig")))
    fr = list(csv.DictReader(first.open(encoding="utf-8-sig"))) if first.exists() else []
    brn = sum(1 for _ in csv.DictReader(br.open(encoding="utf-8-sig"))) if br.exists() else 0
    st = Counter(r["status"] for r in rows)
    same = sum(1 for r in fr if r.get("slots_before_target") == "0")
    print(
        f"oct{d}: backruns {brn}  copies {len(rows)} "
        f"({st.get('failed', 0)} fail, {st.get('success', 0)} ok)  "
        f"first {len(fr)}  same-slot-first {same}"
    )

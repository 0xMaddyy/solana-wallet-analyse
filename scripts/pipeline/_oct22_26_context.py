import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter

for d in range(22, 27):
    first = list(csv.DictReader(open(f"failed_copies_before_target_oct{d}.first.csv", encoding="utf-8-sig")))
    full = list(csv.DictReader(open(f"failed_copies_before_target_oct{d}.csv", encoding="utf-8-sig")))
    br = list(csv.DictReader(open(f"backruns_oct{d}.csv", encoding="utf-8-sig")))
    st = Counter(r["status"] for r in full)
    same = sum(1 for r in first if r["slots_before_target"] == "0")
    clients = Counter(r["leader_client_type"] for r in first)
    bam = clients.get("AgaveBam", 0)
    print(
        f"Oct {d}: {len(br)} backruns, {len(full)} copies on {len(first)} trades "
        f"({st.get('failed',0)} failed, {st.get('success',0)} success). "
        f"{same} of {len(first)} earliest same slot. AgaveBam {bam} of {len(first)}. "
        f"Clients: {dict(clients)}"
    )

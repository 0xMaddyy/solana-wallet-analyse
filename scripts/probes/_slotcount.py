import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import defaultdict
slots = set()
succ_slots = set()
by = defaultdict(set)
for line in open("oct20_allsigs.jsonl", encoding="utf-8"):
    if not line.strip():
        continue
    r = json.loads(line)
    slots.add(r["slot"])
    by[r["bot"][:8]].add(r["slot"])
    if not r["err"]:
        succ_slots.add(r["slot"])
print("all bot slots", len(slots), "success slots", len(succ_slots))
for b, s in sorted(by.items()):
    print(b, len(s))

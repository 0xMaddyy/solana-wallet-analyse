import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import sys
from collections import Counter

old_path, new_path = sys.argv[1], sys.argv[2]
old = list(csv.DictReader(open(old_path, encoding="utf-8-sig")))
new = list(csv.DictReader(open(new_path, encoding="utf-8-sig")))
assert len(old) == len(new)
changed_cols, swq, lost = Counter(), Counter(), []
for o, n in zip(old, new):
    assert o["bot_tx"] == n["bot_tx"]
    for k in o:
        if o[k] != n[k]:
            changed_cols[k] += 1
    if o["target_swqos"] != n["target_swqos"]:
        swq[(o["target_swqos"].split(" 0.")[0], n["target_swqos"].split(" 0.")[0])] += 1
        if o["target_swqos"] != "none detected":
            lost.append((o["target_tx"][:20], o["target_swqos"], n["target_swqos"]))
print("changed columns:", dict(changed_cols))
print("target_swqos transitions:")
for (a, b), c in swq.most_common():
    print(f"  {c:5d}  {a}  ->  {b}")
print("rows that already had a label and changed:", len(lost))
for x in lost[:20]:
    print("  ", x)

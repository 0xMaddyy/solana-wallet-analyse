import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
from collections import Counter, defaultdict

rows = list(csv.DictReader(open("backruns_oct8.csv", encoding="utf-8-sig")))
none = [r for r in rows if r["target_swqos"] == "none detected"]
cnt, payers, amts, plats = Counter(), defaultdict(set), defaultdict(list), defaultdict(Counter)
for r in none:
    for part in filter(None, r["target_unlabeled_transfers"].split("; ")):
        d, v = part.split(" ")
        cnt[d] += 1
        payers[d].add(r["target_wallet"])
        amts[d].append(float(v))
        plats[d][r["target_platform"]] += 1
print(len(cnt), "distinct destinations")
out = []
for d, c in cnt.most_common():
    a = sorted(amts[d])
    out.append({"addr": d, "rows": c, "payers": len(payers[d]), "min": a[0], "med": a[len(a) // 2], "max": a[-1],
                "platforms": dict(plats[d].most_common(3))})
for o in out[:60]:
    print(f"{o['rows']:4d} {o['payers']:4d} {o['addr']:45s} {o['min']:.5f} {o['med']:.5f} {o['max']:.5f} {o['platforms']}")
json.dump(out, open("unl_none.json", "w"), indent=0)

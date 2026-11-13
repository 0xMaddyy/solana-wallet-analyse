import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import math
import os
from collections import Counter

from sno.analyze import rpc

WINDOWS_BEFORE, WINDOWS_AFTER = 2, 3

d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "botcheck", "result.json")))
stake, total = d["stake"], d["stake_total"]
backruns = [b for b in d["buys"] if b.get("bundle_id") and b.get("position", 0) >= 1]
print(f"jito backruns: {len(backruns)}")

before, after, expected_b, expected_a = Counter(), Counter(), Counter(), Counter()
for b in backruns:
    start = b["slot"] - b["slot"] % 4
    lo = start - 4 * WINDOWS_BEFORE
    leaders = rpc("getSlotLeaders", [lo, 4 * (WINDOWS_BEFORE + 1 + WINDOWS_AFTER)])
    windows = [leaders[i] for i in range(0, len(leaders), 4)]
    for l in set(windows[:WINDOWS_BEFORE]) - {b["leader"]}:
        before[l] += 1
    for l in set(windows[WINDOWS_BEFORE + 1:]) - {b["leader"]}:
        after[l] += 1


def poisson_tail(k, lam):
    return 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k))


for name, counts, k in (("BEFORE", before, WINDOWS_BEFORE), ("AFTER", after, WINDOWS_AFTER)):
    rows = []
    for l, c in counts.items():
        lam = len(backruns) * k * stake.get(l, 0) / total
        if lam > 0:
            rows.append((poisson_tail(c, lam), l, c, lam))
    rows.sort()
    print(f"\n== leaders in the {k} windows {name} the backrun window (most over-represented first)")
    for p, l, c, lam in rows[:8]:
        print(f"  {l}  seen {c}  expected {lam:.2f}  p {p:.1e}")

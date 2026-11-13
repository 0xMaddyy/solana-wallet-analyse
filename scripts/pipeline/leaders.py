import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter, defaultdict

from sno.analyze import JITO_TIPS, rpc

results = json.load(open("results.json"))
backruns = [x for x in results if x["prev"] and set(x["prev"]["mints_bought"]) & set(x["bot"]["mints_bought"])]
others = [x for x in results if x not in backruns]

print("== bot SOL transfers (tips) per backrun")
for x in backruns:
    b, p = x["bot"], x["prev"]
    bt = [("JITO" if d in JITO_TIPS else d, round(a, 5)) for d, a in b["transfers"]]
    pt = [("JITO" if d in JITO_TIPS else d, round(a, 5)) for d, a in p["transfers"]]
    print(f"slot {b['slot']} leader {x['leader'][:8]} bot->{bt}\n    target {p['signer'][:8]} progs {sorted(set(p['programs']))[:4]} tips->{pt}")

print("\n== bot buys NOT adjacent to a same-mint buy: bot tips")
for x in others:
    b = x["bot"]
    print(f"slot {b['slot']} buy {-b['sol_delta']:.3f} bot->{[('JITO' if d in JITO_TIPS else d, round(a, 5)) for d, a in b['transfers']]}")

BEFORE, AFTER = 8, 12
nearby = Counter()
current = Counter()
for x in backruns:
    s = x["bot"]["slot"]
    window_start = s - (s % 4)
    leaders = rpc("getSlotLeaders", [window_start - BEFORE, BEFORE + 4 + AFTER])
    cur = x["leader"]
    current[cur] += 1
    seen = set(leaders) - {cur}
    for l in seen:
        nearby[l] += 1

print(f"\n== validators leading within {BEFORE} slots before / {AFTER} slots after the backrun window ({len(backruns)} backruns)")
for k, v in nearby.most_common(15):
    print(f"  {v:3d}  {k}")

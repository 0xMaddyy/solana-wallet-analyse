import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import time
from collections import defaultdict

import gate_6gY1 as g

g.load_cache()
PROG = g.PROG
buys = defaultdict(list)
for t in g.CACHE.values():
    if t.get("err") or PROG not in t.get("programs", []):
        continue
    if not t.get("blockTime") or t["blockTime"] < g.START:
        continue
    w = t["signer"]
    sol = sum(t["dsol"].values())
    got = [k.split("|")[1] for k, d in t["tok"].items()
           if k.split("|")[0] == w and d > 0 and "So111" not in k]
    if sol < 0 and len(got) == 1:
        buys[got[0]].append(t)

mint, txs = max(buys.items(), key=lambda kv: len(kv[1]))
txs.sort(key=lambda t: -t["slot"])
print("mint", mint, "buys", len(txs), "slot span", txs[0]["slot"] - txs[-1]["slot"])
# one tight group: buys within 150 slots of the newest
group_txs = [t for t in txs if txs[0]["slot"] - t["slot"] <= 150]
items = [(t, mint, 1) for t in group_txs]
print("group", len(items))
t0 = time.time()
out = g.group_candidates(mint, items)
dt = time.time() - t0
n = sum(1 for v in out.values() if v)
print(f"{dt:.1f}s  with target {n}/{len(out)}")
if n:
    c = next(v for v in out.values() if v)[0]
    print("example target", c["signer"][:8], "slot", c["slot"], "programs", [p[:8] for p in c["programs"]])

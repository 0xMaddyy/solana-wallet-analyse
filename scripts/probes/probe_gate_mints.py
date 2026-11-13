import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter, defaultdict

mints = Counter()
n = 0
with open("gate_6gY1_txs.jsonl", encoding="utf-8") as fh:
    for line in fh:
        t = json.loads(line)
        if t.get("err") or "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi" not in t.get("programs", []):
            continue
        if t.get("blockTime", 0) < 1760572800:  # rough; real START checked below
            pass
        sol = sum(t["dsol"].values())
        got = []
        w = t["signer"]
        for k, d in t["tok"].items():
            owner, mint = k.split("|")
            if owner == w and d > 0 and not mint.startswith("So111"):
                got.append(mint)
        if sol < 0 and len(got) == 1:
            n += 1
            mints[got[0]] += 1
print("buys", n, "mints", len(mints))
print("buys/mint median", sorted(mints.values())[len(mints)//2], "max", max(mints.values()), "mean", n/len(mints))
print("mints with 1 buy", sum(1 for v in mints.values() if v == 1))
print("top", mints.most_common(5))

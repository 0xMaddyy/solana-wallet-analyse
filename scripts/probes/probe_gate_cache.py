import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter

n = buy = sell = 0
signers = Counter()
progs = Counter()
with open("gate_6gY1_txs.jsonl", encoding="utf-8") as fh:
    for line in fh:
        t = json.loads(line)
        n += 1
        if t.get("missing") or t.get("err"):
            continue
        signers[t["signer"][:8]] += 1
        w = t["signer"]
        sol = sum(t["dsol"].values())
        up = down = False
        for k, d in t["tok"].items():
            owner, mint = k.split("|")
            if owner == w and not mint.startswith("So111"):
                up = up or d > 0
                down = down or d < 0
        if sol < 0 and up:
            buy += 1
        elif sol > 0 and down:
            sell += 1
        for p in t["programs"]:
            if p not in ("11111111111111111111111111111111", "ComputeBudget111111111111111111111111111111"):
                progs[p[:8]] += 1
print("records", n, "buys", buy, "sells", sell, "signers", len(signers))
print(signers.most_common(15))
print(progs.most_common(8))
print("gate_slot sample", t.get("gate_slot"), "slot", t.get("slot"))

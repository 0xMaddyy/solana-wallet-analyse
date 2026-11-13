import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
owners = Counter()
n = match = other = 0
with open("gate_6gY1_txs.jsonl", encoding="utf-8") as fh:
    for line in fh:
        t = json.loads(line)
        if t.get("missing") or t.get("err"):
            continue
        if PROG in t.get("programs", []):
            continue
        n += 1
        signer = t.get("signer")
        ups = []
        for k, d in t["tok"].items():
            owner, mint = k.split("|")
            if d > 0 and not mint.startswith("So111"):
                ups.append(owner)
        if not ups:
            continue
        other += 1
        if signer in ups:
            match += 1
        else:
            owners[ups[0][:8] if ups else "?"] += 1
print("non-gate txs", n, "with token up", other, "signer owns the tokens", match)
print("other owners", owners.most_common(8))

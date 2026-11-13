import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import defaultdict

span = defaultdict(lambda: [10**18, 0, 0])
with open("gate_6gY1_txs.jsonl", encoding="utf-8") as fh:
    for line in fh:
        t = json.loads(line)
        if "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi" not in t.get("programs", []):
            continue
        sol = sum(t["dsol"].values())
        w = t["signer"]
        got = [k.split("|")[1] for k, d in t["tok"].items()
               if k.split("|")[0] == w and d > 0 and "So111" not in k]
        if sol < 0 and len(got) == 1:
            s = span[got[0]]
            s[0] = min(s[0], t["slot"])
            s[1] = max(s[1], t["slot"])
            s[2] += 1
widths = sorted((b - a, n, m) for m, (a, b, n) in span.items())
print("mints", len(widths))
print("widest slots", widths[-8:])
print("width<=300", sum(1 for w, n, m in widths if w <= 300), "width>2000", sum(1 for w, n, m in widths if w > 2000))

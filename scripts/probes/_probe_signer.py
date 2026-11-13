import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import defaultdict
from sno.analyze import rpc

by = defaultdict(list)
for line in open("top_traders_oct20_sigs.jsonl", encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    if r.get("sig"):
        by[r["wallet"]].append(r["sig"])
print("wallets", len(by), "sigs", sum(len(v) for v in by.values()))
# sample first sig of the busiest five
busy = sorted(by, key=lambda w: -len(by[w]))[:5]
for w in busy:
    sig = by[w][0]
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    keys = tx["transaction"]["message"]["accountKeys"]
    signers = [k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")]
    print(w[:8], "n", len(by[w]), "signer", signers[0][:8], "match", signers[0] == w)

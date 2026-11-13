import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import BOT, get_tx, rpc

sigs = rpc("getSignaturesForAddress", [BOT, {"limit": 100}])
failed = [s for s in sigs if s["err"]]
txs = list(ThreadPoolExecutor(6).map(lambda s: get_tx(s["signature"]), failed))

reasons = Counter()
for s, tx in zip(failed, txs):
    msg = tx["transaction"]["message"]
    err = tx["meta"]["err"]
    ix_err = err.get("InstructionError") if isinstance(err, dict) else None
    if ix_err:
        ix = msg["instructions"][ix_err[0]]
        key = f"ix#{ix_err[0]} {ix['programId'][:10]} {json.dumps(ix_err[1])}"
    else:
        key = json.dumps(err)
    reasons[key] += 1

for k, v in reasons.most_common():
    print(f"{v:3d}  {k}")

kind = Counter()
for s, tx in zip(failed, txs):
    logs = tx["meta"]["logMessages"] or []
    progs = [ix["programId"][:8] for ix in tx["transaction"]["message"]["instructions"]]
    k = "Buy" if any("Instruction: Buy" in l for l in logs) else "Sell" if any("Instruction: Sell" in l for l in logs) else "neither-ran"
    kind[(k, " > ".join(progs))] += 1
for k, v in kind.most_common():
    print(f"{v:3d}  {k}")

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import get_tx, rpc
import sno.analyze
analyze.RPC = "https://api.mainnet-beta.solana.com"

sig = json.load(open("2h6d_sigs.json"))[0]["signature"]
print("sig", sig)
tx = get_tx(sig)
msg, meta = tx["transaction"]["message"], tx["meta"]
print("slot", tx["slot"], "fee", meta["fee"], "err", meta["err"])
keys = msg["accountKeys"]
print("signers", [k["pubkey"] for k in keys if k.get("signer")])
for i, ix in enumerate(msg["instructions"]):
    print(f"#{i} {ix['programId']} data {(ix.get('data') or '')[:24]} acc {len(ix.get('accounts') or [])}")
print("--- inner programs")
from collections import Counter
c = Counter()
for g in meta.get("innerInstructions") or []:
    for ii in g["instructions"]:
        c[ii["programId"]] += 1
print(c)
print("--- logs buy/sell")
for l in meta.get("logMessages") or []:
    if "Instruction" in l or "pump" in l.lower() or "stonk" in l.lower() or "Buy" in l or "Sell" in l:
        print(l)

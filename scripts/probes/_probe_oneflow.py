import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import get_tx

SIG = "TDJLLMrjhchgJCEC3vSEyKK83R23d5YNmkxuYK8BHhgM6qTuejcKnEt96N4TfephqrEyh6s2d4Y6ygXauAjK12w"
tx = get_tx(SIG)
msg = tx["transaction"]["message"]
keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
print("signer", keys[0])
print("fee", tx["meta"]["fee"])
for ix in msg["instructions"]:
    print("IX", ix.get("programId", "")[:12], json.dumps(ix.get("parsed"))[:400])
print("--- token balances ---")
for row in (tx["meta"].get("preTokenBalances") or []) + (tx["meta"].get("postTokenBalances") or []):
    print(row["accountIndex"], keys[row["accountIndex"]][:8], row.get("owner","")[:12], row["mint"][:6], row["uiTokenAmount"]["uiAmountString"])
print("--- inner ---")
for grp in tx["meta"].get("innerInstructions") or []:
    for ix in grp["instructions"]:
        p = ix.get("parsed")
        if isinstance(p, dict):
            print(json.dumps(p)[:300])

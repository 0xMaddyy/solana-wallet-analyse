import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import rpc
b = rpc("getBlock", [459226783, {"transactionDetails": "accounts", "rewards": False,
                                 "maxSupportedTransactionVersion": 1, "encoding": "json"}])
tx = b["transactions"][642]
meta = tx["meta"]
print("err", meta.get("err"))
print("pre n", len(meta.get("preTokenBalances") or []), "post n", len(meta.get("postTokenBalances") or []))
post = meta.get("postTokenBalances") or []
if post:
    print(json.dumps(post[0])[:400])
keys = tx["transaction"]["accountKeys"]
signers = [k["pubkey"] for k in keys if k.get("signer")]
print("signer", signers[:2], "nkeys", len(keys))
print("pump", [k["pubkey"] for k in keys if k["pubkey"].endswith("pump")][:4])
print("prog", any(k["pubkey"] == "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" for k in keys))

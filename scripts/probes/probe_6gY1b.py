"""Who signs calls to 6gY1osm, and what the call does."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import base64
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import get_tx, rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
sigs = rpc("getSignaturesForAddress", [PROG, {"limit": 200}])
ok = [s["signature"] for s in sigs if not s.get("err")][:80]

def brief(sig):
    tx = get_tx(sig)
    msg, meta = tx["transaction"]["message"], tx["meta"]
    keys = msg["accountKeys"]
    signer = next(k["pubkey"] for k in keys if k.get("signer"))
    ix = next(i for i in msg["instructions"] if i["programId"] == PROG)
    raw = base64.b64decode(ix["data"]) if False else None
    # jsonParsed data for unknown programs is base58
    return signer, ix.get("data"), ix.get("accounts"), [i["programId"] for i in msg["instructions"]]

with ThreadPoolExecutor(10) as ex:
    rows = list(ex.map(brief, ok))
print("signers", Counter(r[0] for r in rows).most_common(20))
print("n signers", len({r[0] for r in rows}), "of", len(rows))
print("data lens", Counter(len(r[1] or "") for r in rows))
print("acct counts", Counter(len(r[2] or []) for r in rows))
print("sample data", rows[0][1], rows[0][2])
print("outer", Counter(p for r in rows for p in r[3]).most_common(12))

"""Same gate ident twice: same mint, same wallet, or a backrun of someone else?"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sno.analyze import get_tx, rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


SIGS = [
    # filled after a fresh lookup of the repeated ident; resolved below
]


def describe(sig):
    tx = get_tx(sig)
    msg, meta = tx["transaction"]["message"], tx["meta"]
    signer = next(k["pubkey"] for k in msg["accountKeys"] if k.get("signer"))
    mints = sorted({b["mint"] for b in (meta.get("postTokenBalances") or []) if b["mint"].endswith("pump")})
    ix = next(i for i in msg["instructions"] if i["programId"] == PROG)
    ident = b58decode(ix["data"])[1:9].hex()
    progs = [i["programId"][:8] for i in msg["instructions"]]
    print(sig[:12], "slot", tx["slot"], "signer", signer[:8], "ident", ident, "mints", [m[:8] for m in mints], "progs", progs)
    return tx["slot"], signer, mints


# find two recent sigs sharing an ident by scanning 30
sigs = [s["signature"] for s in rpc("getSignaturesForAddress", [PROG, {"limit": 40}]) if not s.get("err")]
seen = {}
pair = None
for sig in sigs:
    tx = get_tx(sig)
    ix = next(i for i in tx["transaction"]["message"]["instructions"] if i["programId"] == PROG)
    ident = b58decode(ix["data"])[1:9].hex()
    if ident in seen:
        pair = (seen[ident], sig)
        break
    seen[ident] = sig
print("pair", pair)
if pair:
    for sig in pair:
        describe(sig)

# how busy is the top wallet right now
top = "EDXC94LZK8GomcNxQgWWZhfLWihSJ8U9tRQTWGT6UFU8"
page = rpc("getSignaturesForAddress", [top, {"limit": 1000}])
print("top wallet newest", page[0]["blockTime"], "oldest in 1000", page[-1]["blockTime"],
      "fail", sum(1 for s in page if s.get("err")))

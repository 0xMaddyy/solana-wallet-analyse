"""Match gate instruction bytes to accounts, and try a lighter history RPC."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import get_tx, rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


def b58encode(b):
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = _B58[r] + s
    pad = 0
    for c in b:
        if c == 0:
            pad += 1
        else:
            break
    return "1" * pad + (s or "")


sigs = [s["signature"] for s in rpc("getSignaturesForAddress", [PROG, {"limit": 12}]) if not s.get("err")][:8]


def one(sig):
    tx = get_tx(sig)
    msg = tx["transaction"]["message"]
    keys = [k["pubkey"] for k in msg["accountKeys"]]
    ix = next(i for i in msg["instructions"] if i["programId"] == PROG)
    raw = b58decode(ix["data"])
    ident = raw[1:9]
    slot_arg = int.from_bytes(raw[9:13], "little")
    hits = [k for k in keys if b58decode(k)[:8] == ident]
    mints = []
    for b in tx["meta"].get("postTokenBalances") or []:
        if b["mint"].endswith("pump"):
            mints.append(b["mint"])
    mint_hit = [m for m in set(mints) if b58decode(m)[:8] == ident]
    return {
        "slot": tx["slot"], "arg_slot": slot_arg, "delta": tx["slot"] - slot_arg,
        "signer": next(k["pubkey"] for k in msg["accountKeys"] if k.get("signer")),
        "prefix_hits": hits, "mint_hits": mint_hit, "ident": ident.hex(),
    }


with ThreadPoolExecutor(6) as ex:
    for r in ex.map(one, sigs):
        print(json.dumps(r))

try:
    light = rpc("getTransactionsForAddress", [PROG, {"transactionDetails": "accounts", "limit": 5,
                                                      "sortOrder": "desc"}])
    print("light keys", list(light)[:8] if isinstance(light, dict) else type(light))
    item = (light.get("data") or light.get("transactions") or [])[:1]
    print(json.dumps(item)[:800])
except Exception as e:
    print("light rpc failed", type(e).__name__, e)

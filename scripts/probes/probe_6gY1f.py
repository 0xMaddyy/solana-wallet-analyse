"""Find where the gate's 8-byte argument lives."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import base64
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import get_tx, rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
STATE = "FHaSvKD6Yk2QSeQ7h8ZqHVGtCj9nkcedHDdBLYdiEAza"
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


raw = base64.b64decode(rpc("getAccountInfo", [STATE, {"encoding": "base64"}])["value"]["data"][0])
sigs = [s["signature"] for s in rpc("getSignaturesForAddress", [PROG, {"limit": 20}]) if not s.get("err")][:12]


def ident(sig):
    tx = get_tx(sig)
    ix = next(i for i in tx["transaction"]["message"]["instructions"] if i["programId"] == PROG)
    b = b58decode(ix["data"])
    return b[0], b[1:9], int.from_bytes(b[9:13], "little"), tx["slot"]


with ThreadPoolExecutor(8) as ex:
    rows = list(ex.map(ident, sigs))
print("disc", {r[0] for r in rows})
for disc, ident8, arg, slot in rows:
    print(f"  slot {slot} arg {arg} ident {ident8.hex()} in_state {raw.find(ident8)}")
# repeated 8-byte windows inside the state
from collections import Counter
wins = Counter(raw[i:i+8] for i in range(0, len(raw) - 7))
print("repeated windows", [(w.hex(), n) for w, n in wins.most_common(5) if n > 2])
print("tail", raw[-32:].hex())

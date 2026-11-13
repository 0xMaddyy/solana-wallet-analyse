"""See whether the gate state account lists the caller wallets."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import base64

from sno.analyze import rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
STATE = "FHaSvKD6Yk2QSeQ7h8ZqHVGtCj9nkcedHDdBLYdiEAza"
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
    pad = sum(1 for c in b if c == 0)
    # leading zero count only at the front
    pad = 0
    for c in b:
        if c == 0:
            pad += 1
        else:
            break
    return "1" * pad + (s or "1")


KNOWN = """
EDXC94LZK8GomcNxQgWWZhfLWihSJ8U9tRQTWGT6UFU8
6vB9VfGpjtSTYdhJ9ZMTLXC32UDCCaKpeQmSVnGNHgXh
HsDkfUyLfoZfiQEscDMh4c81WGuutoW521ywG1ZTByze
DFFXHcmTgdBe5NPVXryoarPc4KYGNM3zWQ5K1PhPZccn
FSz6mptAxKrjDjaJYQiGiCGGwsxL4WgWjsh9sGhw4BZX
A8W81KDBVEovvmkUbKCWoaNx744E5T4PQ1iJsZLA2H8
E8jLeB1YCX33xjtvg426dxm2ERxiwoVBUawZCovnzKkX
Anva6JEutaUxW9JDp2WZ9yq8yHFUpaBrV2BXshQHVJMf
9m4UetMFjysmBcm8o3meL6jJgbcLCTEtVZxx8jQpmpwu
CiueJwuBw1cZVz4YzY4TpPtyaEQJEpmYZmxkLAuXurDC
2CzXSZe8577hmjo1Xi1WQBtSBJc93fD4U2dt7jnJ313Y
FteNBUJPDP5ZtwJYdBnJhvBuEhjHC2a3o7VR1TU4pmZT
Fhbh1DTUDKt6qu9zVg8Q5VgnZa1WWWbxBxG6pCoJoggA
""".split()

val = rpc("getAccountInfo", [STATE, {"encoding": "base64"}])["value"]
raw = base64.b64decode(val["data"][0])
print("len", len(raw))
for w in KNOWN:
    b = b58decode(w)
    i = raw.find(b)
    print(f"  {w[:8]} at {i}")

# print possible pubkey-aligned hits: scan every offset for 32 bytes that look like pubkeys is hard.
# show u32/u64 header fields
print("u32s", [int.from_bytes(raw[i:i+4], "little") for i in range(0, 64, 4)])
print("u64s", [int.from_bytes(raw[i:i+8], "little") for i in range(0, 64, 8)])
# if a length prefix says how many 32-byte keys follow
for off in range(0, 16):
    n = int.from_bytes(raw[off:off+4], "little")
    if 1 <= n <= 40 and off + 4 + n * 32 <= len(raw):
        print("possible count", n, "at", off, "tail", len(raw) - (off + 4 + n * 32))

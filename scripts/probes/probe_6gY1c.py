"""Decode the 6gY1osm gate: instruction bytes, shared account, and a failed call."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import get_tx, rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
STATE = "FHaSvKD6Yk2QSeQ7h8ZqHVGtCj9nkcedHDdBLYdiEAza"

info = rpc("getAccountInfo", [STATE, {"encoding": "base64"}])
val = info["value"]
raw = b58decode(val["data"][0]) if val["data"][1] == "base58" else __import__("base64").b64decode(val["data"][0])
print("state owner", val["owner"], "len", len(raw), "lamports", val["lamports"])
print("state head", raw[:64].hex())

sigs = rpc("getSignaturesForAddress", [PROG, {"limit": 40}])
fail = next(s for s in sigs if s.get("err"))
ok = [s["signature"] for s in sigs if not s.get("err")][:15]

def one(sig):
    tx = get_tx(sig)
    msg, meta = tx["transaction"]["message"], tx["meta"]
    ix = next(i for i in msg["instructions"] if i["programId"] == PROG)
    logs = [l for l in (meta.get("logMessages") or []) if PROG[:6] in l or "Error" in l or "failed" in l]
    return b58decode(ix["data"]).hex(), ix["accounts"], meta["err"], logs[-4:]

print("fail sig", fail["signature"], fail["err"])
print("fail", one(fail["signature"]))
with ThreadPoolExecutor(8) as ex:
    rows = list(ex.map(one, ok))
print("datas", Counter(r[0] for r in rows))
print("acct0", Counter(r[1][0] for r in rows))
print("sample bytes", rows[0][0], "nacc", len(rows[0][1]))

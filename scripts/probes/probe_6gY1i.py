"""Classify 25 recent 6gY1osm buys: backrun, later copy, or first buyer."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import rpc
from sno.multi_fetch import record
from sno.multi_report import block_sigs

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
WSOL = "So11111111111111111111111111111111111111112"
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


sigs = [s["signature"] for s in rpc("getSignaturesForAddress", [PROG, {"limit": 40}]) if not s.get("err")][:25]


def bought_mints(t, wallet):
    out = []
    for k, d in t["tok"].items():
        owner, mint = k.split("|")
        if owner == wallet and mint != WSOL and d > 0:
            out.append(mint)
    return out


def classify(sig):
    t = record(sig, [])
    # re-fetch with the signer so SOL delta is kept
    w = t["signers"][0]
    t = record(sig, [w])
    mints = bought_mints(t, w)
    if len(mints) != 1:
        return "no-single-buy", w, mints
    mint = mints[0]
    hist = rpc("getSignaturesForAddress", [mint, {"before": sig, "limit": 12}])
    earlier = [h for h in hist if h.get("blockTime") and t["slot"] - h["slot"] <= 40]
    kind, tgt = "first buyer", ""
    if earlier:
        h = earlier[0]  # most recent prior tx of this mint
        gap = t["slot"] - h["slot"]
        if h["slot"] == t["slot"]:
            order = block_sigs(t["slot"])
            bi, hi = order.index(sig), order.index(h["signature"])
            kind = "backrun" if bi == hi + 1 else "copy same block"
            tgt = f"gap_pos {bi - hi} idx {bi}"
        else:
            kind = "copy later slot"
            tgt = f"gap_slots {gap}"
        other = record(h["signature"], [])
        tgt = other["signers"][0][:8] + " " + tgt
    sol = t["dsol"].get(w, 0) / 1e9
    return kind, w[:8], round(-sol, 3), mint[:8], tgt


with ThreadPoolExecutor(8) as ex:
    rows = list(ex.map(classify, sigs))
print(Counter(r[0] for r in rows))
for r in rows:
    print(r)

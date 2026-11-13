"""Is a 6gY1osm buy a backrun of the previous tx, and what do the wallet's other txs look like?"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter

from sno.analyze import get_tx, rpc
from sno.multi_fetch import record

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
SIG = "61arBQXsJs4S5zPsnX5CicyWVJUswmxYUAwScSZwfTLyLqeC3fsRtF7oXhfd3FMKbqNYGMp4PxdhgnCXHWbzSq2T"
bot = record(SIG, [])
print("bot signers", bot["signers"], "slot", bot["slot"], "progs", bot["programs"])
print("dsol", bot["dsol"])
mints = {k.split("|")[1] for k, d in bot["tok"].items() if d > 0 and not k.endswith("So11111111111111111111111111111111111111112")}
print("mints up", mints)

sigs = rpc("getBlock", [bot["slot"], {"transactionDetails": "signatures", "rewards": False, "maxSupportedTransactionVersion": 1}])["signatures"]
i = sigs.index(SIG)
print("index", i, "of", len(sigs))
prev = record(sigs[i - 1], [])
print("prev signer", prev["signers"], "progs", prev["programs"])
prev_mints = {k.split("|")[1] for k, d in prev["tok"].items() if d > 0}
print("prev mints up", prev_mints, "overlap", prev_mints & mints)

# other recent txs of this wallet
w = bot["signers"][0]
page = rpc("getSignaturesForAddress", [w, {"limit": 30}])
ok = [s["signature"] for s in page if not s.get("err")][:12]


def kind(sig):
    t = record(sig, [w])
    up = [k for k, d in t["tok"].items() if d > 0 and k.startswith(w)]
    down = [k for k, d in t["tok"].items() if d < 0 and k.startswith(w)]
    return PROG in t["programs"], "buy" if up and not down else "sell" if down and not up else "other", t["programs"]

for sig in ok:
    print(sig[:12], kind(sig))

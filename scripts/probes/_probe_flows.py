import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter
from sno.analyze import get_tx

WALLET = "8HFagtU2YAGxhWRPuFQ9Jrj5K387vQpUUTB7goHpump"
SIGS = [
    "2AJD4RT12J1D56xoJ3PACsfcoaDhL8D1q8LagLAHD8gaJ7YsRyGvjhx1dsKRCWuuR1LETAkLJ4xbTSUEZhfYpKo8",
    "5zUpZyex3ZPLcitKM4QztVbyycE1Evj1T6qV8FJr1n9Zojjdu4coXr33TAGAHyndh59kXt4a9hW7VDbU35XV8wHv",
    "3aV9s1HTJFEr88Z75Dmy98awjgczaVMHgw4VQESRtHuR3two26bJv2BLF5pHWBbFTCwpSPm5NMhkV5WMGXrLfJXQ",
    "6NpT47f1FxnXqhbg6sw6QPfkioyE2AYjcVetoYVHYtQCnisZYMxu1bwCBL8cqXfEbPjZduquv2rbr2FtG8ZpeuU",
]

def brief(sig):
    tx = get_tx(sig)
    msg = tx["transaction"]["message"]
    keys = msg["accountKeys"]
    pubs = [k["pubkey"] if isinstance(k, dict) else k for k in keys]
    signer = pubs[0]
    programs = []
    for ix in msg["instructions"]:
        pid = ix.get("programId") or (pubs[ix["programIdIndex"]] if "programIdIndex" in ix else "?")
        programs.append(str(pid)[:8])
    print("\n", sig[:12], "signer", signer[:8], "match", signer == WALLET, "programs", programs[:8], "n", len(msg["instructions"]))
    for ix in msg["instructions"]:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") in ("transfer", "transferChecked"):
            info = p["info"]
            amt = info.get("lamports") or info.get("tokenAmount", {}).get("uiAmountString")
            print(" ", p["type"], str(info.get("source"))[:8], "->", str(info.get("destination"))[:8], amt, info.get("mint", "")[:8])

for s in SIGS:
    brief(s)

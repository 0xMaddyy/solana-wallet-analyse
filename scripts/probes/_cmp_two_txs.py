import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import get_tx

FAIL = "pXWskrQdi8bT7T9nmmdXsNoKDfGcRincUAKv429She2RQMbiMes7uBRMwmJ4A5GzjyhfJhrESyHD6j5hn9eEnr1"
OK = "3DVgorh9DGPo8v1fNHbncSzp9UT3eeGe3bGmwV4NfP8jn6zgGjdujhZ4ToF2U7qXMynMG6qpHYSkAD7xz6dL8f1o"
TARGET = "4pGreVTK5yA8mUmM1HxP2BDcdcfpx3oKHxzrCmx5rE9anjN8CAMerCRvugrfLtuF5HLW8xhChjCU8Rp5EDJjsXri"
MINT = "75UeSVjeVVdxFZfWrf2zkgqdXnxm2uFwqPBBSbYwpump"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
TOKEN = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKENZ = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


def keys(tx):
    return [k["pubkey"] if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]


def ix_view(tx):
    msg = tx["transaction"]["message"]
    ak = keys(tx)
    out = []
    for i, ix in enumerate(msg["instructions"]):
        accs = ix.get("accounts") or []
        if accs and isinstance(accs[0], int):
            accs = [ak[a] for a in accs]
        data = ix.get("data")
        out.append({
            "i": i,
            "program": ix.get("programId"),
            "n": len(accs),
            "accounts": accs,
            "data": data if isinstance(data, str) else None,
            "parsed": ix.get("parsed") if isinstance(ix.get("parsed"), dict) else None,
        })
    return out, ak


def brief(name, tx):
    meta = tx["meta"]
    ixs, ak = ix_view(tx)
    print("\n====", name, "slot", tx["slot"], "err", meta.get("err"), "fee", meta.get("fee"))
    print("cu", (meta.get("computeUnitsConsumed")))
    print("log tail:")
    logs = meta.get("logMessages") or []
    for line in logs[-12:]:
        print(" ", line)
    print("instructions:")
    for ix in ixs:
        prog = ix["program"]
        parsed = ix["parsed"]
        extra = ""
        if parsed:
            extra = parsed.get("type", "")
        print(f"  [{ix['i']}] {prog} accounts={ix['n']} {extra} data={ix['data']}")
        if prog == PUMP or (ix["n"] and ix["i"] in (2, 3, 4)):
            for a in ix["accounts"]:
                mark = ""
                if a == MINT:
                    mark = " MINT"
                elif a == TOKEN:
                    mark = " TOKEN"
                elif a == TOKENZ:
                    mark = " TOKENZ"
                print(f"      {a}{mark}")
    print("token programs in accounts", TOKEN in ak, "tokenz", TOKENZ in ak, "mint", MINT in ak)


for name, sig in [("FAIL", FAIL), ("OK", OK), ("TARGET", TARGET)]:
    brief(name, get_tx(sig))

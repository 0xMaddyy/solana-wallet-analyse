import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import defaultdict
from sno.analyze import get_tx

WALLET = "8HFagtU2YAGxhWRPuFQ9Jrj5K387vQpUUTB7goHpump"
rows = [r for r in csv.DictReader(open("wallet_8HFa_flows.csv", encoding="utf-8")) if r["asset"] == "USDC" and float(r["amount"]) >= 50]
print("usdc large", len(rows))
sides = defaultdict(lambda: defaultdict(float))

def owners(tx):
    out = {}
    meta = tx["meta"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]
    for row in (meta.get("preTokenBalances") or []) + (meta.get("postTokenBalances") or []):
        idx = row["accountIndex"]
        if idx < len(keys):
            out[keys[idx]] = row.get("owner")
    return out

for r in rows:
    tx = get_tx(r["signature"])
    own = owners(tx)
    msg = tx["transaction"]["message"]
    other = None
    for ix in msg["instructions"]:
        p = ix.get("parsed")
        if not isinstance(p, dict) or p.get("type") not in ("transfer", "transferChecked"):
            continue
        info = p["info"]
        src, dst = info.get("source"), info.get("destination")
        if r["kind"] == "deposit":
            other = own.get(src) or info.get("authority") or src
        else:
            other = own.get(dst) or dst
    sides[r["kind"]][other or "?"] += float(r["amount"])

for kind, m in sides.items():
    print(kind)
    for addr, amt in sorted(m.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {amt:.2f}  {addr}")

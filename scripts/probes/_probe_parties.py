import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import defaultdict
from sno.analyze import get_tx

WALLET = "8HFagtU2YAGxhWRPuFQ9Jrj5K387vQpUUTB7goHpump"
rows = list(csv.DictReader(open("wallet_8HFa_flows.csv", encoding="utf-8")))
large = [r for r in rows if (r["asset"] == "USDC" and float(r["amount"]) >= 50) or (r["asset"] != "USDC" and float(r["amount"]) >= 0.5)]
print("large", len(large))
sides = defaultdict(lambda: defaultdict(float))
for i, r in enumerate(large):
    tx = get_tx(r["signature"])
    msg = tx["transaction"]["message"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    other = None
    for ix in msg["instructions"]:
        p = ix.get("parsed")
        if not isinstance(p, dict) or p.get("type") not in ("transfer", "transferChecked"):
            continue
        info = p["info"]
        src, dst = info.get("source"), info.get("destination")
        if src == WALLET or (src in keys and dst and dst != WALLET and r["kind"] == "withdraw"):
            other = dst
        elif dst == WALLET or r["kind"] == "deposit":
            other = src
    # prefer the non-wallet end of a transfer that matches direction
    other = None
    for ix in msg["instructions"]:
        p = ix.get("parsed")
        if not isinstance(p, dict) or p.get("type") not in ("transfer", "transferChecked"):
            continue
        info = p["info"]
        src, dst = info.get("source"), info.get("destination")
        if r["kind"] == "deposit" and (dst == WALLET or (src and src != WALLET)):
            other = src
        if r["kind"] == "withdraw" and (src == WALLET or src in keys):
            if dst and dst != WALLET:
                other = dst
    sides[(r["kind"], r["asset"])][other or "?"] += float(r["amount"])
    if (i + 1) % 20 == 0:
        print("checked", i + 1, flush=True)

for k, m in sides.items():
    print("\n", k)
    for addr, amt in sorted(m.items(), key=lambda kv: -kv[1])[:6]:
        print(f"  {amt:.4f}  {addr}")

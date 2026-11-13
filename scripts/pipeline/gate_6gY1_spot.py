"""Do 'no recent target' rows actually have an outside buy just before them?"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter

from sno.analyze import get_tx, rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
WSOL = "So11111111111111111111111111111111111111112"
rows = [r for r in csv.DictReader(open("gate_6gY1_oct16.csv", encoding="utf-8-sig"))
        if r["sniping_type"] == "no recent target"]
# spread across the file
step = max(1, len(rows) // 12)
sample = rows[::step][:12]
print("checking", len(sample), "of", len(rows))

def is_buy(tx, mint):
    if tx["meta"]["err"]:
        return False
    keys = tx["transaction"]["message"]["accountKeys"]
    signer = next(k["pubkey"] for k in keys if k.get("signer"))
    progs = [ix["programId"] for ix in tx["transaction"]["message"]["instructions"]]
    if PROG in progs:
        return "bot"
    for b in tx["meta"].get("postTokenBalances") or []:
        if b["mint"] == mint and b.get("owner") == signer:
            pre = next((p for p in (tx["meta"].get("preTokenBalances") or [])
                        if p["accountIndex"] == b["accountIndex"] and p["mint"] == mint), None)
            before = int(pre["uiTokenAmount"]["amount"]) if pre else 0
            if int(b["uiTokenAmount"]["amount"]) > before:
                return signer
    return None

kinds = Counter()
for r in sample:
    hist = rpc("getSignaturesForAddress", [r["mint"], {"before": r["tx"], "limit": 15}])
    slot = int(r["slot"])
    found = None
    for h in hist:
        if h.get("err"):
            continue
        if slot - h["slot"] > 150:
            found = "older than 150 slots"
            break
        tx = get_tx(h["signature"])
        who = is_buy(tx, r["mint"])
        if who == "bot":
            continue
        if who:
            found = f"outside {who[:8]} gap {slot - h['slot']}"
            break
    if found is None:
        found = "no prior buy in 15 mint txs"
    kinds[found.split()[0]] += 1
    print(r["time_utc"], r["mint"][:8], found)
print(kinds)

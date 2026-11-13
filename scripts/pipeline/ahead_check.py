"""For each Oct 13 backrun: did the bot land any tx that mentions the target wallet BEFORE the target tx?

A bot tx that carries the target wallet as an account shows up in the target wallet's signature
history, so getSignaturesForAddress(target, before=target_tx) lists every earlier attempt.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from sno.paths import RESULTS
from sno.analyze import rpc

WINDOW_SLOTS = 150
CSV = sys.argv[1] if len(sys.argv) > 1 else "backruns_oct13.full.csv"
CACHE = sys.argv[2] if len(sys.argv) > 2 else "multi_oct13_{}.jsonl"
rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8-sig")) if not r["buyer_wallet"].startswith("BuekUk")]

recs = {}
for w in {r["buyer_wallet"] for r in rows}:
    for l in open(CACHE.format(w[:8])):
        t = json.loads(l)
        recs[t["sig"]] = t

has_target = Counter()
for r in rows:
    accs = recs[r["bot_tx"]]["accounts"]
    has_target[r["buyer_wallet"][:8], r["target_wallet"] in accs] += 1
print("bot buy includes target wallet as an account (wallet, yes/no): count")
for k, v in sorted(has_target.items()):
    print("  ", k, v)


def signer_of(sig):
    tx = rpc("getTransaction", [sig, {"encoding": "json", "maxSupportedTransactionVersion": 1}])
    return tx["transaction"]["message"]["accountKeys"][0]


def check(r):
    slot, bot, tgt = int(r["slot"]), r["buyer_wallet"], r["target_wallet"]
    before = rpc("getSignaturesForAddress", [tgt, {"before": r["target_tx"], "limit": 200}])
    before = [s for s in before if s["slot"] >= slot - WINDOW_SLOTS]
    after = rpc("getSignaturesForAddress", [tgt, {"until": r["target_tx"], "limit": 1000}])
    after = [s for s in after if s["slot"] == slot]
    ahead = []
    for s in before:
        if signer_of(s["signature"]) == bot:
            ahead.append((slot - s["slot"], "FAIL" if s["err"] else "ok", json.dumps(s["err"])))
    later_same_block = sum(1 for s in after if s["signature"] != r["bot_tx"] and s["err"] and signer_of(s["signature"]) == bot)
    return r, ahead, len(before), later_same_block


with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(check, rows))

per = defaultdict(lambda: Counter())
examples = []
for r, ahead, n_before, later in res:
    w = r["buyer_wallet"][:8]
    per[w]["backruns"] += 1
    per[w]["with_tx_ahead"] += bool(ahead)
    per[w]["failed_ahead"] += sum(a[1] == "FAIL" for a in ahead)
    per[w]["ahead_same_block"] += sum(a[0] == 0 for a in ahead)
    per[w]["failed_copies_after_in_block"] += later
    if ahead and len(examples) < 12:
        examples.append((w, r["target_tx"][:12], ahead[:4]))
print(f"\nper wallet (attempts mentioning the target wallet, landed within {WINDOW_SLOTS} slots before the target tx)")
for w, c in sorted(per.items()):
    print(f"  {w}  {dict(c)}")
tot = sum(per.values(), Counter())
print("  TOTAL", dict(tot))
print("\nexamples (slots before target, status, error):")
for e in examples:
    print("  ", e)

"""Oct 13 bots: custom program per wallet, failed-tx anatomy, target repetition and overlap."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.analyze import rpc

SKIP = ("ComputeBudget", "1111", "AToken", "Token", "6EF8rr", "L2TEx")
r13 = list(csv.DictReader(open("backruns_oct13.full.csv", encoding="utf-8-sig")))
r8 = list(csv.DictReader(open("backruns_oct8.blockorder.csv", encoding="utf-8-sig")))
wallets = sorted({r["buyer_wallet"] for r in r13})

print("== custom programs in each wallet's backrun buys")
recs = {}
for w in wallets:
    for l in open(f"multi_oct13_{w[:8]}.jsonl"):
        t = json.loads(l)
        recs[t["sig"]] = t
for w in wallets:
    c = Counter(p for r in r13 if r["buyer_wallet"] == w for p in recs[r["bot_tx"]]["programs"] if not p.startswith(SKIP))
    print(f"  {w[:8]}  {c.most_common(3)}")

print("\n== target wallets")
tw = Counter(r["target_wallet"] for r in r13)
print(f"  oct13 unique targets {len(tw)} of {len(r13)}; repeated: {[(k[:6], v) for k, v in tw.most_common(6) if v > 1]}")
t8 = {r["target_wallet"] for r in r8}
print(f"  oct13 targets also targeted on oct8: {len(set(tw) & t8)}")
same_tx = Counter(r["target_tx"] for r in r13)
print(f"  target txs backrun by >1 oct13 bot: {sum(v > 1 for v in same_tx.values())}")
print(f"  block_index of bot buys: median {sorted(int(r['block_index']) for r in r13)[len(r13) // 2]}")

print("\n== failed txs (error tally from signature lists, first 2 pages per wallet before Oct 14 00:00)")
END = int(datetime(2026, 10, 14, tzinfo=timezone.utc).timestamp())


def first_page(w):
    last = max((t for t in recs.values() if w in t["signers"] and t["blockTime"] < END), key=lambda t: t["blockTime"])
    out, before = [], last["sig"]
    for _ in range(2):
        page = rpc("getSignaturesForAddress", [w, {"limit": 1000, "before": before}])
        out += page
        before = page[-1]["signature"]
    return w, out


with ThreadPoolExecutor(5) as ex:
    pages = dict(ex.map(first_page, [w for w in wallets if not w.startswith("BuekUk")]))
samples = []
for w, sigs in pages.items():
    errs = Counter(json.dumps(s["err"]) if s["err"] else "ok" for s in sigs)
    print(f"  {w[:8]} {dict(errs.most_common(4))}")
    samples += [(w, s["signature"]) for s in sigs if s["err"]][:6]


def anatomy(ws):
    w, sig = ws
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    msg, meta = tx["transaction"]["message"], tx["meta"]
    ix_i = meta["err"]["InstructionError"][0] if "InstructionError" in (meta["err"] or {}) else None
    failing = msg["instructions"][ix_i]["programId"] if ix_i is not None else None
    progs = [ix["programId"] for ix in msg["instructions"] if not ix["programId"].startswith(SKIP)]
    logs = [l for l in meta.get("logMessages") or [] if "rror" in l or "failed" in l][-2:]
    blk = rpc("getBlock", [tx["slot"], {"transactionDetails": "signatures", "rewards": False, "maxSupportedTransactionVersion": 1}])
    idx = blk["signatures"].index(sig)
    return w[:8], tx["slot"], idx, failing and failing[:8], [p[:8] for p in progs], meta["fee"] / 1e9, logs


print("\n== sample failed txs: wallet, slot, index in block, failing program, programs, fee, error logs")
with ThreadPoolExecutor(8) as ex:
    for a in ex.map(anatomy, samples[:24]):
        print("  ", a)

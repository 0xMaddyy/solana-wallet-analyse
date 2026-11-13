"""For each Oct 13 backrun: does the bot tx reference the target wallet, and did the bot land
(failed) copies before the target, in the target's block or in the 2 slots before it?"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from sno.analyze import rpc

WALLETS = {
    "2LSncYjJrRsorTTG7UeTia9rmGo8pw8JtaAoYbq7CV5F", "46Zk9VL676HwJTMWrhFTxLdFeP1oL4vsCwRnK9g2HMbj",
    "4bHUoZY36hmtW1FbJ1XJ5umWmFWXxx9voAe94M8PWNpL", "55pbD9gt6ftSfu36XhZX3Hheqg4rqvoG7Ydr3mhZgTah",
    "7XLv9c3YCn7B9dh9oe6GqfD8ABCudNkj3o11dC9mGQsf", "9qz7cWBqYBP2TnGfzMmxX64G4PQip7HtogjPBBnMhWpw",
    "D6Fuvs4DATozxeV5fdr14xtZYCQDRfZzEmhGrjm3BgwG", "Fhbh1DTUDKt6qu9zVg8Q5VgnZa1WWWbxBxG6pCoJoggA",
    "FteNBUJPDP5ZtwJYdBnJhvBuEhjHC2a3o7VR1TU4pmZT",
}
PREV_SLOTS = 2

rows = [r for r in csv.DictReader(open("backruns_oct13.full.csv", encoding="utf-8-sig")) if r["buyer_wallet"] in WALLETS]
recs = {}
for w in WALLETS:
    for l in open(f"multi_oct13_{w[:8]}.jsonl"):
        t = json.loads(l)
        recs[t["sig"]] = t


@lru_cache(maxsize=None)
def block(slot):
    try:
        b = rpc("getBlock", [slot, {"transactionDetails": "accounts", "rewards": False,
                                    "maxSupportedTransactionVersion": 1}], retries=3)
    except Exception:
        return None
    out = []
    for i, t in enumerate(b["transactions"]):
        keys = [k["pubkey"] for k in t["transaction"]["accountKeys"]]
        out.append((i, t["transaction"]["signatures"][0], keys[0], set(keys), t["meta"]["err"] is not None))
    return out


def check(r):
    bot, tgt, mint, slot, idx = r["buyer_wallet"], r["target_wallet"], r["mint"], int(r["slot"]), int(r["block_index"])
    res = {"row": r, "bot_has_target": tgt in recs.get(r["bot_tx"], {}).get("accounts", [])}
    blk = block(slot)
    if blk is None:
        res["missing_block"] = True
        return res
    mine = [(i, s, keys, err) for i, s, signer, keys, err in blk if signer == bot]
    rel = [(i, err, tgt in keys, mint in keys) for i, s, keys, err in mine if (tgt in keys or mint in keys)]
    tgt_idx = idx - 1
    res["before"] = [(i, err, has_t) for i, err, has_t, _ in rel if i < tgt_idx]
    res["after"] = [(i, err, has_t) for i, err, has_t, _ in rel if i > idx]
    res["before_any_bot_tx"] = sum(1 for i, *_ in mine if i < tgt_idx)
    prev = []
    for s in range(slot - PREV_SLOTS, slot):
        pb = block(s)
        if pb:
            prev += [(s, i, err, tgt in keys) for i, sig, signer, keys, err in pb
                     if signer == bot and (tgt in keys or mint in keys)]
    res["prev_slots"] = prev
    return res


with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(check, rows))

print(f"rows {len(results)}; bot buy tx lists target wallet: {sum(r['bot_has_target'] for r in results)}")
print(f"missing blocks: {sum(1 for r in results if r.get('missing_block'))}")
ok = [r for r in results if not r.get("missing_block")]
b4 = [r for r in ok if r["before"]]
pv = [r for r in ok if r["prev_slots"]]
print(f"rows with bot copies (same mint/target) BEFORE the target in the same block: {len(b4)}")
print(f"rows with bot copies in the {PREV_SLOTS} slots before the target's slot: {len(pv)}")
print(f"rows with bot copies AFTER the bot's success in the same block: {sum(1 for r in ok if r['after'])}; "
      f"copies after: {sum(len(r['after']) for r in ok)}, failed {sum(e for r in ok for _, e, _ in r['after'])}, "
      f"listing target wallet {sum(h for r in ok for *_, h in r['after'])}")
per = Counter()
for r in ok:
    w = r["row"]["buyer_wallet"][:8]
    per[(w, "rows")] += 1
    per[(w, "before")] += bool(r["before"])
    per[(w, "prev")] += bool(r["prev_slots"])
for w in sorted({k[0] for k in per}):
    print(f"  {w}  rows {per[(w, 'rows')]:3d}  copies-before-target {per[(w, 'before')]:3d}  copies-in-prev-slots {per[(w, 'prev')]:3d}")
for r in (b4 + pv)[:15]:
    row = r["row"]
    print("  example", row["buyer_wallet"][:8], row["slot"], "target idx", int(row["block_index"]) - 1,
          "before:", r["before"][:5], "prev slots:", r["prev_slots"][:5])

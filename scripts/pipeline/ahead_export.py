"""Export every bot tx that landed before its backrun target (same block or up to WINDOW_SLOTS earlier).

Candidates come from two places:
- the target wallet's signature history before the target tx (bots that put the target wallet in their buy)
- the target's own block (bots that only reference the mint)
A candidate counts when the bot signed it and it touches the mint or the target wallet.
Writes failed_copies_before_target.csv.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import glob
import json
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import get_tx, rpc

WINDOW_SLOTS = 150
WORKERS = 8
# usage: ahead_export.py [out.csv] [backruns.csv ...]
OUT = sys.argv[1] if len(sys.argv) > 1 else "failed_copies_before_target.csv"
SOURCES = sys.argv[2:] or ["backruns_oct13.full.csv", "backruns_oct13cnjo.csv"]

_lock = threading.Lock()
_blocks = {}
_tx_fh = open("ahead_txcache.jsonl", "a", encoding="utf-8")


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def load_known(bots):
    known = {}
    prefixes = {b[:8] for b in bots}
    paths = []
    for pref in prefixes:
        paths.extend(glob.glob(f"multi_*_{pref}.jsonl"))
        paths.extend(glob.glob(f"multi_{pref}.jsonl"))
    if os_path_exists("ahead_txcache.jsonl"):
        paths.append("ahead_txcache.jsonl")
    for path in paths:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
            except json.JSONDecodeError:
                continue
            if t.get("missing") or "accounts" not in t or "sig" not in t:
                continue
            known[t["sig"]] = {
                "sig": t["sig"], "slot": t.get("slot"), "err": t.get("err"),
                "fee": t.get("fee") or 0, "accounts": t["accounts"],
            }
    log(f"known txs with account keys: {len(known)}")
    return known


def os_path_exists(path):
    import os
    return os.path.exists(path)


def page_sigs(addr, min_slot):
    out, before = [], None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [addr, opts])
        if not page:
            break
        out.extend(page)
        before = page[-1]["signature"]
        if page[-1]["slot"] < min_slot or len(page) < 1000:
            break
    return [s for s in out if s["slot"] >= min_slot]


def tx_of(sig, known):
    with _lock:
        hit = known.get(sig)
    if hit:
        return hit
    tx = get_tx(sig)
    if not tx or not tx.get("meta"):
        return None
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]
    meta = tx["meta"]
    rec = {"sig": sig, "slot": tx["slot"], "err": meta.get("err"), "fee": meta.get("fee") or 0, "accounts": keys}
    line = json.dumps(rec) + "\n"
    with _lock:
        known[sig] = rec
        _tx_fh.write(line)
        _tx_fh.flush()
    return rec


def block_sigs(slot):
    with _lock:
        hit = _blocks.get(slot)
    if hit is not None:
        return hit
    b = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                               "maxSupportedTransactionVersion": 1}])
    sigs = b["signatures"]
    with _lock:
        _blocks[slot] = sigs
    return sigs


def target_slots(r):
    tslot = int(r["slot"])
    hist = rpc("getSignaturesForAddress", [r["target_wallet"], {"before": r["target_tx"], "limit": 200}])
    slots = {tslot} | {s["slot"] for s in hist if s["slot"] >= tslot - WINDOW_SLOTS}
    return r["target_tx"], slots


rows = [r for src in SOURCES for r in csv.DictReader(open(src, encoding="utf-8-sig"))
        if not r["buyer_wallet"].startswith("BuekUk")]
log(f"backruns {len(rows)}")
bots = sorted({r["buyer_wallet"] for r in rows})
known = load_known(bots)

by_bot = defaultdict(list)
for r in rows:
    by_bot[r["buyer_wallet"]].append(r)

SIG_CACHE = "ahead_botsigs.json"
saved_sigs = {}
if os_path_exists(SIG_CACHE):
    try:
        saved_sigs = json.load(open(SIG_CACHE, encoding="utf-8"))
    except json.JSONDecodeError:
        saved_sigs = {}

bot_by_slot = {}
for bot, brows in by_bot.items():
    min_slot = min(int(r["slot"]) for r in brows) - WINDOW_SLOTS
    cached = saved_sigs.get(bot)
    if cached and cached.get("min_slot") == min_slot:
        sigs = cached["sigs"]
        log(f"{bot[:8]}: {len(sigs)} sigs from cache")
    else:
        sigs = [{"signature": s["signature"], "slot": s["slot"]} for s in page_sigs(bot, min_slot)]
        saved_sigs[bot] = {"min_slot": min_slot, "sigs": sigs}
        json.dump(saved_sigs, open(SIG_CACHE, "w", encoding="utf-8"))
        log(f"{bot[:8]}: {len(sigs)} sigs in range")
    slot_map = defaultdict(list)
    for s in sigs:
        slot_map[s["slot"]].append(s["signature"])
    bot_by_slot[bot] = slot_map
    log(f"{bot[:8]}: {len(slot_map)} slots")

with ThreadPoolExecutor(WORKERS) as ex:
    slot_sets = dict(ex.map(target_slots, rows))
log(f"target histories {len(slot_sets)}")

candidates = []
for r in rows:
    slots = slot_sets[r["target_tx"]]
    for slot in slots:
        for sig in bot_by_slot[r["buyer_wallet"]].get(slot, []):
            candidates.append(sig)
need = [s for s in dict.fromkeys(candidates) if s not in known]
log(f"candidate sigs {len(set(candidates))}; fetching {len(need)}")
_fetch_n = {"n": 0}


def fetch_one(sig):
    tx_of(sig, known)
    with _lock:
        _fetch_n["n"] += 1
        n = _fetch_n["n"]
    if n % 500 == 0 or n == len(need):
        log(f"fetched {n}/{len(need)}")


with ThreadPoolExecutor(WORKERS) as ex:
    list(ex.map(fetch_one, need))

found = []
for i, r in enumerate(rows, 1):
    bot, tgt, mint, tslot = r["buyer_wallet"], r["target_wallet"], r["mint"], int(r["slot"])
    try:
        tsigs = block_sigs(tslot)
        tindex = tsigs.index(r["target_tx"])
    except Exception as e:
        log(f"target index failed {r['target_tx'][:12]}: {e}")
        continue
    slots = slot_sets[r["target_tx"]]
    for slot in sorted(slots):
        for sig in bot_by_slot[bot].get(slot, []):
            info = known.get(sig)
            if not info or not info["accounts"] or info["accounts"][0] != bot:
                continue
            if not ({mint, tgt} & set(info["accounts"])):
                continue
            try:
                cindex = block_sigs(slot).index(sig)
            except ValueError:
                continue
            if slot == tslot and cindex >= tindex:
                continue
            err = info["err"]
            found.append({
                "bot_wallet": bot, "target_wallet": tgt, "mint": mint, "target_tx": r["target_tx"],
                "target_slot": tslot, "target_index": tindex, "bot_backrun_tx": r["bot_tx"],
                "bot_backrun_index": r["block_index"], "copy_tx": sig, "copy_slot": slot, "copy_index": cindex,
                "slots_before_target": tslot - slot,
                "positions_before_target": tindex - cindex if slot == tslot else "",
                "status": "failed" if err else "success",
                "error": "" if not err else str(err).replace("'", '"'),
                "fee_sol": (info["fee"] or 0) / 1e9,
                "references_target_wallet": tgt in info["accounts"],
            })
    if i % 100 == 0 or i == len(rows):
        log(f"matched {i}/{len(rows)} backruns, copies {len(found)}")

found.sort(key=lambda c: (c["bot_wallet"], c["target_slot"], c["copy_slot"], c["copy_index"]))
FIELDS = list(found[0]) if found else [
    "bot_wallet", "target_wallet", "mint", "target_tx", "target_slot", "target_index",
    "bot_backrun_tx", "bot_backrun_index", "copy_tx", "copy_slot", "copy_index",
    "slots_before_target", "positions_before_target", "status", "error", "fee_sol",
    "references_target_wallet",
]
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(found)

print(f"backruns scanned {len(rows)}; copies before target {len(found)} "
      f"(failed {sum(c['status'] == 'failed' for c in found)}, success {sum(c['status'] == 'success' for c in found)}); "
      f"backruns affected {len({c['target_tx'] for c in found})}")
per = {}
for c in found:
    p = per.setdefault(c["bot_wallet"][:8], [set(), 0])
    p[0].add(c["target_tx"])
    p[1] += 1
for w, (t, n) in sorted(per.items()):
    print(f"  {w}  backruns {len(t)}  copies {n}")

"""Failed bot sprays in each Oct 20 backrun's slot, besides the successful backrun and the copies already exported."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from sno.paths import RESULTS
from sno.analyze import get_tx, rpc

CACHE = str(RESULTS / "ahead_txcache.jsonl")
WORKERS = 6
_lock = threading.Lock()
_blocks = {}


def log(msg):
    print(msg, flush=True)


def custom_code(err):
    if not isinstance(err, dict):
        return ""
    ie = err.get("InstructionError")
    if isinstance(ie, list) and len(ie) == 2 and isinstance(ie[1], dict) and "Custom" in ie[1]:
        return ie[1]["Custom"]
    return ""


def load_cache():
    known = {}
    try:
        fh = open(CACHE, encoding="utf-8")
    except FileNotFoundError:
        return known
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            t = json.loads(line)
        except json.JSONDecodeError:
            continue
        if t.get("sig") and t.get("accounts"):
            known[t["sig"]] = t
    return known


def tx_of(sig, known, fh):
    with _lock:
        hit = known.get(sig)
    if hit and hit.get("accounts"):
        return hit
    tx = get_tx(sig)
    if not tx or not tx.get("meta"):
        return None
    msg = tx["transaction"]["message"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    meta = tx["meta"]
    rec = {"sig": sig, "slot": tx["slot"], "err": meta.get("err"), "fee": meta.get("fee") or 0, "accounts": keys}
    with _lock:
        known[sig] = rec
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
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


def main():
    backruns = list(csv.DictReader(open("backruns_oct20.csv", encoding="utf-8-sig")))
    already = {r["copy_tx"] for r in csv.DictReader(open("failed_copies_before_target_oct20.csv", encoding="utf-8-sig"))}
    by_slot = defaultdict(list)
    for line in open("oct20_allsigs.jsonl", encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        by_slot[(r["bot"], r["slot"])].append(r)

    jobs = []
    for b in backruns:
        key = (b["buyer_wallet"], int(b["slot"]))
        for r in by_slot.get(key, []):
            if not r["err"] or r["sig"] == b["bot_tx"] or r["sig"] in already:
                continue
            jobs.append((b, r["sig"]))
    # one sig can sit on two backruns only if the same bot has two backruns in one slot
    log(f"candidate failed sigs {len(jobs)}")

    known = load_cache()
    need = [sig for _, sig in jobs if sig not in known]
    uniq = list(dict.fromkeys(need))
    log(f"cached {len(jobs) - len(uniq)} to fetch {len(uniq)}")
    with open(CACHE, "a", encoding="utf-8") as fh:
        done = {"n": 0}

        def one(sig):
            tx_of(sig, known, fh)
            with _lock:
                done["n"] += 1
                n = done["n"]
            if n % 500 == 0 or n == len(uniq):
                log(f"fetched {n}/{len(uniq)}")

        if uniq:
            with ThreadPoolExecutor(WORKERS) as ex:
                list(ex.map(one, uniq))

    rows = []
    missed = 0
    for b, sig in jobs:
        rec = known.get(sig)
        if not rec or not rec.get("accounts"):
            missed += 1
            continue
        accounts = rec["accounts"]
        if b["mint"] not in accounts and b["target_wallet"] not in accounts:
            continue
        slot = int(b["slot"])
        try:
            sigs = block_sigs(slot)
            cindex = sigs.index(sig)
        except Exception:
            cindex = ""
        tindex = int(b["block_index"])
        err = rec.get("err")
        rows.append({
            "bot_wallet": b["buyer_wallet"],
            "target_wallet": b["target_wallet"],
            "mint": b["mint"],
            "target_tx": b["target_tx"],
            "target_slot": slot,
            "target_index": tindex,
            "bot_backrun_tx": b["bot_tx"],
            "bot_backrun_index": "",
            "copy_tx": sig,
            "copy_slot": rec["slot"],
            "copy_index": cindex,
            "slots_before_target": slot - rec["slot"],
            "positions_before_target": (tindex - cindex) if cindex != "" else "",
            "status": "failed",
            "error": "" if not err else str(err).replace("'", '"'),
            "fee_sol": (rec.get("fee") or 0) / 1e9,
            "references_target_wallet": b["target_wallet"] in accounts,
            "error_code": custom_code(err),
        })

    # bot backrun index from the same block
    for r in rows:
        if r["copy_index"] == "":
            continue
        try:
            sigs = block_sigs(int(r["target_slot"]))
            r["bot_backrun_index"] = sigs.index(r["bot_backrun_tx"])
        except ValueError:
            pass

    rows.sort(key=lambda r: (r["bot_wallet"], r["target_slot"], r["copy_index"] if r["copy_index"] != "" else 0))
    fields = ["bot_wallet", "target_wallet", "mint", "target_tx", "target_slot", "target_index",
              "bot_backrun_tx", "bot_backrun_index", "copy_tx", "copy_slot", "copy_index",
              "slots_before_target", "positions_before_target", "status", "error", "fee_sol",
              "references_target_wallet", "error_code"]
    out = "failed_bulks_oct20.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    buckets = defaultdict(list)
    for r in rows:
        buckets[r["target_tx"]].append(r)
    first_fields = ["bot_wallet", "target_wallet", "mint", "target_tx", "target_slot", "target_index",
                    "bot_backrun_tx", "bot_backrun_index", "txs_count", "copy_tx", "copy_slot", "copy_index",
                    "slots_before_target", "positions_before_target", "status", "error", "fee_sol",
                    "references_target_wallet", "error_code"]
    first = "failed_bulks_oct20.first.csv"
    with open(first, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=first_fields)
        w.writeheader()
        ordered = sorted(buckets.values(), key=lambda rs: (rs[0]["bot_wallet"], int(rs[0]["target_slot"])))
        for rs in ordered:
            rs.sort(key=lambda r: r["copy_index"] if r["copy_index"] != "" else 0)
            row = dict(rs[0])
            row["txs_count"] = len(rs)
            w.writerow({k: row.get(k, "") for k in first_fields})
    log(f"kept {len(rows)} failed txs for {len(buckets)} targets, fetch misses {missed}")
    log(f"wrote {out} and {first}")


if __name__ == "__main__":
    main()

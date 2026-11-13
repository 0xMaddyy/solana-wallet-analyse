"""Export Oct 20 bot sprays that failed in full for one target.

The failed-copies file only keeps copies that landed before a successful backrun.
This scans every bot signature that day, keeps slots where the bot's transactions
all failed and there are at least 3 of them, groups those by mint, and attaches
the target buy when one is in the same slot or shortly after.
"""

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

WALLETS = [ln.strip() for ln in open("wallets_oct14.txt") if ln.strip()]
BOTS = set(WALLETS)
MIN_BULK = 3
FORWARD_SLOTS = 40
SUCCESS_WINDOW = 150
WORKERS = 6
CACHE = str(RESULTS / "ahead_txcache.jsonl")
OUT = "failed_bulks_all_failed_oct20.csv"
FIRST = "failed_bulks_all_failed_oct20.first.csv"

_lock = threading.Lock()
_blocks = {}


def log(msg):
    print(msg, flush=True)


def custom_code(err):
    if not isinstance(err, dict):
        return None
    ie = err.get("InstructionError")
    if isinstance(ie, list) and len(ie) == 2 and isinstance(ie[1], dict) and "Custom" in ie[1]:
        return ie[1]["Custom"]
    return None


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


def load_sigs():
    rows = []
    for line in open("oct20_allsigs.jsonl", encoding="utf-8"):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def success_mints():
    """bot -> list of (slot, mint) from successful cached txs."""
    out = defaultdict(list)
    for bot in WALLETS:
        path = f"multi_oct20_{bot[:8]}.jsonl"
        try:
            fh = open(path, encoding="utf-8")
        except FileNotFoundError:
            continue
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
            except json.JSONDecodeError:
                continue
            if t.get("err") or t.get("missing") or not t.get("accounts"):
                continue
            mints = [a for a in t["accounts"] if isinstance(a, str) and a.endswith("pump")]
            for m in mints:
                out[bot].append((t.get("slot") or 0, m))
    return out


def mint_of(accounts):
    mints = [a for a in accounts if isinstance(a, str) and a.endswith("pump")]
    if len(mints) == 1:
        return mints[0]
    return None


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
    line = json.dumps(rec) + "\n"
    with _lock:
        known[sig] = rec
        fh.write(line)
        fh.flush()
    return rec


def block_of(slot):
    with _lock:
        hit = _blocks.get(slot)
    if hit is not None:
        return hit
    b = rpc("getBlock", [slot, {"transactionDetails": "accounts", "rewards": False,
                               "maxSupportedTransactionVersion": 1, "encoding": "json"}])
    txs = []
    for i, tx in enumerate(b["transactions"]):
        msg = tx["transaction"]
        keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
        signers = [k["pubkey"] for k in msg["accountKeys"] if isinstance(k, dict) and k.get("signer")]
        sig = msg["signatures"][0]
        txs.append({"index": i, "sig": sig, "signers": signers, "accounts": keys})
    with _lock:
        _blocks[slot] = txs
    return txs


def find_target(bot, mint, accounts, slot_lo, slot_hi):
    """Earliest non-bot tx of this mint at or after slot_lo whose signer is in the bot tx, else any outside buy."""
    for slot in range(slot_lo, slot_hi + 1):
        referenced, fallback = [], []
        try:
            txs = block_of(slot)
        except Exception as e:
            log(f"block {slot} failed {e}")
            continue
        for tx in txs:
            if mint not in tx["accounts"]:
                continue
            signer = tx["signers"][0] if tx["signers"] else None
            if not signer or signer in BOTS:
                continue
            hit = (slot, tx["index"], tx["sig"], signer)
            if signer in accounts:
                referenced.append(hit)
            else:
                fallback.append(hit)
        if referenced:
            return min(referenced)
        if fallback:
            return min(fallback)
    return None


def main():
    sigs = load_sigs()
    by_slot = defaultdict(list)
    for r in sigs:
        by_slot[(r["bot"], r["slot"])].append(r)
    chosen = []
    for rs in by_slot.values():
        if len(rs) >= MIN_BULK and all(r["err"] for r in rs):
            chosen.extend(rs)
    log(f"all-fail bulk txs {len(chosen)} in {sum(1 for rs in by_slot.values() if len(rs) >= MIN_BULK and all(r['err'] for r in rs))} slots")

    known = load_cache()
    need = [r for r in chosen if r["sig"] not in known]
    log(f"cached {len(chosen) - len(need)} to fetch {len(need)}")
    with open(CACHE, "a", encoding="utf-8") as fh:
        done = {"n": 0}

        def one(r):
            rec = tx_of(r["sig"], known, fh)
            with _lock:
                done["n"] += 1
                n = done["n"]
            if n % 500 == 0 or n == len(need):
                log(f"fetched {n}/{len(need)}")
            return rec

        if need:
            with ThreadPoolExecutor(WORKERS) as ex:
                list(ex.map(one, need))

    successes = success_mints()
    groups = defaultdict(list)  # (bot, mint, slot) -> records
    skipped_nomint = 0
    for r in chosen:
        rec = known.get(r["sig"])
        if not rec or not rec.get("accounts"):
            continue
        mint = mint_of(rec["accounts"])
        if not mint:
            skipped_nomint += 1
            continue
        groups[(r["bot"], mint, r["slot"])].append(rec)
    log(f"slot groups {len(groups)} skipped without one pump mint {skipped_nomint}")

    # Merge same bot+mint slots when the gap is at most 10.
    items = sorted(groups, key=lambda k: (k[0], k[1], k[2]))
    clusters = []
    for key in items:
        bot, mint, slot = key
        if clusters and clusters[-1]["bot"] == bot and clusters[-1]["mint"] == mint and slot - clusters[-1]["slots"][-1] <= 10:
            clusters[-1]["slots"].append(slot)
            clusters[-1]["recs"].extend(groups[key])
        else:
            clusters.append({"bot": bot, "mint": mint, "slots": [slot], "recs": list(groups[key])})
    clusters = [c for c in clusters if len(c["recs"]) >= MIN_BULK]
    log(f"clusters {len(clusters)}")

    kept = []
    for c in clusters:
        lo, hi = c["slots"][0], c["slots"][-1]
        near = any(lo - SUCCESS_WINDOW <= slot <= hi + SUCCESS_WINDOW for slot, m in successes[c["bot"]] if m == c["mint"])
        if near:
            continue
        kept.append(c)
    log(f"clusters with no nearby success {len(kept)} txs {sum(len(c['recs']) for c in kept)}")

    already = set()
    try:
        for r in csv.DictReader(open("failed_copies_before_target_oct20.csv", encoding="utf-8-sig")):
            already.add(r["copy_tx"])
    except FileNotFoundError:
        pass

    rows_out = []
    for i, c in enumerate(kept, 1):
        accounts = set()
        for rec in c["recs"]:
            accounts.update(rec["accounts"])
        lo, hi = min(r["slot"] for r in c["recs"]), max(r["slot"] for r in c["recs"])
        target = find_target(c["bot"], c["mint"], accounts, lo, hi + FORWARD_SLOTS)
        if i % 25 == 0 or i == len(kept):
            log(f"resolved {i}/{len(kept)}")
        tslot = tindex = tsig = twallet = None
        if target:
            tslot, tindex, tsig, twallet = target
        for rec in c["recs"]:
            if rec["sig"] in already:
                continue
            err = rec.get("err")
            cindex = ""
            try:
                sigs = [tx["sig"] for tx in block_of(rec["slot"])]
                cindex = sigs.index(rec["sig"])
            except Exception:
                pass
            rows_out.append({
                "bot_wallet": c["bot"],
                "target_wallet": twallet or "",
                "mint": c["mint"],
                "target_tx": tsig or "",
                "target_slot": tslot if tslot is not None else "",
                "target_index": tindex if tindex is not None else "",
                "copy_tx": rec["sig"],
                "copy_slot": rec["slot"],
                "copy_index": cindex,
                "slots_before_target": (tslot - rec["slot"]) if tslot is not None else "",
                "positions_before_target": (tindex - cindex) if tslot == rec["slot"] and cindex != "" and tindex is not None else "",
                "status": "failed",
                "error": "" if not err else str(err).replace("'", '"'),
                "fee_sol": (rec.get("fee") or 0) / 1e9,
                "references_target_wallet": bool(twallet and twallet in rec["accounts"]),
                "error_code": custom_code(err) if custom_code(err) is not None else "",
            })

    rows_out.sort(key=lambda r: (r["bot_wallet"], r["mint"], r["copy_slot"], r["copy_index"] if r["copy_index"] != "" else 0))
    fields = ["bot_wallet", "target_wallet", "mint", "target_tx", "target_slot", "target_index",
              "copy_tx", "copy_slot", "copy_index", "slots_before_target", "positions_before_target",
              "status", "error", "fee_sol", "references_target_wallet", "error_code"]
    with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)

    # One row per bot + target tx (or mint if the target buy was not found), the earliest copy, plus txs_count.
    buckets = defaultdict(list)
    for r in rows_out:
        key = (r["bot_wallet"], r["target_tx"] or r["mint"] + ":" + str(r["copy_slot"]))
        buckets[key].append(r)
    first_fields = ["bot_wallet", "target_wallet", "mint", "target_tx", "target_slot", "target_index",
                    "txs_count", "copy_tx", "copy_slot", "copy_index", "slots_before_target",
                    "positions_before_target", "status", "error", "fee_sol", "references_target_wallet", "error_code"]
    with open(FIRST, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=first_fields)
        w.writeheader()
        for rs in buckets.values():
            rs.sort(key=lambda r: (r["copy_slot"], r["copy_index"] if r["copy_index"] != "" else 0))
            row = dict(rs[0])
            row["txs_count"] = len(rs)
            w.writerow({k: row.get(k, "") for k in first_fields})
    log(f"wrote {len(rows_out)} copies in {len(buckets)} groups to {OUT}")


if __name__ == "__main__":
    main()

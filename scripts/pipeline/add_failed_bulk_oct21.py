"""Add failed_bulk_count to backruns_oct21.csv.

For each successful copy, the count is failed transactions that bot signed in
the same slot, other than the successful copy, that include the mint or the
target wallet.
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

BACKRUNS = "backruns_oct21.csv"
CACHE = str(RESULTS / "ahead_txcache.jsonl")
WORKERS = 6
_lock = threading.Lock()


def log(msg):
    print(msg, flush=True)


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
        if t.get("sig") and "accounts" in t:
            known[t["sig"]] = t
    return known


def page_failed(bot, slots):
    """Failed signatures whose slot is one of this bot's backrun slots."""
    out, before = [], None
    floor = min(slots)
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [bot, opts])
        if not page:
            break
        for s in page:
            if s["slot"] in slots and s.get("err"):
                out.append(s["signature"])
        before = page[-1]["signature"]
        if page[-1]["slot"] < floor or len(page) < 1000:
            break
    return out


def main():
    rows = list(csv.DictReader(open(BACKRUNS, encoding="utf-8-sig")))
    fields = list(rows[0].keys())
    if "failed_bulk_count" not in fields:
        fields.append("failed_bulk_count")
    slots_by_bot = defaultdict(set)
    success = defaultdict(set)
    for r in rows:
        slots_by_bot[r["buyer_wallet"]].add(int(r["slot"]))
        success[(r["buyer_wallet"], int(r["slot"]))].add(r["bot_tx"])

    failed = {}
    for bot, slots in slots_by_bot.items():
        sigs = page_failed(bot, slots)
        failed[bot] = sigs
        log(f"{bot[:8]} backrun slots {len(slots)} failed sigs {len(sigs)}")

    known = load_cache()
    need = [s for sigs in failed.values() for s in sigs if s not in known]
    need = list(dict.fromkeys(need))
    log(f"cached {sum(len(v) for v in failed.values()) - len(need)} to fetch {len(need)}")
    with open(CACHE, "a", encoding="utf-8") as fh:
        done = {"n": 0}

        def one(sig):
            tx = get_tx(sig)
            rec = None
            if tx and tx.get("meta"):
                msg = tx["transaction"]["message"]
                keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
                rec = {"sig": sig, "slot": tx["slot"], "err": tx["meta"].get("err"), "accounts": keys}
            with _lock:
                if rec:
                    known[sig] = rec
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
                done["n"] += 1
                n = done["n"]
            if n % 500 == 0 or n == len(need):
                log(f"fetched {n}/{len(need)}")

        if need:
            with ThreadPoolExecutor(WORKERS) as ex:
                list(ex.map(one, need))

    by_slot = defaultdict(list)
    for bot, sigs in failed.items():
        for sig in sigs:
            rec = known.get(sig)
            if rec and rec.get("accounts"):
                by_slot[(bot, rec["slot"])].append(rec)

    missed = 0
    for r in rows:
        bot, slot = r["buyer_wallet"], int(r["slot"])
        n = 0
        for rec in by_slot.get((bot, slot), []):
            if rec["sig"] in success[(bot, slot)]:
                continue
            accounts = rec["accounts"]
            if r["mint"] in accounts or r["target_wallet"] in accounts:
                n += 1
        r["failed_bulk_count"] = n
    log(f"rows {len(rows)} with a bulk {sum(1 for r in rows if int(r['failed_bulk_count']))} "
        f"median lookup misses noted separately")
    with open(BACKRUNS, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    log(f"wrote {BACKRUNS}")


if __name__ == "__main__":
    main()

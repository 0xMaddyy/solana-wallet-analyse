"""FIFO PnL for sno buyer/seller pairs, UTC Nov 5–8 2026 (sells through Nov 9 04:00)."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.paths import RESULTS
from sno.analyze import rpc
from sno.multi_fetch import record
from sno.multi_report import pair_mints, pair_sol

START = int(datetime(2026, 11, 5, tzinfo=timezone.utc).timestamp())
BUY_END = int(datetime(2026, 11, 9, tzinfo=timezone.utc).timestamp())  # buys Nov5–8
END = BUY_END + 4 * 3600  # sell buffer
TAG = "nov5_8"
CACHE_DIR = "."
OUT_DAILY = str(RESULTS / "pair_pnl_nov5_8_daily.csv")
OUT_SUMMARY = str(RESULTS / "pair_pnl_nov5_8_summary.csv")
OUT_TXT = str(RESULTS / "pair_pnl_nov5_8.txt")
NAMES = {
    "BPKVyybfMjhTEDFWBYa2wDnRV5a4Z3Lks8ZfMec3qUAW": "sno BPK pair",
    "E7hhZy9v9v2WwPx72yf8gTYF5AcJoVaSWVuJ31tueN5C": "sno E7h pair",
    "FaHvzFA7qJzZQ2kc3wA6gM6TyKKakGSfdqSy1vZ5hXB": "sno FaH pair",
    "TMWwfSM5LjA17HaWAFkvu3WXuwgk1SZ5iTuzEwdoci9": "sno TMW pair",
    "FdBhsbFNpEPQSyme9WMUaUoFWfF4Qfnrc7tBihU6HbkQ": "sno FdB pair",
    "3pDHoZBjQhAf9w5zTWsVyys7NxiQdewbjj6jnZcKP9ya": "sno 3pD pair",
    "2PAijCsZGAmG8tVgrAmwyGC5UcXxwktYkAiy57CAXTuy": "sno 2PA pair",
    "5qsuh6KapqaF6WdhdvqBKF8JiQxVmnXD7Uqr8D36iePp": "sno 5qs pair",
    "DTGbH68GcJujkim2BfGG7nHUv5Sox4GBJKsdDRKutANm": "sno DTG pair",
    "CH7GewnUqV8pdnjywGz71QVFRZ549BsDqNnpBxhzREQk": "sno CH7 pair",
    "8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF": "sno 8N4 pair",
}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def load_pairs():
    pairs = []
    for line in open("wallets_sno_pairs.txt", encoding="utf-8"):
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if parts:
            pairs.append((parts[0], parts[-1]))
    return pairs


def out_path(buyer):
    return f"multi_{TAG}_{buyer[:8]}.jsonl"


def signatures(addr):
    out, before = [], None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [addr, opts]) or []
        if not page:
            break
        out += [s for s in page if s.get("blockTime") and START <= s["blockTime"] < END and not s.get("err")]
        before = page[-1]["signature"]
        if (page[-1].get("blockTime") or END) < START:
            break
    return out


def fetch_pair(buyer, seller):
    path = out_path(buyer)
    sigs = {}
    for w in dict.fromkeys((buyer, seller)):
        for s in signatures(w):
            sigs[s["signature"]] = s
    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                try:
                    done.add(json.loads(line)["sig"])
                except Exception:
                    pass
    todo = [s for s in sigs if s not in done]
    log(f"{NAMES.get(buyer, buyer[:8])}: {len(sigs)} txs, {len(todo)} to fetch")
    t0 = time.time()
    with open(path, "a", encoding="utf-8") as f, ThreadPoolExecutor(6) as ex:
        for i, r in enumerate(ex.map(lambda s: record(s, [buyer, seller]), todo), 1):
            f.write(json.dumps(r) + "\n")
            if i % 400 == 0:
                log(f"  {buyer[:8]} {i}/{len(todo)} ({time.time()-t0:.0f}s)")
    log(f"  {buyer[:8]} done fetch ({time.time()-t0:.0f}s)")


def block_order(txs, buyer):
    """Sort by slot then in-block position for same-slot buy/sell."""
    need = defaultdict(set)
    counts = Counter(t["slot"] for t in txs)
    for t in txs:
        if counts[t["slot"]] > 1:
            need[t["slot"]].add(t["sig"])
    pos = {}
    cache_path = f"block_pos_{TAG}_{buyer[:8]}.json"
    if os.path.exists(cache_path):
        pos = {int(k): v for k, v in json.load(open(cache_path)).items()}

    def indexes(slot):
        if slot in pos and all(s in pos[slot] for s in need[slot]):
            return slot, pos[slot]
        try:
            sigs = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                           "maxSupportedTransactionVersion": 1}])["signatures"]
        except Exception as e:
            log(f"block {slot} {e}")
            return slot, {}
        return slot, {s: i for i, s in enumerate(sigs) if s in need[slot]}

    missing = [s for s in need if s not in pos or any(x not in pos[s] for x in need[s])]
    with ThreadPoolExecutor(8) as ex:
        for slot, found in ex.map(indexes, missing):
            pos[slot] = {**(pos.get(slot) or {}), **found}
    json.dump({str(k): v for k, v in pos.items()}, open(cache_path, "w"))
    return sorted(txs, key=lambda t: (t["slot"], pos.get(t["slot"], {}).get(t["sig"], 0)))


def fifo_pair(buyer, seller):
    path = out_path(buyer)
    pair = {buyer, seller}
    txs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    txs = [t for t in txs if not t.get("missing") and t.get("err") is None and t.get("blockTime")]
    txs = block_order(txs, buyer)
    open_lots = defaultdict(list)
    closed = []
    for t in txs:
        mints = pair_mints(t, pair)
        if not mints:
            continue
        s = pair_sol(t, pair)
        buys = {m: d for m, d in mints.items() if d > 0}
        sells = {m: d for m, d in mints.items() if d < 0}
        if buys and not sells:
            # cost = -s when s < 0
            per = s / len(buys)
            for m, d in buys.items():
                open_lots[m].append({
                    "buy_sig": t["sig"], "buy_bt": t["blockTime"], "buy_slot": t["slot"],
                    "tokens": d, "sold": 0, "cost": -per, "proceeds": 0.0,
                })
        elif sells and not buys:
            per = s / len(sells)
            for m, d in sells.items():
                left = -d
                for lot in open_lots[m]:
                    take = min(left, lot["tokens"] - lot["sold"])
                    if take <= 0:
                        continue
                    lot["sold"] += take
                    lot["proceeds"] += per * (take / -d)
                    left -= take
                    if lot["sold"] >= lot["tokens"] and lot.get("_done") is None:
                        lot["_done"] = True
                        closed.append(lot)
                    if left == 0:
                        break
                open_lots[m] = [l for l in open_lots[m] if l["sold"] < l["tokens"]]
    opens = [l for lots in open_lots.values() for l in lots]
    return closed, opens


def day_of(bt):
    return datetime.fromtimestamp(bt, timezone.utc).strftime("%Y-%m-%d")


def main():
    pairs = load_pairs()
    t0 = time.time()
    log(f"fetching {len(pairs)} pairs Nov5–8 (+4h sell buffer)")
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda p: fetch_pair(*p), pairs))

    daily_rows = []
    summary = []
    lines = [
        "sno buyer/seller pairs — realized FIFO PnL",
        "buys UTC 2026-11-05 .. 2026-11-08; sells through 2026-11-09 04:00 UTC",
        "",
    ]
    grand = 0.0
    for buyer, seller in pairs:
        name = NAMES.get(buyer, buyer[:8])
        closed, opens = fifo_pair(buyer, seller)
        # only lots whose buy is in Nov5–8
        in_win = [l for l in closed if START <= l["buy_bt"] < BUY_END]
        open_win = [l for l in opens if START <= l["buy_bt"] < BUY_END]
        # partial realized on open
        by_day = defaultdict(lambda: {"profit": 0.0, "n": 0, "wins": 0, "open": 0})
        tot = 0.0
        for lot in in_win:
            p = (lot["proceeds"] - lot["cost"]) / 1e9
            d = day_of(lot["buy_bt"])
            by_day[d]["profit"] += p
            by_day[d]["n"] += 1
            if p > 0:
                by_day[d]["wins"] += 1
            tot += p
        for lot in open_win:
            d = day_of(lot["buy_bt"])
            by_day[d]["open"] += 1
            if lot["sold"] > 0:
                frac = lot["sold"] / lot["tokens"]
                p = (lot["proceeds"] - lot["cost"] * frac) / 1e9
                by_day[d]["profit"] += p
                by_day[d]["n"] += 1
                if p > 0:
                    by_day[d]["wins"] += 1
                tot += p
        grand += tot
        summary.append({
            "name": name, "buyer": buyer, "seller": seller,
            "closed_buys": len(in_win), "open_buys": len(open_win),
            "profit_sol": round(tot, 6),
        })
        lines.append(f"{name}  ({buyer[:8]}… / {seller[:8]}…)")
        lines.append(f"  total {tot:+.4f} SOL   closed {len(in_win)}  still-open {len(open_win)}")
        for d in sorted(by_day):
            x = by_day[d]
            wr = 100 * x["wins"] / x["n"] if x["n"] else 0
            lines.append(f"  {d}  {x['profit']:+10.4f} SOL  trades {x['n']:4d}  win {wr:5.1f}%  open {x['open']}")
            daily_rows.append({
                "day": d, "name": name, "buyer": buyer,
                "profit_sol": round(x["profit"], 6),
                "trades": x["n"], "wins": x["wins"], "open": x["open"],
            })
        lines.append("")

    lines.append(f"GRAND TOTAL  {grand:+.4f} SOL")
    lines.append(f"elapsed {time.time()-t0:.0f}s")
    text = "\n".join(lines) + "\n"
    open(OUT_TXT, "w", encoding="utf-8").write(text)
    with open(OUT_DAILY, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["day", "name", "buyer", "profit_sol", "trades", "wins", "open"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(daily_rows, key=lambda r: (r["day"], r["name"])))
    with open(OUT_SUMMARY, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "buyer", "seller", "closed_buys", "open_buys", "profit_sol"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(summary)
    print(text)
    log(f"wrote {OUT_TXT} {OUT_DAILY} {OUT_SUMMARY}")


if __name__ == "__main__":
    main()

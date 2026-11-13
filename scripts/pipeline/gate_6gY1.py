"""Trades of every wallet that called 6gY1osm on 2026-10-16 UTC.

The program is a shared gate: instruction data is disc 0x01, an 8-byte id that must
already sit in state account FHaSvKD6, and a slot deadline. The buy itself goes
through 41Pr4XqE into pump.fun. Sells are separate transactions.

A buy is a backrun when the previous transaction in the block is an outside wallet
buying the same mint. It is a copy when an outside buy of that mint landed earlier
in the same block, or within LOOKBACK_SLOTS. Otherwise there is no recent target.

Usage: python -u gate_6gY1.py
Resumes from gate_6gY1_txs.jsonl. Writes gate_6gY1_oct16.csv.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import os
import sys
import threading
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sno.paths import RESULTS
from sno.analyze import RPC, rpc
from sno.multi_report import (
    DEX_NAMES, PLAIN_PROGRAMS, WSOL, fee_platform_of, pair_mints, pair_sol, program_platform, swqos_of,
)

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"
START = int(datetime(2026, 10, 16, tzinfo=timezone.utc).timestamp())
END = int(time.time())
# Fetch two extra hours so a sell can match a buy that opened before midnight.
FETCH_START = START - 2 * 3600
LOOKBACK_SLOTS = 150
CACHE_PATH = str(RESULTS / "gate_6gY1_txs.jsonl")
CSV_PATH = str(RESULTS / "gate_6gY1_oct16.csv")
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
END_LABEL = datetime.fromtimestamp(END, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

CACHE, _lock = {}, threading.Lock()
_fh = None


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def load_cache():
    global _fh
    if os.path.exists(CACHE_PATH):
        for line in open(CACHE_PATH, encoding="utf-8"):
            if not line.strip():
                continue
            t = json.loads(line)
            CACHE[t["sig"]] = t
    _fh = open(CACHE_PATH, "a", encoding="utf-8")
    log(f"cache {len(CACHE)} txs")


def save(t):
    if not t or t.get("missing"):
        return None
    with _lock:
        if t["sig"] in CACHE:
            return CACHE[t["sig"]]
        CACHE[t["sig"]] = t
        _fh.write(json.dumps(t) + "\n")
        _fh.flush()
    return t


def fetch_tx(sig):
    if sig in CACHE:
        return CACHE[sig]
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    if tx is None:
        return {"sig": sig, "missing": True}
    msg, meta = tx["transaction"]["message"], tx["meta"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    signers = [k["pubkey"] for k in msg["accountKeys"] if isinstance(k, dict) and k.get("signer")]
    signer = signers[0] if signers else ""
    dsol = {}
    if signer in keys:
        i = keys.index(signer)
        dsol[signer] = meta["postBalances"][i] - meta["preBalances"][i]
    pre, post = {}, {}
    for src, dst in ((meta.get("preTokenBalances"), pre), (meta.get("postTokenBalances"), post)):
        for b in src or []:
            dst[(b["accountIndex"], b["mint"], b.get("owner"))] = int(b["uiTokenAmount"]["amount"])
    tok = {}
    for k in set(pre) | set(post):
        d = post.get(k, 0) - pre.get(k, 0)
        if d:
            key = f"{k[2]}|{k[1]}"
            tok[key] = tok.get(key, 0) + d
    transfers = []
    for ix in msg["instructions"] + [i for g in meta.get("innerInstructions") or [] for i in g["instructions"]]:
        p = ix.get("parsed")
        if isinstance(p, dict) and ix.get("program") == "system" and p.get("type") == "transfer":
            transfers.append([p["info"]["source"], p["info"]["destination"], p["info"]["lamports"]])
    gate_slot = None
    for ix in msg["instructions"]:
        if ix.get("programId") == PROG and ix.get("data"):
            raw = b58decode(ix["data"])
            if len(raw) >= 13 and raw[0] == 1:
                gate_slot = int.from_bytes(raw[9:13], "little")
    return save({
        "sig": sig, "slot": tx["slot"], "blockTime": tx["blockTime"], "err": meta["err"],
        "fee": meta["fee"], "n_sigs": len(tx["transaction"]["signatures"]), "signer": signer,
        "dsol": dsol, "tok": tok, "transfers": transfers, "gate_slot": gate_slot,
        "programs": sorted({ix["programId"] for ix in msg["instructions"]}),
        "inner_programs": sorted({i["programId"] for g in meta.get("innerInstructions") or [] for i in g["instructions"]}),
    })


def safe_fetch(sig):
    try:
        return fetch_tx(sig)
    except Exception as e:
        log(f"fetch fail {sig[:12]} {e}")
        return None


def signatures(addr, fetch_start):
    """Successful signatures in [fetch_start, END). Failed count is only for [START, END)."""
    ok, failed, before = [], 0, None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [addr, opts])
        if not page:
            break
        for s in page:
            bt = s.get("blockTime") or 0
            if fetch_start <= bt < END:
                if s.get("err"):
                    if bt >= START:
                        failed += 1
                else:
                    ok.append(s["signature"])
        before = page[-1]["signature"]
        oldest = page[-1].get("blockTime") or 0
        if oldest < fetch_start or len(page) < 1000:
            break
    return ok, failed


def fetch_many(sigs, label):
    todo = [s for s in sigs if s not in CACHE]
    log(f"{label}: {len(sigs)} sigs, {len(todo)} to fetch")
    if not todo:
        return
    t0 = time.time()
    with ThreadPoolExecutor(10) as ex:
        for i, _ in enumerate(ex.map(safe_fetch, todo), 1):
            if i % 500 == 0:
                log(f"  {label} {i}/{len(todo)} ({time.time() - t0:.0f}s)")
    log(f"  {label} done ({time.time() - t0:.0f}s)")


def positive_mints(t):
    signer = t.get("signer")
    return {k.split("|")[1] for k, d in t["tok"].items()
            if d > 0 and k.split("|")[0] == signer and not k.endswith(WSOL)}


def platform_of(t):
    progs = t["programs"] + t["inner_programs"]
    platform = program_platform(progs)
    fee_hits, tips, other = Counter(), defaultdict(int), defaultdict(int)
    for src, dst, lam in t["transfers"]:
        if src != t["signer"]:
            continue
        p = fee_platform_of(dst)
        s = swqos_of(dst)
        if p:
            fee_hits[p] += 1
        elif s:
            tips[s] += lam
        else:
            other[dst] += lam
    if not platform and fee_hits:
        platform = fee_hits.most_common(1)[0][0]
    if not platform:
        nonplain = [p for p in t["programs"] if p not in PLAIN_PROGRAMS]
        if not nonplain:
            dex = "/".join(sorted({DEX_NAMES[p] for p in progs if p in DEX_NAMES})) or "unknown DEX"
            platform = f"direct {dex} (no platform router or known fee wallet)"
        else:
            platform = f"unknown router {nonplain[0]}"
    if "axm" in "".join(tips) and platform.startswith("direct"):
        platform = "Axiom (by private tip)"
    tip = "; ".join(f"{k} {v / 1e9:.5f}" for k, v in sorted(tips.items()))
    return platform, tip


def group_candidates(mint, items):
    """Nearest outside buys for buys that all sit within LOOKBACK_SLOTS of the newest.

    items are (tx, mint, sol), newest slot first. One walk of the mint's signatures
    covers the whole group, and transactions already in the cache are not fetched again.
    """
    oldest = items[-1][0]["slot"]
    start = items[0][0]["sig"]
    # The copy target is the nearest prior outside buy, which is within the first
    # few mint transactions. Small pages keep a hot mint from turning into a long scan.
    events, before, pages, uncached = [], start, 0, 0
    while pages < 4:
        pages += 1
        page = rpc("getSignaturesForAddress", [mint, {"before": before, "limit": 25}])
        if not page:
            break
        halt = False
        for h in page:
            if oldest - h["slot"] > LOOKBACK_SLOTS:
                halt = True
                break
            if h.get("err"):
                continue
            sig = h["signature"]
            t = CACHE.get(sig)
            if t is None:
                if uncached >= 20:
                    halt = True
                    break
                uncached += 1
                t = safe_fetch(sig)
            outside = (t and not t.get("missing") and not t.get("err")
                       and PROG not in t.get("programs", []) and mint in positive_mints(t))
            events.append((h["slot"], sig, t if outside else None))
        if not halt and events:
            # Stop as soon as every buy has a nearer-or-equal-slot outside buy behind it.
            # Waiting for the slot number to fall scans the rest of a busy slot.
            seen = {sig: i for i, (_es, sig, _etx) in enumerate(events)}

            def ready(it):
                bsig, bslot = it[0]["sig"], it[0]["slot"]
                if bsig == start:
                    begin = 0
                elif bsig not in seen:
                    return False
                else:
                    begin = seen[bsig] + 1
                for es, _esig, etx in events[begin:]:
                    if bslot - es > LOOKBACK_SLOTS:
                        return True
                    if etx is not None and es <= bslot:
                        return True
                return False

            if all(ready(it) for it in items):
                halt = True
        before = page[-1]["signature"]
        if halt or len(page) < 25:
            break
    index = {sig: i for i, (_slot, sig, _tx) in enumerate(events)}
    out = {}
    for it in items:
        sig, slot = it[0]["sig"], it[0]["slot"]
        cands = []
        for _es, _esig, etx in events[index.get(sig, -1) + 1:]:
            if slot - _es > LOOKBACK_SLOTS:
                break
            if etx is not None and _es <= slot:
                cands.append(etx)
                if len(cands) == 4:
                    break
        out[sig] = cands
    # A same-slot buy newer in signature order than the cursor was not part of the walk.
    for it in items:
        sig = it[0]["sig"]
        if sig != start and sig not in index and it[0]["slot"] == items[0][0]["slot"]:
            try:
                tgt = find_target(sig, it[0]["slot"], mint)
            except Exception as e:
                log(f"target fail {sig[:12]} {e}")
                tgt = None
            out[sig] = [tgt] if tgt else []
    return out


def find_target(buy_sig, slot, mint):
    before, scanned = buy_sig, 0
    while scanned < 200:
        page = rpc("getSignaturesForAddress", [mint, {"before": before, "limit": 50}])
        if not page:
            return None
        for h in page:
            scanned += 1
            if h["slot"] > slot:
                continue
            if slot - h["slot"] > LOOKBACK_SLOTS:
                return None
            if h.get("err"):
                continue
            t = safe_fetch(h["signature"])
            if not t or t.get("err"):
                continue
            if PROG in t["programs"]:
                continue
            if mint in positive_mints(t):
                return t
        before = page[-1]["signature"]
        if slot - page[-1]["slot"] > LOOKBACK_SLOTS:
            return None
    return None


def indexes(slot, wanted):
    try:
        sigs = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                       "maxSupportedTransactionVersion": 1}])["signatures"]
    except Exception as e:
        log(f"block {slot} {e}")
        return {}
    return {s: i for i, s in enumerate(sigs) if s in wanted}


def batch_rpc(calls):
    body = json.dumps([
        {"jsonrpc": "2.0", "id": i, "method": method, "params": params}
        for i, (method, params) in enumerate(calls)
    ]).encode()
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                out = json.loads(r.read())
            if isinstance(out, dict):
                raise RuntimeError(out.get("error"))
            by_id = {int(item["id"]): item for item in out}
            return [None if "error" in by_id.get(i, {"error": 1}) else by_id[i].get("result") for i in range(len(calls))]
        except Exception as e:
            last = e
            time.sleep(0.4 * (attempt + 1))
    log(f"batch fail {last}")
    return [None] * len(calls)


def _outside(t, mint):
    return (t and not t.get("missing") and not t.get("err")
            and PROG not in t.get("programs", []) and mint in positive_mints(t))


def resolve_batched(groups):
    """Find the nearest outside buy for every group using batched signature lookups."""
    pages = [[] for _ in groups]
    before = [g[0][0]["sig"] for g in groups]
    exhausted = [False] * len(groups)
    cands = {it[0]["sig"]: [] for g in groups for it in g}

    def walk(i):
        g = groups[i]
        mint, oldest, start = g[0][1], g[-1][0]["slot"], g[0][0]["sig"]
        events, hit_old = [], False
        for h in pages[i]:
            if oldest - h["slot"] > LOOKBACK_SLOTS:
                hit_old = True
                break
            if h.get("err"):
                continue
            t = CACHE.get(h["signature"])
            if t is None:
                _assign(g, start, events)
                return h["signature"]
            events.append((h["slot"], h["signature"], t if _outside(t, mint) else None))
        _assign(g, start, events)
        if hit_old or exhausted[i] or len(pages[i]) >= 60 or _ready(g, start, events):
            return None
        return "PAGE"

    def _assign(g, start, events):
        index = {sig: n for n, (_s, sig, _t) in enumerate(events)}
        for it in g:
            sig, slot = it[0]["sig"], it[0]["slot"]
            if sig == start:
                begin = 0
            elif sig not in index:
                continue
            else:
                begin = index[sig] + 1
            found = []
            for es, _esig, etx in events[begin:]:
                if slot - es > LOOKBACK_SLOTS:
                    break
                if etx is not None and es <= slot:
                    found.append(etx)
                    if len(found) == 4:
                        break
            if found:
                cands[sig] = found

    def _ready(g, start, events):
        index = {sig: n for n, (_s, sig, _t) in enumerate(events)}
        for it in g:
            sig, slot = it[0]["sig"], it[0]["slot"]
            if cands.get(sig):
                continue
            if sig != start and sig not in index:
                return False
            return False
        return True

    for wave in range(6):
        need = [i for i in range(len(groups)) if not exhausted[i] and len(pages[i]) < 60]
        # ask only groups that still need history: first wave all, later only PAGE
        if wave:
            need = page_need
        if not need:
            break
        log(f"  signature pages wave {wave}: {len(need)} groups")
        t0 = time.time()
        for off in range(0, len(need), 20):
            chunk = need[off:off + 20]
            calls = [("getSignaturesForAddress", [groups[i][0][1], {"before": before[i], "limit": 20}]) for i in chunk]
            for i, page in zip(chunk, batch_rpc(calls)):
                page = page or []
                pages[i].extend(page)
                if page:
                    before[i] = page[-1]["signature"]
                if len(page) < 20:
                    exhausted[i] = True
            if off and off % 2000 == 0:
                log(f"    {off}/{len(need)} ({time.time() - t0:.0f}s)")
        missing, page_need, seen = [], [], set()
        for i in range(len(groups)):
            if cands and all(cands.get(it[0]["sig"]) for it in groups[i]):
                continue
            got = walk(i)
            if got == "PAGE":
                page_need.append(i)
            elif isinstance(got, str):
                if got not in CACHE and got not in seen:
                    missing.append(got)
                    seen.add(got)
        log(f"    fetch {len(missing)} txs, {len(page_need)} groups need another page")
        fetch_many(missing, f"wave{wave}")
        if not missing and not page_need:
            break
    # one last walk now that fetches are cached
    for i in range(len(groups)):
        walk(i)
    return cands


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def analyze(wallet_fail):
    by_wallet = defaultdict(list)
    for t in CACHE.values():
        if t.get("missing") or t.get("err") or not t.get("signer"):
            continue
        if t.get("blockTime") and FETCH_START <= t["blockTime"] < END:
            by_wallet[t["signer"]].append(t)

    # Callers are wallets with at least one gate instruction in the window.
    callers = {w for w, txs in by_wallet.items()
               if any(PROG in t["programs"] and t["blockTime"] >= START for t in txs)}
    log(f"callers {len(callers)}")

    buys = []
    for w in callers:
        for t in by_wallet[w]:
            if PROG not in t["programs"] or t["blockTime"] < START:
                continue
            mints = pair_mints(t, {w})
            sol = pair_sol(t, {w})
            got = [m for m, d in mints.items() if d > 0]
            if sol < 0 and len(got) == 1:
                buys.append((t, got[0], -sol))
    groups = []
    by_mint = defaultdict(list)
    for item in buys:
        by_mint[item[1]].append(item)
    for items in by_mint.values():
        items.sort(key=lambda it: -it[0]["slot"])
        cur = []
        for it in items:
            if cur and cur[0][0]["slot"] - it[0]["slot"] > LOOKBACK_SLOTS:
                groups.append(cur)
                cur = []
            cur.append(it)
        groups.append(cur)
    log(f"gate buys {len(buys)} in {len(groups)} mint groups; resolving targets")
    cands = resolve_batched(groups)
    log(f"  targets found {sum(1 for v in cands.values() if v)}/{len(cands)}")

    wanted = defaultdict(set)
    for w in callers:
        counts = Counter(t["slot"] for t in by_wallet[w])
        for t in by_wallet[w]:
            if counts[t["slot"]] > 1:
                wanted[t["slot"]].add(t["sig"])
    for t, mint, sol in buys:
        wanted[t["slot"]].add(t["sig"])
        for tgt in cands.get(t["sig"], ()):
            wanted[tgt["slot"]].add(tgt["sig"])
    log(f"block indexes for {len(wanted)} slots")
    pos = {}
    slots = list(wanted)
    with ThreadPoolExecutor(8) as ex:
        for slot, found in ex.map(lambda s: (s, indexes(s, wanted[s])), slots):
            pos[slot] = found

    def choose(t, cand_list):
        bi = pos.get(t["slot"], {}).get(t["sig"])
        for c in cand_list:
            if c["slot"] > t["slot"] or t["slot"] - c["slot"] > LOOKBACK_SLOTS:
                continue
            if c["slot"] < t["slot"]:
                return c
            ti = pos.get(c["slot"], {}).get(c["sig"])
            if bi is None or ti is None or ti < bi:
                return c
        return None

    resolved = [(t, mint, sol, choose(t, cands.get(t["sig"], ()))) for t, mint, sol in buys]

    def ordered(txs):
        return sorted(txs, key=lambda t: (t["slot"], pos.get(t["slot"], {}).get(t["sig"], 0)))

    # FIFO profit per buy, same rules as fill_profit.py.
    lots = {}
    for w in callers:
        open_lots = defaultdict(list)
        for t in ordered(by_wallet[w]):
            mints = pair_mints(t, {w})
            if not mints:
                continue
            s = pair_sol(t, {w})
            paid = [m for m, d in mints.items() if (d < 0) == (s > 0)] or list(mints)
            for m, d in mints.items():
                share = s / len(paid) if m in paid else 0
                if d > 0:
                    if share >= 0:
                        continue
                    lot = {"tokens": d, "cost": -share, "sold": 0, "proceeds": 0.0, "sells": []}
                    open_lots[m].append(lot)
                    lots[(w, t["sig"], m)] = lot
                    continue
                left = -d
                for lot in open_lots[m]:
                    take = min(left, lot["tokens"] - lot["sold"])
                    if take <= 0:
                        continue
                    lot["sold"] += take
                    lot["proceeds"] += share * take / -d
                    lot["sells"].append(t)
                    left -= take
                    if left == 0:
                        break
                open_lots[m] = [lot for lot in open_lots[m] if lot["sold"] < lot["tokens"]]

    rows = []
    for t, mint, sol, tgt in resolved:
        w = t["signer"]
        lot = lots.get((w, t["sig"], mint))
        bi = pos.get(t["slot"], {}).get(t["sig"], "")
        if tgt is None:
            kind = "no recent target"
            tgt_wallet = tgt_tx = tgt_time = tgt_plat = ""
            tgt_slot = tgt_index = gap_slots = gap_pos = ""
            tgt_sol = ""
        else:
            tgt_slot = tgt["slot"]
            ti = pos.get(tgt["slot"], {}).get(tgt["sig"], "")
            gap_slots = t["slot"] - tgt["slot"]
            if tgt["slot"] == t["slot"] and bi != "" and ti != "":
                gap_pos = bi - ti
                kind = "backrun" if gap_pos == 1 else "copy same block"
            elif tgt["slot"] == t["slot"]:
                gap_pos = ""
                kind = "copy same block"
            else:
                gap_pos = ""
                kind = "copy later slot"
            tgt_wallet, tgt_tx = tgt["signer"], tgt["sig"]
            tgt_time = utc(tgt["blockTime"]) if tgt.get("blockTime") else ""
            tgt_plat, _ = platform_of(tgt)
            tgt_index = ti
            tgt_sol = round(-pair_sol(tgt, {tgt["signer"]}) / 1e9, 6)
        _, tip = platform_of(t)
        if lot is None:
            profit, status, sell_n, sell_sol, hold, last = "", "unmatched", 0, "", "", ""
        else:
            profit = round((lot["proceeds"] - lot["cost"]) / 1e9, 6)
            unsold = 1 - lot["sold"] / lot["tokens"]
            status = "closed" if unsold < 1e-9 else f"open at {END_LABEL} ({unsold:.0%} unsold)"
            sell_n = len({s["sig"] for s in lot["sells"]})
            sell_sol = round(lot["proceeds"] / 1e9, 6)
            hold = lot["sells"][0]["blockTime"] - t["blockTime"] if lot["sells"] else ""
            last = lot["sells"][-1]["sig"] if lot["sells"] else ""
        rows.append({
            "wallet": w, "time_utc": utc(t["blockTime"]), "slot": t["slot"], "block_index": bi,
            "tx": t["sig"], "mint": mint, "buy_sol": round(sol / 1e9, 6),
            "priority_fee_sol": round((t["fee"] - 5000 * t["n_sigs"]) / 1e9, 6),
            "tip": tip, "gate_deadline_slot": t.get("gate_slot") or "",
            "sniping_type": kind, "target_wallet": tgt_wallet, "target_tx": tgt_tx,
            "target_time_utc": tgt_time, "target_slot": tgt_slot, "target_block_index": tgt_index,
            "slots_after_target": gap_slots, "positions_after_target": gap_pos,
            "target_platform": tgt_plat, "target_buy_sol": tgt_sol,
            "sell_count": sell_n, "sell_sol": sell_sol, "hold_seconds": hold,
            "trade_profit_sol": profit, "trade_status": status, "last_sell_tx": last,
        })

    rows.sort(key=lambda r: (r["wallet"], r["slot"], r["block_index"] if r["block_index"] != "" else 0))
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def closed(rs):
        return [r for r in rs if r["trade_status"] == "closed" and r["trade_profit_sol"] != ""]

    log(f"\nwrote {len(rows)} trades to {CSV_PATH}")
    log(f"sniping {Counter(r['sniping_type'] for r in rows)}")
    all_closed = closed(rows)
    log(f"closed {len(all_closed)}/{len(rows)} profit {sum(r['trade_profit_sol'] for r in all_closed):+.3f} SOL "
        f"win {sum(1 for r in all_closed if r['trade_profit_sol'] > 0) / max(len(all_closed), 1):.1%}")
    for kind in ("backrun", "copy same block", "copy later slot", "no recent target"):
        rs = closed([r for r in rows if r["sniping_type"] == kind])
        if not rs:
            continue
        log(f"  {kind:20} n {len(rs):5d} profit {sum(r['trade_profit_sol'] for r in rs):+9.3f} "
            f"win {sum(1 for r in rs if r['trade_profit_sol'] > 0) / len(rs):.0%} "
            f"median {median([r['trade_profit_sol'] for r in rs]):+.4f} "
            f"buy {median([r['buy_sol'] for r in rs]):.3f}")
    holds = [r["hold_seconds"] for r in all_closed if r["hold_seconds"] != ""]
    if holds:
        log(f"hold seconds median {median(holds):.0f} mean {sum(holds) / len(holds):.0f}")
    log("== per wallet")
    for w in sorted(callers):
        rs = [r for r in rows if r["wallet"] == w]
        cl = closed(rs)
        kinds = Counter(r["sniping_type"] for r in rs)
        prof = sum(r["trade_profit_sol"] for r in cl)
        log(f"  {w} buys {len(rs):5d} closed {len(cl):5d} profit {prof:+9.3f} "
            f"win {sum(1 for r in cl if r['trade_profit_sol'] > 0) / max(len(cl), 1):.0%} "
            f"fail {wallet_fail.get(w, 0)} {dict(kinds)}")


def main():
    load_cache()
    prog_ok, prog_fail = signatures(PROG, START)
    log(f"program txs in window ok {len(prog_ok)} failed {prog_fail}")
    fetch_many(prog_ok, "gate")
    callers = sorted({t["signer"] for t in CACHE.values()
                      if t.get("signer") and PROG in t.get("programs", []) and t.get("blockTime")
                      and START <= t["blockTime"] < END})
    log(f"caller wallets {len(callers)}")
    open("gate_6gY1_wallets.txt", "w").write("\n".join(callers) + "\n")
    wallet_fail = {}

    def wallet_sigs(w):
        ok, failed = signatures(w, FETCH_START)
        return w, ok, failed

    extra = []
    with ThreadPoolExecutor(4) as ex:
        for w, ok, failed in ex.map(wallet_sigs, callers):
            wallet_fail[w] = failed
            extra.extend(ok)
            log(f"  {w[:8]} txs {len(ok)} failed {failed}")
    fetch_many(list(dict.fromkeys(extra)), "wallets")
    analyze(wallet_fail)
    log("DONE")


if __name__ == "__main__":
    main()

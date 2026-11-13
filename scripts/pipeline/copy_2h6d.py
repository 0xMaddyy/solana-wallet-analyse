"""Buys of copy bot 2H6Dwrq on 2026-10-16 and 2026-10-17 UTC.

Writes copy_2H6Dwrq_oct16_17.csv with the buy, its tip, the copied target,
and both transactions' positions in their slots.

Uses the public Solana RPC because the Helius key in analyze.py returns 403.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from sno.paths import RESULTS

import csv
import json
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.multi_report import WSOL, fee_platform_of, pair_mints, pair_sol, program_platform, swqos_of, PLAIN_PROGRAMS, DEX_NAMES

RPC = "https://api.mainnet-beta.solana.com"
WALLET = "2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf"
START = int(datetime(2026, 10, 16, tzinfo=timezone.utc).timestamp())
END = int(datetime(2026, 10, 18, tzinfo=timezone.utc).timestamp())
LOOKBACK = 150
CACHE = str(RESULTS / "copy_2H6Dwrq_txs.jsonl")
OUT = "copy_2H6Dwrq_oct16_17.csv"


def log(msg):
    print(msg, flush=True)


def rpc(method, params, retries=8):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except Exception as e:
            last = e
            time.sleep(0.4 * (attempt + 1))
    raise last


def fetch_tx(sig):
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
    return {
        "sig": sig, "slot": tx["slot"], "blockTime": tx["blockTime"], "err": meta["err"],
        "fee": meta["fee"], "n_sigs": len(tx["transaction"]["signatures"]), "signer": signer,
        "dsol": dsol, "tok": tok, "transfers": transfers,
        "programs": sorted({ix["programId"] for ix in msg["instructions"]}),
        "inner_programs": sorted({i["programId"] for g in meta.get("innerInstructions") or [] for i in g["instructions"]}),
    }


def signatures():
    out, before = [], None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [WALLET, opts])
        if not page:
            break
        for s in page:
            bt = s.get("blockTime") or 0
            if START <= bt < END and not s.get("err"):
                out.append(s["signature"])
        before = page[-1]["signature"]
        if (page[-1].get("blockTime") or 0) < START or len(page) < 1000:
            break
    return out


def tips_of(t):
    tips, other = defaultdict(int), defaultdict(int)
    for src, dst, lam in t["transfers"]:
        if src != t["signer"]:
            continue
        s = swqos_of(dst)
        if s:
            tips[s] += lam
        elif not fee_platform_of(dst):
            other[dst] += lam
    label = "; ".join(f"{k} {v / 1e9:.5f}" for k, v in sorted(tips.items())) or "none (priority fee only)"
    return label, sum(tips.values()) / 1e9


def platform_of(t):
    progs = t["programs"] + t["inner_programs"]
    platform = program_platform(progs)
    if not platform:
        nonplain = [p for p in t["programs"] if p not in PLAIN_PROGRAMS]
        if not nonplain:
            dex = "/".join(sorted({DEX_NAMES[p] for p in progs if p in DEX_NAMES})) or "unknown DEX"
            platform = f"direct {dex} (no platform router or known fee wallet)"
        else:
            platform = f"unknown router {nonplain[0]}"
    return platform


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def main():
    known = {}
    try:
        for line in open(CACHE, encoding="utf-8"):
            if line.strip():
                t = json.loads(line)
                known[t["sig"]] = t
    except FileNotFoundError:
        pass
    sigs = signatures()
    todo = [s for s in sigs if s not in known]
    log(f"successful txs {len(sigs)}, to fetch {len(todo)}, cached {len(known)}")
    t0 = time.time()
    def safe_fetch(sig):
        try:
            return fetch_tx(sig)
        except Exception as e:
            log(f"fetch fail {sig[:12]} {e}")
            return None

    with open(CACHE, "a", encoding="utf-8") as fh:
        with ThreadPoolExecutor(3) as ex:
            for i, t in enumerate(ex.map(safe_fetch, todo), 1):
                if t and not t.get("missing"):
                    known[t["sig"]] = t
                    fh.write(json.dumps(t) + "\n")
                    fh.flush()
                if i % 100 == 0:
                    log(f"  fetched {i}/{len(todo)} ({time.time() - t0:.0f}s)")
    if todo:
        log(f"  fetch done ({time.time() - t0:.0f}s)")

    buys = []
    for t in known.values():
        if t.get("missing") or t.get("err") or t.get("signer") != WALLET:
            continue
        if not t.get("blockTime") or not (START <= t["blockTime"] < END):
            continue
        mints = pair_mints(t, {WALLET})
        sol = pair_sol(t, {WALLET})
        got = [m for m, d in mints.items() if d > 0]
        if sol < 0 and len(got) == 1:
            buys.append((t, got[0], -sol))
    buys.sort(key=lambda b: (b[0]["slot"], b[0]["sig"]))
    log(f"buys {len(buys)}")

    def find_target(item):
        t, mint, sol = item
        before, scanned = t["sig"], 0
        while scanned < 40:
            page = rpc("getSignaturesForAddress", [mint, {"before": before, "limit": 20}])
            if not page:
                return t, mint, sol, None
            for h in page:
                scanned += 1
                if t["slot"] - h["slot"] > LOOKBACK:
                    return t, mint, sol, None
                if h.get("err"):
                    continue
                other = known.get(h["signature"])
                if other is None:
                    try:
                        other = fetch_tx(h["signature"])
                    except Exception as e:
                        log(f"target fail {h['signature'][:12]} {e}")
                        continue
                    if other and not other.get("missing"):
                        known[other["sig"]] = other
                if not other or other.get("err") or other.get("signer") == WALLET:
                    continue
                if mint in {k.split("|")[1] for k, d in other["tok"].items()
                            if d > 0 and k.split("|")[0] == other["signer"] and not k.endswith(WSOL)}:
                    return t, mint, sol, other
            before = page[-1]["signature"]
        return t, mint, sol, None

    log("resolving targets")
    t0 = time.time()
    resolved = []
    with ThreadPoolExecutor(3) as ex:
        for i, row in enumerate(ex.map(find_target, buys), 1):
            resolved.append(row)
            if i % 50 == 0:
                log(f"  targets {i}/{len(buys)} ({time.time() - t0:.0f}s)")
    # persist any target txs fetched above
    have = set()
    try:
        for line in open(CACHE, encoding="utf-8"):
            if line.strip():
                have.add(json.loads(line)["sig"])
    except FileNotFoundError:
        pass
    with open(CACHE, "a", encoding="utf-8") as fh:
        for t in known.values():
            if t["sig"] not in have and not t.get("missing"):
                fh.write(json.dumps(t) + "\n")

    wanted = defaultdict(set)
    for t, mint, sol, tgt in resolved:
        wanted[t["slot"]].add(t["sig"])
        if tgt is not None:
            wanted[tgt["slot"]].add(tgt["sig"])
    log(f"block indexes for {len(wanted)} slots")
    pos = {}

    def indexes(slot):
        try:
            sigs = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                           "maxSupportedTransactionVersion": 1}])["signatures"]
        except Exception as e:
            log(f"block {slot} {e}")
            return slot, {}
        need = wanted[slot]
        return slot, {s: i for i, s in enumerate(sigs) if s in need}

    with ThreadPoolExecutor(3) as ex:
        for slot, found in ex.map(indexes, list(wanted)):
            pos[slot] = found

    rows = []
    for t, mint, sol, tgt in resolved:
        tip, tip_sol = tips_of(t)
        bi = pos.get(t["slot"], {}).get(t["sig"], "")
        if tgt is None:
            kind = "no recent target"
            tw = ttx = ttime = tplat = ttip = ""
            tslot = tindex = gap_slots = gap_pos = tsol = ""
        else:
            ttip, _ = tips_of(tgt)
            tplat = platform_of(tgt)
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
            tw, ttx, tslot, tindex = tgt["signer"], tgt["sig"], tgt["slot"], ti
            ttime = utc(tgt["blockTime"]) if tgt.get("blockTime") else ""
            tsol = round(-pair_sol(tgt, {tgt["signer"]}) / 1e9, 6)
        rows.append({
            "time_utc": utc(t["blockTime"]),
            "slot": t["slot"],
            "bot_buy_index": bi,
            "bot_tx": t["sig"],
            "mint": mint,
            "buy_sol": round(sol / 1e9, 6),
            "priority_fee_sol": round((t["fee"] - 5000 * t["n_sigs"]) / 1e9, 6),
            "tip": tip,
            "tip_sol": round(tip_sol, 6),
            "sniping_type": kind,
            "target_wallet": tw,
            "target_tx": ttx,
            "target_time_utc": ttime,
            "target_slot": tslot,
            "target_buy_index": tindex,
            "slots_after_target": gap_slots,
            "positions_after_target": gap_pos,
            "target_platform": tplat,
            "target_buy_sol": tsol,
            "target_tip": ttip,
        })
    rows.sort(key=lambda r: (r["time_utc"], r["bot_buy_index"] if r["bot_buy_index"] != "" else 0))
    with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    log(f"wrote {len(rows)} buys to {OUT}")
    log(f"sniping {Counter(r['sniping_type'] for r in rows)}")
    log(f"tips {Counter(r['tip'].split(' ')[0] for r in rows)}")
    log(f"buy sol median {sorted(r['buy_sol'] for r in rows)[len(rows)//2]}")
    for day in ("2026-10-16", "2026-10-17"):
        n = sum(1 for r in rows if r["time_utc"].startswith(day))
        log(f"  {day} buys {n}")


if __name__ == "__main__":
    main()

"""Pump.fun and stonk.fun buys by two copy bots on 2026-10-16 and 2026-10-17 UTC.

Resumes from 2h6d_txs.jsonl. Writes 2h6d_buys_oct16_17.csv with tip, buy,
target, and both transactions' indexes in their slots.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from sno.paths import RESULTS

import csv
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sno.multi_report import WSOL, fee_platform_of, program_platform, swqos_of

RPC = __import__('os').environ.get('SNO_RPC_URL') or __import__('os').environ.get('HELIUS_RPC_URL')
if not RPC:
    raise RuntimeError('Set SNO_RPC_URL or HELIUS_RPC_URL')
WALLETS = [
    "2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf",
    "CDXzx7BRZbJEYiirxoAJ7sxpftUNpSYRcr4NFifb4raJ",
]
W = WALLETS[0]
START = int(datetime(2026, 10, 16, tzinfo=timezone.utc).timestamp())
END = int(datetime(2026, 10, 18, tzinfo=timezone.utc).timestamp())
CACHE = str(RESULTS / "2h6d_txs.jsonl")
SIGS_PATH = str(RESULTS / "2h6d_sigs.json")
BLOCK_PATH = str(RESULTS / "2h6d_blocks.jsonl")
CSV_PATH = str(RESULTS / "2h6d_buys_oct16_17.csv")
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMP_AMM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
LAB = "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"
CPMM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
STONK_ACCOUNTS = {
    "6BwHHDg3u1854jC8PDLXvR4spTcLNaoBxLJNGC4nTESt",
    "4E876qZTE9FJMrBzgVtBrSrzz2TLivB5Y5QXPjB4gZL7",
    "5CEbueQnq1Ym2uSSx2xXds3jQAqT1BDnkA59RZobSPAG",
}
LOOKBACK = 150
_write_lock = threading.Lock()


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def rpc(method, params, timeout=45):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read())
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except urllib.error.HTTPError as e:
            log(f"http {e.code}")
            time.sleep(0.6 * (attempt + 1))
        except Exception as e:
            log(f"rpc {type(e).__name__} {e}")
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(method)


def fetch_tx(sig):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    if tx is None:
        return {"sig": sig, "missing": True}
    msg, meta = tx["transaction"]["message"], tx["meta"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    signers = [k["pubkey"] for k in msg["accountKeys"] if isinstance(k, dict) and k.get("signer")]
    signer = signers[0] if signers else ""
    dsol = {}
    for w in dict.fromkeys([signer, *[a for a in WALLETS if a in keys]]):
        if w in keys:
            i = keys.index(w)
            dsol[w] = meta["postBalances"][i] - meta["preBalances"][i]
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
        "dsol": dsol, "tok": tok, "transfers": transfers, "accounts": keys,
        "programs": sorted({ix["programId"] for ix in msg["instructions"]}),
        "inner_programs": sorted({i["programId"] for g in meta.get("innerInstructions") or [] for i in g["instructions"]}),
    }


def load_cache():
    out = {}
    try:
        fh = open(CACHE, encoding="utf-8")
    except FileNotFoundError:
        return out
    for line in fh:
        if not line.strip():
            continue
        try:
            t = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(t, dict) and t.get("sig"):
            out[t["sig"]] = t
    return out


def venue_of(t):
    progs = set(t["programs"]) | set(t.get("inner_programs") or [])
    acc = set(t.get("accounts") or [])
    if PUMP in progs:
        return "pump.fun"
    if PUMP_AMM in progs:
        return "pump.fun amm"
    if LAB in progs and (acc & STONK_ACCOUNTS):
        return "stonk.fun"
    if CPMM in progs and (acc & STONK_ACCOUNTS or any(dst in STONK_ACCOUNTS for _s, dst, _l in t["transfers"])):
        return "stonk.fun graduated"
    return None


def received_mints(t, owner):
    out = []
    for k, d in t["tok"].items():
        who, mint = k.split("|")
        if who == owner and d > 0 and mint != WSOL:
            out.append(mint)
    return out


def spent_quote(t, owner, bought):
    """Token paid besides the mint that was bought. Returns (mint, ui-less raw amount)."""
    best = None
    for k, d in t["tok"].items():
        who, mint = k.split("|")
        if who == owner and d < 0 and mint not in bought:
            if best is None or d < best[1]:
                best = (mint, d)
    return best


def is_outside_buy(t, mint):
    if not t or t.get("missing") or t.get("err"):
        return False
    if not venue_of(t):
        # any buy of this mint counts as a target, even from another venue
        pass
    signer = t.get("signer")
    for k, d in t["tok"].items():
        who, m = k.split("|")
        if m == mint and who == signer and d > 0:
            return True
    return False


def load_blocks(cache):
    try:
        fh = open(BLOCK_PATH, encoding="utf-8")
    except FileNotFoundError:
        return
    for line in fh:
        if not line.strip():
            continue
        try:
            b = json.loads(line)
        except json.JSONDecodeError:
            continue
        cache[f"block:{b['slot']}"] = b["sigs"]


def block_sigs(slot, cache):
    key = f"block:{slot}"
    with _write_lock:
        hit = cache.get(key)
    if hit is not None:
        return hit
    block = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                    "maxSupportedTransactionVersion": 1}], timeout=90)
    sigs = (block or {}).get("signatures") or []
    with _write_lock:
        if key not in cache:
            cache[key] = sigs
            with open(BLOCK_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"slot": slot, "sigs": sigs}) + "\n")
        else:
            sigs = cache[key]
    return sigs


def cache_put_tx(cache, t):
    with _write_lock:
        cache[t["sig"]] = t
        with open(CACHE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(t) + "\n")


def collect_sigs():
    """Successful signatures for both wallets in [Oct 16, Oct 18) UTC."""
    found = []
    for addr in WALLETS:
        out, before = [], None
        while True:
            opts = {"limit": 1000}
            if before:
                opts["before"] = before
            page = rpc("getSignaturesForAddress", [addr, opts])
            if not page:
                break
            for s in page:
                bt = s.get("blockTime") or 0
                if START <= bt < END and not s.get("err"):
                    out.append({"signature": s["signature"], "slot": s["slot"], "blockTime": bt, "wallet": addr})
            before = page[-1]["signature"]
            oldest = page[-1].get("blockTime") or 0
            log(f"  {addr[:8]} page {len(page)} kept {len(out)} oldest {oldest}")
            if oldest < START or len(page) < 1000:
                break
        log(f"{addr[:8]} sigs {len(out)}")
        found.extend(out)
    # one sig can be on both lists; keep the first wallet
    uniq = {}
    for s in found:
        uniq.setdefault(s["signature"], s)
    sigs = list(uniq.values())
    json.dump(sigs, open(SIGS_PATH, "w"))
    log(f"signatures {len(sigs)}")
    return sigs


def fetch_all(cache):
    sigs = json.load(open(SIGS_PATH))
    wallet_of = {s["signature"]: s.get("wallet", W) for s in sigs}
    todo = [s["signature"] for s in sigs if s["signature"] not in cache]
    log(f"fetch {len(todo)} of {len(sigs)}")
    done = 0

    def one(sig):
        try:
            t = fetch_tx(sig)
        except Exception as e:
            log(f"skip {sig[:12]} {e}")
            return None
        t["wallet"] = wallet_of.get(sig, t.get("signer"))
        return t

    with open(CACHE, "a", encoding="utf-8") as fh, ThreadPoolExecutor(8) as ex:
        for t in ex.map(one, todo):
            done += 1
            if t is None:
                continue
            with _write_lock:
                cache[t["sig"]] = t
                fh.write(json.dumps(t) + "\n")
                if done % 20 == 0:
                    fh.flush()
            if done % 100 == 0:
                log(f"  {done}/{len(todo)}")
    log("fetch done")


def analyze(cache):
    buys = []
    venues = defaultdict(int)
    wallet_of = {}
    try:
        wallet_of = {s["signature"]: s.get("wallet") for s in json.load(open(SIGS_PATH))}
    except OSError:
        pass
    for t in cache.values():
        if not isinstance(t, dict) or t.get("missing") or t.get("err") or str(t.get("sig", "")).startswith("block:"):
            continue
        v = venue_of(t)
        if not v:
            continue
        owner = t.get("wallet") or wallet_of.get(t.get("sig")) or t.get("signer")
        if owner not in WALLETS:
            continue
        mints = received_mints(t, owner)
        if len(mints) != 1:
            continue
        venues[v] += 1
        buys.append((t, mints[0], v, owner))
    log(f"buys {len(buys)} {dict(venues)}")
    load_blocks(cache)

    def build_row(item):
        t, mint, venue, owner = item
        target = None
        before, scanned = t["sig"], 0
        while scanned < 40 and target is None:
            try:
                page = rpc("getSignaturesForAddress", [mint, {"before": before, "limit": 20}])
            except Exception as e:
                log(f"sigs {mint[:8]} {e}")
                break
            if not page:
                break
            for h in page:
                scanned += 1
                if t["slot"] - h["slot"] > LOOKBACK:
                    scanned = 40
                    break
                if h.get("err"):
                    continue
                with _write_lock:
                    other = cache.get(h["signature"])
                if other is None:
                    try:
                        other = fetch_tx(h["signature"])
                    except Exception as e:
                        log(f"target skip {h['signature'][:12]} {e}")
                        continue
                    cache_put_tx(cache, other)
                if is_outside_buy(other, mint) and other.get("signer") != owner:
                    target = other
                    break
            else:
                before = page[-1]["signature"]
                continue
            break
        bot_index = target_index = ""
        try:
            order = block_sigs(t["slot"], cache)
            bot_index = order.index(t["sig"])
        except Exception as e:
            log(f"block {t['slot']} {e}")
            order = []
        if target is not None and target["slot"] == t["slot"] and bot_index != "":
            try:
                if target["sig"] not in order:
                    order = block_sigs(t["slot"], cache)
                target_index = order.index(target["sig"])
                if target_index >= bot_index:
                    target = None
                    target_index = ""
            except ValueError:
                target_index = ""
        elif target is not None and target["slot"] != t["slot"]:
            try:
                target_index = block_sigs(target["slot"], cache).index(target["sig"])
            except Exception:
                target_index = ""
        tips = defaultdict(int)
        for src, dst, lam in t["transfers"]:
            if src != owner:
                continue
            name = swqos_of(dst)
            if name:
                tips[name] += lam
        quote = spent_quote(t, owner, {mint})
        sol = -t["dsol"].get(owner, t["dsol"].get(t["signer"], 0))
        row = {
            "wallet": owner,
            "time_utc": datetime.fromtimestamp(t["blockTime"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "slot": t["slot"],
            "bot_tx": t["sig"],
            "bot_buy_index": bot_index,
            "venue": venue,
            "mint": mint,
            "buy_sol": round(sol / 1e9, 6),
            "quote_mint": quote[0] if quote else "",
            "quote_amount_raw": -quote[1] if quote else "",
            "priority_fee_sol": round((t["fee"] - 5000 * t["n_sigs"]) / 1e9, 6),
            "tip": "; ".join(f"{k} {v / 1e9:.5f}" for k, v in sorted(tips.items())) or "none (priority fee only)",
            "tip_sol": round(sum(tips.values()) / 1e9, 6),
        }
        if target is None:
            row.update({
                "target_wallet": "", "target_tx": "", "target_slot": "", "target_buy_index": "",
                "slots_after_target": "", "positions_after_target": "", "target_buy_sol": "", "target_platform": "",
            })
        else:
            gap_pos = (bot_index - target_index) if bot_index != "" and target_index != "" and target["slot"] == t["slot"] else ""
            tsol = -target["dsol"].get(target["signer"], 0)
            progs = target["programs"] + target.get("inner_programs", [])
            plat = program_platform(progs) or ""
            if not plat:
                for src, dst, _lam in target["transfers"]:
                    if src == target["signer"] and fee_platform_of(dst):
                        plat = fee_platform_of(dst)
                        break
            row.update({
                "target_wallet": target["signer"],
                "target_tx": target["sig"],
                "target_slot": target["slot"],
                "target_buy_index": target_index,
                "slots_after_target": t["slot"] - target["slot"],
                "positions_after_target": gap_pos,
                "target_buy_sol": round(tsol / 1e9, 6),
                "target_platform": plat,
            })
        return row

    rows = []
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(build_row, b) for b in buys]
        for n, fut in enumerate(as_completed(futs), 1):
            rows.append(fut.result())
            if n % 10 == 0 or n == len(buys):
                log(f"  analyzed {n}/{len(buys)}")

    if not rows:
        log("no buys")
        return
    rows.sort(key=lambda r: (r["wallet"], r["time_utc"], r["bot_buy_index"] if r["bot_buy_index"] != "" else 0))
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    log(f"wrote {len(rows)} {CSV_PATH}")
    from collections import Counter
    log(f"venue {Counter(r['venue'] for r in rows)}")
    log(f"with target {sum(1 for r in rows if r['target_tx'])}")
    log(f"same slot {sum(1 for r in rows if r['positions_after_target'] != '')}")
    log(f"tip {Counter(r['tip'].split(' ')[0] for r in rows).most_common(8)}")


if __name__ == "__main__":
    cache = load_cache()
    log(f"cache {len(cache)}")
    if not (len(sys.argv) > 1 and sys.argv[1] == "analyze"):
        collect_sigs()
        fetch_all(cache)
    analyze(cache)

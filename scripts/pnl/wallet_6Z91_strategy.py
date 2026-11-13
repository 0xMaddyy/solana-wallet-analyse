"""Split 6Z91 trading P&L into token-launch sniping vs copy trading.

Rules (per buy):
  launch  – mint already had activity only within LAUNCH_SLOTS before the buy
            (or the buy is the mint's first activity). Captures create-slot snipes.
  copy    – mint activity exists older than LAUNCH_SLOTS before the buy
            (following a token that is already trading).

Daily combo USDC uses 1 SOL = SOL_USD USDC. Open lots at end are marked open.
Resumes from wallet_6Z91_trades.jsonl / wallet_6Z91_mint_age.json.
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
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sno.paths import RESULTS
from sno.analyze import rpc

WALLET = "6Z91Dgiz9E44bMW11rQuMBjt1NwwPoQGXFNZieGfVtAb"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
LAUNCH_SLOTS = 10  # ~4s; buys this soon after first mint activity = launch snipe
SOL_USD = 100.0
TRADES = "wallet_6Z91_trades.jsonl"
MINT_AGE = "wallet_6Z91_mint_age.json"
OUT_TRADES = str(RESULTS / "wallet_6Z91_strategy_trades.csv")
OUT_DAILY = str(RESULTS / "wallet_6Z91_strategy_daily.csv")
OUT_TXT = str(RESULTS / "wallet_6Z91_strategy.txt")
_lock = threading.Lock()


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def utc_day(bt):
    return datetime.fromtimestamp(bt, timezone.utc).strftime("%Y-%m-%d")


def pubkey(k):
    return k["pubkey"] if isinstance(k, dict) else k


def account_keys(item):
    msg = item["transaction"]["message"]
    keys = [pubkey(k) for k in msg["accountKeys"]]
    loaded = (item.get("meta") or {}).get("loadedAddresses") or {}
    keys += loaded.get("writable") or []
    keys += loaded.get("readonly") or []
    return keys


def token_map(balances, owner):
    out = {}
    for row in balances or []:
        if row.get("owner") == owner:
            out[row["mint"]] = out.get(row["mint"], 0) + int(row["uiTokenAmount"]["amount"])
    return out


def fetch_trades():
    """Append-only trade event cache from getTransactionsForAddress."""
    have = set()
    if os.path.exists(TRADES):
        for line in open(TRADES, encoding="utf-8"):
            if line.strip():
                have.add(json.loads(line)["sig"])
        log(f"trade cache {len(have)}")
    # Skip full rescan when cache already covers the wallet's trading history.
    if len(have) >= 20000 and os.environ.get("SNO_FORCE_FETCH") != "1":
        log("skipping fetch (cache present); set SNO_FORCE_FETCH=1 to rescan")
        return load_trades()
    token = seen = None
    pages = wrote = 0
    with open(TRADES, "a", encoding="utf-8") as fh:
        while True:
            cfg = {
                "limit": 100,
                "sortOrder": "asc",
                "transactionDetails": "full",
                "encoding": "json",
                "maxSupportedTransactionVersion": 1,
                "filters": {"status": "succeeded"},
            }
            if token:
                cfg["paginationToken"] = token
            res = rpc("getTransactionsForAddress", [WALLET, cfg])
            batch = res.get("data") or []
            pages += 1
            for item in batch:
                sig = item["transaction"]["signatures"][0]
                if sig in have:
                    continue
                meta = item["meta"]
                keys = account_keys(item)
                if WALLET not in keys:
                    continue
                idx = keys.index(WALLET)
                pre = token_map(meta.get("preTokenBalances"), WALLET)
                post = token_map(meta.get("postTokenBalances"), WALLET)
                fee = (meta.get("fee") or 0) if keys[0] == WALLET else 0
                sol_delta = meta["postBalances"][idx] - meta["preBalances"][idx]  # lamports
                wsol_delta = post.get(WSOL, 0) - pre.get(WSOL, 0)
                # SOL spent/received for trading ≈ native + wsol change + fee (fee already in native)
                quote_lamports = sol_delta + wsol_delta
                memes = []
                for m in set(pre) | set(post):
                    if m in (WSOL, USDC):
                        continue
                    d = post.get(m, 0) - pre.get(m, 0)
                    if d:
                        memes.append((m, d))
                if not memes:
                    have.add(sig)
                    continue
                row = {
                    "sig": sig,
                    "slot": item["slot"],
                    "bt": item.get("blockTime"),
                    "quote": quote_lamports,
                    "memes": memes,
                }
                fh.write(json.dumps(row) + "\n")
                have.add(sig)
                wrote += 1
            log(f"page {pages} wrote {wrote} cache {len(have)} batch {len(batch)}")
            token = res.get("paginationToken")
            if not token or len(batch) < 100 or token == seen:
                break
            seen = token
    return load_trades()


def load_trades():
    rows = []
    for line in open(TRADES, encoding="utf-8"):
        if line.strip():
            rows.append(json.loads(line))
    rows.sort(key=lambda r: (r["slot"], r["sig"]))
    return rows


def fifo(trades):
    """Return list of closed/open lots with profit in SOL."""
    open_lots = defaultdict(list)
    closed = []
    for t in trades:
        quote = t["quote"]  # lamports; buy usually negative
        memes = t["memes"]
        buys = [(m, d) for m, d in memes if d > 0]
        sells = [(m, d) for m, d in memes if d < 0]
        # split quote across buys or sells (whichever side matches sign)
        if buys and not sells:
            # cost is -quote when quote < 0
            per = quote / len(buys)
            for m, d in buys:
                lot = {
                    "mint": m, "buy_sig": t["sig"], "buy_slot": t["slot"], "buy_bt": t["bt"],
                    "tokens": d, "sold": 0, "cost_lamports": -per, "proceeds_lamports": 0.0,
                    "sell_sigs": [], "status": "open",
                }
                open_lots[m].append(lot)
        elif sells and not buys:
            per = quote / len(sells)  # usually positive
            for m, d in sells:
                left = -d
                for lot in open_lots[m]:
                    take = min(left, lot["tokens"] - lot["sold"])
                    if take <= 0:
                        continue
                    lot["sold"] += take
                    lot["proceeds_lamports"] += per * (take / -d)
                    lot["sell_sigs"].append(t["sig"])
                    lot["last_sell_bt"] = t["bt"]
                    lot["last_sell_slot"] = t["slot"]
                    left -= take
                    if lot["sold"] >= lot["tokens"]:
                        lot["status"] = "closed"
                        closed.append(lot)
                    if left == 0:
                        break
                open_lots[m] = [l for l in open_lots[m] if l["sold"] < l["tokens"]]
        else:
            # rare mixed; ignore attribution edge
            pass
    opens = [l for lots in open_lots.values() for l in lots]
    return closed, opens


def classify_mint_buy(mint, buy_sig, buy_slot, cache):
    """Return 'launch' or 'copy'. Uses signature lookback only (1 RPC)."""
    key = f"{mint}:{buy_sig}"
    with _lock:
        if key in cache:
            return cache[key]
    try:
        page = rpc("getSignaturesForAddress", [mint, {"before": buy_sig, "limit": 40}]) or []
    except Exception as e:
        log(f"mint sigs {mint[:8]} {e}")
        kind = "copy"
        with _lock:
            cache[key] = kind
        return kind
    if not page:
        kind = "launch"
    else:
        oldest = min(h["slot"] for h in page)
        kind = "launch" if buy_slot - oldest <= LAUNCH_SLOTS else "copy"
    with _lock:
        cache[key] = kind
    return kind


def classify_lots(lots):
    cache = {}
    if os.path.exists(MINT_AGE):
        cache = json.load(open(MINT_AGE, encoding="utf-8"))
        log(f"mint-age cache {len(cache)}")
    todo = lots
    log(f"classify {len(todo)} lots")

    def one(lot):
        kind = classify_mint_buy(lot["mint"], lot["buy_sig"], lot["buy_slot"], cache)
        return id(lot), kind

    done = 0
    kinds = {}
    with ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(one, l) for l in todo]
        for fut in as_completed(futs):
            lid, kind = fut.result()
            kinds[lid] = kind
            done += 1
            if done % 200 == 0:
                log(f"  classified {done}/{len(todo)}")
                with _lock:
                    json.dump(cache, open(MINT_AGE, "w", encoding="utf-8"))
    for lot in lots:
        lot["strategy"] = kinds[id(lot)]
    json.dump(cache, open(MINT_AGE, "w", encoding="utf-8"))
    return lots


def main():
    t0 = time.time()
    log("fetching trades")
    trades = fetch_trades()
    log(f"trades {len(trades)} ({time.time()-t0:.0f}s)")
    closed, opens = fifo(trades)
    log(f"lots closed {len(closed)} open {len(opens)}")
    all_lots = closed + opens
    classify_lots(all_lots)

    # write trade csv
    rows = []
    for lot in all_lots:
        profit_sol = (lot["proceeds_lamports"] - lot["cost_lamports"]) / 1e9
        # for open lots, profit is -cost (mark unrealized as cost only if no proceeds)
        if lot["status"] != "closed":
            # count only realized portion
            if lot["sold"] > 0:
                frac = lot["sold"] / lot["tokens"]
                profit_sol = (lot["proceeds_lamports"] - lot["cost_lamports"] * frac) / 1e9
            else:
                profit_sol = 0.0  # fully open: exclude from daily until sold
        day = utc_day(lot["buy_bt"]) if lot.get("buy_bt") else ""
        rows.append({
            "day": day,
            "strategy": lot["strategy"],
            "status": lot["status"],
            "mint": lot["mint"],
            "buy_sig": lot["buy_sig"],
            "buy_slot": lot["buy_slot"],
            "buy_sol": round(lot["cost_lamports"] / 1e9, 6),
            "sell_sol": round(lot["proceeds_lamports"] / 1e9, 6),
            "profit_sol": round(profit_sol, 6),
            "tokens": lot["tokens"],
            "sold": lot["sold"],
        })
    with open(OUT_TRADES, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # daily: only realized profit (closed + partial)
    daily = defaultdict(lambda: {
        "launch_sol": 0.0, "copy_sol": 0.0,
        "launch_n": 0, "copy_n": 0,
        "launch_open_n": 0, "copy_open_n": 0,
    })
    for r in rows:
        if not r["day"]:
            continue
        d = daily[r["day"]]
        key = r["strategy"]
        if r["status"] == "closed" or r["sold"] > 0:
            d[f"{key}_sol"] += r["profit_sol"]
            d[f"{key}_n"] += 1
        else:
            d[f"{key}_open_n"] += 1

    out_daily = []
    tot_l = tot_c = 0.0
    lines = [
        f"wallet {WALLET}",
        f"LAUNCH_SLOTS={LAUNCH_SLOTS}  SOL_USD={SOL_USD}",
        f"lots closed {len(closed)} open {len(opens)}",
        "",
        f"{'day':<12} {'launch_SOL':>12} {'copy_SOL':>12} {'launch_USDC':>12} {'copy_USDC':>12} "
        f"{'total_USDC':>12} {'n_launch':>8} {'n_copy':>8}",
    ]
    for day in sorted(daily):
        x = daily[day]
        lu = x["launch_sol"] * SOL_USD
        cu = x["copy_sol"] * SOL_USD
        tot_l += x["launch_sol"]
        tot_c += x["copy_sol"]
        lines.append(
            f"{day:<12} {x['launch_sol']:+12.4f} {x['copy_sol']:+12.4f} {lu:+12.2f} {cu:+12.2f} "
            f"{lu+cu:+12.2f} {x['launch_n']:8d} {x['copy_n']:8d}"
        )
        out_daily.append({
            "day": day,
            "launch_profit_sol": round(x["launch_sol"], 6),
            "copy_profit_sol": round(x["copy_sol"], 6),
            "launch_profit_usdc": round(lu, 2),
            "copy_profit_usdc": round(cu, 2),
            "total_profit_usdc": round(lu + cu, 2),
            "launch_trades": x["launch_n"],
            "copy_trades": x["copy_n"],
            "launch_open": x["launch_open_n"],
            "copy_open": x["copy_open_n"],
        })
    lines += [
        "",
        f"TOTAL launch {tot_l:+.4f} SOL = {tot_l*SOL_USD:+.2f} USDC",
        f"TOTAL copy   {tot_c:+.4f} SOL = {tot_c*SOL_USD:+.2f} USDC",
        f"TOTAL both   {tot_l+tot_c:+.4f} SOL = {(tot_l+tot_c)*SOL_USD:+.2f} USDC",
        f"elapsed {time.time()-t0:.0f}s",
    ]
    text = "\n".join(lines) + "\n"
    open(OUT_TXT, "w", encoding="utf-8").write(text)
    with open(OUT_DAILY, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_daily[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(out_daily)
    print(text)
    log(f"wrote {OUT_TRADES} {OUT_DAILY} {OUT_TXT}")


if __name__ == "__main__":
    main()

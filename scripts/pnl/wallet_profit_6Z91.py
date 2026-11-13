"""Daily net profit of 6Z91 via SOL/WSOL/USDC deposits vs withdrawals, first funding -> now."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import defaultdict
from datetime import datetime, timezone

from sno.paths import RESULTS
from sno.analyze import rpc

WALLET = "6Z91Dgiz9E44bMW11rQuMBjt1NwwPoQGXFNZieGfVtAb"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
END = int(datetime.now(timezone.utc).timestamp()) + 60
DUST_SOL = 1e-6
DUST_USDC = 1e-4
PLAIN = {
    "ComputeBudget111111111111111111111111111111",
    "11111111111111111111111111111111",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
    "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
    "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo",
}
OUT_DAILY = str(RESULTS / "wallet_6Z91_daily.csv")
OUT_FLOWS = str(RESULTS / "wallet_6Z91_flows.csv")
OUT_TXT = str(RESULTS / "wallet_6Z91_profit.txt")


def pubkey(k):
    return k["pubkey"] if isinstance(k, dict) else k


def account_keys(item):
    msg = item["transaction"]["message"]
    keys = [pubkey(k) for k in msg["accountKeys"]]
    loaded = (item.get("meta") or {}).get("loadedAddresses") or {}
    keys += loaded.get("writable") or []
    keys += loaded.get("readonly") or []
    return keys


def token_deltas(meta, owner):
    pre, post = {}, {}
    for row in meta.get("preTokenBalances") or []:
        if row.get("owner") == owner:
            pre[row["mint"]] = pre.get(row["mint"], 0) + int(row["uiTokenAmount"]["amount"])
    for row in meta.get("postTokenBalances") or []:
        if row.get("owner") == owner:
            post[row["mint"]] = post.get(row["mint"], 0) + int(row["uiTokenAmount"]["amount"])
    out = {}
    for mint in set(pre) | set(post):
        delta = post.get(mint, 0) - pre.get(mint, 0)
        if delta:
            out[mint] = delta
    return pre, post, out


def day_of(bt):
    return datetime.fromtimestamp(bt, timezone.utc).strftime("%Y-%m-%d")


def main():
    trades = funding = pages = scanned = 0
    first_time = last_time = None
    start_sol = start_wsol = start_usdc = None
    end_sol = end_wsol = end_usdc = None
    events = []
    # per day: sol_in, sol_out, wsol_in, wsol_out, usdc_in, usdc_out,
    #          day_open_sol, day_close_sol, day_open_usdc, day_close_usdc (SOL+WSOL combined for open/close)
    daily = defaultdict(lambda: {
        "sol_in": 0.0, "sol_out": 0.0, "wsol_in": 0.0, "wsol_out": 0.0,
        "usdc_in": 0.0, "usdc_out": 0.0,
        "open_sol": None, "close_sol": None, "open_usdc": None, "close_usdc": None,
    })
    token = None
    seen = None
    while True:
        cfg = {
            "limit": 100,
            "sortOrder": "asc",
            "transactionDetails": "full",
            "encoding": "json",
            "maxSupportedTransactionVersion": 1,
            "filters": {"status": "succeeded", "blockTime": {"lt": END}},
        }
        if token:
            cfg["paginationToken"] = token
        res = rpc("getTransactionsForAddress", [WALLET, cfg])
        batch = res.get("data") or []
        pages += 1
        scanned += len(batch)
        for item in batch:
            meta = item.get("meta") or {}
            keys = account_keys(item)
            if WALLET not in keys:
                continue
            idx = keys.index(WALLET)
            pre_sol = meta["preBalances"][idx] / 1e9
            post_sol = meta["postBalances"][idx] / 1e9
            pre_tok, post_tok, deltas = token_deltas(meta, WALLET)
            bt = item.get("blockTime")
            if bt is None:
                continue
            d = day_of(bt)
            sol_now_pre = pre_sol + pre_tok.get(WSOL, 0) / 1e9
            sol_now_post = post_sol + post_tok.get(WSOL, 0) / 1e9
            usdc_pre = pre_tok.get(USDC, 0) / 1e6
            usdc_post = post_tok.get(USDC, 0) / 1e6
            if daily[d]["open_sol"] is None:
                daily[d]["open_sol"] = sol_now_pre
                daily[d]["open_usdc"] = usdc_pre
            daily[d]["close_sol"] = sol_now_post
            daily[d]["close_usdc"] = usdc_post
            if start_sol is None:
                start_sol = pre_sol
                start_wsol = pre_tok.get(WSOL, 0) / 1e9
                start_usdc = usdc_pre
                first_time = bt
            end_sol = post_sol
            end_wsol = post_tok.get(WSOL, 0) / 1e9
            end_usdc = usdc_post
            last_time = bt
            other = [m for m in deltas if m not in (WSOL, USDC)]
            prog_ids = []
            msg = item["transaction"]["message"]
            for ix in msg["instructions"]:
                if "programIdIndex" in ix and ix["programIdIndex"] < len(keys):
                    prog_ids.append(keys[ix["programIdIndex"]])
            for grp in meta.get("innerInstructions") or []:
                for ix in grp.get("instructions") or []:
                    if "programIdIndex" in ix and ix["programIdIndex"] < len(keys):
                        prog_ids.append(keys[ix["programIdIndex"]])
            if other or any(p not in PLAIN for p in prog_ids):
                trades += 1
                continue
            fee_payer = keys[0] if keys else None
            fee = (meta.get("fee") or 0) / 1e9 if fee_payer == WALLET else 0.0
            sol_delta = post_sol - pre_sol
            wsol_delta = deltas.get(WSOL, 0) / 1e9
            usdc_delta = deltas.get(USDC, 0) / 1e6
            ext_sol = sol_delta + fee
            ext_wsol = wsol_delta
            if ext_sol < 0 and ext_wsol > 0:
                cancel = min(-ext_sol, ext_wsol)
                ext_sol += cancel
                ext_wsol -= cancel
            elif ext_sol > 0 and ext_wsol < 0:
                cancel = min(ext_sol, -ext_wsol)
                ext_sol -= cancel
                ext_wsol += cancel
            quote_sol = ext_sol + ext_wsol
            if abs(quote_sol) > DUST_SOL and abs(usdc_delta) > DUST_USDC and quote_sol * usdc_delta < 0:
                trades += 1
                continue
            funding += 1
            sig = item["transaction"]["signatures"][0]
            when = datetime.fromtimestamp(bt, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if ext_sol > DUST_SOL:
                daily[d]["sol_in"] += ext_sol
                events.append((when, "deposit", "SOL", round(ext_sol, 6), sig))
            elif ext_sol < -DUST_SOL:
                daily[d]["sol_out"] += -ext_sol
                events.append((when, "withdraw", "SOL", round(-ext_sol, 6), sig))
            if ext_wsol > DUST_SOL:
                daily[d]["wsol_in"] += ext_wsol
                events.append((when, "deposit", "WSOL", round(ext_wsol, 6), sig))
            elif ext_wsol < -DUST_SOL:
                daily[d]["wsol_out"] += -ext_wsol
                events.append((when, "withdraw", "WSOL", round(-ext_wsol, 6), sig))
            if usdc_delta > DUST_USDC:
                daily[d]["usdc_in"] += usdc_delta
                events.append((when, "deposit", "USDC", round(usdc_delta, 4), sig))
            elif usdc_delta < -DUST_USDC:
                daily[d]["usdc_out"] += -usdc_delta
                events.append((when, "withdraw", "USDC", round(-usdc_delta, 4), sig))
        print(f"page {pages} scanned {scanned} trades {trades} funding {funding}", flush=True)
        token = res.get("paginationToken")
        if not token or len(batch) < 100 or token == seen:
            break
        seen = token

    start_sol = start_sol or 0
    start_wsol = start_wsol or 0
    start_usdc = start_usdc or 0
    end_sol = end_sol or 0
    end_wsol = end_wsol or 0
    end_usdc = end_usdc or 0

    rows = []
    tot_sol_in = tot_sol_out = tot_usdc_in = tot_usdc_out = 0.0
    tot_sol_profit = tot_usdc_profit = 0.0
    for d in sorted(daily):
        x = daily[d]
        sol_in = x["sol_in"] + x["wsol_in"]
        sol_out = x["sol_out"] + x["wsol_out"]
        usdc_in, usdc_out = x["usdc_in"], x["usdc_out"]
        open_sol = x["open_sol"] or 0
        close_sol = x["close_sol"] or 0
        open_usdc = x["open_usdc"] or 0
        close_usdc = x["close_usdc"] or 0
        # profit = bal change + withdrawn - deposited
        sol_profit = (close_sol - open_sol) + sol_out - sol_in
        usdc_profit = (close_usdc - open_usdc) + usdc_out - usdc_in
        tot_sol_in += sol_in
        tot_sol_out += sol_out
        tot_usdc_in += usdc_in
        tot_usdc_out += usdc_out
        tot_sol_profit += sol_profit
        tot_usdc_profit += usdc_profit
        rows.append({
            "day": d,
            "sol_deposited": round(sol_in, 6),
            "sol_withdrawn": round(sol_out, 6),
            "sol_deposit_minus_withdraw": round(sol_in - sol_out, 6),
            "sol_profit": round(sol_profit, 6),
            "usdc_deposited": round(usdc_in, 4),
            "usdc_withdrawn": round(usdc_out, 4),
            "usdc_deposit_minus_withdraw": round(usdc_in - usdc_out, 4),
            "usdc_profit": round(usdc_profit, 4),
            "open_sol": round(open_sol, 6),
            "close_sol": round(close_sol, 6),
            "open_usdc": round(open_usdc, 4),
            "close_usdc": round(close_usdc, 4),
        })

    overall_sol = (end_sol - start_sol) + (end_wsol - start_wsol) + tot_sol_out - tot_sol_in
    overall_usdc = (end_usdc - start_usdc) + tot_usdc_out - tot_usdc_in
    lines = [
        f"wallet {WALLET}",
        f"first funding/activity {datetime.fromtimestamp(first_time, timezone.utc) if first_time else None}",
        f"last {datetime.fromtimestamp(last_time, timezone.utc) if last_time else None}",
        f"scanned {scanned} trades {trades} funding {funding} days {len(rows)}",
        f"start SOL {start_sol + start_wsol:.6f} USDC {start_usdc:.4f}",
        f"end   SOL {end_sol + end_wsol:.6f} USDC {end_usdc:.4f}",
        f"SOL  deposited {tot_sol_in:.6f}  withdrawn {tot_sol_out:.6f}  deposit-withdraw {tot_sol_in - tot_sol_out:.6f}",
        f"USDC deposited {tot_usdc_in:.4f}  withdrawn {tot_usdc_out:.4f}  deposit-withdraw {tot_usdc_in - tot_usdc_out:.4f}",
        f"SOL+WSOL profit (incl. bal) {overall_sol:.6f}  sum daily {tot_sol_profit:.6f}",
        f"USDC profit (incl. bal) {overall_usdc:.4f}  sum daily {tot_usdc_profit:.4f}",
        "",
        "day  sol_in  sol_out  sol_profit  usdc_in  usdc_out  usdc_profit",
    ]
    for r in rows:
        lines.append(
            f"{r['day']}  {r['sol_deposited']:.6f}  {r['sol_withdrawn']:.6f}  {r['sol_profit']:+.6f}  "
            f"{r['usdc_deposited']:.4f}  {r['usdc_withdrawn']:.4f}  {r['usdc_profit']:+.4f}"
        )
    print("\n".join(lines), flush=True)
    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(OUT_FLOWS, "w", encoding="utf-8") as fh:
        fh.write("time,kind,asset,amount,signature\n")
        for row in events:
            fh.write(",".join(map(str, row)) + "\n")
    import csv
    with open(OUT_DAILY, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [
            "day", "sol_deposited", "sol_withdrawn", "sol_deposit_minus_withdraw", "sol_profit",
            "usdc_deposited", "usdc_withdrawn", "usdc_deposit_minus_withdraw", "usdc_profit",
            "open_sol", "close_sol", "open_usdc", "close_usdc",
        ], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()

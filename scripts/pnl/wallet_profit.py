"""Net profit of 8HFagt from SOL, WSOL and USDC deposits vs withdrawals.

A deposit or withdrawal is a successful transaction in which the wallet's only
balance changes are SOL, WSOL and USDC. Swaps that move any other token are
trades, not funding. Wrapping SOL cancels out. The fee is not a withdrawal.

Profit = (ending balance - starting balance) + withdrawals - deposits.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from datetime import datetime, timezone

from sno.analyze import rpc

WALLET = "8HFagtU2YAGxhWRPuFQ9Jrj5K387vQpUUTB7goHpump"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
START = int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp())
END = int(datetime(2026, 10, 21, tzinfo=timezone.utc).timestamp())
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


def main():
    sol_in = sol_out = wsol_in = wsol_out = usdc_in = usdc_out = 0.0
    trades = funding = pages = scanned = 0
    start_sol = start_wsol = start_usdc = None
    end_sol = end_wsol = end_usdc = None
    first_time = last_time = None
    events = []
    token = None
    seen = None
    while True:
        cfg = {
            "limit": 100,
            "sortOrder": "asc",
            "transactionDetails": "full",
            "encoding": "json",
            "maxSupportedTransactionVersion": 1,
            "filters": {"status": "succeeded", "blockTime": {"gte": START, "lt": END}},
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
            if start_sol is None:
                start_sol = pre_sol
                start_wsol = pre_tok.get(WSOL, 0) / 1e9
                start_usdc = pre_tok.get(USDC, 0) / 1e6
                first_time = bt
            end_sol = post_sol
            end_wsol = post_tok.get(WSOL, 0) / 1e9
            end_usdc = post_tok.get(USDC, 0) / 1e6
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
            header = item["transaction"]["message"].get("header") or {}
            nsig = header.get("numRequiredSignatures", 1)
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
                sol_in += ext_sol
                events.append((when, "deposit", "SOL", round(ext_sol, 6), sig))
            elif ext_sol < -DUST_SOL:
                sol_out += -ext_sol
                events.append((when, "withdraw", "SOL", round(-ext_sol, 6), sig))
            if ext_wsol > DUST_SOL:
                wsol_in += ext_wsol
                events.append((when, "deposit", "WSOL", round(ext_wsol, 6), sig))
            elif ext_wsol < -DUST_SOL:
                wsol_out += -ext_wsol
                events.append((when, "withdraw", "WSOL", round(-ext_wsol, 6), sig))
            if usdc_delta > DUST_USDC:
                usdc_in += usdc_delta
                events.append((when, "deposit", "USDC", round(usdc_delta, 4), sig))
            elif usdc_delta < -DUST_USDC:
                usdc_out += -usdc_delta
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
    sol_profit = (end_sol - start_sol) + (end_wsol - start_wsol) + (sol_out + wsol_out) - (sol_in + wsol_in)
    usdc_profit = (end_usdc - start_usdc) + usdc_out - usdc_in
    lines = [
        f"window 2026-06-01 .. 2026-10-20 UTC",
        f"first {datetime.fromtimestamp(first_time, timezone.utc) if first_time else None}",
        f"last {datetime.fromtimestamp(last_time, timezone.utc) if last_time else None}",
        f"scanned {scanned} trades {trades} funding {funding}",
        f"start SOL {start_sol:.6f} WSOL {start_wsol:.6f} USDC {start_usdc:.4f}",
        f"end   SOL {end_sol:.6f} WSOL {end_wsol:.6f} USDC {end_usdc:.4f}",
        f"SOL  in {sol_in:.6f} out {sol_out:.6f}",
        f"WSOL in {wsol_in:.6f} out {wsol_out:.6f}",
        f"USDC in {usdc_in:.4f} out {usdc_out:.4f}",
        f"SOL+WSOL profit {sol_profit:.6f}",
        f"USDC profit {usdc_profit:.4f}",
    ]
    print("\n".join(lines), flush=True)
    with open("wallet_8HFa_flows.csv", "w", encoding="utf-8") as fh:
        fh.write("time,kind,asset,amount,signature\n")
        for row in events:
            fh.write(",".join(map(str, row)) + "\n")
    with open("wallet_8HFa_profit.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

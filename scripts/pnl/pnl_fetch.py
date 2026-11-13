import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.analyze import rpc

WALLETS = ["8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF", "HZUCsc7pThddRkSW8CyBfvHo4ZskrHMsg7uK46Mk1nS7"]
START = int(datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc).timestamp())
END = int(datetime(2026, 10, 9, 4, 0, tzinfo=timezone.utc).timestamp())
WSOL = "So11111111111111111111111111111111111111112"
OUT = "pnl_txs.jsonl"


def signatures(addr):
    out, before = [], None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [addr, opts])
        if not page:
            break
        out += [s for s in page if s.get("blockTime") and START <= s["blockTime"] < END]
        before = page[-1]["signature"]
        oldest = page[-1].get("blockTime") or END
        print(f"{addr[:6]} paged to {datetime.fromtimestamp(oldest, timezone.utc)} ({len(out)} in range)", file=sys.stderr)
        if oldest < START:
            break
    return out


def record(sig):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    if tx is None:
        return {"sig": sig, "missing": True}
    msg, meta = tx["transaction"]["message"], tx["meta"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    signers = [k["pubkey"] for k in msg["accountKeys"] if isinstance(k, dict) and k.get("signer")]
    dsol = {w: meta["postBalances"][keys.index(w)] - meta["preBalances"][keys.index(w)] for w in WALLETS if w in keys}

    def bal(lst):
        out = {}
        for b in lst or []:
            out[(b["accountIndex"], b["mint"], b.get("owner"))] = int(b["uiTokenAmount"]["amount"])
        return out

    pre, post = bal(meta.get("preTokenBalances")), bal(meta.get("postTokenBalances"))
    tok = {}
    for k in set(pre) | set(post):
        d = post.get(k, 0) - pre.get(k, 0)
        if d:
            owner_mint = f"{k[2]}|{k[1]}"
            tok[owner_mint] = tok.get(owner_mint, 0) + d

    transfers = []
    for ix in msg["instructions"] + [i for inner in meta.get("innerInstructions") or [] for i in inner["instructions"]]:
        p = ix.get("parsed")
        if isinstance(p, dict) and ix.get("program") == "system" and p.get("type") == "transfer":
            transfers.append([p["info"]["source"], p["info"]["destination"], p["info"]["lamports"]])

    return {
        "sig": sig, "slot": tx["slot"], "blockTime": tx["blockTime"], "err": meta["err"], "fee": meta["fee"],
        "signers": signers, "dsol": dsol, "tok": tok, "transfers": transfers,
        "programs": sorted({ix["programId"] for ix in msg["instructions"]}),
    }


def main():
    sigs = {}
    for w in WALLETS:
        for s in signatures(w):
            sigs[s["signature"]] = s
    print(f"unique txs in range: {len(sigs)}", file=sys.stderr)

    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["sig"] for l in open(OUT)}
    todo = [s for s in sigs if s not in done]
    print(f"to fetch: {len(todo)}", file=sys.stderr)

    t0 = time.time()
    with open(OUT, "a") as f, ThreadPoolExecutor(10) as ex:
        for i, r in enumerate(ex.map(record, todo), 1):
            f.write(json.dumps(r) + "\n")
            if i % 250 == 0:
                print(f"fetched {i}/{len(todo)} ({time.time() - t0:.0f}s)", file=sys.stderr)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()

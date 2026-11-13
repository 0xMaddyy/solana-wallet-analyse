import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.analyze import rpc
from sno.paths import RESULTS, WALLETS, wallet_file

PAIRS = [
    ("3pDHoZBjQhAf9w5zTWsVyys7NxiQdewbjj6jnZcKP9ya", "C8qCb6smwarmisb89kUejVsd8uHHj96AXWT2Ex1XD33i"),
    ("2PAijCsZGAmG8tVgrAmwyGC5UcXxwktYkAiy57CAXTuy", "Bj5PgdHXkZT4bw7YxQXuBeSbjfqqHgMoZAsDxdaYzGSt"),
    ("5qsuh6KapqaF6WdhdvqBKF8JiQxVmnXD7Uqr8D36iePp", "FzwbhYksjD9JJTFwZozcQQmXMKDCmY1uMz71daBAoMsy"),
    ("DTGbH68GcJujkim2BfGG7nHUv5Sox4GBJKsdDRKutANm", "Fa9qPovB2gxs67eCxWM9KheYJH9BgyPjGBqj8cL1bLRG"),
    ("CH7GewnUqV8pdnjywGz71QVFRZ549BsDqNnpBxhzREQk", "EKn5wiBAQ2UuMTAK94gPmqFabVSMCxWtzHRKxRqMYzP7"),
    ("8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF", "HZUCsc7pThddRkSW8CyBfvHo4ZskrHMsg7uK46Mk1nS7"),
]
# SNO_DAY=YYYY-MM-DD analyzes another UTC day; SNO_WALLETS=<file> replaces PAIRS with lines
# "buyer[,seller]" (a single wallet that buys and sells itself is its own seller).
DAY = os.environ.get("SNO_DAY", "2026-10-08")
if os.environ.get("SNO_WALLETS"):
    PAIRS = []
    for line in open(os.environ["SNO_WALLETS"] if os.path.isabs(os.environ["SNO_WALLETS"]) else str(WALLETS / os.environ["SNO_WALLETS"])):
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if parts:
            PAIRS.append((parts[0], parts[-1]))
START = int(datetime.strptime(DAY, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
BUY_END = START + 86400
END = BUY_END + 4 * 3600
TAG = os.environ.get("SNO_TAG") or (f"oct{int(DAY[8:])}" if DAY[5:7] == "10" else DAY)
CSV = str(RESULTS / f"backruns_{TAG}.csv")
END_LABEL = datetime.fromtimestamp(END, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def out_path(buyer):
    name = f"multi_{buyer[:8]}.jsonl" if DAY == "2026-10-08" else f"multi_{TAG}_{buyer[:8]}.jsonl"
    return str(RESULTS / name)


def signatures(addr):
    out, before = [], None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [addr, opts])
        if not page:
            break
        out += [s for s in page if s.get("blockTime") and START <= s["blockTime"] < END and not s.get("err")]
        before = page[-1]["signature"]
        if (page[-1].get("blockTime") or END) < START:
            break
    return out


def record(sig, wallets):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    if tx is None:
        return {"sig": sig, "missing": True}
    msg, meta = tx["transaction"]["message"], tx["meta"]
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    signers = [k["pubkey"] for k in msg["accountKeys"] if isinstance(k, dict) and k.get("signer")]
    dsol = {w: meta["postBalances"][keys.index(w)] - meta["preBalances"][keys.index(w)] for w in wallets if w in keys}
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
        "sig": sig, "slot": tx["slot"], "blockTime": tx["blockTime"], "err": meta["err"], "fee": meta["fee"],
        "n_sigs": len(tx["transaction"]["signatures"]), "signers": signers, "dsol": dsol, "tok": tok,
        "transfers": transfers, "programs": sorted({ix["programId"] for ix in msg["instructions"]}),
        "inner_programs": sorted({i["programId"] for g in meta.get("innerInstructions") or [] for i in g["instructions"]}),
        "accounts": keys,
    }


def fetch_pair(buyer, seller):
    path = out_path(buyer)
    sigs = {}
    for w in dict.fromkeys((buyer, seller)):
        for s in signatures(w):
            sigs[s["signature"]] = s
    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["sig"])
            except (json.JSONDecodeError, KeyError):
                continue
    todo = [s for s in sigs if s not in done]
    print(f"{buyer[:8]}: {len(sigs)} txs in window, {len(todo)} to fetch", file=sys.stderr, flush=True)
    t0 = time.time()
    with open(path, "a") as f, ThreadPoolExecutor(6) as ex:
        for i, r in enumerate(ex.map(lambda s: record(s, [buyer, seller]), todo), 1):
            f.write(json.dumps(r) + "\n")
            if i % 500 == 0:
                print(f"  {buyer[:8]} {i}/{len(todo)} ({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda p: fetch_pair(*p), PAIRS))
    print("ALL DONE", file=sys.stderr, flush=True)

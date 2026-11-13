"""Sample recent 6Z91 txs: buy/sell counts, programs, create-in-tx."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from sno.analyze import rpc, get_tx

WALLET = "6Z91Dgiz9E44bMW11rQuMBjt1NwwPoQGXFNZieGfVtAb"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
# pump create discriminators (idl): create, create_v2
CREATE_DISCS = {
    bytes([24, 30, 200, 40, 5, 28, 7, 119]),  # create
    bytes([214, 144, 76, 236, 118, 12, 70, 247]),  # maybe create_v2 guess; also check logs
}


def keys_of(tx):
    msg = tx["transaction"]["message"]
    ks = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    loaded = (tx.get("meta") or {}).get("loadedAddresses") or {}
    ks += loaded.get("writable") or []
    ks += loaded.get("readonly") or []
    return ks


def progs(tx):
    msg = tx["transaction"]["message"]
    ks = keys_of(tx)
    out = set()
    for ix in msg.get("instructions") or []:
        if "programId" in ix:
            out.add(ix["programId"])
        elif "programIdIndex" in ix:
            out.add(ks[ix["programIdIndex"]])
    for inner in (tx.get("meta") or {}).get("innerInstructions") or []:
        for ix in inner.get("instructions") or []:
            if "programId" in ix:
                out.add(ix["programId"])
            elif "programIdIndex" in ix:
                out.add(ks[ix["programIdIndex"]])
    return out


def token_deltas(meta, owner):
    pre, post = {}, {}
    for row in meta.get("preTokenBalances") or []:
        if row.get("owner") == owner:
            pre[row["mint"]] = pre.get(row["mint"], 0) + int(row["uiTokenAmount"]["amount"])
    for row in meta.get("postTokenBalances") or []:
        if row.get("owner") == owner:
            post[row["mint"]] = post.get(row["mint"], 0) + int(row["uiTokenAmount"]["amount"])
    return {m: post.get(m, 0) - pre.get(m, 0) for m in set(pre) | set(post)
            if post.get(m, 0) - pre.get(m, 0)}


def has_create(tx):
    logs = "\n".join((tx.get("meta") or {}).get("logMessages") or [])
    if "Instruction: Create" in logs or "Instruction: CreateV2" in logs:
        return True
    # also check pump ix data
    msg = tx["transaction"]["message"]
    ks = keys_of(tx)
    for ix in msg.get("instructions") or []:
        pid = ix.get("programId") or (ks[ix["programIdIndex"]] if "programIdIndex" in ix else None)
        if pid != PUMP:
            continue
        data = ix.get("data")
        if not data:
            continue
        # base58 raw in json encoding sometimes; skip if not parseable
    return False


res = rpc("getTransactionsForAddress", [WALLET, {
    "limit": 50,
    "sortOrder": "desc",
    "transactionDetails": "full",
    "encoding": "json",
    "maxSupportedTransactionVersion": 1,
    "filters": {"status": "succeeded"},
}])
batch = res.get("data") or []
kinds = Counter()
prog_top = Counter()
samples = []
for item in batch:
    meta = item.get("meta") or {}
    d = token_deltas(meta, WALLET)
    memes = {m: v for m, v in d.items() if m not in (WSOL, USDC)}
    buy = any(v > 0 for v in memes.values())
    sell = any(v < 0 for v in memes.values())
    ps = progs(item)
    create = has_create(item)
    kind = "buy+create" if buy and create else ("buy" if buy else ("sell" if sell else "other"))
    kinds[kind] += 1
    for p in ps:
        prog_top[p] += 1
    if len(samples) < 8 and (buy or sell):
        mint = next(iter(memes), "")
        samples.append((kind, item.get("signature", "")[:20], mint[:12], sorted(ps)[:4]))

print("kinds", dict(kinds))
print("top programs")
for p, n in prog_top.most_common(12):
    print(f"  {n:3d} {p}")
print("samples")
for s in samples:
    print(" ", s)

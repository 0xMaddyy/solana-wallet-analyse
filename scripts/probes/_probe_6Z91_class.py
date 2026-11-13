"""Classify a handful of recent 6Z91 buys as launch vs copy."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sno.analyze import rpc, get_tx

WALLET = "6Z91Dgiz9E44bMW11rQuMBjt1NwwPoQGXFNZieGfVtAb"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
LOOKBACK = 150


def keys_of(tx):
    msg = tx["transaction"]["message"]
    ks = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    loaded = (tx.get("meta") or {}).get("loadedAddresses") or {}
    return ks + (loaded.get("writable") or []) + (loaded.get("readonly") or [])


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


def signer_of(tx):
    for k in tx["transaction"]["message"]["accountKeys"]:
        if isinstance(k, dict) and k.get("signer"):
            return k["pubkey"]
    return keys_of(tx)[0]


def logs_create(tx):
    logs = "\n".join((tx.get("meta") or {}).get("logMessages") or [])
    return ("Instruction: Create" in logs) or ("Instruction: CreateV2" in logs)


res = rpc("getTransactionsForAddress", [WALLET, {
    "limit": 100,
    "sortOrder": "desc",
    "transactionDetails": "full",
    "encoding": "jsonParsed",
    "maxSupportedTransactionVersion": 1,
    "filters": {"status": "succeeded"},
}])
buys = []
for item in res.get("data") or []:
    d = token_deltas(item["meta"], WALLET)
    memes = {m: v for m, v in d.items() if m not in (WSOL, USDC) and v > 0}
    if not memes:
        continue
    mint = max(memes, key=lambda m: memes[m])
    buys.append({
        "sig": item.get("signature") or item.get("transaction", {}).get("signatures", [""])[0],
        "slot": item["slot"],
        "mint": mint,
        "bt": item.get("blockTime"),
        "create_in_tx": logs_create(item),
    })
    if len(buys) >= 12:
        break

print(f"buys sampled {len(buys)}")
for b in buys:
    # earliest mint sigs: last page of getSignaturesForAddress with searchTransactionHistory
    # get first txs of mint (oldest) via until=None, sort ascending isn't available;
    # instead walk before from buy and also fetch create via looking at mint age.
    page = rpc("getSignaturesForAddress", [b["mint"], {"before": b["sig"], "limit": 25}]) or []
    # also check if create is earlier - fetch oldest by paging to end is expensive;
    # count prior mint txs in this page and see creates
    outside_buys = 0
    create_slot = None
    prior = []
    for h in page:
        if h.get("err"):
            continue
        t = get_tx(h["signature"])
        if not t:
            continue
        create = logs_create(t)
        if create:
            create_slot = t["slot"]
        # outside buy of mint?
        sd = token_deltas(t["meta"], signer_of(t))
        if sd.get(b["mint"], 0) > 0 and signer_of(t) != WALLET:
            outside_buys += 1
            prior.append((t["slot"], signer_of(t)[:8], create, b["slot"] - t["slot"]))
        if create and create_slot is not None:
            # keep scanning a bit more for create
            pass
    # if create not in page, try one more older page
    if create_slot is None and page:
        page2 = rpc("getSignaturesForAddress", [b["mint"], {"before": page[-1]["signature"], "limit": 25}]) or []
        for h in page2:
            if h.get("err"):
                continue
            t = get_tx(h["signature"])
            if t and logs_create(t):
                create_slot = t["slot"]
                break

    gap_create = (b["slot"] - create_slot) if create_slot is not None else None
    if b["create_in_tx"] or (gap_create is not None and gap_create <= 5 and outside_buys == 0):
        kind = "launch_snipe"
    elif outside_buys > 0:
        kind = "copy"
    elif gap_create is not None and gap_create <= 30:
        kind = "launch_snipe"
    else:
        kind = "unknown/no_target"
    print(f"{kind:16} create_in={b['create_in_tx']} gap_create={gap_create} outside={outside_buys} "
          f"slot={b['slot']} mint={b['mint'][:12]} prior={prior[:3]}")

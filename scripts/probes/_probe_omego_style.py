"""Classify a few omego buys: backrun / copy / launch; decode tip labels."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from sno.analyze import rpc, get_tx

WALLET = "omegoMAe1AMY5MFKQQr3JwXVy8F4eCvmBAfcpo8XAfq"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
EXEC = "7xdwTaV5QModH7HBysseq2AaNXRajLjL7KAwvFwBJzkX"
OLD_ROUTER = "HDk4dSrLnX14ARzqCwsdfsgizLFY2PvNuUXgByRhFuHy"


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
    return tx["transaction"]["message"]["accountKeys"][0]["pubkey"]


# tip label resolve from sources if present
try:
    import json
    orb = json.load(open("sources/orb_tags.json", encoding="utf-8"))
except Exception:
    orb = {}

sigs = rpc("getSignaturesForAddress", [WALLET, {"limit": 60}]) or []
buys = []
for s in sigs:
    if s.get("err"):
        continue
    tx = get_tx(s["signature"])
    if not tx:
        continue
    d = token_deltas(tx["meta"], WALLET)
    memes = [m for m, v in d.items() if m not in (WSOL, USDC) and v > 0]
    if not memes:
        continue
    buys.append((tx, memes[0], s["signature"]))
    if len(buys) >= 8:
        break

print(f"checking {len(buys)} buys for adjacency / create proximity")
kinds = Counter()
for tx, mint, sig in buys:
    slot = tx["slot"]
    try:
        block = rpc("getBlock", [slot, {
            "transactionDetails": "full", "rewards": False,
            "maxSupportedTransactionVersion": 1, "encoding": "jsonParsed",
        }])
    except Exception as e:
        print(" block", e)
        continue
    txs = block["transactions"]
    idx = next(i for i, t in enumerate(txs) if t["transaction"]["signatures"][0] == sig)
    # previous tx same-mint buy?
    kind = "solo"
    prev_w = ""
    if idx > 0:
        prev = txs[idx - 1]
        for row in prev["meta"].get("postTokenBalances") or []:
            if row.get("mint") != mint or row.get("owner") in (None, WALLET):
                continue
            pre_amt = 0
            for r in prev["meta"].get("preTokenBalances") or []:
                if r.get("accountIndex") == row["accountIndex"]:
                    pre_amt = int(r["uiTokenAmount"]["amount"])
            if int(row["uiTokenAmount"]["amount"]) > pre_amt:
                kind = "backrun"
                prev_w = row["owner"][:8]
                break
    # same-slot earlier outside buy?
    if kind == "solo":
        for j in range(idx):
            other = txs[j]
            for row in other["meta"].get("postTokenBalances") or []:
                if row.get("mint") != mint or row.get("owner") in (None, WALLET):
                    continue
                pre_amt = 0
                for r in other["meta"].get("preTokenBalances") or []:
                    if r.get("accountIndex") == row["accountIndex"]:
                        pre_amt = int(r["uiTokenAmount"]["amount"])
                if int(row["uiTokenAmount"]["amount"]) > pre_amt:
                    kind = "copy_same_block"
                    prev_w = row["owner"][:8]
                    break
            if kind != "solo":
                break
    # fee / tip
    fee = tx["meta"]["fee"] / 1e9
    kinds[kind] += 1
    print(f"  {kind:16} idx={idx:4d} fee={fee:.6f} prev={prev_w} mint={mint[:12]}")

print("kinds", dict(kinds))
print(f"executor program {EXEC}")
print(f"old router seen in earlier research {OLD_ROUTER}")

# look up tip wallets from a buy
tx0 = buys[0][0]
ixs = list(tx0["transaction"]["message"].get("instructions") or [])
for g in tx0["meta"].get("innerInstructions") or []:
    ixs += g.get("instructions") or []
print("SOL outs from sample buy:")
for ix in ixs:
    p = ix.get("parsed")
    if isinstance(p, dict) and p.get("type") == "transfer" and ix.get("program") == "system":
        info = p["info"]
        if info.get("source") == WALLET:
            dest = info["destination"]
            label = orb.get(dest) or orb.get(dest[:8]) or ""
            print(f"  {info['lamports']/1e9:.6f} -> {dest} {label}")

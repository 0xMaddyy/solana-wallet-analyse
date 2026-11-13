"""Deeper look at omego trading logic on a recent window of buys."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import rpc, get_tx

WALLET = "omegoMAe1AMY5MFKQQr3JwXVy8F4eCvmBAfcpo8XAfq"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
EXEC = "7xdwTaV5QModH7HBysseq2AaNXRajLjL7KAwvFwBJzkX"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
LAUNCH_SLOTS = 10
LOOKBACK = 80  # slots for "copy later"


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


def keys_of(tx):
    msg = tx["transaction"]["message"]
    ks = [k["pubkey"] if isinstance(k, dict) else k for k in msg["accountKeys"]]
    loaded = (tx.get("meta") or {}).get("loadedAddresses") or {}
    return ks + (loaded.get("writable") or []) + (loaded.get("readonly") or [])


def has_create(tx):
    logs = "\n".join((tx.get("meta") or {}).get("logMessages") or [])
    return "Instruction: Create" in logs or "Instruction: CreateV2" in logs


def sol_spent(tx):
    ks = keys_of(tx)
    if WALLET not in ks:
        return 0
    i = ks.index(WALLET)
    return (tx["meta"]["preBalances"][i] - tx["meta"]["postBalances"][i]) / 1e9


# Collect ~40 successful buys from newest sigs
sigs = rpc("getSignaturesForAddress", [WALLET, {"limit": 200}]) or []
buys = []
for s in sigs:
    if s.get("err"):
        continue
    tx = get_tx(s["signature"])
    if not tx:
        continue
    d = token_deltas(tx["meta"], WALLET)
    memes = [(m, v) for m, v in d.items() if m not in (WSOL, USDC) and v > 0]
    if not memes:
        continue
    mint, tok = max(memes, key=lambda x: x[1])
    buys.append({
        "sig": s["signature"], "slot": tx["slot"], "bt": tx["blockTime"],
        "mint": mint, "tokens": tok, "sol": sol_spent(tx),
        "fee": tx["meta"]["fee"] / 1e9,
        "exec": EXEC in set(keys_of(tx)) or any(
            (ix.get("programId") == EXEC) for ix in tx["transaction"]["message"].get("instructions") or []
        ),
    })
    if len(buys) >= 40:
        break

print(f"buys sampled {len(buys)}")
print(f"buy SOL median {sorted(b['sol'] for b in buys)[len(buys)//2]:.4f}  "
      f"min {min(b['sol'] for b in buys):.4f} max {max(b['sol'] for b in buys):.4f}")
print(f"fee median {sorted(b['fee'] for b in buys)[len(buys)//2]:.6f}")

# Hold time: for each buy mint, find next sell of that mint by wallet
def first_sell_after(mint, after_slot):
    page = rpc("getSignaturesForAddress", [WALLET, {"limit": 30}])  # too coarse
    return None


# Classify via mint prior sigs (cheap)
kinds = Counter()
create_gaps = []
target_wallets = Counter()
slot_gaps = []


def classify(b):
    page = rpc("getSignaturesForAddress", [b["mint"], {"before": b["sig"], "limit": 30}]) or []
    if not page:
        return "launch_first", None, None
    oldest = min(h["slot"] for h in page)
    # find nearest prior outside buy
    outside = None
    create_slot = None
    for h in page:
        if h.get("err"):
            continue
        if b["slot"] - h["slot"] > LOOKBACK:
            break
        t = get_tx(h["signature"])
        if not t:
            continue
        if has_create(t):
            create_slot = t["slot"]
        # any non-omego owner gained mint
        for row in t["meta"].get("postTokenBalances") or []:
            if row.get("mint") != b["mint"]:
                continue
            owner = row.get("owner")
            if not owner or owner == WALLET:
                continue
            pre_amt = 0
            for r in t["meta"].get("preTokenBalances") or []:
                if r.get("accountIndex") == row["accountIndex"]:
                    pre_amt = int(r["uiTokenAmount"]["amount"])
            if int(row["uiTokenAmount"]["amount"]) > pre_amt:
                outside = (owner, t["slot"], h["signature"])
                break
        if outside:
            break
    # also scan older page edge for create if needed
    if create_slot is None and page and b["slot"] - oldest <= LAUNCH_SLOTS:
        # mint activity all within launch window
        pass
    if create_slot is not None:
        create_gaps.append(b["slot"] - create_slot)

    if b["slot"] - oldest <= LAUNCH_SLOTS and outside is None:
        return "launch_snipe", None, create_slot
    if outside:
        gap = b["slot"] - outside[1]
        slot_gaps.append(gap)
        target_wallets[outside[0]] += 1
        if gap == 0:
            return "copy_same_slot", outside[0], create_slot
        return "copy_later", outside[0], create_slot
    if b["slot"] - oldest <= LAUNCH_SLOTS:
        return "launch_snipe", None, create_slot
    return "no_recent_target", None, create_slot


print("classifying…")
results = []
with ThreadPoolExecutor(6) as ex:
    for kind, tgt, cslot in ex.map(classify, buys):
        kinds[kind] += 1
        results.append((kind, tgt, cslot))

print("kinds", dict(kinds))
if slot_gaps:
    slot_gaps.sort()
    print(f"slots after target: median {slot_gaps[len(slot_gaps)//2]}  "
          f"p90 {slot_gaps[int(len(slot_gaps)*0.9)]}  max {slot_gaps[-1]}")
if create_gaps:
    create_gaps.sort()
    print(f"slots after create: n={len(create_gaps)} median {create_gaps[len(create_gaps)//2]}  "
          f"min {create_gaps[0]} max {create_gaps[-1]}")
print("top copied wallets:")
for w, n in target_wallets.most_common(10):
    print(f"  {n:3d} {w}")

# Hold times: walk wallet sigs chronologically for these mints
print("\nhold times (buy -> first sell of same mint):")
# fetch denser wallet history covering the buys
need_mints = {b["mint"]: b for b in buys}
holds = []
seen_sell = set()
# get sigs after oldest buy
oldest_bt = min(b["bt"] for b in buys)
# walk forward from a bit before using getSignatures desc and match
wallet_txs = []
before = None
for _ in range(8):
    opts = {"limit": 1000}
    if before:
        opts["before"] = before
    page = rpc("getSignaturesForAddress", [WALLET, opts]) or []
    if not page:
        break
    wallet_txs.extend(page)
    before = page[-1]["signature"]
    if (page[-1].get("blockTime") or 0) < oldest_bt - 60:
        break

# map sig -> tx for sells of our mints (fetch on demand)
buy_by_mint_slot = sorted(buys, key=lambda b: b["slot"])
# for each buy, find earliest later wallet tx that sells that mint
def sell_time(b):
    # signatures after buy: those with higher slot in wallet_txs (list is newest-first)
    cands = [s for s in wallet_txs if not s.get("err") and s["slot"] > b["slot"]]
    cands.sort(key=lambda s: s["slot"])
    for s in cands[:40]:
        t = get_tx(s["signature"])
        if not t:
            continue
        d = token_deltas(t["meta"], WALLET)
        if d.get(b["mint"], 0) < 0:
            return s["slot"] - b["slot"], (s["blockTime"] or b["bt"]) - b["bt"]
    return None, None

hold_slots, hold_secs = [], []
with ThreadPoolExecutor(6) as ex:
    for gap_slot, gap_sec in ex.map(sell_time, buys):
        if gap_slot is not None:
            hold_slots.append(gap_slot)
            hold_secs.append(gap_sec)

if hold_secs:
    hold_secs.sort()
    hold_slots.sort()
    print(f"  closed {len(hold_secs)}/{len(buys)}")
    print(f"  hold seconds median {hold_secs[len(hold_secs)//2]}  "
          f"p10 {hold_secs[max(0,int(len(hold_secs)*0.1))]}  p90 {hold_secs[int(len(hold_secs)*0.9)]}")
    print(f"  hold slots median {hold_slots[len(hold_slots)//2]}")
else:
    print("  no holds resolved")

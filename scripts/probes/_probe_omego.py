"""Probe omego wallet: programs, buy/sell pattern, delegates, tips."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from datetime import datetime, timezone
from sno.analyze import rpc, get_tx

WALLET = "omegoMAe1AMY5MFKQQr3JwXVy8F4eCvmBAfcpo8XAfq"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"


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


def programs(tx):
    msg = tx["transaction"]["message"]
    ks = keys_of(tx)
    out = set()
    for ix in msg.get("instructions") or []:
        if "programId" in ix:
            out.add(ix["programId"])
        elif "programIdIndex" in ix:
            out.add(ks[ix["programIdIndex"]])
    for g in (tx.get("meta") or {}).get("innerInstructions") or []:
        for ix in g.get("instructions") or []:
            if "programId" in ix:
                out.add(ix["programId"])
            elif "programIdIndex" in ix:
                out.add(ks[ix["programIdIndex"]])
    return out


def delegates(tx):
    out = []
    ixs = list(tx["transaction"]["message"].get("instructions") or [])
    for g in (tx.get("meta") or {}).get("innerInstructions") or []:
        ixs += g.get("instructions") or []
    for ix in ixs:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") in ("approve", "approveChecked"):
            d = (p.get("info") or {}).get("delegate")
            if d:
                out.append(d)
    return out


def sol_transfers(tx):
    out = []
    ixs = list(tx["transaction"]["message"].get("instructions") or [])
    for g in (tx.get("meta") or {}).get("innerInstructions") or []:
        ixs += g.get("instructions") or []
    for ix in ixs:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") == "transfer" and ix.get("program") == "system":
            info = p["info"]
            if info.get("source") == WALLET:
                out.append((info["destination"], info["lamports"] / 1e9))
    return out


# recent succeeded
sigs = rpc("getSignaturesForAddress", [WALLET, {"limit": 50}]) or []
print(f"recent sigs {len(sigs)}")
if sigs:
    print(f"  newest {datetime.fromtimestamp(sigs[0]['blockTime'], timezone.utc)} slot {sigs[0]['slot']}")
    print(f"  oldest-in-page {datetime.fromtimestamp(sigs[-1]['blockTime'], timezone.utc)}")

kinds = Counter()
prog_c = Counter()
dels = Counter()
tips = Counter()
samples = []
buys = 0
sells = 0
for s in sigs:
    if s.get("err"):
        continue
    tx = get_tx(s["signature"])
    if not tx:
        continue
    meta = tx["meta"]
    d = token_deltas(meta, WALLET)
    memes = {m: v for m, v in d.items() if m not in (WSOL, USDC)}
    buy = any(v > 0 for v in memes.values())
    sell = any(v < 0 for v in memes.values())
    if buy:
        buys += 1
        kinds["buy"] += 1
    elif sell:
        sells += 1
        kinds["sell"] += 1
    else:
        kinds["other"] += 1
    ps = programs(tx)
    for p in ps:
        prog_c[p] += 1
    for dlt in delegates(tx):
        if dlt != WALLET:
            dels[dlt] += 1
    for dest, amt in sol_transfers(tx):
        if amt >= 0.00005:
            tips[dest[:12]] += 1
    if len(samples) < 6 and (buy or sell):
        mint = next(iter(memes), "")[:16]
        samples.append({
            "kind": "buy" if buy else "sell",
            "slot": tx["slot"],
            "bt": datetime.fromtimestamp(tx["blockTime"], timezone.utc).isoformat(),
            "mint": mint,
            "progs": sorted(p[:12] for p in ps if p not in (
                "ComputeBudget111111111111111111111111111111",
                "11111111111111111111111111111111",
                "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
            ))[:5],
            "dels": delegates(tx)[:2],
            "fee": meta.get("fee"),
        })

print("kinds", dict(kinds), f"buys {buys} sells {sells}")
print("top programs:")
for p, n in prog_c.most_common(15):
    print(f"  {n:3d} {p}")
print("delegates", dels.most_common(5))
print("tip dest prefixes", tips.most_common(8))
print("samples:")
for s in samples:
    print(" ", s)

# count Nov 9-10 activity volume
START = int(datetime(2026, 11, 9, tzinfo=timezone.utc).timestamp())
END = int(datetime(2026, 11, 11, tzinfo=timezone.utc).timestamp())
n = 0
before = None
while True:
    opts = {"limit": 1000}
    if before:
        opts["before"] = before
    page = rpc("getSignaturesForAddress", [WALLET, opts]) or []
    if not page:
        break
    for s in page:
        bt = s.get("blockTime") or 0
        if bt >= END:
            continue
        if bt < START:
            print(f"nov9-10 succeededish pages done, counted {n}")
            raise SystemExit
        if not s.get("err"):
            n += 1
    before = page[-1]["signature"]
    if (page[-1].get("blockTime") or 0) < START:
        break
print(f"nov9-10 succeeded {n}")

"""How omego bot works: sample recent txs for programs, buy/sell, approve, tips, copy pattern."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from sno.analyze import rpc, get_tx

WALLET = "omegoMAe1AMY5MFKQQr3JwXVy8F4eCvmBAfcpo8XAfq"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
ROUTER = "HDk4dSrLnX14ARzqCwsdfsgizLFY2PvNuUXgByRhFuHy"


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


def progs(tx):
    msg = tx["transaction"]["message"]
    ks = keys_of(tx)
    out = set()
    for ix in list(msg.get("instructions") or []):
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
    meta = tx["meta"]
    msg = tx["transaction"]["message"]
    ixs = list(msg.get("instructions") or [])
    for g in meta.get("innerInstructions") or []:
        ixs += g.get("instructions") or []
    for ix in ixs:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") in ("approve", "approveChecked"):
            d = (p.get("info") or {}).get("delegate")
            if d:
                out.append(d)
    return out


def transfers_out(tx):
    """SOL transfers from wallet (tips)."""
    out = []
    meta = tx["meta"]
    msg = tx["transaction"]["message"]
    ixs = list(msg.get("instructions") or [])
    for g in meta.get("innerInstructions") or []:
        ixs += g.get("instructions") or []
    for ix in ixs:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") == "transfer" and ix.get("program") == "system":
            info = p["info"]
            if info.get("source") == WALLET:
                out.append((info["destination"], info["lamports"] / 1e9))
    return out


# recent succeeded sigs
sigs = rpc("getSignaturesForAddress", [WALLET, {"limit": 80}]) or []
ok = [s for s in sigs if not s.get("err")]
print(f"recent sigs {len(sigs)} ok {len(ok)} first_bt={ok[0].get('blockTime') if ok else None}")

kinds = Counter()
prog_c = Counter()
dels = Counter()
tips = Counter()
buy_sizes = []
samples = []
for s in ok[:40]:
    tx = get_tx(s["signature"])
    if not tx:
        continue
    meta = tx["meta"]
    d = token_deltas(meta, WALLET)
    memes = {m: v for m, v in d.items() if m not in (WSOL, USDC)}
    buy = any(v > 0 for v in memes.values())
    sell = any(v < 0 for v in memes.values())
    kind = "buy" if buy else ("sell" if sell else "other")
    kinds[kind] += 1
    ps = progs(tx)
    for p in ps:
        prog_c[p] += 1
    for dgt in delegates(tx):
        dels[dgt] += 1
    for dest, amt in transfers_out(tx):
        tips[dest[:12]] += amt
    ks = keys_of(tx)
    idx = ks.index(WALLET) if WALLET in ks else 0
    sol_d = (meta["postBalances"][idx] - meta["preBalances"][idx]) / 1e9
    if buy:
        buy_sizes.append(-sol_d if sol_d < 0 else sol_d)
    if len(samples) < 6:
        samples.append({
            "kind": kind,
            "slot": tx["slot"],
            "sol_d": round(sol_d, 4),
            "router": ROUTER in ps,
            "pump": PUMP in ps,
            "dels": delegates(tx)[:1],
            "progs": sorted(p[:8] for p in ps if p not in (
                "ComputeBudget111111111111111111111111111111",
                "11111111111111111111111111111111",
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
                "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
            ))[:5],
        })

print("kinds", dict(kinds))
print("top programs")
for p, n in prog_c.most_common(15):
    print(f"  {n:3d} {p}")
print("delegates", dels.most_common(5))
print("tip dests (sum SOL)", tips.most_common(8))
if buy_sizes:
    buy_sizes.sort()
    print(f"buy sol median {buy_sizes[len(buy_sizes)//2]:.4f} n={len(buy_sizes)}")
print("samples")
for s in samples:
    print(" ", s)

# check one buy: is it a backrun (prev tx same mint)?
buys = []
for s in ok[:25]:
    tx = get_tx(s["signature"])
    if not tx:
        continue
    d = token_deltas(tx["meta"], WALLET)
    memes = [m for m, v in d.items() if m not in (WSOL, USDC) and v > 0]
    if memes:
        buys.append((tx, memes[0]))
    if len(buys) >= 3:
        break

print("\nbackrun check (3 buys):")
for tx, mint in buys:
    slot = tx["slot"]
    sig = tx["transaction"]["signatures"][0]
    try:
        block = rpc("getBlock", [slot, {"transactionDetails": "full", "rewards": False,
                                        "maxSupportedTransactionVersion": 1, "encoding": "jsonParsed"}])
    except Exception as e:
        print("  block err", e)
        continue
    txs = block.get("transactions") or []
    idx = next((i for i, t in enumerate(txs) if t["transaction"]["signatures"][0] == sig), None)
    prev_same = False
    prev_signer = None
    if idx and idx > 0:
        prev = txs[idx - 1]
        pmeta = prev["meta"]
        # any other wallet gained the mint?
        for row in pmeta.get("postTokenBalances") or []:
            if row.get("mint") == mint and row.get("owner") and row["owner"] != WALLET:
                pre_amt = 0
                for r in pmeta.get("preTokenBalances") or []:
                    if r.get("accountIndex") == row["accountIndex"]:
                        pre_amt = int(r["uiTokenAmount"]["amount"])
                post_amt = int(row["uiTokenAmount"]["amount"])
                if post_amt > pre_amt:
                    prev_same = True
                    prev_signer = row["owner"][:8]
                    break
    print(f"  slot {slot} idx {idx} mint {mint[:8]}… backrun_adj={prev_same} prev={prev_signer}")

"""What/when omego copies: target size, platform, slot gap, position gap, buy ratio."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.analyze import rpc, get_tx
from sno.multi_report import fee_platform_of, program_platform, swqos_of

WALLET = "omegoMAe1AMY5MFKQQr3JwXVy8F4eCvmBAfcpo8XAfq"
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
N_BUYS = 60
LOOKBACK_SIGS = 40


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


def signer_of(tx):
    for k in tx["transaction"]["message"]["accountKeys"]:
        if isinstance(k, dict) and k.get("signer"):
            return k["pubkey"]
    ak = tx["transaction"]["message"]["accountKeys"][0]
    return ak["pubkey"] if isinstance(ak, dict) else ak


def sol_delta(tx, owner):
    ks = keys_of(tx)
    if owner not in ks:
        return 0.0
    i = ks.index(owner)
    native = (tx["meta"]["postBalances"][i] - tx["meta"]["preBalances"][i]) / 1e9
    # + wsol
    d = token_deltas(tx["meta"], owner)
    native += d.get(WSOL, 0) / 1e9
    return native


def programs(tx):
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


def tip_dests(tx, owner):
    out = []
    ixs = list(tx["transaction"]["message"].get("instructions") or [])
    for g in (tx.get("meta") or {}).get("innerInstructions") or []:
        ixs += g.get("instructions") or []
    for ix in ixs:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") == "transfer" and ix.get("program") == "system":
            info = p["info"]
            if info.get("source") == owner and info["lamports"] >= 50_000:
                # skip large amounts that look like the swap itself (>0.05 often bonding)
                amt = info["lamports"] / 1e9
                if amt < 0.05:
                    out.append((info["destination"], amt))
    return out


def platform_of(tx):
    progs = programs(tx)
    p = program_platform(progs)
    if p:
        return p
    # fee wallet / tip
    for dest, _ in tip_dests(tx, signer_of(tx)):
        fp = fee_platform_of(dest)
        if fp:
            return fp
        sq = swqos_of(dest)
        if sq:
            return f"tip:{sq}"
    # known routers in accounts
    for a in keys_of(tx):
        fp = fee_platform_of(a)
        if fp:
            return fp
    return "unknown/direct"


def hour_utc(bt):
    return datetime.fromtimestamp(bt, timezone.utc).strftime("%H")


# --- collect omego buys ---
sigs = rpc("getSignaturesForAddress", [WALLET, {"limit": 300}]) or []
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
    mint, _ = max(memes, key=lambda x: x[1])
    buys.append({
        "sig": s["signature"], "slot": tx["slot"], "bt": tx["blockTime"],
        "mint": mint, "buy_sol": -sol_delta(tx, WALLET),
        "fee": tx["meta"]["fee"] / 1e9, "tx": tx,
    })
    if len(buys) >= N_BUYS:
        break

print(f"omego buys {len(buys)}")


def find_target(b):
    page = rpc("getSignaturesForAddress", [b["mint"], {"before": b["sig"], "limit": LOOKBACK_SIGS}]) or []
    for h in page:
        if h.get("err"):
            continue
        if b["slot"] - h["slot"] > 20:
            break
        t = get_tx(h["signature"])
        if not t:
            continue
        owner_gains = []
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
            gained = int(row["uiTokenAmount"]["amount"]) - pre_amt
            if gained > 0:
                owner_gains.append((owner, gained))
        if not owner_gains:
            continue
        # pick the signer if they gained, else largest gainer
        sig = signer_of(t)
        if any(o == sig for o, _ in owner_gains):
            tgt = sig
        else:
            tgt = max(owner_gains, key=lambda x: x[1])[0]
        tsol = -sol_delta(t, tgt)
        return {
            "wallet": tgt,
            "sig": h["signature"],
            "slot": t["slot"],
            "bt": t["blockTime"],
            "buy_sol": tsol,
            "platform": platform_of(t),
            "fee": t["meta"]["fee"] / 1e9,
            "swqos": [swqos_of(d) for d, _ in tip_dests(t, tgt) if swqos_of(d)],
        }
    return None


print("resolving targets…")
rows = []
with ThreadPoolExecutor(6) as ex:
    targets = list(ex.map(find_target, buys))

# block indexes for same-slot pairs
want = defaultdict(set)
for b, t in zip(buys, targets):
    if not t:
        continue
    want[b["slot"]].add(b["sig"])
    if t["slot"] == b["slot"]:
        want[t["slot"]].add(t["sig"])


def indexes(slot):
    try:
        sigs = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                       "maxSupportedTransactionVersion": 1}])["signatures"]
    except Exception:
        return slot, {}
    need = want[slot]
    return slot, {s: i for i, s in enumerate(sigs) if s in need}


pos = {}
with ThreadPoolExecutor(6) as ex:
    for slot, found in ex.map(indexes, list(want)):
        pos[slot] = found

platforms = Counter()
gaps = []
pos_gaps = []
tgt_sizes = []
bot_sizes = []
ratios = []
hours = Counter()
repeat_w = Counter()
filters = Counter()  # buckets by target size

for b, t in zip(buys, targets):
    if not t:
        filters["no_target"] += 1
        continue
    gap = b["slot"] - t["slot"]
    gaps.append(gap)
    platforms[t["platform"]] += 1
    repeat_w[t["wallet"]] += 1
    hours[hour_utc(b["bt"])] += 1
    tgt_sizes.append(t["buy_sol"])
    bot_sizes.append(b["buy_sol"])
    if t["buy_sol"] > 0.05:
        ratios.append(b["buy_sol"] / t["buy_sol"])
    bi = pos.get(b["slot"], {}).get(b["sig"])
    ti = pos.get(t["slot"], {}).get(t["sig"]) if t["slot"] == b["slot"] else None
    if bi is not None and ti is not None:
        pos_gaps.append(bi - ti)
        if bi - ti == 1:
            filters["adj_backrun"] += 1
        else:
            filters["same_slot_gap>1"] += 1
    elif gap == 0:
        filters["same_slot_no_idx"] += 1
    elif gap <= 3:
        filters["copy_1_3_slots"] += 1
    else:
        filters["copy_4plus_slots"] += 1

    # target size buckets
    ts = t["buy_sol"]
    if ts < 0.3:
        filters["tgt_<0.3"] += 1
    elif ts < 1.0:
        filters["tgt_0.3-1"] += 1
    elif ts < 3.0:
        filters["tgt_1-3"] += 1
    else:
        filters["tgt_>=3"] += 1

def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


print("\n=== WHEN ===")
print(f"resolved {sum(1 for t in targets if t)}/{len(buys)}")
print("timing buckets", dict(filters))
if gaps:
    gaps_s = sorted(gaps)
    print(f"slot gap after target: median {med(gaps)}  p90 {gaps_s[int(len(gaps_s)*0.9)]}  max {gaps_s[-1]}")
if pos_gaps:
    pos_gaps_s = sorted(pos_gaps)
    print(f"tx positions after target (same slot): median {med(pos_gaps)}  "
          f"min {pos_gaps_s[0]} max {pos_gaps_s[-1]}  n={len(pos_gaps)}")
    print(f"  adjacent (pos+1) {sum(1 for x in pos_gaps if x == 1)}/{len(pos_gaps)}")
print("hour UTC distribution (top):", hours.most_common(8))

print("\n=== WHAT (targets) ===")
print("platforms", platforms.most_common())
if tgt_sizes:
    print(f"target buy SOL: median {med(tgt_sizes):.3f}  "
          f"p10 {sorted(tgt_sizes)[max(0,int(len(tgt_sizes)*0.1))]:.3f}  "
          f"p90 {sorted(tgt_sizes)[int(len(tgt_sizes)*0.9)]:.3f}")
if bot_sizes:
    print(f"omego buy SOL:  median {med(bot_sizes):.3f}  "
          f"p10 {sorted(bot_sizes)[max(0,int(len(bot_sizes)*0.1))]:.3f}  "
          f"p90 {sorted(bot_sizes)[int(len(bot_sizes)*0.9)]:.3f}")
if ratios:
    print(f"omego/target size ratio: median {med(ratios):.2f}x  "
          f"p10 {sorted(ratios)[max(0,int(len(ratios)*0.1))]:.2f}  "
          f"p90 {sorted(ratios)[int(len(ratios)*0.9)]:.2f}")

print("\ntop target wallets:")
for w, n in repeat_w.most_common(12):
    print(f"  {n:2d}x  {w}")

# sample rows
print("\nsample copies:")
shown = 0
for b, t in zip(buys, targets):
    if not t:
        continue
    gap = b["slot"] - t["slot"]
    bi = pos.get(b["slot"], {}).get(b["sig"], "?")
    ti = pos.get(t["slot"], {}).get(t["sig"], "?") if t["slot"] == b["slot"] else "-"
    print(f"  gap_slots={gap} pos={ti}->{bi} tgt={t['buy_sol']:.2f} SOL  omego={b['buy_sol']:.2f}  "
          f"plat={t['platform'][:28]}  tgt={t['wallet'][:8]}…")
    shown += 1
    if shown >= 12:
        break

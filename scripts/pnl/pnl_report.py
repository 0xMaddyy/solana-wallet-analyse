import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from pnl_fetch import START, WALLETS, WSOL

BUYER, SELLER = WALLETS
DAYS = {
    "Oct 8 UTC (00:00-24:00 UTC)": (START, START + 86400),
    "Oct 8 Eastern (00:00-24:00 UTC-4)": (START + 4 * 3600, START + 28 * 3600),
}

txs = [json.loads(l) for l in open("pnl_txs.jsonl")]
missing = [t for t in txs if t.get("missing")]
txs = [t for t in txs if not t.get("missing")]
print(f"txs loaded: {len(txs)}  missing: {len(missing)}")

foreign_owners = Counter()
for t in txs:
    for k in t["tok"]:
        owner, mint = k.split("|")
        if owner not in WALLETS and SELLER in t["signers"] and BUYER not in t["dsol"]:
            foreign_owners[owner] += 1
print(f"seller-signed txs touching token accounts of OTHER owners (excluding pools): top {foreign_owners.most_common(5)}")


def pair_sol(t):
    lamports = sum(t["dsol"].values())
    for k, d in t["tok"].items():
        owner, mint = k.split("|")
        if mint == WSOL and owner in WALLETS:
            lamports += d
    return lamports


def pair_mints(t):
    out = {}
    for k, d in t["tok"].items():
        owner, mint = k.split("|")
        if owner in WALLETS and mint != WSOL:
            out[mint] = out.get(mint, 0) + d
    return out


def classify(t):
    if t["err"] is not None:
        return "failed (fees only)"
    m = pair_mints(t)
    if m:
        return "buy" if all(d > 0 for d in m.values()) else "sell" if all(d < 0 for d in m.values()) else "mixed trade"
    external = [x for x in t["transfers"] if (x[0] in WALLETS) != (x[1] in WALLETS)]
    if any(x[2] >= 50_000_000 for x in external):
        return "external transfer (>=0.05 SOL)"
    internal = [x for x in t["transfers"] if x[0] in WALLETS and x[1] in WALLETS]
    if internal:
        return "internal transfer"
    return "other (rent, approvals, closes)"


for label, (lo, hi) in DAYS.items():
    day = [t for t in txs if lo <= t["blockTime"] < hi]
    by_kind = defaultdict(lambda: [0, 0])
    per_mint_sol, per_mint_tok, mint_first_buy = defaultdict(int), defaultdict(int), {}
    for t in day:
        k = classify(t)
        s = pair_sol(t)
        by_kind[k][0] += 1
        by_kind[k][1] += s
        if k in ("buy", "sell", "mixed trade"):
            mints = pair_mints(t)
            share = s / len(mints)
            for mint, d in mints.items():
                per_mint_sol[mint] += share
                per_mint_tok[mint] += d
                if d > 0:
                    mint_first_buy.setdefault(mint, t["blockTime"])

    print(f"\n================ {label}  ({len(day)} txs)")
    total = 0
    for k, (n, s) in sorted(by_kind.items(), key=lambda kv: kv[1][1]):
        print(f"  {k:36s} {n:5d} txs   {s / 1e9:+10.4f} SOL")
        total += s
    ext = by_kind.get("external transfer (>=0.05 SOL)", [0, 0])[1]
    print(f"  {'net SOL change of pair':36s}            {total / 1e9:+10.4f} SOL")
    print(f"  {'net excluding external transfers':36s}            {(total - ext) / 1e9:+10.4f} SOL")

    closed = {m for m in per_mint_sol if m in mint_first_buy and per_mint_tok[m] <= 0}
    still_open = {m for m in per_mint_sol if m in mint_first_buy and per_mint_tok[m] > 0}
    sold_only = {m for m in per_mint_sol if m not in mint_first_buy}
    realized = sum(per_mint_sol[m] for m in closed)
    wins = sum(1 for m in closed if per_mint_sol[m] > 0)
    print(f"  tokens bought & fully sold in the day: {len(closed)}  realized {realized / 1e9:+.4f} SOL  "
          f"(winners {wins}, losers {len(closed) - wins})")
    print(f"  tokens bought but still held at day end: {len(still_open)}  "
          f"SOL spent on them {sum(per_mint_sol[m] for m in still_open) / 1e9:+.4f}")
    print(f"  tokens only sold (bought before the day): {len(sold_only)}  "
          f"SOL received {sum(per_mint_sol[m] for m in sold_only) / 1e9:+.4f}")
    best = sorted(closed, key=lambda m: per_mint_sol[m])
    print("  worst closed:", [(m[:6], round(per_mint_sol[m] / 1e9, 3)) for m in best[:3]])
    print("  best closed: ", [(m[:6], round(per_mint_sol[m] / 1e9, 3)) for m in best[-3:]])

    ext_tx = [t for t in day if classify(t) == "external transfer (>=0.05 SOL)"]
    for t in ext_tx[:10]:
        for x in t["transfers"]:
            if (x[0] in WALLETS) != (x[1] in WALLETS):
                print(f"    ext {datetime.fromtimestamp(t['blockTime'], timezone.utc):%H:%M} {x[0][:6]} -> {x[1][:6]} {x[2] / 1e9:.4f} SOL")

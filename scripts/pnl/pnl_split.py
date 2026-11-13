import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from sno.analyze import JITO_TIPS, get_tx, rpc, summarize
from pnl_fetch import START
from pnl_report import classify, pair_mints, pair_sol

BUYER = "8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF"
txs = [json.loads(l) for l in open("pnl_txs.jsonl")]
day = sorted((t for t in txs if START <= t["blockTime"] < START + 86400), key=lambda t: (t["slot"], t["blockTime"]))


@lru_cache(maxsize=None)
def block_sigs(slot):
    return tuple(rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                         "maxSupportedTransactionVersion": 1}])["signatures"])


def buy_info(t):
    sigs = block_sigs(t["slot"])
    i = sigs.index(t["sig"])
    prev = summarize(get_tx(sigs[i - 1])) if i else None
    mints = set(pair_mints(t))
    backrun = bool(prev and prev["signer"] != BUYER and set(prev["mints_bought"]) & mints)
    jito = any(dst in JITO_TIPS for src, dst, _ in t["transfers"] if src == BUYER)
    return {"sig": t["sig"], "backrun": backrun, "jito": jito, "index": i}


real_buys = [t for t in day if classify(t) == "buy" and pair_sol(t) < 0 and BUYER in t["signers"]]
slots = sorted({t["slot"] for t in real_buys})
with ThreadPoolExecutor(8) as ex:
    list(ex.map(block_sigs, slots))
    infos = {r["sig"]: r for r in ex.map(buy_info, real_buys)}

mint_sol, mint_tok, mint_first_buy = defaultdict(int), defaultdict(int), {}
for t in day:
    if classify(t) not in ("buy", "sell", "mixed trade"):
        continue
    mints = pair_mints(t)
    s = pair_sol(t)
    for m, d in mints.items():
        mint_sol[m] += s / len(mints)
        mint_tok[m] += d
        if t["sig"] in infos and m not in mint_first_buy:
            mint_first_buy[m] = infos[t["sig"]]

groups = defaultdict(list)
for m, info in mint_first_buy.items():
    if mint_tok[m] > 0:
        continue
    kind = "backrun" if info["backrun"] else "non-backrun"
    route = "jito bundle" if info["jito"] else "direct (no tip)"
    groups[(kind, "all")].append(mint_sol[m])
    groups[(kind, route)].append(mint_sol[m])


def show(label, vals):
    if not vals:
        return
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v <= 0]
    print(f"{label:34s} tokens {len(vals):4d}  profit {sum(vals) / 1e9:+9.3f} SOL  avg {sum(vals) / len(vals) / 1e9:+.4f}  "
          f"win rate {len(wins) / len(vals) * 100:5.1f}%  avg win {sum(wins) / max(len(wins), 1) / 1e9:+.3f}  "
          f"avg loss {sum(losses) / max(len(losses), 1) / 1e9:+.3f}")


buy_cost = defaultdict(int)
for t in real_buys:
    i = infos[t["sig"]]
    buy_cost["backrun" if i["backrun"] else "non-backrun"] += -pair_sol(t)

print(f"Oct 8 UTC: {len(real_buys)} buys, {sum(1 for i in infos.values() if i['backrun'])} backruns\n")
for kind in ("backrun", "non-backrun"):
    show(f"{kind} - all", groups[(kind, "all")])
    for route in ("jito bundle", "direct (no tip)"):
        show(f"   {route}", groups[(kind, route)])
    print(f"   SOL spent on buys: {buy_cost[kind] / 1e9:.2f}  -> margin "
          f"{sum(groups[(kind, 'all')]) / max(buy_cost[kind], 1) * 100:.2f}%\n")
json.dump(infos, open("buy_infos.json", "w"))

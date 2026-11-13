import csv
import json
import random

from sno.multi_fetch import PAIRS, out_path, record
from sno.multi_report import pair_mints, pair_sol

rows = list(csv.DictReader(open("backruns_oct8.profit.csv", encoding="utf-8-sig")))
sigs = {r["bot_tx"] for r in rows}
seller_of = dict(PAIRS)

blank = [r for r in rows if r["trade_profit_sol"] and r["position_profit_sol"] != r["trade_profit_sol"]]
orphan_firsts = set()
old = list(csv.DictReader(open("backruns_oct8.new.csv", encoding="utf-8-sig")))
orphans = [o for o in old if o["trade_status"].startswith("same trade as") and o["trade_status"][14:] not in sigs]
random.seed(1)
picks = random.sample(blank, 2) + [next(r for r in rows if r["bot_tx"] == orphans[0]["bot_tx"])]

dual = set()
for buyer, seller in PAIRS:
    for l in open(out_path(buyer)):
        t = json.loads(l)
        if t.get("missing") or t["err"] is not None or t["signers"][0] not in (buyer, seller):
            continue
        m = pair_mints(t, {buyer, seller})
        if len(m) == 2 and any(d < 0 for d in m.values()):
            dual |= {(buyer, k) for k, d in m.items() if d < 0}
picks += [next(r for r in rows if (r["buyer_wallet"], r["mint"]) in dual)]

for r in picks:
    buyer, mint = r["buyer_wallet"], r["mint"]
    pair = {buyer, seller_of[buyer]}
    mint_sigs = []
    for l in open(out_path(buyer)):
        t = json.loads(l)
        if not t.get("missing") and t["err"] is None and mint in pair_mints(t, pair):
            mint_sigs.append(t["sig"])
    fresh = [record(s, list(pair)) for s in mint_sigs]
    fresh.sort(key=lambda t: (t["slot"], t["blockTime"]))
    print(f"\n{buyer[:8]} {mint[:8]} row buy {r['bot_tx'][:12]}  csv trade_profit {r['trade_profit_sol']}  "
          f"position {r['position_profit_sol']}  status {r['trade_status']}")
    lots, pos = [], 0
    for t in fresh:
        m = pair_mints(t, pair)
        s = pair_sol(t, pair)
        d = m[mint]
        paid_for = [k for k, v in m.items() if (v < 0) == (s > 0)] or list(m)
        sh = s / len(paid_for) if mint in paid_for else 0
        pos += sh
        print(f"   {t['sig'][:12]} {'BUY ' if d > 0 else 'SELL'} tokens {d:+16d}  sol {sh / 1e9:+.6f}  mints_in_tx {len(m)}")
        if d > 0:
            lots.append([t["sig"], d, -sh, 0, 0.0])
        else:
            left = -d
            for lot in lots:
                take = min(left, lot[1] - lot[3])
                if take > 0:
                    lot[3] += take
                    lot[4] += sh * take / -d
                    left -= take
    mine = next(l for l in lots if l[0] == r["bot_tx"])
    print(f"   fresh: this buy profit {(mine[4] - mine[2]) / 1e9:+.6f}  position {pos / 1e9:+.6f}")

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import math
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.analyze import rpc
from pnl_fetch import START
from pnl_report import classify, pair_mints, pair_sol

JITO_REGIONS = {
    "ny": (40.71, -74.01), "slc": (40.76, -111.89), "amsterdam": (52.37, 4.90), "frankfurt": (50.11, 8.68),
    "london": (51.51, -0.13), "dublin": (53.35, -6.26), "singapore": (1.35, 103.82), "tokyo": (35.68, 139.69),
}

infos = json.load(open("buy_infos.json"))
txs = {t["sig"]: t for t in map(json.loads, open("pnl_txs.jsonl"))}
day = sorted((t for t in txs.values() if START <= t["blockTime"] < START + 86400), key=lambda t: t["slot"])

mint_sol, mint_tok, first_buy_of_mint = defaultdict(int), defaultdict(int), {}
for t in day:
    if classify(t) not in ("buy", "sell", "mixed trade"):
        continue
    mints = pair_mints(t)
    for m, d in mints.items():
        mint_sol[m] += pair_sol(t) / len(mints)
        mint_tok[m] += d
        if t["sig"] in infos and m not in first_buy_of_mint:
            first_buy_of_mint[m] = t["sig"]
pnl_by_sig = {sig: mint_sol[m] for m, sig in first_buy_of_mint.items() if mint_tok[m] <= 0}


def leader_of(slot):
    try:
        return rpc("getSlotLeaders", [slot, 1])[0]
    except Exception:
        block = rpc("getBlock", [slot, {"transactionDetails": "none", "rewards": True, "maxSupportedTransactionVersion": 1}])
        return next(r["pubkey"] for r in block["rewards"] if r["rewardType"] == "Fee")


slots = sorted({txs[s]["slot"] for s in infos})
with ThreadPoolExecutor(8) as ex:
    leaders = dict(zip(slots, ex.map(leader_of, slots)))

nodes = {n["pubkey"]: n for n in rpc("getClusterNodes", [])}
ips = {}
for ident in set(leaders.values()):
    gossip = (nodes.get(ident) or {}).get("gossip")
    if gossip:
        ips[ident] = gossip.rsplit(":", 1)[0]

geo = {}
uniq = sorted(set(ips.values()))
for i in range(0, len(uniq), 100):
    body = json.dumps([{"query": ip, "fields": "query,status,country,city,lat,lon,org,as"} for ip in uniq[i:i + 100]]).encode()
    req = urllib.request.Request("http://ip-api.com/batch", data=body, headers={"Content-Type": "application/json"})
    for g in json.loads(urllib.request.urlopen(req, timeout=60).read()):
        geo[g["query"]] = g


def nearest_region(lat, lon):
    def dist(p):
        la1, lo1, la2, lo2 = map(math.radians, (lat, lon, *p))
        return math.acos(min(1, math.sin(la1) * math.sin(la2) + math.cos(la1) * math.cos(la2) * math.cos(lo1 - lo2)))
    return min(JITO_REGIONS, key=lambda r: dist(JITO_REGIONS[r]))


rows = []
for sig, info in infos.items():
    t = txs[sig]
    leader = leaders[t["slot"]]
    g = geo.get(ips.get(leader), {})
    ok = g.get("status") == "success"
    rows.append({
        "time_utc": datetime.fromtimestamp(t["blockTime"], timezone.utc).strftime("%H:%M:%S"),
        "slot": t["slot"], "sig": sig,
        "type": "backrun" if info["backrun"] else "non-backrun",
        "route": "jito" if info["jito"] else "direct",
        "buy_sol": round(-pair_sol(t) / 1e9, 4),
        "token_pnl_sol": round(pnl_by_sig[sig] / 1e9, 4) if sig in pnl_by_sig else "",
        "leader": leader,
        "leader_ip": ips.get(leader, ""),
        "city": g.get("city", "") if ok else "unknown",
        "country": g.get("country", "") if ok else "unknown",
        "hosting": g.get("org") or g.get("as", "") if ok else "",
        "nearest_jito_region": nearest_region(g["lat"], g["lon"]) if ok else "unknown",
    })
rows.sort(key=lambda r: r["slot"])

with open("buys_by_leader_region.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

agg = defaultdict(lambda: {"buys": 0, "backrun": 0, "jito": 0, "pnl": 0.0, "pnl_backrun": 0.0, "pnl_non": 0.0})
for r in rows:
    a = agg[r["nearest_jito_region"]]
    a["buys"] += 1
    a["backrun"] += r["type"] == "backrun"
    a["jito"] += r["route"] == "jito"
    if r["token_pnl_sol"] != "":
        a["pnl"] += r["token_pnl_sol"]
        a["pnl_backrun" if r["type"] == "backrun" else "pnl_non"] += r["token_pnl_sol"]

print(f"buys: {len(rows)}  distinct leaders: {len(set(leaders.values()))}  leaders without gossip IP: "
      f"{len(set(leaders.values()) - set(ips))}")
print(f"{'region':12s} {'buys':>5s} {'backrun':>8s} {'backrun%':>9s} {'jito':>5s} {'pnl SOL':>9s} {'pnl backrun':>12s} {'pnl non':>9s}")
for region, a in sorted(agg.items(), key=lambda kv: -kv[1]["buys"]):
    print(f"{region:12s} {a['buys']:5d} {a['backrun']:8d} {a['backrun'] / a['buys'] * 100:8.1f}% {a['jito']:5d} "
          f"{a['pnl']:+9.3f} {a['pnl_backrun']:+12.3f} {a['pnl_non']:+9.3f}")

city = defaultdict(lambda: [0, 0])
for r in rows:
    k = f"{r['city']}, {r['country']}"
    city[k][0] += 1
    city[k][1] += r["type"] == "backrun"
print("\nby leader city (top 20):")
for k, (n, b) in sorted(city.items(), key=lambda kv: -kv[1][0])[:20]:
    print(f"  {n:4d} buys  {b:4d} backrun ({b / n * 100:5.1f}%)  {k}")

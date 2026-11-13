from sno.paths import RESULTS, SOURCES, LABELS, label_file, source_file, ROOT
"""Add leader_client_type to backruns_oct8.csv from getClusterNodes clientId (gossip)."""
import csv
import json
import sys
from collections import Counter, defaultdict

from sno.analyze import rpc

path = sys.argv[1] if len(sys.argv) > 1 else "backruns_oct8.csv"
nodes = rpc("getClusterNodes", [])
json.dump(nodes, open("sources/cluster_nodes.json", "w"))
client = {n["pubkey"]: n.get("clientId") or "Unknown" for n in nodes}
version = {n["pubkey"]: n.get("version") or "" for n in nodes}

va = rpc("getVoteAccounts", [])
stake = Counter()
for v in va["current"] + va["delinquent"]:
    stake[client.get(v["nodePubkey"], "not in gossip")] += v["activatedStake"]
total_stake = sum(stake.values())

rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
cols = [c for c in rows[0] if c != "leader_client_type"]
cols.insert(cols.index("leader") + 1, "leader_client_type")
for r in rows:
    r["leader_client_type"] = client.get(r["leader"], "not in gossip")

with open(path, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

by = defaultdict(Counter)
for r in rows:
    by[r["leader_client_type"]][r["bot_route"]] += 1
n_direct = sum(c["direct"] for c in by.values())
n_bundle = sum(c["jito bundle"] for c in by.values())

print(f"{'client':20s} {'stake%':>7s} {'bundle':>7s} {'bndl%':>6s} {'direct':>7s} {'dir%':>6s} {'leaders':>8s}")
leaders = defaultdict(set)
for r in rows:
    leaders[r["leader_client_type"]].add(r["leader"])
for k in sorted(set(by) | set(stake), key=lambda k: -stake.get(k, 0)):
    c = by.get(k, Counter())
    print(f"{k:20s} {100*stake.get(k,0)/total_stake:6.1f}% {c['jito bundle']:7d} {100*c['jito bundle']/n_bundle:5.1f}% "
          f"{c['direct']:7d} {100*c['direct']/n_direct:5.1f}% {len(leaders.get(k, ())):8d}")

print("\ndirect sends per client: bot_swqos")
sw = defaultdict(Counter)
for r in rows:
    if r["bot_route"] == "direct":
        sw[r["leader_client_type"]][r["bot_swqos"]] += 1
for k, c in sorted(sw.items(), key=lambda x: -sum(x[1].values())):
    print(f"  {k:20s} {dict(c.most_common(5))}")

print("\nbundles per client: bot_swqos")
sw = defaultdict(Counter)
for r in rows:
    if r["bot_route"] == "jito bundle":
        sw[r["leader_client_type"]][r["bot_swqos"]] += 1
for k, c in sorted(sw.items(), key=lambda x: -sum(x[1].values())):
    print(f"  {k:20s} {dict(c.most_common(5))}")

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter, defaultdict

from sno.analyze import rpc
from pnl_fetch import START, WALLETS
from pnl_report import classify, pair_mints

BUYER, SELLER = WALLETS
txs = [json.loads(l) for l in open("pnl_txs.jsonl")]
day = [t for t in txs if START <= t["blockTime"] < START + 86400]

flow = defaultdict(lambda: defaultdict(int))
signer_by_kind = defaultdict(Counter)
for t in day:
    k = classify(t)
    for w, d in t["dsol"].items():
        flow[k][w[:6]] += d
    signer_by_kind[k][",".join(s[:6] for s in t["signers"])] += 1
for k in ("buy", "sell"):
    print(k, {w: round(v / 1e9, 3) for w, v in flow[k].items()}, "signers:", signer_by_kind[k].most_common(3))

owners = Counter()
for t in day:
    for key in t["tok"]:
        owner = key.split("|")[0]
        if owner not in WALLETS:
            owners[owner] += 1
sample = [o for o, _ in owners.most_common(6)]
infos = rpc("getMultipleAccounts", [sample, {"encoding": "base64"}])["value"]
for o, info in zip(sample, infos):
    print(f"other token owner {o[:8]} seen {owners[o]}x  owner program {info['owner'] if info else 'none (no account)'}")

held = defaultdict(list)
for t in sorted(day, key=lambda t: t["blockTime"]):
    for m, d in pair_mints(t).items():
        held[m].append((t["blockTime"], d))
durations = sorted(ev[-1][0] - ev[0][0] for ev in held.values() if len(ev) > 1)
if durations:
    print(f"holding time per token: median {durations[len(durations) // 2]}s, 90th pct {durations[int(len(durations) * 0.9)]}s")

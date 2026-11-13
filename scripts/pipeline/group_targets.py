"""Group Axiom / GMGN / Terminal target wallets by their fee settings.

Fingerprint = platform + tip transfers (provider, exact lamports) + priority fee (exact lamports).
GMGN sets the priority fee dynamically per tx, so for GMGN the fingerprint is the tip only.
Axiom splits one user budget into tip + priority, so odd tips (0.001891 + 0.000109) are normal.

Tiers:
- strong: two wallets with the same fingerprint bought the same mint within CLOSE_SLOTS.
- candidate: wallets share an uncommon (non-round) fingerprint.
- weak: wallets share only a round preset (0.0001 / 0.001 ...); listed per preset, never chained.
Clusters chain wallets through uncommon fingerprints and strong pairs only.
Writes target_groups.csv.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations

from sno.multi_report import fee_platform_of, swqos_of

SRC = sys.argv[1] if len(sys.argv) > 1 else "backruns_oct8.client.csv"
PLATFORMS = {"Axiom", "GMGN", "Terminal (pump.fun)"}
DYNAMIC_PRIORITY = {"GMGN"}
PRESET_WALLETS = 15
CLOSE_SLOTS = 150
PROTOCOL_PROGRAMS = {"6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
                     "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"}

txs = {}
for line in open("target_txs.jsonl"):
    rec = json.loads(line)
    txs[rec["sig"]] = rec["tx"]


def fingerprint(tx):
    msg, meta = tx["transaction"]["message"], tx["meta"]
    signer = msg["accountKeys"][0]["pubkey"]
    inner = {g["index"]: g["instructions"] for g in meta.get("innerInstructions") or []}
    tips, unl = [], []
    for i, ix in enumerate(msg["instructions"]):
        seq = [(ix, None)]
        stack = {1: ix["programId"]}
        for ii in inner.get(i, []):
            h = ii.get("stackHeight") or 2
            stack[h] = ii["programId"]
            seq.append((ii, stack.get(h - 1)))
        for x, parent in seq:
            p = x.get("parsed")
            if not (isinstance(p, dict) and x.get("program") == "system" and p.get("type") == "transfer"):
                continue
            info = p["info"]
            if info["source"] != signer or parent in PROTOCOL_PROGRAMS:
                continue
            dst, lam = info["destination"], info["lamports"]
            if fee_platform_of(dst):
                continue
            sq = swqos_of(dst)
            if sq:
                tips.append((sq, lam))
            else:
                unl.append((dst, lam))
    priority = meta["fee"] - 5000 * len(tx["transaction"]["signatures"])
    return tips, unl, priority


def sol(lam):
    return f"{lam / 1e9:.9f}".rstrip("0").rstrip(".")


def sig_digits(lam):
    return len(str(lam).strip("0"))


def fmt_key(k):
    plat, parts, prio = k
    s = " + ".join(f"{p} {sol(l)}" for p, l in parts)
    return f"{plat} | tip {s}" + ("" if prio is None else f" | priority {sol(prio)}")


rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8-sig")) if r["target_platform"] in PLATFORMS]
per_tx = {}
for r in rows:
    sig = r["target_tx"]
    if sig in per_tx:
        continue
    tips, unl, prio = fingerprint(txs[sig])
    # No labeled tip: fall back to small unlabeled transfers (tip-like, e.g. GMGN BTG9wL...).
    parts = tuple(sorted(tips) or sorted(("unlabeled " + d[:6], l) for d, l in unl if l <= 50_000_000))
    plat = r["target_platform"]
    key = (plat, parts, None if plat in DYNAMIC_PRIORITY else prio) if parts else None
    per_tx[sig] = {"wallet": r["target_wallet"], "platform": plat, "key": key,
                   "mint": r["mint"], "slot": int(r["slot"]), "time": r["time_utc"]}

by_key = defaultdict(list)
for t in per_tx.values():
    if t["key"]:
        by_key[t["key"]].append(t)


def is_preset(k):
    _, parts, prio = k
    round_ = all(sig_digits(l) <= 2 for _, l in parts) and (prio is None or sig_digits(prio) <= 2)
    return round_ or len({t["wallet"] for t in by_key[k]}) >= PRESET_WALLETS


def close_pairs(ts):
    out = []
    for a, b in combinations(ts, 2):
        if a["wallet"] != b["wallet"] and a["mint"] == b["mint"] and abs(a["slot"] - b["slot"]) <= CLOSE_SLOTS:
            out.append((a, b))
    return out


parent = {}


def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    parent[find(a)] = find(b)


partners = defaultdict(set)
for k, ts in by_key.items():
    for a, b in close_pairs(ts):
        union(a["wallet"], b["wallet"])
        partners[a["wallet"]].add(b["wallet"])
        partners[b["wallet"]].add(a["wallet"])
    if not is_preset(k):
        ws = sorted({t["wallet"] for t in ts})
        for w in ws[1:]:
            union(ws[0], w)

wallet_txs = defaultdict(list)
for t in per_tx.values():
    wallet_txs[t["wallet"]].append(t)
    find(t["wallet"])

comps = defaultdict(set)
for w in wallet_txs:
    comps[find(w)].add(w)
clusters = []
for ws in comps.values():
    if len(ws) < 2:
        continue
    keys = Counter(t["key"] for w in ws for t in wallet_txs[w] if t["key"])
    clusters.append({"wallets": ws, "keys": keys,
                     "tier": "strong" if any(partners[w] & ws for w in ws) else "candidate"})
clusters.sort(key=lambda c: (c["tier"] != "strong", -len(c["wallets"])))
clustered = {w for c in clusters for w in c["wallets"]}

presets = []
for k, ts in by_key.items():
    ws = {t["wallet"] for t in ts}
    if is_preset(k) and len(ws) >= 2:
        presets.append({"key": k, "wallets": ws})
presets.sort(key=lambda p: -len(p["wallets"]))
in_preset = {w for p in presets for w in p["wallets"]}


def wallet_row(group, tier, size, w, keys=None):
    wt = wallet_txs[w]
    fps = sorted({fmt_key(t["key"]) for t in wt if t["key"] and (keys is None or t["key"] in keys)})
    return {"group": group, "tier": tier, "group_size": size, "target_wallet": w,
            "fingerprints": "; ".join(fps) or f"{wt[0]['platform']} | no tip",
            "same_mint_within_60s": " ".join(sorted(partners[w])), "target_txs": len(wt),
            "times_utc": " ".join(sorted(t["time"][11:19] for t in wt))}


out = []
for i, c in enumerate(clusters, 1):
    for w in sorted(c["wallets"]):
        out.append(wallet_row(f"C{i}", c["tier"], len(c["wallets"]), w))
for i, p in enumerate(presets, 1):
    for w in sorted(p["wallets"]):
        out.append(wallet_row(f"P{i}", "weak (common preset)", len(p["wallets"]), w, {p["key"]}))
for w in sorted(set(wallet_txs) - clustered - in_preset):
    out.append(wallet_row("", "single", 1, w))
with open("target_groups.csv", "w", newline="", encoding="utf-8-sig") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(out[0]))
    wr.writeheader()
    wr.writerows(out)

print(f"target txs {len(per_tx)}, wallets {len(wallet_txs)}, untipped txs {sum(1 for t in per_tx.values() if not t['key'])}")
print(f"clusters {len(clusters)} ({len(clustered)} wallets): "
      f"strong {sum(c['tier'] == 'strong' for c in clusters)}, candidate {sum(c['tier'] == 'candidate' for c in clusters)}; "
      f"preset buckets {len(presets)}; wallets in no group {len(set(wallet_txs) - clustered - in_preset)}")
for i, c in enumerate(clusters, 1):
    print(f"\nC{i} [{c['tier']}] {len(c['wallets'])} wallets")
    for k, n in c["keys"].most_common(4):
        print(f"   {n:3d}x  {fmt_key(k)}")
    for w in sorted(c["wallets"]):
        p = f"  <- same mint <=60s: {', '.join(x[:6] for x in sorted(partners[w] & c['wallets']))}" if partners[w] & c["wallets"] else ""
        print(f"    {w}{p}")
print("\npreset buckets (weak):")
for i, p in enumerate(presets, 1):
    print(f"  P{i}  {len(p['wallets']):3d} wallets  {fmt_key(p['key'])}")

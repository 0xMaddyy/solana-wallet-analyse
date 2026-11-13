import csv
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import rpc
from sno.multi_fetch import CSV
from sno.multi_report import DEX_NAMES, PLAIN_PROGRAMS, PLAT, fee_platform_of, swqos_of

PLAT["programs"].update({
    "6Vo3245eszAb5wuqEMw8mGdbfRUdKbHhDHP5LcaGuTAB": "pump.fun app (mobile router)",
    "MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e": "pump.fun app (router B)",
    "b1oomGGqPKGD6errbyfbVMBuzSC8WtAAYo8MwNafWW1": "Bloom",
    "DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH": "DFlow",
})
PROTOCOL_PROGRAMS = {"6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
                     "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"}


def platform_by_program(progs):
    for p in progs:
        if p in PLAT["programs"]:
            return PLAT["programs"][p]
        for pre, name in PLAT["program_prefixes"].items():
            if p.startswith(pre):
                return name
    return None


def label(sig):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    msg, meta = tx["transaction"]["message"], tx["meta"]
    signer = msg["accountKeys"][0]["pubkey"]
    top = msg["instructions"]
    inner = {g["index"]: g["instructions"] for g in meta.get("innerInstructions") or []}
    transfers = []
    all_programs = set()
    for i, ix in enumerate(top):
        all_programs.add(ix["programId"])
        stack = {1: ix["programId"]}
        p = ix.get("parsed")
        if isinstance(p, dict) and ix.get("program") == "system" and p.get("type") == "transfer":
            transfers.append((p["info"]["source"], p["info"]["destination"], p["info"]["lamports"], None))
        for ii in inner.get(i, []):
            h = ii.get("stackHeight") or 2
            stack[h] = ii["programId"]
            all_programs.add(ii["programId"])
            pp = ii.get("parsed")
            if isinstance(pp, dict) and ii.get("program") == "system" and pp.get("type") == "transfer":
                transfers.append((pp["info"]["source"], pp["info"]["destination"], pp["info"]["lamports"], stack.get(h - 1)))

    platform = platform_by_program([ix["programId"] for ix in top]) or platform_by_program(sorted(all_programs))
    fee_hits, tips, other = Counter(), defaultdict(int), defaultdict(int)
    for src, dst, lam, parent in transfers:
        if src != signer or parent in PROTOCOL_PROGRAMS:
            continue
        fp, sq = fee_platform_of(dst), swqos_of(dst)
        if fp:
            fee_hits[fp] += 1
        elif sq:
            tips[sq] += lam
        else:
            other[dst] += lam
    if not platform and fee_hits:
        platform = fee_hits.most_common(1)[0][0]
    if not platform and any(k.startswith("Nozomi (Axiom") for k in tips):
        platform = "Axiom (by private tip)"
    if not platform:
        nonplain = [ix["programId"] for ix in top if ix["programId"] not in PLAIN_PROGRAMS]
        if nonplain:
            platform = f"unknown router {nonplain[0]}"
        else:
            dex = "/".join(sorted({DEX_NAMES[p] for p in all_programs if p in DEX_NAMES})) or "unknown DEX"
            platform = f"direct {dex} (no router or known fee wallet)"
    return sig, {
        "target_platform": platform,
        "target_swqos": "; ".join(f"{k} {v / 1e9:.5f}" for k, v in sorted(tips.items())) or "none detected",
        "target_unlabeled_transfers": "; ".join(f"{d} {v / 1e9:.5f}" for d, v in sorted(other.items(), key=lambda kv: -kv[1])[:3]),
    }


rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
targets = sorted({r["target_tx"] for r in rows})
with ThreadPoolExecutor(12) as ex:
    labels = dict(ex.map(label, targets))
for r in rows:
    r.update(labels[r["target_tx"]])
out_path = sys.argv[1] if len(sys.argv) > 1 else CSV
with open(out_path, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

for col in ("target_platform", "target_swqos"):
    print(f"\n== {col}")
    for k, v in Counter(r[col].split(" 0.")[0] for r in rows).most_common(20):
        print(f"  {v:5d}  {k}")
unl, payers = Counter(), defaultdict(set)
for r in rows:
    for part in filter(None, r["target_unlabeled_transfers"].split("; ")):
        d = part.split(" ")[0]
        unl[d] += 1
        payers[d].add(r["target_wallet"])
print("\n== top unlabeled destinations (count, distinct paying wallets)")
for k, v in unl.most_common(25):
    print(f"  {v:5d} {len(payers[k]):5d}  {k}")
json.dump({k: v for k, v in unl.most_common(60)}, open("unlabeled_top.json", "w"), indent=0)

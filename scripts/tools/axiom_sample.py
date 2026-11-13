import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import sys

from sno.analyze import rpc

AXIOM_PDAS = {"3Tu1Y9aNveLFN4WTAwnAwXL6tbUp5MMe3RxyybG4jTAS", "3PvqoztjnRxaAiFmLuEfqZkU4GSbjUareks8S2xCZaTa",
              "HkJYryz2BNeMQfuuSWDYktWt5fZLV26eK6nqu7EJycoG", "ECDrSz47nXihe5kyK4oWEePPsPi9qz6u5d6Fa2sDj3uM",
              "2ApLdwLrGayEmxgpLX9BTR47Q2QprfMg5SpjrLeaK8s7", "5vPNE6VFyXmCmzmWotdxmRk57LEWiXxuAfZL3hKbi2LH",
              "EqGzowSp6cKAsMSRyyrFTaBxnZEVeNY81LC18YFy8Cx9"}
from sno.paths import label_file
labels = json.load(open(label_file("labels_swqos.json")))
plat = json.load(open(label_file("labels_platforms.json")))["fee_wallets"]
rows = list(csv.DictReader(open("backruns_oct8.csv", encoding="utf-8-sig")))
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
picked = [r for r in rows if any(a in r["target_unlabeled_transfers"] for a in AXIOM_PDAS)][:n]
for r in picked:
    sig = r["target_tx"]
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    msg, meta = tx["transaction"]["message"], tx["meta"]
    print("\n==", sig, r["target_swqos"], "|", r["target_unlabeled_transfers"])
    inner = {g["index"]: g["instructions"] for g in meta.get("innerInstructions") or []}
    for i, ix in enumerate(msg["instructions"]):
        p = ix.get("parsed")
        desc = f"{p['type']} {json.dumps(p.get('info'))[:160]}" if isinstance(p, dict) else f"data={ix.get('data', '')[:30]} accts={len(ix.get('accounts', []))}"
        print(f"  [{i}] {ix['programId'][:12]} {desc}")
        for ii in inner.get(i, []):
            pp = ii.get("parsed")
            if isinstance(pp, dict) and pp.get("type") == "transfer" and ii.get("program") == "system":
                d = pp["info"]["destination"]
                tag = labels.get(d) or plat.get(d) or ("AXIOM_PDA" if d in AXIOM_PDAS else "")
                print(f"      -> transfer {pp['info']['lamports'] / 1e9:.5f} to {d} {tag}")
    for line in meta.get("logMessages", [])[:12]:
        print("   log:", line[:140])

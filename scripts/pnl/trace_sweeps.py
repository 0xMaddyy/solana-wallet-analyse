import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter

from sno.analyze import get_tx, rpc

GROUPS = {
    "A (min 0.005)": ["3Tu1Y9aNveLFN4WTAwnAwXL6tbUp5MMe3RxyybG4jTAS", "3PvqoztjnRxaAiFmLuEfqZkU4GSbjUareks8S2xCZaTa",
                      "HkJYryz2BNeMQfuuSWDYktWt5fZLV26eK6nqu7EJycoG"],
    "B (min 0.00001)": ["8GV86MhDQST6rh56oTMU9v5TdHwRtXnFQ3zdGD3WT3mG", "H9bSW2VTrRU7LuT5Zo5XEx3uuGhLDTeAJdEUxQX39314",
                        "DU3oUMrzewfvuUN8HNA3rXTvbscCA3krY365mzfFixrT"],
    "Jupiter-row": ["HR6xhpJYYiTvmAtUZvpLMN7qbr6TxCw1Sgq3fab8vCoa"],
    "Bloom-row": ["7HeD6sLLqAnKVRuSfc1Ko3BSPMNKWgGTiWLKXJF31vKM"],
}

for group, addrs in GROUPS.items():
    for a in addrs:
        info = rpc("getAccountInfo", [a, {"encoding": "base64"}])["value"]
        sigs = rpc("getSignaturesForAddress", [a, {"limit": 1000}])
        outs = Counter()
        checked = 0
        for s in sigs:
            if checked >= 400:
                break
            tx = get_tx(s["signature"])
            checked += 1
            if not tx:
                continue
            keys = [k["pubkey"] for k in tx["transaction"]["message"]["accountKeys"]]
            if keys[0] != a:
                continue
            for ix in tx["transaction"]["message"]["instructions"]:
                p = ix.get("parsed")
                if isinstance(p, dict) and p.get("type") == "transfer" and p["info"].get("source") == a:
                    outs[p["info"]["destination"]] += p["info"]["lamports"]
        print(f"{group:16s} {a}  owner {info['owner'] if info else None}  balance {info['lamports'] / 1e9 if info else 0:.3f}  "
              f"recent sigs {len(sigs)}  outgoing (signed by itself): {[(d, round(v / 1e9, 3)) for d, v in outs.most_common(3)]}")

rows = list(csv.DictReader(open("backruns_oct8.csv", encoding="utf-8-sig")))
direct = [r for r in rows if r["target_platform"].startswith("direct")]
print(f"\ndirect pump.fun targets: {len(direct)}")
print("  swqos:", Counter(r["target_swqos"].split(" 0.")[0] for r in direct).most_common(6))
print("  with unlabeled transfers:", sum(1 for r in direct if r["target_unlabeled_transfers"]))
print("  jitodontfront:", sum(1 for r in direct if r["target_jitodontfront"] == "True"))

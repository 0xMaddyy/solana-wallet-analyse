import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json

wallets = json.load(open("target_wallets_list.json", encoding="utf-8"))
sol = json.load(open("solscan_names.json", encoding="utf-8"))
orb = json.load(open("orb_names.json", encoding="utf-8"))
missing_sol = [a for a in sol if a not in set(wallets)]
missing_orb = [a for a in orb if a not in set(wallets)]
with open("target_wallets_named.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["target_wallet", "solscan_name", "orb_name"])
    for a in wallets:
        w.writerow([a, sol.get(a, ""), orb.get(a, "")])
print("rows", len(wallets))
print("solscan", sum(1 for a in wallets if sol.get(a)))
print("orb", sum(1 for a in wallets if orb.get(a)))
print("both", sum(1 for a in wallets if sol.get(a) and orb.get(a)))
print("extra_sol", len(missing_sol), "extra_orb", len(missing_orb))

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json

files = [
    "backruns_oct8.csv", "backruns_oct12.csv", "backruns_oct13.csv",
    "backruns_oct14.csv", "backruns_oct15.csv", "backruns_oct16.csv",
    "backruns_oct17.csv", "backruns_oct18.csv", "backruns_oct19.csv",
    "backruns_oct20.csv", "backruns_oct21.csv",
]
wallets = []
seen = set()
for f in files:
    for r in csv.DictReader(open(f, encoding="utf-8-sig")):
        w = (r.get("target_wallet") or "").strip()
        if w and w not in seen:
            seen.add(w)
            wallets.append(w)
wallets.sort()
json.dump(wallets, open("target_wallets_list.json", "w"), indent=0)
print(len(wallets))

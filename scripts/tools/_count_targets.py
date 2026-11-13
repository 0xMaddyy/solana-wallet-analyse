import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter

files = [
    "backruns_oct8.csv", "backruns_oct12.csv", "backruns_oct13.csv",
    "backruns_oct14.csv", "backruns_oct15.csv", "backruns_oct16.csv",
    "backruns_oct17.csv", "backruns_oct18.csv", "backruns_oct19.csv",
    "backruns_oct20.csv", "backruns_oct21.csv",
]
wallets = Counter()
for f in files:
    n = 0
    for r in csv.DictReader(open(f, encoding="utf-8-sig")):
        w = (r.get("target_wallet") or "").strip()
        if w:
            wallets[w] += 1
            n += 1
    print(f, n, "unique so far", len(wallets))
print("unique", len(wallets))

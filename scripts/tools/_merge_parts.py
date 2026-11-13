import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import glob
import json
base = json.load(open("solscan_names.json", encoding="utf-8"))
for p in sorted(glob.glob("_sol_part*.json")):
    base.update(json.load(open(p, encoding="utf-8")))
json.dump(base, open("solscan_names.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(base))

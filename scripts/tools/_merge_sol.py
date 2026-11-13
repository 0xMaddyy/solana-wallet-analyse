import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
base = {}
try:
    base.update(json.load(open("solscan_names_00.json", encoding="utf-8")))
except FileNotFoundError:
    pass
try:
    base.update(json.load(open("solscan_names.json", encoding="utf-8")))
except FileNotFoundError:
    pass
base.update(json.load(open("_sol_extra.json", encoding="utf-8")))
json.dump(base, open("solscan_names.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(base))

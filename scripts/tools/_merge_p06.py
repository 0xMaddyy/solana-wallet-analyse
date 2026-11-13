import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
base = json.load(open("solscan_names.json", encoding="utf-8"))
base.update(json.load(open("_sol_part06.json", encoding="utf-8")))
json.dump(base, open("solscan_names.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(base))

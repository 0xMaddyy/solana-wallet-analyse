import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
path = "orb_names.json"
data = json.load(open(path, encoding="utf-8"))
extra = json.load(open("_orb_extra.json", encoding="utf-8"))
data.update(extra)
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)
print(len(data))

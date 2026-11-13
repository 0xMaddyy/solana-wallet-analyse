import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
wallets = json.load(open("target_wallets_list.json", encoding="utf-8"))
size = 150
for i in range(0, len(wallets), size):
    part = wallets[i:i + size]
    json.dump(part, open(f"name_part_{i // size:02d}.json", "w"), separators=(",", ":"))
print("parts", (len(wallets) + size - 1) // size, "last", len(wallets) % size or size)

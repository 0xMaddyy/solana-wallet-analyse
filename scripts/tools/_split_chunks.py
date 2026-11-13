import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
wallets = json.load(open("target_wallets_list.json", encoding="utf-8"))
n = 400
for i in range(0, len(wallets), n):
    chunk = wallets[i:i + n]
    json.dump(chunk, open(f"name_chunk_{i // n:02d}.json", "w"), separators=(",", ":"))
    print(i // n, len(chunk))

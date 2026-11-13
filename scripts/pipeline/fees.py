import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json

from sno.analyze import JITO_TIPS, get_tx

results = json.load(open("results.json"))
for x in results:
    b, p = x["bot"], x["prev"]
    adjacent = bool(p and set(p["mints_bought"]) & set(b["mints_bought"]))
    bt = get_tx(b["sig"])
    pt = get_tx(x["prev_sig"]) if adjacent else None
    tipped = any(d in JITO_TIPS for d, _ in b["transfers"])
    print(f"slot {b['slot']} adjacent={adjacent!s:5} jito={tipped!s:5} "
          f"bot fee {bt['meta']['fee'] / 1e9:.6f} CU {bt['meta'].get('computeUnitsConsumed')} "
          f"first prog {b['programs'][0][:8]}"
          + (f" | target fee {pt['meta']['fee'] / 1e9:.6f}" if pt else ""))

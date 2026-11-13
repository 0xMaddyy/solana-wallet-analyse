import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import os
import sys

from sno.analyze import get_tx, rpc, summarize

prefix = sys.argv[1] if len(sys.argv) > 1 else "6YY2VS44"
d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "botcheck", "result.json")))
for b in [x for x in d["buys"] if x["leader"].startswith(prefix)]:
    blk = rpc("getBlock", [b["slot"], {"transactionDetails": "signatures", "rewards": False,
                                       "maxSupportedTransactionVersion": 1}])
    sigs = blk["signatures"]
    i = sigs.index(b["sig"])
    tx = get_tx(b["sig"])
    me = summarize(tx)
    prev = summarize(get_tx(sigs[i - 1])) if i else None
    adjacent = bool(prev and set(prev["mints_bought"]) & set(me["mints_bought"]))
    print(f"slot {b['slot']} idx {i}/{len(sigs)} buy {b['sol_out']:.3f} "
          f"{'ADJACENT backrun' if adjacent else 'not adjacent'} bot fee {tx['meta']['fee'] / 1e9:.6f} "
          f"first prog {me['programs'][0][:8]} prev signer {prev['signer'][:8] if prev else None}")

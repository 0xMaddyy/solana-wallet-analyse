import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter

from sno.multi_fetch import PAIRS, out_path
from sno.multi_report import pair_mints, pair_sol

kinds = Counter()
examples = []
for buyer, seller in PAIRS:
    pair = {buyer, seller}
    for l in open(out_path(buyer)):
        t = json.loads(l)
        if t.get("missing") or t["err"] is not None:
            continue
        mints = pair_mints(t, pair)
        if not mints or pair_sol(t, pair) < 0 or not any(d > 0 for d in mints.values()):
            continue
        signer_in = t["signers"][0] in pair
        k = ("signed by pair" if signer_in else "signed by outsider", len(mints), any(d < 0 for d in mints.values()))
        kinds[k] += 1
        if len(examples) < 6 and (not signer_in or len(examples) < 3):
            examples.append((buyer[:8], t["sig"], t["signers"][0][:8], pair_sol(t, pair), mints, t["dsol"]))
print(kinds)
for e in examples:
    print(e)

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json

tags = json.load(open("sources/orb_tags.json"))
owners = json.load(open("unl_owners.json"))["owners"]
left = [o for o in json.load(open("unl_none.json")) if o["addr"] not in tags]
print(len(left), "unresolved,", sum(o["rows"] for o in left), "row hits")
for o in left:
    own = owners.get(o["addr"])
    own = "none" if own is None else ("system" if own.startswith("1111") else own[:10])
    print(f"{o['rows']:4d} {o['addr']:45s} {own:10s} {o['med']:.5f} {list(o['platforms'])[0][:40]}")
print(",".join(o["addr"] for o in left))

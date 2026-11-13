import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import RPC, rpc

KEY = RPC.split("api-key=")[1]
addrs = [o["addr"] for o in json.load(open("unl_none.json"))]

owners = {}
for i in range(0, len(addrs), 100):
    chunk = addrs[i:i + 100]
    res = rpc("getMultipleAccounts", [chunk, {"encoding": "base64", "dataSlice": {"offset": 0, "length": 0}}])["value"]
    for a, acc in zip(chunk, res):
        owners[a] = acc["owner"] if acc else None


def funded_by(a):
    url = f"https://api.helius.xyz/v1/wallet/{a}/funded-by?api-key={KEY}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return a, json.loads(r.read())
    except Exception as e:
        return a, {"error": str(e)}


with ThreadPoolExecutor(8) as ex:
    funders = dict(ex.map(funded_by, addrs))

json.dump({"owners": owners, "funders": funders}, open("unl_owners.json", "w"), indent=0)
print(json.dumps(funders[addrs[0]])[:500])
from collections import Counter
print(Counter(owners.values()))

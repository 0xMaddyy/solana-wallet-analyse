import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request

URLS = [
    "https://solana-mainnet.rpc.extrnode.com",
    "https://solana.api.onfinality.io/public",
    "https://solana.rpc.subquery.network/public",
    "https://public.rpc.solanavibestation.com",
    "https://api.mainnet.rpcpool.com",
    "https://rpc.hellomoon.io",
]
body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []}).encode()
for url in URLS:
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.loads(r.read())
        print(url, "ok", out.get("result"))
    except Exception as e:
        print(url, type(e).__name__, e)

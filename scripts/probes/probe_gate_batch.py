import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import time
import urllib.request

from sno.analyze import RPC

base = [
    "8jdHSCJRer9j6LWsYpBeo3BgmZz3cfAqYn8rqiZcpump",
    "BnsM4vV4F4sM2tHx4ttsceL256VVRtnLwG3TZGrpump",
    "5xri1bAx8YEYe5JZ25tehxcxehfJD76NJq5YbGFepump",
    "BeFPuzVLBKZ8pEmMpj4g9Dzj1F2ke798jQmCesUWpump",
    "Cdg9seoR2yiNf4dgdwCasbco43FgEGM189V4wkepxY7Z",
]
mints = base * 4
body = json.dumps([
    {"jsonrpc": "2.0", "id": i, "method": "getSignaturesForAddress",
     "params": [m, {"limit": 15}]}
    for i, m in enumerate(mints)
]).encode()
t0 = time.time()
req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as r:
    out = json.loads(r.read())
print(f"{time.time() - t0:.2f}s n={len(out)} err={sum('error' in x for x in out)} lens={[len(x.get('result') or []) for x in out]}")

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request

addrs = [
    "1krnKHh9AqrLsA9jRusuD1AUJhzTu3cmD7TvwtroKAJ",
    "4vw54BmAogeRV3vPKWyFet5yf8DTLcREzdSzx4rw9Ud9",
]
body = json.dumps({"addresses": addrs}).encode()
req = urllib.request.Request(
    "https://orbmarkets.io/api/tags/resolve",
    data=body,
    headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://orbmarkets.io",
        "Referer": "https://orbmarkets.io/",
    },
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(r.status, r.read()[:400])
except Exception as e:
    raw = e.read()[:300] if hasattr(e, "read") else str(e).encode()
    print(getattr(e, "code", 0), raw[:300])

"""See which public fields Solscan and Orb return for one labeled wallet."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request

KNOWN = "4vw54BmAogeRV3vPKWyFet5yf8DTLcREzdSzx4rw9Ud9"  # Decu


def get(url, headers=None, data=None, timeout=25):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()[:4000]
    except Exception as e:
        body = e.read()[:600] if hasattr(e, "read") else str(e).encode()
        return getattr(e, "code", 0), body


def show(label, status, body):
    text = body.decode("utf-8", "replace")
    print(f"\n== {label} {status} {len(text)}")
    print(text[:1500].replace("\n", " "))


sol = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://solscan.io",
    "Referer": "https://solscan.io/",
}
urls = [
    ("solscan account", f"https://api-v2.solscan.io/v2/account?address={KNOWN}", sol),
    ("solscan meta", f"https://api-v2.solscan.io/v2/account/metadata?address={KNOWN}", sol),
    ("solscan domain", f"https://api-v2.solscan.io/v2/account/domain?address={KNOWN}", sol),
    ("orb v1", f"https://api.orbmarkets.io/v1/address/{KNOWN}", None),
    ("orb api address", f"https://orbmarkets.io/api/address/{KNOWN}", None),
    ("orb page", f"https://orbmarkets.io/address/{KNOWN}", None),
]
for label, url, headers in urls:
    show(label, *get(url, headers))

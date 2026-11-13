"""Probe public name sources for one known wallet and one target wallet."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import urllib.request

KNOWN = "13gj9sYDkj42PsC7koDk2cR9mj2YpVQxWvSBLcJcLkzG"  # @jo5htheboss on Orb
TARGET = "4vw54BmAogeRV3vPKWyFet5yf8DTLcREzdSzx4rw9Ud9"
RPC = __import__('os').environ.get('SNO_RPC_URL') or __import__('os').environ.get('HELIUS_RPC_URL')
if not RPC:
    raise RuntimeError('Set SNO_RPC_URL or HELIUS_RPC_URL')
KEY = RPC.split("api-key=")[1]


def get(url, headers=None, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, r.headers.get("content-type", ""), body[:2500]
    except Exception as e:
        if hasattr(e, "read"):
            return getattr(e, "code", 0), "", e.read()[:800]
        return 0, "", str(e).encode()


def show(label, status, ctype, body):
    text = body.decode("utf-8", "replace")
    print(f"\n== {label} {status} {ctype} {len(text)}")
    print(text[:1200].replace("\n", " ")[:1200])


urls = [
    ("orb html", f"https://orbmarkets.io/address/{KNOWN}"),
    ("orb api", f"https://api.orbmarkets.io/v1/address/{KNOWN}"),
    ("helius identity", f"https://api.helius.xyz/v1/wallet/{KNOWN}/identity?api-key={KEY}"),
    ("helius identity mainnet", f"https://mainnet.helius-rpc.com/v1/wallet/{KNOWN}/identity?api-key={KEY}"),
]
for label, url in urls:
    show(label, *get(url))

body = json.dumps({"addresses": [KNOWN, TARGET]}).encode()
show("batch identity", *get(
    f"https://api.helius.xyz/v1/wallet/batch-identity?api-key={KEY}",
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    data=body,
))

sol_headers = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://solscan.io",
    "Referer": "https://solscan.io/",
}
show("solscan v2", *get(f"https://api-v2.solscan.io/v2/account?address={KNOWN}", sol_headers))
show("solscan meta", *get(f"https://api-v2.solscan.io/v2/account/metadata?address={KNOWN}", sol_headers))

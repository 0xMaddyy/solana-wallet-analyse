"""Find Token-2022/Token approve delegates (sellers) for the new buyer wallets."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from sno.analyze import rpc, get_tx

BUYERS = [
    "BPKVyybfMjhTEDFWBYa2wDnRV5a4Z3Lks8ZfMec3qUAW",
    "E7hhZy9v9v2WwPx72yf8gTYF5AcJoVaSWVuJ31tueN5C",
    "FaHvzFA7qJzZQ2kc3wA6gM6TyKKakGSfdqSy1vZ5hXB",
    "TMWwfSM5LjA17HaWAFkvu3WXuwgk1SZ5iTuzEwdoci9",
    "FdBhsbFNpEPQSyme9WMUaUoFWfF4Qfnrc7tBihU6HbkQ",
]
KNOWN = {
    "3pDHoZBjQhAf9w5zTWsVyys7NxiQdewbjj6jnZcKP9ya": "C8qCb6smwarmisb89kUejVsd8uHHj96AXWT2Ex1XD33i",
    "2PAijCsZGAmG8tVgrAmwyGC5UcXxwktYkAiy57CAXTuy": "Bj5PgdHXkZT4bw7YxQXuBeSbjfqqHgMoZAsDxdaYzGSt",
    "5qsuh6KapqaF6WdhdvqBKF8JiQxVmnXD7Uqr8D36iePp": "FzwbhYksjD9JJTFwZozcQQmXMKDCmY1uMz71daBAoMsy",
    "DTGbH68GcJujkim2BfGG7nHUv5Sox4GBJKsdDRKutANm": "Fa9qPovB2gxs67eCxWM9KheYJH9BgyPjGBqj8cL1bLRG",
    "CH7GewnUqV8pdnjywGz71QVFRZ549BsDqNnpBxhzREQk": "EKn5wiBAQ2UuMTAK94gPmqFabVSMCxWtzHRKxRqMYzP7",
    "8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF": "HZUCsc7pThddRkSW8CyBfvHo4ZskrHMsg7uK46Mk1nS7",
}


def delegates_in_tx(tx):
    out = []
    meta = tx["meta"]
    msg = tx["transaction"]["message"]
    ixs = list(msg.get("instructions") or [])
    for g in meta.get("innerInstructions") or []:
        ixs += g.get("instructions") or []
    for ix in ixs:
        p = ix.get("parsed")
        if not isinstance(p, dict):
            continue
        if p.get("type") in ("approve", "approveChecked"):
            info = p.get("info") or {}
            d = info.get("delegate")
            if d:
                out.append(d)
    return out


for buyer in BUYERS:
    sigs = rpc("getSignaturesForAddress", [buyer, {"limit": 40}]) or []
    dels = Counter()
    checked = 0
    for s in sigs:
        if s.get("err"):
            continue
        tx = get_tx(s["signature"])
        if not tx:
            continue
        checked += 1
        for d in delegates_in_tx(tx):
            if d != buyer:
                dels[d] += 1
        if checked >= 15:
            break
    top = dels.most_common(3)
    print(f"{buyer[:8]}  checked={checked}  delegates={top}")

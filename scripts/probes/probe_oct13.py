"""Probe the Oct 13 activity of candidate bot wallets: tx count, buys/sells, delegate approvals."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.analyze import rpc

WALLETS = sys.argv[1:] or [l.strip() for l in open("wallets_oct13.txt") if l.strip()]
MAX_PAGES = 60
START = int(datetime(2026, 10, 13, tzinfo=timezone.utc).timestamp())
END = START + 86400


def sigs_in_day(addr, cap=6000):
    out, before, pages = [], None, 0
    while len(out) < cap and pages < MAX_PAGES:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = rpc("getSignaturesForAddress", [addr, opts])
        pages += 1
        if not page:
            break
        if pages % 5 == 0:
            print(f"   {addr[:6]} page {pages} at {datetime.fromtimestamp(page[-1].get('blockTime') or 0, timezone.utc)}", flush=True)
        out += [s for s in page if s.get("blockTime") and START <= s["blockTime"] < END]
        before = page[-1]["signature"]
        if (page[-1].get("blockTime") or END) < START:
            break
    return out


def look(sig, wallet):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    msg, meta = tx["transaction"]["message"], tx["meta"]
    signers = [k["pubkey"] for k in msg["accountKeys"] if k.get("signer")]
    delegates = set()
    for ix in msg["instructions"] + [i for g in meta.get("innerInstructions") or [] for i in g["instructions"]]:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") in ("approve", "approveChecked"):
            delegates.add(p["info"].get("delegate"))
    tok = Counter()
    for side, sign in (("preTokenBalances", -1), ("postTokenBalances", 1)):
        for b in meta.get(side) or []:
            if b.get("owner") == wallet:
                tok[b["mint"]] += sign * int(b["uiTokenAmount"]["amount"])
    keys = [k["pubkey"] for k in msg["accountKeys"]]
    dsol = meta["postBalances"][keys.index(wallet)] - meta["preBalances"][keys.index(wallet)] if wallet in keys else 0
    kind = "other"
    moved = {m: d for m, d in tok.items() if d and not m.startswith("So111")}
    if moved:
        kind = "buy" if all(d > 0 for d in moved.values()) else "sell" if all(d < 0 for d in moved.values()) else "mixed"
    return {"signer0": signers[0], "wallet_signs": wallet in signers, "delegates": delegates, "kind": kind,
            "err": meta["err"] is not None, "dsol": dsol}


for w in WALLETS:
    sigs = sigs_in_day(w)
    ok = [s["signature"] for s in sigs if not s.get("err")]
    sample = ok[:: max(1, len(ok) // 40)][:40]
    with ThreadPoolExecutor(10) as ex:
        res = list(ex.map(lambda s: look(s, w), sample))
    kinds = Counter((r["kind"], r["wallet_signs"]) for r in res)
    other_signers = Counter(r["signer0"] for r in res if r["signer0"] != w)
    dels = Counter(d for r in res for d in r["delegates"] if d)
    print(f"{w}  oct13 txs {len(sigs)} (failed {len(sigs) - len(ok)})  sample {len(sample)}")
    print(f"   kinds (kind, wallet signs): {dict(kinds)}")
    print(f"   other fee payers: {dict(other_signers.most_common(3))}  delegates approved: {dict(dels.most_common(3))}")

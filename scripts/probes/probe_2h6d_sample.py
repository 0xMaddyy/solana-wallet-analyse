"""Slowly fetch 12 successful txs spread across Oct 16-17 and print shape."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import time
import urllib.request
from datetime import datetime, timezone

RPC = "https://api.mainnet-beta.solana.com"
W = "2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf"
sigs = json.load(open("2h6d_sigs.json"))
pick = [sigs[i] for i in range(0, len(sigs), max(1, len(sigs) // 12))][:12]


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except Exception as e:
            time.sleep(2 * (attempt + 1))
            print("retry", e, flush=True)
    raise RuntimeError("give up")


for s in pick:
    tx = rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    msg, meta = tx["transaction"]["message"], tx["meta"]
    progs = []
    for ix in msg["instructions"]:
        progs.append(ix["programId"][:8])
    ups = []
    signer = next(k["pubkey"] for k in msg["accountKeys"] if k.get("signer"))
    for b in meta.get("postTokenBalances") or []:
        if b.get("owner") != signer:
            continue
        pre = next((p for p in (meta.get("preTokenBalances") or [])
                    if p["accountIndex"] == b["accountIndex"] and p["mint"] == b["mint"]), None)
        before = int(pre["uiTokenAmount"]["amount"]) if pre else 0
        d = int(b["uiTokenAmount"]["amount"]) - before
        if d > 0 and not b["mint"].startswith("So111"):
            ups.append(b["mint"][:6])
    i = msg["accountKeys"][0]["pubkey"]
    # signer sol
    keys = [k["pubkey"] for k in msg["accountKeys"]]
    si = keys.index(signer)
    dsol = (meta["postBalances"][si] - meta["preBalances"][si]) / 1e9
    print(datetime.fromtimestamp(s["blockTime"], timezone.utc), f"dsol {dsol:+.4f}", "up", ups, "progs", progs, flush=True)
    time.sleep(0.8)

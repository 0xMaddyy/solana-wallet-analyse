"""Page 2H6Dwrq signatures for Oct 16-17 and dump one successful buy."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone

RPC = "https://api.mainnet-beta.solana.com"
W = "2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf"
START = int(datetime(2026, 10, 16, tzinfo=timezone.utc).timestamp())


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(8):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except Exception as e:
            if attempt == 7:
                raise
            time.sleep(1.2 * (attempt + 1))
            print("retry", attempt, type(e).__name__, file=__import__("sys").stderr, flush=True)


ok, fail, before = [], 0, None
while True:
    opts = {"limit": 1000}
    if before:
        opts["before"] = before
    page = rpc("getSignaturesForAddress", [W, opts])
    if not page:
        break
    for s in page:
        bt = s.get("blockTime") or 0
        if bt >= START:
            (fail := fail + 1) if s.get("err") else ok.append(s)
    before = page[-1]["signature"]
    oldest = page[-1].get("blockTime") or 0
    print(f"page {len(page)} oldest {datetime.fromtimestamp(oldest, timezone.utc)} ok {len(ok)} fail {fail}", flush=True)
    if oldest < START or len(page) < 1000:
        break
    time.sleep(0.4)

print("DONE", len(ok), fail)
if ok:
    print("newest", datetime.fromtimestamp(ok[0]["blockTime"], timezone.utc))
    print("oldest ok", datetime.fromtimestamp(ok[-1]["blockTime"], timezone.utc))
json.dump([{"signature": s["signature"], "slot": s["slot"], "blockTime": s["blockTime"]} for s in ok],
          open("2h6d_sigs.json", "w"))

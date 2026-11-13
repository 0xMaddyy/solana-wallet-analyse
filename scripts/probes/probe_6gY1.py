"""Sample callers of 6gY1osm and dump one successful tx's instruction shape."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import Counter
from datetime import datetime, timezone

from sno.analyze import rpc

PROG = "6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi"

out, before = [], None
for page_i in range(8):
    opts = {"limit": 1000}
    if before:
        opts["before"] = before
    page = rpc("getSignaturesForAddress", [PROG, opts])
    if not page:
        break
    out += page
    before = page[-1]["signature"]
    t0 = datetime.fromtimestamp(page[0]["blockTime"], timezone.utc)
    t1 = datetime.fromtimestamp(page[-1]["blockTime"], timezone.utc)
    print(f"page {page_i} n={len(page)} {t0} .. {t1} err={sum(1 for s in page if s.get('err'))}", flush=True)

print("total", len(out), "failed", sum(1 for s in out if s.get("err")))
# one success
ok = next(s for s in out if not s.get("err"))
tx = rpc("getTransaction", [ok["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
msg, meta = tx["transaction"]["message"], tx["meta"]
keys = msg["accountKeys"]
print("sample", ok["signature"])
print("signers", [k["pubkey"] for k in keys if k.get("signer")])
print("fee payer", keys[0]["pubkey"], "fee", meta["fee"])
print("outer programs:")
for i, ix in enumerate(msg["instructions"]):
    data = ix.get("data", "")
    print(f"  #{i} {ix['programId']} accounts={len(ix.get('accounts') or [])} data={data[:40]}")
inner = Counter()
for g in meta.get("innerInstructions") or []:
    for ii in g["instructions"]:
        inner[ii["programId"]] += 1
print("inner", inner.most_common())
json.dump({"sig": ok["signature"], "slot": tx["slot"]}, open("probe_6gY1_sample.json", "w"))

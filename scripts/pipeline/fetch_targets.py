"""Cache the target txs of backruns_oct8.client.csv into target_txs.jsonl."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import rpc

src = sys.argv[1] if len(sys.argv) > 1 else "backruns_oct8.client.csv"
out = "target_txs.jsonl"
rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
have = set()
if os.path.exists(out):
    have = {json.loads(l)["sig"] for l in open(out)}
todo = sorted({r["target_tx"] for r in rows} - have)
print("to fetch", len(todo))


def fetch(sig):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    return {"sig": sig, "tx": tx}


with open(out, "a") as fh, ThreadPoolExecutor(12) as ex:
    for i, rec in enumerate(ex.map(fetch, todo)):
        fh.write(json.dumps(rec) + "\n")
        if i % 200 == 0:
            print(i)

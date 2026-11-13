import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from sno.analyze import get_tx

FAIL = "pXWskrQdi8bT7T9nmmdXsNoKDfGcRincUAKv429She2RQMbiMes7uBRMwmJ4A5GzjyhfJhrESyHD6j5hn9eEnr1"
OK = "3DVgorh9DGPo8v1fNHbncSzp9UT3eeGe3bGmwV4NfP8jn6zgGjdujhZ4ToF2U7qXMynMG6qpHYSkAD7xz6dL8f1o"
TARGET = "4pGreVTK5yA8mUmM1HxP2BDcdcfpx3oKHxzrCmx5rE9anjN8CAMerCRvugrfLtuF5HLW8xhChjCU8Rp5EDJjsXri"

def show(name, tx):
    print("\n==", name, "index would be in meta", "slot", tx["slot"])
    for i, ix in enumerate(tx["transaction"]["message"]["instructions"]):
        p = ix.get("parsed")
        if isinstance(p, dict):
            print(i, ix["programId"][:8], p.get("type"), json.dumps(p.get("info"), default=str)[:400])
    logs = tx["meta"].get("logMessages") or []
    for line in logs:
        if "Instruction:" in line or "Create" in line or "incorrect" in line.lower():
            print("LOG", line)

for name, sig in [("FAIL", FAIL), ("OK", OK), ("TARGET", TARGET)]:
    show(name, get_tx(sig))

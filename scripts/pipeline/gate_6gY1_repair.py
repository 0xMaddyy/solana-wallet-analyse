"""Rebuild gate_6gY1_txs.jsonl after concurrent appends split some lines."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import os

src = "gate_6gY1_txs.jsonl"
dst = "gate_6gY1_txs.repaired.jsonl"
dec = json.JSONDecoder()
buf, n, dropped = "", 0, 0
seen = set()
with open(src, encoding="utf-8") as fh, open(dst, "w", encoding="utf-8") as out:
    for line in fh:
        buf += line
        while True:
            s = buf.lstrip()
            if not s:
                buf = ""
                break
            try:
                obj, end = dec.raw_decode(s)
            except json.JSONDecodeError:
                if len(buf) > 5_000_000:
                    dropped += 1
                    buf = ""
                break
            buf = s[end:]
            sig = obj.get("sig") if isinstance(obj, dict) else None
            if not sig or sig in seen:
                continue
            seen.add(sig)
            out.write(json.dumps(obj) + "\n")
            n += 1
            if n % 20000 == 0:
                print(n, flush=True)
    if buf.strip():
        dropped += 1
print("kept", n, "dropped fragments", dropped)
os.replace(dst, src)
print("replaced")

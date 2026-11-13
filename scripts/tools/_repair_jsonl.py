import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import glob
import json
import os

for path in sorted(glob.glob("multi_oct1[6-8]_*.jsonl")):
    with open(path, "rb") as fh:
        data = fh.read()
    if not data:
        print(f"{path} empty")
        continue
    if not data.endswith(b"\n"):
        nl = data.rfind(b"\n")
        data = data[: nl + 1] if nl >= 0 else b""
        with open(path, "wb") as fh:
            fh.write(data)
        print(f"{path} truncated partial line")
    n = bad = 0
    kept = []
    for line in data.splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
            kept.append(line)
            n += 1
        except json.JSONDecodeError:
            bad += 1
    if bad:
        with open(path, "wb") as fh:
            fh.write(b"\n".join(kept) + (b"\n" if kept else b""))
        print(f"{path} dropped {bad} bad lines, kept {n}")
    else:
        print(f"{path} ok {n}")

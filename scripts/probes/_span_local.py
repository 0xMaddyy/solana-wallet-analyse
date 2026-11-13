import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from datetime import datetime, timezone
rows = []
for i, line in enumerate(open("oct20_allsigs.jsonl", encoding="utf-8")):
    if not line.strip():
        continue
    r = json.loads(line)
    rows.append((r["blockTime"], r["slot"]))
rows.sort()
print("n", len(rows))
print("first", datetime.fromtimestamp(rows[0][0], timezone.utc), rows[0])
print("last", datetime.fromtimestamp(rows[-1][0], timezone.utc), rows[-1])
# rate
a, b = rows[0], rows[-1]
rate = (b[1] - a[1]) / (b[0] - a[0])
print("slots per sec", rate)
start = int(datetime(2026, 10, 20, tzinfo=timezone.utc).timestamp())
end = start + 86400
print("est start slot", int(a[1] - (a[0] - start) * rate))
print("est end slot", int(a[1] + (end - a[0]) * rate))

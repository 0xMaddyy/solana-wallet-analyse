"""How busy is 2H6Dwrq, and which programs do its recent buys use?"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from collections import Counter
from datetime import datetime, timezone

from sno.analyze import rpc
from sno.multi_fetch import record

W = "2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf"
page = rpc("getSignaturesForAddress", [W, {"limit": 1000}])
print("newest", datetime.fromtimestamp(page[0]["blockTime"], timezone.utc),
      "oldest in 1000", datetime.fromtimestamp(page[-1]["blockTime"], timezone.utc),
      "fail", sum(1 for s in page if s.get("err")))
ok = [s["signature"] for s in page if not s.get("err")][:8]
for sig in ok:
    t = record(sig, [W])
    print(datetime.fromtimestamp(t["blockTime"], timezone.utc), "progs", t["programs"])

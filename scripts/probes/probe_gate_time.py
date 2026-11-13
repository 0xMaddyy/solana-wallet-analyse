import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time
from sno.analyze import rpc

mints = [
    "8jdHSCJRer9j6LWsYpBeo3BgmZz3cfAqYn8rqiZcpump",
    "BnsM4vV4F4sM2tHx4ttsceL256VVRtnLwG3TZGrpump",
    "5xri1bAx8YEYe5JZ25tehxcxehfJD76NJq5YbGFepump",
]
for m in mints:
    t0 = time.time()
    page = rpc("getSignaturesForAddress", [m, {"limit": 25}])
    print(f"{m[:8]} {len(page)} sigs {time.time() - t0:.2f}s")

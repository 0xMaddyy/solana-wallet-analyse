import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
from collections import defaultdict

KNOWN = set()
KNOWN.update(ln.strip() for ln in open("wallets_oct14.txt") if ln.strip())
KNOWN.update([
    "FfW5e8gKJfgaZPog6DiJoW6Kif6Fb23CokWprRhHVjV1",
    "CRjYEJowq4YaPUSkJsJResF6Hu5ko4GiB4PX9jmX7CrE",
    "D1gszVJ9vvAdrfaAWcYU745WKywKR8C16hFeyPjY8dJg",
    "3pDHoZBjQhAf9w5zTWsVyys7NxiQdewbjj6jnZcKP9ya",
    "2PAijCsZGAmG8tVgrAmwyGC5UcXxwktYkAiy57CAXTuy",
    "5qsuh6KapqaF6WdhdvqBKF8JiQxVmnXD7Uqr8D36iePp",
    "DTGbH68GcJujkim2BfGG7nHUv5Sox4GBJKsdDRKutANm",
    "CH7GewnUqV8pdnjywGz71QVFRZ549BsDqNnpBxhzREQk",
    "8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF",
    "2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf",
    "CDXzx7BRZbJEYiirxoAJ7sxpftUNpSYRcr4NFifb4raJ",
    "BuekUk3YMmm7Agnb4ni1qMCmShVpeBTdQZYNyihyzr7u",
])

# one row per wallet+target
seen = {}
for line in open("backrun_events_oct20.jsonl", encoding="utf-8"):
    if not line.strip():
        continue
    e = json.loads(line)
    seen[(e["wallet"], e["target_sig"])] = e
print("events", len(seen))
by = defaultdict(list)
for e in seen.values():
    by[e["wallet"]].append(e)
print("wallets", len(by), "unknown", sum(1 for w in by if w not in KNOWN))
unk = {w: rs for w, rs in by.items() if w not in KNOWN and len(rs) >= 2}
print("unknown with >=2 backruns", len(unk))
for w, rs in sorted(unk.items(), key=lambda kv: -len(kv[1]))[:15]:
    bulk = sum(1 for e in rs if e["txs"] > 1 and e["successes"] == 1)
    single = sum(1 for e in rs if e["txs"] == 1)
    print(f"{w} targets {len(rs)} single {single} bulk {bulk}")

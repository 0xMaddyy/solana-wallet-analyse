"""Export address lookup tables from the successful bot backrun on each .first.csv row."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import get_tx

DAYS = [12, 14, 15, 16, 17, 18, 19]
ROWS = []
for day in DAYS:
    path = f"failed_copies_before_target_oct{day}.first.csv"
    for r in csv.DictReader(open(path, newline="", encoding="utf-8-sig")):
        ROWS.append({
            "day": f"oct{day}",
            "bot_wallet": r["bot_wallet"],
            "bot_backrun_tx": r["bot_backrun_tx"],
        })

sigs = list(dict.fromkeys(r["bot_backrun_tx"] for r in ROWS))


def lookup_tables(sig):
    tx = get_tx(sig)
    if tx is None:
        return sig, None
    msg = tx["transaction"]["message"]
    tables = [lk["accountKey"] for lk in msg.get("addressTableLookups") or []]
    return sig, tables


found = {}
with ThreadPoolExecutor(4) as ex:
    for i, (sig, tables) in enumerate(ex.map(lookup_tables, sigs), 1):
        found[sig] = tables
        if i % 25 == 0 or i == len(sigs):
            print(f"fetched {i}/{len(sigs)}", flush=True)

missing = [s for s, t in found.items() if t is None]
detail_path = "backrun_lookup_tables.csv"
with open(detail_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["day", "bot_wallet", "bot_backrun_tx", "alt_index", "alt_address"])
    for r in ROWS:
        tables = found[r["bot_backrun_tx"]]
        if not tables:
            w.writerow([r["day"], r["bot_wallet"], r["bot_backrun_tx"], "", ""])
            continue
        for i, alt in enumerate(tables):
            w.writerow([r["day"], r["bot_wallet"], r["bot_backrun_tx"], i, alt])

counts = Counter()
days = defaultdict(set)
bots = defaultdict(set)
for r in ROWS:
    for alt in found[r["bot_backrun_tx"]] or []:
        counts[alt] += 1
        days[alt].add(r["day"])
        bots[alt].add(r["bot_wallet"])

list_path = "backrun_lookup_table_list.csv"
with open(list_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["alt_address", "txs", "days", "bots"])
    for alt, n in counts.most_common():
        w.writerow([alt, n, " ".join(sorted(days[alt])), " ".join(sorted(b[:8] for b in bots[alt]))])

none = sum(1 for r in ROWS if not found[r["bot_backrun_tx"]])
print(f"rows {len(ROWS)} unique txs {len(sigs)} missing {len(missing)} txs with no lookup table {none}")
print(f"unique lookup tables {len(counts)}")
print(f"wrote {detail_path} and {list_path}")

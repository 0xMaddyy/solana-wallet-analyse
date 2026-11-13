"""Add leader, leader_region and leader_client_type (for copy_slot) to failed_copies_before_target.first.csv."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import sys

from sno.analyze import rpc
from sno.multi_report import geolocate, leader_of

PATH = sys.argv[1] if len(sys.argv) > 1 else "failed_copies_before_target.first.csv"
rows = list(csv.DictReader(open(PATH, encoding="utf-8-sig")))
if not rows:
    print("no rows")
    sys.exit(0)
for r in rows:
    r["leader"] = leader_of(int(r["copy_slot"]))
    r["target_leader"] = leader_of(int(r["target_slot"]))
geo = geolocate({r["leader"] for r in rows})
client = {n["pubkey"]: n.get("clientId") or "Unknown" for n in rpc("getClusterNodes", [])}

same = all(r["leader"] == r["target_leader"] for r in rows)
cols = [c for c in rows[0] if c not in ("leader", "target_leader")]
at = cols.index("copy_tx")
new = ["leader", "leader_region", "leader_client_type"]
cols[at:at] = new
for r in rows:
    r["leader_region"] = geo[r["leader"]]["region"]
    r["leader_client_type"] = client.get(r["leader"], "not in gossip")
    if same:
        del r["target_leader"]
if not same:
    cols.insert(at + 3, "target_leader")

with open(PATH, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
print("copy-slot leader == target-slot leader for every row:", same)
for r in rows:
    print(r["bot_wallet"][:8], r["copy_slot"], r["leader"][:8], r["leader_region"], r["leader_client_type"],
          "" if same else f"target leader {r['target_leader'][:8]}")

"""Fetch backruns + failed copies before target for Oct 22-26 UTC."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os
import subprocess
import sys
from datetime import datetime

WALLETS = "wallets_oct14.txt"
DAYS = [22, 23, 24, 25, 26]


def run(cmd, env, label):
    print(f"\n[{datetime.now():%H:%M:%S}] === {label} ===", flush=True)
    print(" ", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        raise SystemExit(f"{label} failed with {r.returncode}")


def main():
    for d in DAYS:
        day = f"2026-10-{d}"
        tag = f"oct{d}"
        env = os.environ.copy()
        env["SNO_DAY"] = day
        env["SNO_WALLETS"] = WALLETS
        env["SNO_TAG"] = tag
        br = f"backruns_{tag}.csv"
        out = f"failed_copies_before_target_{tag}.csv"
        first = f"failed_copies_before_target_{tag}.first.csv"
        run([sys.executable, "multi_fetch.py"], env, f"{tag} multi_fetch")
        run([sys.executable, "multi_report.py"], env, f"{tag} multi_report")
        run([sys.executable, "ahead_export.py", out, br], env, f"{tag} ahead_export")
        run([sys.executable, "ahead_reduce.py", out, first], env, f"{tag} ahead_reduce")
        run([sys.executable, "ahead_leaders.py", first], env, f"{tag} ahead_leaders")
        print(f"[{datetime.now():%H:%M:%S}] === {tag} DONE ===", flush=True)
    print(f"\n[{datetime.now():%H:%M:%S}] ALL DAYS DONE", flush=True)


if __name__ == "__main__":
    main()

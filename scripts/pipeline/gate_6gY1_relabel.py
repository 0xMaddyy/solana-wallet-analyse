"""Fill sniping_type for rows the first pass left as 'no recent target'.

The first pass often stopped before the outside buy. This walks 12 prior mint
transactions, using the cache, and rewrites gate_6gY1_oct16.csv.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from sno.paths import RESULTS

import csv
from collections import Counter, defaultdict

from scripts.pipeline import gate_6gY1 as g

PROG = g.PROG
CSV = str(RESULTS / "gate_6gY1_oct16.csv")
g.load_cache()
rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
todo = [r for r in rows if r["sniping_type"] == "no recent target"]
g.log(f"rows {len(rows)} to relabel {len(todo)}")

pages = {i: [] for i in range(len(todo))}
before = {i: todo[i]["tx"] for i in range(len(todo))}
exhausted = set()


def outside(t, mint):
    return (t and not t.get("missing") and not t.get("err")
            and PROG not in t.get("programs", []) and mint in g.positive_mints(t))


def walk(i):
    """Nearest outside buys, a missing signature, 'PAGE', or None (nothing in the lookback)."""
    r = todo[i]
    mint, slot = r["mint"], int(r["slot"])
    found = []
    for h in pages[i]:
        if slot - h["slot"] > g.LOOKBACK_SLOTS:
            return found
        if h.get("err"):
            continue
        t = g.CACHE.get(h["signature"])
        if t is None:
            return h["signature"]
        if outside(t, mint):
            found.append(t)
            if len(found) == 3:
                return found
    if found or i in exhausted or len(pages[i]) >= 36:
        return found
    return "PAGE"


for wave in range(8):
    need = [i for i in range(len(todo)) if i not in exhausted and len(pages[i]) < 36]
    if wave:
        need = page_need
    if not need:
        break
    g.log(f"wave {wave} pages {len(need)}")
    for off in range(0, len(need), 20):
        chunk = need[off:off + 20]
        calls = [("getSignaturesForAddress", [todo[i]["mint"], {"before": before[i], "limit": 12}]) for i in chunk]
        for i, page in zip(chunk, g.batch_rpc(calls)):
            page = page or []
            pages[i].extend(page)
            if page:
                before[i] = page[-1]["signature"]
            if len(page) < 12:
                exhausted.add(i)
    missing, page_need, seen = [], [], set()
    resolved = 0
    for i in range(len(todo)):
        if todo[i].get("_done"):
            continue
        got = walk(i)
        if isinstance(got, list):
            todo[i]["_cands"] = got
            todo[i]["_done"] = True
            resolved += 1
        elif got == "PAGE":
            page_need.append(i)
        elif isinstance(got, str) and got not in seen:
            missing.append(got)
            seen.add(got)
    g.log(f"  resolved {resolved} fetch {len(missing)} next page {len(page_need)}")
    g.fetch_many(missing, f"relabel{wave}")
    if not missing and not page_need:
        break

# final walk
cands = {}
for i, r in enumerate(todo):
    got = r.get("_cands")
    if got is None:
        got = walk(i)
        if not isinstance(got, list):
            got = []
    cands[r["tx"]] = got

wanted = defaultdict(set)
for r in todo:
    for t in cands.get(r["tx"], []):
        if t["slot"] == int(r["slot"]):
            wanted[t["slot"]].add(t["sig"])
            wanted[int(r["slot"])].add(r["tx"])
g.log(f"indexes {len(wanted)} slots")
pos = {}
with g.ThreadPoolExecutor(8) as ex:
    for slot, found in ex.map(lambda s: (s, g.indexes(s, wanted[s])), list(wanted)):
        pos[slot] = found

changed = Counter()
for r in rows:
    if r["sniping_type"] != "no recent target":
        continue
    bi = pos.get(int(r["slot"]), {}).get(r["tx"])
    chosen = None
    for t in cands.get(r["tx"], []):
        if t["slot"] > int(r["slot"]) or int(r["slot"]) - t["slot"] > g.LOOKBACK_SLOTS:
            continue
        if t["slot"] < int(r["slot"]):
            chosen = t
            break
        ti = pos.get(t["slot"], {}).get(t["sig"])
        if bi is None or ti is None or ti < bi:
            chosen = t
            break
    if chosen is None:
        continue
    gap_slots = int(r["slot"]) - chosen["slot"]
    if chosen["slot"] == int(r["slot"]) and bi is not None and pos.get(chosen["slot"], {}).get(chosen["sig"]) is not None:
        gap_pos = bi - pos[chosen["slot"]][chosen["sig"]]
        kind = "backrun" if gap_pos == 1 else "copy same block"
    elif chosen["slot"] == int(r["slot"]):
        gap_pos = ""
        kind = "copy same block"
    else:
        gap_pos = ""
        kind = "copy later slot"
    plat, _tip = g.platform_of(chosen)
    r["sniping_type"] = kind
    r["target_wallet"] = chosen["signer"]
    r["target_tx"] = chosen["sig"]
    r["target_time_utc"] = g.utc(chosen["blockTime"]) if chosen.get("blockTime") else ""
    r["target_slot"] = chosen["slot"]
    r["target_block_index"] = pos.get(chosen["slot"], {}).get(chosen["sig"], "")
    r["slots_after_target"] = gap_slots
    r["positions_after_target"] = gap_pos
    r["target_platform"] = plat
    r["target_buy_sol"] = round(-g.pair_sol(chosen, {chosen["signer"]}) / 1e9, 6)
    changed[kind] += 1

with open(CSV, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=[k for k in rows[0] if not k.startswith("_")])
    w.writeheader()
    for r in rows:
        w.writerow({k: v for k, v in r.items() if not k.startswith("_")})

g.log(f"relabelled {dict(changed)}")
g.log(f"sniping {Counter(r['sniping_type'] for r in rows)}")
closed = [r for r in rows if r["trade_status"] == "closed" and r["trade_profit_sol"] != ""]
g.log(f"closed {len(closed)} profit {sum(float(r['trade_profit_sol']) for r in closed):+.3f}")
for kind in ("backrun", "copy same block", "copy later slot", "no recent target"):
    rs = [r for r in closed if r["sniping_type"] == kind]
    if not rs:
        continue
    prof = sum(float(r["trade_profit_sol"]) for r in rs)
    g.log(f"  {kind:20} n {len(rs):5d} profit {prof:+9.3f} "
          f"win {sum(1 for r in rs if float(r['trade_profit_sol']) > 0) / len(rs):.0%}")

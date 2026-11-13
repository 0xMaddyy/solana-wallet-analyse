"""Find Oct 20 pump.fun backrunners in blocks where the known bots traded.

A backrun is a successful buy whose previous transaction is a different wallet
buying the same mint. Bulk means that wallet sent more than one transaction
for that mint in the slot and only one succeeded.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.analyze import rpc

PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
START = int(datetime(2026, 10, 20, tzinfo=timezone.utc).timestamp())
END = START + 86400
WORKERS = 3
DONE_PATH = "backrun_scan_done.txt"
EVENT_PATH = "backrun_events_oct20.jsonl"
OUT = "backrunners_oct20.csv"

NEW = {
    "FfW5e8gKJfgaZPog6DiJoW6Kif6Fb23CokWprRhHVjV1",
    "CRjYEJowq4YaPUSkJsJResF6Hu5ko4GiB4PX9jmX7CrE",
    "D1gszVJ9vvAdrfaAWcYU745WKywKR8C16hFeyPjY8dJg",
}
KNOWN = set(NEW)
KNOWN.update(ln.strip() for ln in open("wallets_oct14.txt") if ln.strip())
KNOWN.update([
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
_lock = threading.Lock()


def log(msg):
    print(msg, flush=True)


def page_slots(addr):
    slots, before = set(), None
    while True:
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        batch = rpc("getSignaturesForAddress", [addr, opts])
        if not batch:
            break
        for s in batch:
            bt = s.get("blockTime")
            if bt is not None and START <= bt < END:
                slots.add(s["slot"])
        before = batch[-1]["signature"]
        last = batch[-1].get("blockTime") or 0
        if last < START or len(batch) < 1000:
            break
    return slots


def slot_list():
    slots = set()
    for line in open("oct20_allsigs.jsonl", encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if not r["err"]:
            slots.add(r["slot"])
    for w in NEW:
        extra = page_slots(w)
        log(f"{w[:8]} slots {len(extra)}")
        slots |= extra
    return sorted(slots)


def pubkey(k):
    return k["pubkey"] if isinstance(k, dict) else k


def parse(tx, index):
    msg = tx["transaction"]
    keys = msg["accountKeys"]
    pubs = [pubkey(k) for k in keys]
    signers = [k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")]
    signer = signers[0] if signers else (pubs[0] if pubs else "")
    meta = tx["meta"] or {}
    pre, post = {}, {}
    for row in meta.get("preTokenBalances") or []:
        if row.get("owner") == signer:
            pre[row["mint"]] = int(row["uiTokenAmount"]["amount"])
    for row in meta.get("postTokenBalances") or []:
        if row.get("owner") == signer:
            post[row["mint"]] = int(row["uiTokenAmount"]["amount"])
    bought = {m for m in set(pre) | set(post) if post.get(m, 0) > pre.get(m, 0) and (m.endswith("pump") or PUMP in pubs)}
    touched = {a for a in pubs if isinstance(a, str) and a.endswith("pump")}
    touched |= {m for m in set(pre) | set(post) if m.endswith("pump")}
    return {
        "index": index,
        "sig": msg["signatures"][0],
        "signer": signer,
        "err": meta.get("err"),
        "bought": bought,
        "touched": touched,
        "pump": PUMP in pubs,
    }


def get_block(slot):
    import time
    import urllib.error
    import urllib.request
    from sno.analyze import RPC
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getBlock", "params": [slot, {
        "transactionDetails": "accounts", "rewards": False,
        "maxSupportedTransactionVersion": 1, "encoding": "json",
    }]}).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            if "error" in out:
                msg = str(out["error"].get("message", ""))
                if "skipped" in msg or "not available" in msg or "cleaned up" in msg:
                    return None
                raise RuntimeError(out["error"])
            return out["result"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                time.sleep(min(8, 1.5 * (attempt + 1)))
                continue
            raise
        except Exception:
            if attempt == 5:
                raise
            time.sleep(0.5 * (attempt + 1))
    return None


def scan(slot):
    block = get_block(slot)
    if not block:
        return []
    parsed = [parse(tx, i) for i, tx in enumerate(block["transactions"])]
    counts = defaultdict(lambda: [0, 0])
    for p in parsed:
        if not p["pump"]:
            continue
        for m in p["touched"]:
            counts[(p["signer"], m)][0] += 1
            if not p["err"] and m in p["bought"]:
                counts[(p["signer"], m)][1] += 1
    events = []
    for i, p in enumerate(parsed):
        if i == 0 or p["err"] or not p["bought"]:
            continue
        prev = parsed[i - 1]
        for m in p["bought"]:
            if m not in prev["bought"] or prev["signer"] == p["signer"]:
                continue
            n, succ = counts[(p["signer"], m)]
            events.append({
                "slot": slot,
                "index": p["index"],
                "wallet": p["signer"],
                "sig": p["sig"],
                "mint": m,
                "target_wallet": prev["signer"],
                "target_sig": prev["sig"],
                "target_index": prev["index"],
                "txs": n,
                "successes": succ,
            })
    return events


def main():
    slots = slot_list()
    try:
        done = {int(x) for x in open(DONE_PATH) if x.strip()}
    except FileNotFoundError:
        done = set()
    todo = [s for s in slots if s not in done]
    log(f"slots {len(slots)} done {len(done)} todo {len(todo)}")
    finished = {"n": 0}

    def one(slot):
        try:
            events = scan(slot)
        except Exception as e:
            log(f"slot {slot} failed {e}")
            return slot, []
        return slot, events

    with open(EVENT_PATH, "a", encoding="utf-8") as ev, open(DONE_PATH, "a", encoding="utf-8") as dn:
        with ThreadPoolExecutor(WORKERS) as ex:
            for slot, events in ex.map(one, todo):
                with _lock:
                    for e in events:
                        ev.write(json.dumps(e) + "\n")
                    ev.flush()
                    dn.write(str(slot) + "\n")
                    dn.flush()
                    finished["n"] += 1
                    n = finished["n"]
                if n % 100 == 0 or n == len(todo):
                    log(f"scanned {n}/{len(todo)}")
    log("SCAN DONE")


if __name__ == "__main__":
    main()

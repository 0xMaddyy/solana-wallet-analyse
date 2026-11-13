"""October 20 pump.fun backrunners of the listed top traders.

A backrun is a different wallet's successful buy of the same mint in the next
transaction. Single: that wallet has one transaction for the mint in the slot.
Bulk: more than one, and exactly one of them succeeded.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from sno.analyze import rpc

PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
WSOL = "So11111111111111111111111111111111111111112"
SLOT_GTE = 459023999
SLOT_LT = 459421250
BUYS = "trader_buys_oct20.jsonl"
DONE = "trader_buys_oct20.done"
SLOTS = "trader_buys_oct20.slots"
DETAIL = "frontrunners_oct20_detail.csv"
SUMMARY = "frontrunners_oct20.csv"
WORKERS = 3
_lock = threading.Lock()


def log(msg):
    print(msg, flush=True)


def load_traders():
    rows = json.load(open("top_traders_oct20.json", encoding="utf-8"))
    return {r["address"]: r["name"] for r in rows}


def pubkey(k):
    return k["pubkey"] if isinstance(k, dict) else k


def bought_mints(item, addr):
    msg = item["transaction"]["message"]
    header = msg.get("header") or {}
    n = header.get("numRequiredSignatures", 1)
    signers = [pubkey(k) for k in msg["accountKeys"][:n]]
    if addr not in signers:
        return []
    keys = [pubkey(k) for k in msg["accountKeys"]]
    if PUMP not in keys and "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA" not in keys:
        return []
    meta = item.get("meta") or {}
    pre = {}
    for b in meta.get("preTokenBalances") or []:
        if b.get("owner") == addr:
            pre[b["mint"]] = int(b["uiTokenAmount"]["amount"])
    out = []
    for b in meta.get("postTokenBalances") or []:
        mint = b.get("mint")
        if b.get("owner") == addr and mint and mint != WSOL and str(mint).endswith("pump"):
            if int(b["uiTokenAmount"]["amount"]) > pre.get(mint, 0):
                out.append(mint)
    return out


def page_buys(addr):
    token = None
    seen = None
    pages = 0
    buys = []
    scanned = 0
    while True:
        cfg = {
            "limit": 100,
            "sortOrder": "asc",
            "transactionDetails": "full",
            "encoding": "json",
            "maxSupportedTransactionVersion": 1,
            "filters": {"status": "succeeded", "slot": {"gte": SLOT_GTE, "lt": SLOT_LT}},
        }
        if token:
            cfg["paginationToken"] = token
        res = rpc("getTransactionsForAddress", [addr, cfg])
        batch = res.get("data") or []
        pages += 1
        scanned += len(batch)
        for item in batch:
            mints = bought_mints(item, addr)
            if not mints:
                continue
            sig = item["transaction"]["signatures"][0]
            for mint in mints:
                buys.append({
                    "wallet": addr,
                    "sig": sig,
                    "slot": item["slot"],
                    "index": item.get("transactionIndex"),
                    "mint": mint,
                })
        token = res.get("paginationToken")
        if pages % 25 == 0:
            log(f"  {addr[:8]} page {pages} scanned {scanned} buys {len(buys)}")
        if not token or len(batch) < 100 or token == seen:
            break
        seen = token
    return buys, pages, scanned


def parse_tx(i, tx):
    msg = tx["transaction"]
    keys = msg["accountKeys"]
    signers = [k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")]
    signer = signers[0] if signers else None
    pubs = [pubkey(k) for k in keys]
    meta = tx.get("meta") or {}
    pre = {}
    for b in meta.get("preTokenBalances") or []:
        if b.get("owner") == signer:
            pre[b["mint"]] = int(b["uiTokenAmount"]["amount"])
    bought = []
    for b in meta.get("postTokenBalances") or []:
        if b.get("owner") == signer and b.get("mint") != WSOL:
            amt = int(b["uiTokenAmount"]["amount"])
            if amt > pre.get(b["mint"], 0):
                bought.append(b["mint"])
    return {
        "i": i,
        "sig": msg["signatures"][0],
        "signer": signer,
        "err": meta.get("err"),
        "bought": bought,
        "mints": [p for p in pubs if isinstance(p, str) and p.endswith("pump")],
    }


def mentions(tx, mint):
    return mint in tx["mints"] or mint in tx["bought"]


def collect_buys(names):
    done = set()
    try:
        done = {ln.strip() for ln in open(DONE, encoding="utf-8") if ln.strip()}
    except FileNotFoundError:
        pass
    todo = [a for a in names if a not in done]
    log(f"traders {len(names)} buys cached {len(done)} to page {len(todo)}")
    with open(BUYS, "a", encoding="utf-8") as bh, open(DONE, "a", encoding="utf-8") as dh:
        def one(addr):
            try:
                rows, pages, scanned = page_buys(addr)
            except Exception as e:
                log(f"page failed {addr[:8]} {e}")
                return 0
            with _lock:
                for r in rows:
                    bh.write(json.dumps(r) + "\n")
                bh.flush()
                dh.write(addr + "\n")
                dh.flush()
            log(f"paged {addr[:8]} {names[addr]} pages {pages} scanned {scanned} buys {len(rows)}")
            return len(rows)
        if todo:
            with ThreadPoolExecutor(WORKERS) as ex:
                list(ex.map(one, todo))


def main():
    names = load_traders()
    collect_buys(names)
    by_slot = defaultdict(list)
    nbuys = 0
    for line in open(BUYS, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        by_slot[r["slot"]].append(r)
        nbuys += 1
    log(f"buys {nbuys} slots {len(by_slot)}")

    seen_slots = set()
    try:
        seen_slots = {int(ln) for ln in open(SLOTS, encoding="utf-8") if ln.strip()}
    except FileNotFoundError:
        seen_slots = set()
    pending = [s for s in by_slot if s not in seen_slots]
    log(f"slots cached {len(seen_slots)} to fetch {len(pending)}")

    fields = ["frontrunner", "kind", "txs", "successes", "target_wallet", "target_name",
              "target_tx", "target_slot", "target_index", "mint", "success_tx", "success_index"]
    import os
    new_file = not os.path.exists(DETAIL) or os.path.getsize(DETAIL) == 0
    out_lock = threading.Lock()
    detail_fh = open(DETAIL, "a", newline="", encoding="utf-8-sig")
    writer = csv.DictWriter(detail_fh, fieldnames=fields)
    if new_file:
        writer.writeheader()
        detail_fh.flush()

    def scan(slot):
        try:
            block = rpc("getBlock", [slot, {
                "transactionDetails": "accounts",
                "rewards": False,
                "maxSupportedTransactionVersion": 1,
                "encoding": "json",
            }])
        except Exception as e:
            log(f"slot {slot} failed {e}")
            block = None
        rows = []
        if block:
            txs = [parse_tx(i, tx) for i, tx in enumerate(block["transactions"])]
            by_sig = {t["sig"]: t for t in txs}
            for buy in by_slot[slot]:
                tx = by_sig.get(buy["sig"])
                if not tx or tx["err"] or buy["mint"] not in tx["bought"]:
                    continue
                if tx["signer"] != buy["wallet"]:
                    continue
                nxt = txs[tx["i"] + 1] if tx["i"] + 1 < len(txs) else None
                if not nxt or nxt["signer"] == tx["signer"] or nxt["err"] or buy["mint"] not in nxt["bought"]:
                    continue
                bot = nxt["signer"]
                related = [t for t in txs if t["signer"] == bot and mentions(t, buy["mint"])]
                successes = [t for t in related if not t["err"] and buy["mint"] in t["bought"]]
                if len(related) == 1:
                    kind = "single"
                elif len(successes) == 1:
                    kind = "bulk"
                else:
                    kind = "multi"
                rows.append({
                    "frontrunner": bot,
                    "kind": kind,
                    "txs": len(related),
                    "successes": len(successes),
                    "target_wallet": buy["wallet"],
                    "target_name": names.get(buy["wallet"], ""),
                    "target_tx": buy["sig"],
                    "target_slot": slot,
                    "target_index": tx["i"],
                    "mint": buy["mint"],
                    "success_tx": nxt["sig"],
                    "success_index": nxt["i"],
                })
        with out_lock:
            for r in rows:
                writer.writerow(r)
            detail_fh.flush()
            with open(SLOTS, "a", encoding="utf-8") as sf:
                sf.write(str(slot) + "\n")
        return len(rows)

    hit_n = 0
    if pending:
        with ThreadPoolExecutor(3) as ex:
            for i, n in enumerate(ex.map(scan, pending), 1):
                hit_n += n
                if i % 25 == 0 or i == len(pending):
                    log(f"scanned {i}/{len(pending)} hits {hit_n}")
    detail_fh.close()

    hits = list(csv.DictReader(open(DETAIL, encoding="utf-8-sig")))
    uniq = {}
    for r in hits:
        uniq[(r["frontrunner"], r["target_tx"], r["mint"])] = r
    hits = list(uniq.values())
    by = defaultdict(list)
    for r in hits:
        by[r["frontrunner"]].append(r)
    sum_fields = ["frontrunner", "kind", "single_targets", "bulk_targets", "multi_targets",
                  "targets", "traders", "bulk_txs_median"]
    with open(SUMMARY, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=sum_fields)
        w.writeheader()
        for wallet, rs in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            single = sum(1 for r in rs if r["kind"] == "single")
            bulk = sum(1 for r in rs if r["kind"] == "bulk")
            multi = sum(1 for r in rs if r["kind"] == "multi")
            if single and not bulk and not multi:
                kind = "single"
            elif bulk and not single and not multi:
                kind = "bulk"
            elif multi and not single and not bulk:
                kind = "multi"
            else:
                kind = "mixed"
            sizes = sorted(int(r["txs"]) for r in rs if r["kind"] == "bulk")
            w.writerow({
                "frontrunner": wallet,
                "kind": kind,
                "single_targets": single,
                "bulk_targets": bulk,
                "multi_targets": multi,
                "targets": len(rs),
                "traders": len({r["target_wallet"] for r in rs}),
                "bulk_txs_median": sizes[len(sizes) // 2] if sizes else "",
            })
    log(f"wallets {len(by)} backruns {len(hits)} wrote {SUMMARY}")


if __name__ == "__main__":
    main()

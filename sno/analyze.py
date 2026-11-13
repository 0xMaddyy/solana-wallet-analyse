import json
import os
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

RPC = os.environ.get(
    "SNO_RPC_URL",
    os.environ.get(
        "HELIUS_RPC_URL",
        "https://mainnet.helius-rpc.com/?api-key=" + os.environ.get("HELIUS_API_KEY", ""),
    ),
)
if "api-key=" in RPC and RPC.endswith("api-key="):
    raise RuntimeError("Set SNO_RPC_URL or HELIUS_API_KEY before calling RPC")
BOT = "8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF"
MIN_BUY_SOL = float(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) > 1 else 2.0

JITO_TIPS = {
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
}
SKIP_PROGRAMS = {
    "ComputeBudget111111111111111111111111111111", "11111111111111111111111111111111",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
}


def rpc(method, params, retries=18):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except Exception as e:
            if attempt == retries - 1:
                raise
            if getattr(e, "code", None) == 429:
                delay = min(12.0, 1.5 * (attempt + 1))
            else:
                delay = min(8.0, 0.5 * (attempt + 1))
            time.sleep(delay)


def get_tx(sig):
    return rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])


def keys(tx):
    return [k["pubkey"] if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]


def summarize(tx):
    msg = tx["transaction"]["message"]
    ak = keys(tx)
    meta = tx["meta"]
    signer = ak[0]
    sol_delta = (meta["postBalances"][0] - meta["preBalances"][0]) / 1e9
    programs = [ix["programId"] for ix in msg["instructions"]]
    transfers = []
    for ix in msg["instructions"]:
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") == "transfer" and ix["programId"] == "11111111111111111111111111111111":
            transfers.append((p["info"]["destination"], p["info"]["lamports"] / 1e9))
    dontfront = any(k.startswith("jitodontfront") for k in ak) or any(
        any(a.startswith("jitodontfront") for a in ix.get("accounts", [])) for ix in msg["instructions"])
    mints_up = set()
    pre = {(b["accountIndex"], b["mint"]): float(b["uiTokenAmount"]["uiAmount"] or 0) for b in meta.get("preTokenBalances") or [] if b.get("owner") == signer}
    for b in meta.get("postTokenBalances") or []:
        if b.get("owner") == signer:
            if float(b["uiTokenAmount"]["uiAmount"] or 0) > pre.get((b["accountIndex"], b["mint"]), 0):
                mints_up.add(b["mint"])
    return {
        "signer": signer, "sol_delta": sol_delta, "programs": programs, "transfers": transfers,
        "dontfront": dontfront, "mints_bought": sorted(mints_up), "err": meta["err"], "slot": tx["slot"],
    }


def main():
    sigs = rpc("getSignaturesForAddress", [BOT, {"limit": 100}])
    print(f"fetched {len(sigs)} signatures, newest slot {sigs[0]['slot']}, oldest slot {sigs[-1]['slot']}", file=sys.stderr)

    with ThreadPoolExecutor(6) as ex:
        txs = list(ex.map(lambda s: get_tx(s["signature"]), sigs))

    rows = []
    for s, tx in zip(sigs, txs):
        if tx is None:
            continue
        sm = summarize(tx)
        sm["sig"] = s["signature"]
        rows.append(sm)

    kinds = Counter()
    for r in rows:
        if r["err"] is not None:
            kinds["failed"] += 1
        elif r["mints_bought"]:
            kinds["buy"] += 1
        elif r["sol_delta"] > 0:
            kinds["sell / SOL in"] += 1
        else:
            kinds["other"] += 1
    print("tx kinds:", dict(kinds), file=sys.stderr)
    big_buys = [r for r in rows if r["err"] is None and r["mints_bought"] and -r["sol_delta"] >= MIN_BUY_SOL]
    print(f"successful buys >= {MIN_BUY_SOL} SOL: {len(big_buys)} of {len(rows)} txs", file=sys.stderr)

    def analyze(r):
        block = rpc("getBlock", [r["slot"], {"transactionDetails": "signatures", "rewards": False,
                                             "maxSupportedTransactionVersion": 1}])
        bsigs = block["signatures"]
        idx = bsigs.index(r["sig"])
        prev_sig = bsigs[idx - 1] if idx > 0 else None
        prev = summarize(get_tx(prev_sig)) if prev_sig else None
        leader = rpc("getSlotLeaders", [r["slot"], 1])[0]
        return {"bot": r, "bot_index": idx, "block_tx_count": len(bsigs), "prev_sig": prev_sig,
                "prev": prev, "leader": leader, "slot_in_leader_window": r["slot"] % 4}

    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(analyze, big_buys))

    json.dump(results, open("results.json", "w"), indent=1)

    leaders, target_progs, target_dests, same_mint, dontfront = Counter(), Counter(), Counter(), 0, 0
    for x in results:
        b, p = x["bot"], x["prev"]
        leaders[x["leader"]] += 1
        sm = bool(p and set(p["mints_bought"]) & set(b["mints_bought"]))
        same_mint += sm
        dontfront += bool(p and p["dontfront"])
        jito_tip = sum(a for d, a in b["transfers"] if d in JITO_TIPS)
        if p:
            for prog in set(p["programs"]) - SKIP_PROGRAMS:
                target_progs[prog] += 1
            for d, a in p["transfers"]:
                target_dests["JITO_TIP" if d in JITO_TIPS else d] += 1
        print(f"slot {b['slot']} (leader-window pos {x['slot_in_leader_window']}) idx {x['bot_index']}/{x['block_tx_count']} "
              f"buy {-b['sol_delta']:.3f} SOL jitoTip {jito_tip:.5f} | prev signer {p['signer'] if p else None} "
              f"sameMint={sm} dontfront={p['dontfront'] if p else None} leader {x['leader']}")

    print("\n== target is the immediately preceding tx and buys the same mint:", same_mint, "/", len(results))
    print("== target has jitodontfront:", dontfront, "/", len(results))
    print("\n== leaders (validator identity) of backrun slots:")
    for k, v in leaders.most_common():
        print(f"  {v:3d}  {k}")
    print("\n== non-trivial programs used by targets (platform routers):")
    for k, v in target_progs.most_common():
        print(f"  {v:3d}  {k}")
    print("\n== SOL transfer destinations in targets (fees / SWQoS tips):")
    for k, v in target_dests.most_common():
        print(f"  {v:3d}  {k}")


if __name__ == "__main__":
    main()

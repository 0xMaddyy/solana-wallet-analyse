import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json, sys, time, urllib.request
from collections import Counter

RPC = "https://api.mainnet-beta.solana.com"
WALLET = "8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF"
MIN_SOL = 2.0
MAX_SIGS = int(sys.argv[1]) if len(sys.argv) > 1 else 300

JITO_TIP = {
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
}
SKIP_PROGRAMS = {"ComputeBudget111111111111111111111111111111", "11111111111111111111111111111111",
                 "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                 "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"}


def rpc(method, params, retries=8):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(RPC, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read())
            if "error" in res:
                raise RuntimeError(res["error"])
            return res["result"]
        except Exception as e:
            wait = 2 * (i + 1)
            print(f"  ! {method} failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"{method} gave up")


def get_tx(sig):
    time.sleep(0.25)
    return rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])


def summarize(tx):
    msg = tx["transaction"]["message"]
    keys = [k["pubkey"] for k in msg["accountKeys"]]
    payer = keys[0]
    programs, transfers, dontfront = [], [], False
    for ix in msg["instructions"]:
        pid = ix["programId"]
        if pid not in SKIP_PROGRAMS:
            programs.append(pid)
        if any(str(a).startswith("jitodontfront") for a in ix.get("accounts", [])):
            dontfront = True
        p = ix.get("parsed")
        if isinstance(p, dict) and p.get("type") == "transfer" and "lamports" in p.get("info", {}):
            transfers.append((p["info"]["destination"], p["info"]["lamports"] / 1e9))
    if any(k.startswith("jitodontfront") for k in keys):
        dontfront = True
    sol_change = (tx["meta"]["postBalances"][0] - tx["meta"]["preBalances"][0]) / 1e9
    return {"payer": payer, "programs": programs, "transfers": transfers,
            "dontfront": dontfront, "sol_change": sol_change}


sigs, before = [], None
while len(sigs) < MAX_SIGS:
    opts = {"limit": min(1000, MAX_SIGS - len(sigs))}
    if before:
        opts["before"] = before
    page = rpc("getSignaturesForAddress", [WALLET, opts])
    if not page:
        break
    sigs += page
    before = page[-1]["signature"]
print(f"fetched {len(sigs)} signatures", file=sys.stderr)

results = []
for s in sigs:
    if s["err"]:
        continue
    tx = get_tx(s["signature"])
    if not tx:
        continue
    me = summarize(tx)
    if me["payer"] != WALLET or me["sol_change"] > -MIN_SOL:
        continue
    slot = tx["slot"]
    time.sleep(0.25)
    block = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                    "maxSupportedTransactionVersion": 1}])
    order = block["signatures"]
    idx = order.index(s["signature"])
    prev_sig = order[idx - 1] if idx > 0 else None
    target = summarize(get_tx(prev_sig)) if prev_sig else None
    leader = rpc("getSlotLeaders", [slot, 1])[0]
    row = {"sig": s["signature"], "slot": slot, "leader": leader, "index": idx, "block_txs": len(order),
           "spent": round(-me["sol_change"], 3),
           "bot_tips": [(d, a) for d, a in me["transfers"] if d in JITO_TIP],
           "target_sig": prev_sig, "target": target}
    results.append(row)
    t = target or {}
    print(f"slot {slot} leader {leader[:8]} idx {idx}/{len(order)} spent {row['spent']} SOL | "
          f"target payer {t.get('payer','?')[:8]} programs {t.get('programs')} dontfront {t.get('dontfront')} "
          f"transfers {[(d[:6], round(a,4)) for d,a in t.get('transfers', [])]}", flush=True)

with open("results.json", "w") as f:
    json.dump(results, f, indent=1)

print("\n=== leaders of slots where big copy buys landed")
for k, v in Counter(r["leader"] for r in results).most_common():
    print(v, k)
print("\n=== target platforms (first non-system program)")
for k, v in Counter((r["target"]["programs"] or ["?"])[0] for r in results if r["target"]).most_common():
    print(v, k)
print("\n=== target transfer destinations (tips / fees)")
for k, v in Counter(d for r in results if r["target"] for d, _ in r["target"]["transfers"]).most_common(30):
    print(v, k, "(jito tip)" if k in JITO_TIP else "")

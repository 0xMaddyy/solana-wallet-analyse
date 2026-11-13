import json, sys, time, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

BOT = "8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF"
RPC = "https://api.mainnet-beta.solana.com"
MAX_SIGS = int(sys.argv[1]) if len(sys.argv) > 1 else 600
OUT = r"C:\Users\Administrator\AppData\Local\Temp\botcheck\result.json"


def http(url, body=None, retries=6):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                         headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            time.sleep(1.5 * (i + 1))
    return None


def rpc(method, params):
    r = http(RPC, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    return (r or {}).get("result")


sigs, before = [], None
while len(sigs) < MAX_SIGS:
    opts = {"limit": 1000}
    if before:
        opts["before"] = before
    page = rpc("getSignaturesForAddress", [BOT, opts]) or []
    if not page:
        break
    sigs += page
    before = page[-1]["signature"]
sigs = [s for s in sigs[:MAX_SIGS] if s.get("err") is None]
print(f"successful sigs: {len(sigs)}", flush=True)


def analyze(s):
    sig = s["signature"]
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
    time.sleep(0.25)
    if not tx:
        return None
    keys = [k["pubkey"] for k in tx["transaction"]["message"]["accountKeys"]]
    if keys[0] != BOT:
        return None
    logs = tx["meta"].get("logMessages") or []
    is_buy = any("Instruction: Buy" in l for l in logs)
    sol_out = (tx["meta"]["preBalances"][0] - tx["meta"]["postBalances"][0]) / 1e9
    return {"sig": sig, "slot": tx["slot"], "blockTime": tx.get("blockTime"), "buy": is_buy, "sol_out": sol_out}


with ThreadPoolExecutor(4) as ex:
    txs = [t for t in ex.map(analyze, sigs) if t]
buys = [t for t in txs if t["buy"]]
print(f"bot-signed txs: {len(txs)}, buys: {len(buys)}", flush=True)


def jito(t):
    b = http(f"https://bundles.jito.wtf/api/v1/bundles/transaction/{t['sig']}", retries=2)
    t["bundle_id"] = b[0]["bundle_id"] if isinstance(b, list) and b else None
    if t["bundle_id"]:
        d = http(f"https://bundles.jito.wtf/api/v1/bundles/bundle/{t['bundle_id']}", retries=3)
        d = d[0] if isinstance(d, list) and d else {}
        t["validator"] = d.get("validator")
        t["bundle_txs"] = d.get("txSignatures")
        t["tip"] = (d.get("landedTipLamports") or 0) / 1e9
        t["position"] = d["txSignatures"].index(t["sig"]) if d.get("txSignatures") and t["sig"] in d["txSignatures"] else None
    time.sleep(0.2)
    return t


with ThreadPoolExecutor(4) as ex:
    buys = list(ex.map(jito, buys))


def leader(t):
    if not t.get("validator"):
        r = rpc("getSlotLeaders", [t["slot"], 1])
        t["leader"] = r[0] if r else None
    else:
        t["leader"] = t["validator"]
    return t


with ThreadPoolExecutor(4) as ex:
    buys = list(ex.map(leader, buys))

va = rpc("getVoteAccounts", [{}]) or {"current": [], "delinquent": []}
stake = {v["nodePubkey"]: v["activatedStake"] for v in va["current"] + va["delinquent"]}
total = sum(stake.values()) or 1

json.dump({"buys": buys, "stake_total": total, "stake": {k: stake.get(k, 0) for k in {b["leader"] for b in buys}}},
          open(OUT, "w"), indent=1)


def summarize(label, rows):
    print(f"\n=== {label}: {len(rows)}")
    if not rows:
        return
    backrun = [r for r in rows if r.get("position") and r["position"] > 0]
    print(f"in a Jito bundle: {sum(1 for r in rows if r.get('bundle_id'))}, backrun (bot tx not first): {len(backrun)}")
    c = Counter(r["leader"] for r in rows)
    print("leaders (count, share of these buys, leader's share of network stake):")
    for k, n in c.most_common(25):
        print(f"  {k}  {n:4d}  {n/len(rows):6.1%}  stake {stake.get(k,0)/total:6.2%}")
    print(f"  distinct leaders: {len(c)}")


big = [b for b in buys if b["sol_out"] > 2]
small = [b for b in buys if b["sol_out"] <= 2]
if buys:
    print("time range:", min(b["blockTime"] for b in buys), max(b["blockTime"] for b in buys))
summarize("buys > 2 SOL", big)
summarize("buys <= 2 SOL", small)

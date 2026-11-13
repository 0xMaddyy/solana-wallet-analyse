import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json
import math
import os
import shutil
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sno.paths import RESULTS
from sno.analyze import rpc

PAIRS = [
    ("3pDHoZBjQhAf9w5zTWsVyys7NxiQdewbjj6jnZcKP9ya", "C8qCb6smwarmisb89kUejVsd8uHHj96AXWT2Ex1XD33i"),
    ("2PAijCsZGAmG8tVgrAmwyGC5UcXxwktYkAiy57CAXTuy", "Bj5PgdHXkZT4bw7YxQXuBeSbjfqqHgMoZAsDxdaYzGSt"),
    ("5qsuh6KapqaF6WdhdvqBKF8JiQxVmnXD7Uqr8D36iePp", "FzwbhYksjD9JJTFwZozcQQmXMKDCmY1uMz71daBAoMsy"),
    ("DTGbH68GcJujkim2BfGG7nHUv5Sox4GBJKsdDRKutANm", "Fa9qPovB2gxs67eCxWM9KheYJH9BgyPjGBqj8cL1bLRG"),
    ("CH7GewnUqV8pdnjywGz71QVFRZ549BsDqNnpBxhzREQk", "EKn5wiBAQ2UuMTAK94gPmqFabVSMCxWtzHRKxRqMYzP7"),
    ("8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF", "HZUCsc7pThddRkSW8CyBfvHo4ZskrHMsg7uK46Mk1nS7"),
]
DAY_START = int(datetime(2026, 10, 8, tzinfo=timezone.utc).timestamp())
DAY_END = DAY_START + 86400
FETCH_END = DAY_END + 1800
WSOL = "So11111111111111111111111111111111111111112"
CACHE = "multi_cache"
os.makedirs(CACHE, exist_ok=True)

TIPS = {a: ("BLOXROUTE" if p == "BLOX" else p) for a, p in json.load(open("tip_registry.json")).items()}

PLATFORM_FEE_ACCOUNTS = {
    "Trojan": ["9yMwSPk9mrXSN7yDHUuZurAh1sjbJsfpUqjZ7SvVtdco", "BBYXdwhqbCxVRVtnuMTTxh8biNisz3ZxsnHfr44jXytR",
               "92Med3qeK7duC5iiYsHX38H2f2twJfRsSx93oNrza2VH", "2jwHNxavSoMZMEDbT1eV9PcPt5dDcayCqM6MkgaPpmWQ",
               "65gDv7pZQCZELsNpNYSFEBtNFpWZAbxmRFB6BGMqFkHH", "BWgb8wR1FEGiu1jCDSKuHKf752W27b4iN6SvoNCiK4qp",
               "8jgg7moFJkHyTtAv9M6RBSPMp2oXeXhuiUMKW8YbYCWn"],
    "BONKbot": ["ZG98FUCjb8mJ824Gbs6RsgVmr1FhXb2oNiJHa2dwmPd", "HVbzPxiet4ZgAP6CySVouY8RC3MNxgS35MgE3pWvUVC8"],
    "Axiom": ["7LCZckF6XXGQ1hDY6HFXBKWAtiUgL9QY5vj1C4Bn1Qjj", "4V65jvcDG9DSQioUVqVPiUcUY9v6sb6HKtMnsxSKEz5S",
              "CeA3sPZfWWToFEBmw5n1Y93tnV66Vmp8LacLzsVprgxZ", "AaG6of1gbj1pbDumvbSiTuJhRCRkkUNaWVxijSbWvTJW",
              "7oi1L8U9MRu5zDz5syFahsiLUric47LzvJBQX6r827ws", "9kPrgLggBJ69tx1czYAbp7fezuUmL337BsqQTKETUEhP",
              "DKyUs1xXMDy8Z11zNsLnUg3dy9HZf6hYZidB6WodcaGy", "4FobGn5ZWYquoJkxMzh2VUAWvV36xMgxQ3M7uG1pGGhd",
              "76sxKrPtgoJHDJvxwFHqb3cAXWfRHFLe3VpKcLCAHSEf", "H2cDR3EkJjtTKDQKk8SJS48du9mhsdzQhy8xJx5UMqQK",
              "8m5GkL7nVy95G4YVUbs79z873oVKqg2afgKRmqxsiiRm", "4kuG6NsAFJNwqEkac8GFDMMheCGKUPEbaRVHHyFHSwWz",
              "8vFGAKdwpn4hk7kc1cBgfWZzpyW3MEMDATDzVZhddeQb", "86Vh4XGLW2b6nvWbRyDs4ScgMXbuvRCHT7WbUT3RFxKG",
              "DZfEurFKFtSbdWZsKSDTqpqsQgvXxmESpvRtXkAdgLwM", "5L2QKqDn5ukJSWGyqR4RPvFvwnBabKWqAqMzH4heaQNB",
              "DYVeNgXGLAhZdeLMMYnCw1nPnMxkBN7fJnNpHmizTrrF", "Hbj6XdxX6eV4nfbYTseysibp4zZJtVRRPn2J3BhGRuK9",
              "846ah7iBSu9ApuCyEhA5xpnjHHX7d4QJKetWLbwzmJZ8", "5BqYhuD4q1YD3DMAYkc1FeTu9vqQVYYdfBAmkZjamyZg"],
    "GMGN": ["BB5dnY55FXS1e1NXqZDwCzgdYJdMCj3B92PU6Q5Fb6DT", "7sHXjs1j7sDJGVSMSPjD1b4v3FD6uRSvRWfhRdfv5BiA",
             "HeZVpHj9jLwTVtMMbzQRf6mLtFPkWNSg11o68qrbUBa3", "ByRRgnZenY6W2sddo1VJzX9o4sMU4gPDUkcmgrpGBxRy",
             "DXfkEGoo6WFsdL7x6gLZ7r6Hw2S6HrtrAQVPWYx2A1s9", "3t9EKmRiAUcQUYzTZpNojzeGP1KBAVEEbDNmy6wECQpK",
             "DymeoWc5WLNiQBaoLuxrxDnDRvLgGZ1QGsEoCAM7Jsrx", "dBhdrmwBkRa66XxBuAK4WZeZnsZ6bHeHCCLXa3a8bTJ",
             "6TxjC5wJzuuZgTtnTMipwwULEbMPx5JPW3QwWkdTGnrn"],
    "BullX": ["9RYJ3qr5eU5xAooqVcbmdeusjcViL5Nkiq7Gske3tiKq", "F4hJ3Ee3c5UuaorKAMfELBjYCjiiLH75haZTKqTywRP3"],
    "Maestro": ["MaestroUL88UBnZr3wfoN7hqmNWFi3ZYCGqZoJJHE36", "FRMxAnZgkW58zbYcE7Bxqsg99VWpJh6sMP5xLzAWNabN"],
    "Bloom": ["7HeD6sLLqAnKVRuSfc1Ko3BSPMNKWgGTiWLKXJF31vKM"],
    "BananaGun": ["47hEzz83VFR23rLTEeVm9A7eFzjJwjvdupPPmX3cePqF", "4BBNEVRgrxVKv9f7pMNE788XM1tt379X9vNjpDH2KCL7",
                  "8r2hZoDfk5hDWJ1sDujAi2Qr45ZyZw5EQxAXiMZWLKh2", "JBok73TJsWdgeJy2x59TaTFKtngtxeYPvizafTnhvMGV",
                  "6nPV8EChoA3HUZRbFmM6cXDv41NApX9ALKwDw4vYfjWp", "35q8cao77A8ceJVxQaoN5w9kyTjTJUsmQcy2RRNrJBMc",
                  "3spK1TmrAnFUDRN2bErDAVw225tLE7uFpQeP9WNXP2nY", "36ZCrKd6N9iGmArccia15saDyepL5wShHJyGTvea3Akf"],
    "Photon": ["AVUCZyuT35YSuj4RH7fwiyPu82Djn2Hfg7y2ND2XcnZH"],
    "Padre/Terminal": ["J5XGHmzrRmnYWbmw45DbYkdZAU2bwERFZ11qCDXPvFB5", "DoAsxPQgiyAxyaJNvpAAUb2ups6rbJRdYrCPyWxwRxBb"],
    "PepeBoost": ["G9PhF9C9H83mAjjkdJz4MDqkufiTPMJkx7TnKE1kFyCp"],
    "STBot": ["F34kcgMgCF7mYWkwLN3WN7KrFprr2NbwxuLvXx4fbztj"],
    "MevX": ["3kxSQybWEeQZsMuNWMRJH4TxrhwoDwfv41TNMLRzFP5A", "4Lpvp1q69SHentfYcMBUrkgvppeEx6ovHCSYjg4UYXiq"],
    "Nova": ["noVaE91mUL5jTb8e9Vf6dqJdNPzJpEQ3uAdnQ8h4nVz", "noVakKQGTTjpHARvecAUbVnc85AatCLm3ijDFk8JXZB"],
}
FEE_TO_PLATFORM = {a: p for p, accts in PLATFORM_FEE_ACCOUNTS.items() for a in accts}
PROGRAM_PREFIX_TO_PLATFORM = [
    ("GMgn", "GMGN"), ("FLASHX", "Axiom"), ("troy", "Trojan"), ("BANANA", "BananaGun"), ("Maestro", "Maestro"),
    ("NoVA", "Nova"), ("JUP", "Jupiter"), ("DF1ow", "DFlow"), ("term9YPb", "Padre/Terminal?"),
]
VENUES = {"6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pump.fun", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "PumpSwap"}
INFRA = {"ComputeBudget111111111111111111111111111111", "11111111111111111111111111111111",
         "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
         "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb", "noopb9bkMVfRPU8AsbpTUg8AQkHtKwMYZiFUjNRtMmV",
         "L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95", "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ",
         "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr", "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo"}
JITO_REGIONS = {"ny": (40.71, -74.01), "slc": (40.76, -111.89), "amsterdam": (52.37, 4.90), "frankfurt": (50.11, 8.68),
                "london": (51.51, -0.13), "dublin": (53.35, -6.26), "singapore": (1.35, 103.82), "tokyo": (35.68, 139.69)}


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def get_tx(sig):
    return rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])


def parse_tx(sig, tx, wallets):
    msg, meta = tx["transaction"]["message"], tx["meta"]
    keys = [k["pubkey"] for k in msg["accountKeys"]]
    signers = [k["pubkey"] for k in msg["accountKeys"] if k.get("signer")]
    dsol = {w: meta["postBalances"][keys.index(w)] - meta["preBalances"][keys.index(w)] for w in wallets if w in keys}
    pre = {(b["accountIndex"], b["mint"], b.get("owner")): int(b["uiTokenAmount"]["amount"]) for b in meta.get("preTokenBalances") or []}
    post = {(b["accountIndex"], b["mint"], b.get("owner")): int(b["uiTokenAmount"]["amount"]) for b in meta.get("postTokenBalances") or []}
    tok = defaultdict(int)
    for k in set(pre) | set(post):
        d = post.get(k, 0) - pre.get(k, 0)
        if d:
            tok[f"{k[2]}|{k[1]}"] += d
    all_ix = msg["instructions"] + [i for g in meta.get("innerInstructions") or [] for i in g["instructions"]]
    transfers = []
    for ix in all_ix:
        p = ix.get("parsed")
        if isinstance(p, dict) and ix.get("program") == "system" and p.get("type") == "transfer":
            transfers.append([p["info"]["source"], p["info"]["destination"], p["info"]["lamports"]])
    return {
        "sig": sig, "slot": tx["slot"], "blockTime": tx["blockTime"], "err": meta["err"], "fee": meta["fee"],
        "signers": signers, "dsol": dsol, "tok": dict(tok), "transfers": transfers,
        "top_programs": [ix["programId"] for ix in msg["instructions"]],
        "all_programs": sorted({ix["programId"] for ix in all_ix}),
        "dontfront": any(k.startswith("jitodontfront") for k in keys) or any(
            a.startswith("jitodontfront") for ix in all_ix for a in ix.get("accounts", [])),
    }


def fetch_pair(buyer, seller):
    path = f"{CACHE}/{buyer[:8]}_txs.jsonl"
    if buyer.startswith("8N4CBW") and not os.path.exists(path) and os.path.exists("pnl_txs.jsonl"):
        shutil.copy("pnl_txs.jsonl", path)
    have = {json.loads(l)["sig"] for l in open(path)} if os.path.exists(path) else set()
    sigs = {}
    for addr in (buyer, seller):
        before = None
        while True:
            opts = {"limit": 1000, **({"before": before} if before else {})}
            page = rpc("getSignaturesForAddress", [addr, opts])
            if not page:
                break
            for s in page:
                if s.get("blockTime") and DAY_START <= s["blockTime"] < FETCH_END:
                    sigs[s["signature"]] = s
            before = page[-1]["signature"]
            if (page[-1].get("blockTime") or DAY_END) < DAY_START:
                break
    todo = [s for s in sigs if s not in have]
    log(f"{buyer[:8]}: {len(sigs)} txs in window, {len(todo)} to fetch")
    with open(path, "a") as f, ThreadPoolExecutor(10) as ex:
        for i, (s, tx) in enumerate(zip(todo, ex.map(get_tx, todo)), 1):
            if tx:
                f.write(json.dumps(parse_tx(s, tx, [buyer, seller])) + "\n")
            if i % 500 == 0:
                log(f"{buyer[:8]}: fetched {i}/{len(todo)}")
    return [json.loads(l) for l in open(path) if DAY_START <= json.loads(l)["blockTime"] < FETCH_END]


def pair_sol(t, wallets):
    lam = sum(v for w, v in t["dsol"].items() if w in wallets)
    for k, d in t["tok"].items():
        owner, mint = k.split("|")
        if mint == WSOL and owner in wallets:
            lam += d
    return lam


def pair_mints(t, wallets):
    out = defaultdict(int)
    for k, d in t["tok"].items():
        owner, mint = k.split("|")
        if owner in wallets and mint != WSOL:
            out[mint] += d
    return out


_blocks = {}


def block_sigs(slot):
    if slot not in _blocks:
        b = rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": True, "maxSupportedTransactionVersion": 1}])
        leader = next((r["pubkey"] for r in b.get("rewards") or [] if r["rewardType"] == "Fee"), None)
        _blocks[slot] = (b["signatures"], leader)
    return _blocks[slot]


def tips_of(t, payer):
    out = defaultdict(int)
    for src, dst, lam in t["transfers"]:
        if src == payer and dst in TIPS:
            out[TIPS[dst]] += lam
    return dict(out)


def platform_of(t):
    names = set()
    for src, dst, lam in t["transfers"]:
        if dst in FEE_TO_PLATFORM:
            names.add(FEE_TO_PLATFORM[dst])
    for prog in t["top_programs"]:
        for prefix, name in PROGRAM_PREFIX_TO_PLATFORM:
            if prog.startswith(prefix):
                names.add(name)
        if prog.startswith("axm"):
            names.add("Axiom")
    for src, dst, lam in t["transfers"]:
        if dst.startswith("axm"):
            names.add("Axiom")
    if names:
        return "+".join(sorted(names))
    routers = [p for p in t["top_programs"] if p not in INFRA and p not in VENUES]
    venues = sorted({VENUES[p] for p in t["all_programs"] if p in VENUES})
    if routers:
        return f"unknown router {routers[0][:8]} ({'/'.join(venues) or 'other venue'})"
    other_dsts = [dst for src, dst, lam in t["transfers"] if src == t["signers"][0] and dst not in TIPS and lam < 10**9]
    if venues:
        return f"direct {'/'.join(venues)}" + (f" (fee/transfer to {other_dsts[0][:8]})" if other_dsts else "")
    return "unknown"


def analyze_pair(buyer, seller):
    out_path = f"{CACHE}/{buyer[:8]}_backruns.json"
    if os.path.exists(out_path):
        return json.load(open(out_path))
    wallets = {buyer, seller}
    txs = sorted(fetch_pair(buyer, seller), key=lambda t: (t["slot"], t["blockTime"]))
    ok = [t for t in txs if t["err"] is None]

    mint_sol, mint_tok, mint_buys, mint_sells = defaultdict(int), defaultdict(int), defaultdict(list), defaultdict(int)
    for t in ok:
        mints = pair_mints(t, wallets)
        if not mints:
            continue
        s = pair_sol(t, wallets)
        if s == 0 and all(d > 0 for d in mints.values()):
            continue
        for m, d in mints.items():
            mint_sol[m] += s / len(mints)
            mint_tok[m] += d
            if d > 0 and s < 0 and buyer in t["signers"]:
                mint_buys[m].append(t)
            elif d < 0:
                mint_sells[m] += 1

    buys = [b for m, lst in mint_buys.items() for b in lst if DAY_START <= b["blockTime"] < DAY_END]
    log(f"{buyer[:8]}: {len(buys)} buys on Oct 8, checking block positions")

    def check(b):
        sigs, leader = block_sigs(b["slot"])
        i = sigs.index(b["sig"])
        if i == 0:
            return None
        prev_raw = get_tx(sigs[i - 1])
        prev = parse_tx(sigs[i - 1], prev_raw, [])
        p_signer = prev["signers"][0]
        if p_signer in wallets:
            return None
        bought = {k.split("|")[1] for k, d in prev["tok"].items() if d > 0 and k.split("|")[0] == p_signer}
        mint = next(iter(pair_mints(b, wallets)))
        if mint not in bought:
            return None
        return {"bot": b, "target": prev, "index": i, "block_size": len(sigs), "leader": leader, "mint": mint}

    with ThreadPoolExecutor(8) as ex:
        found = [r for r in ex.map(check, buys) if r]
    for r in found:
        m = r["mint"]
        r["token_profit_sol"] = mint_sol[m] / 1e9 if mint_tok[m] <= 0 else None
        r["token_open_cost_sol"] = mint_sol[m] / 1e9 if mint_tok[m] > 0 else None
        r["sells"] = mint_sells[m]
    json.dump(found, open(out_path, "w"))
    log(f"{buyer[:8]}: {len(found)} backruns")
    return found


def jito_bundle(sig):
    for _ in range(3):
        try:
            req = urllib.request.Request(f"https://bundles.jito.wtf/api/v1/bundles/transaction/{sig}",
                                         headers={"User-Agent": "Mozilla/5.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=20).read())
            return data[0]["bundle_id"] if isinstance(data, list) and data else ""
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            time.sleep(1.5)
        except Exception:
            time.sleep(1.5)
    return "lookup-failed"


def geolocate(leaders):
    nodes = {n["pubkey"]: n for n in rpc("getClusterNodes", [])}
    ips = {l: nodes[l]["gossip"].rsplit(":", 1)[0] for l in leaders if l in nodes and nodes[l].get("gossip")}
    geo = {}
    uniq = sorted(set(ips.values()))
    for i in range(0, len(uniq), 100):
        body = json.dumps([{"query": ip, "fields": "query,status,country,city,lat,lon,org,as"} for ip in uniq[i:i + 100]]).encode()
        req = urllib.request.Request("http://ip-api.com/batch", data=body, headers={"Content-Type": "application/json"})
        for g in json.loads(urllib.request.urlopen(req, timeout=60).read()):
            geo[g["query"]] = g
        time.sleep(4.5)

    def nearest(lat, lon):
        def d(p):
            a1, o1, a2, o2 = map(math.radians, (lat, lon, *p))
            return math.acos(min(1, math.sin(a1) * math.sin(a2) + math.cos(a1) * math.cos(a2) * math.cos(o1 - o2)))
        return min(JITO_REGIONS, key=lambda r: d(JITO_REGIONS[r]))

    out = {}
    for l in leaders:
        g = geo.get(ips.get(l), {})
        if g.get("status") == "success":
            out[l] = (ips[l], g.get("city", ""), g.get("country", ""), g.get("org") or g.get("as", ""), nearest(g["lat"], g["lon"]))
        else:
            out[l] = (ips.get(l, ""), "unknown", "unknown", "", "unknown")
    return out


def main():
    rows_raw = []
    for buyer, seller in PAIRS:
        for r in analyze_pair(buyer, seller):
            r["buyer"], r["seller"] = buyer, seller
            rows_raw.append(r)
    log(f"total backruns: {len(rows_raw)}; Jito bundle lookups")

    bundle_cache_path = f"{CACHE}/jito_bundles.json"
    bundles = json.load(open(bundle_cache_path)) if os.path.exists(bundle_cache_path) else {}
    todo = [r["bot"]["sig"] for r in rows_raw if r["bot"]["sig"] not in bundles or bundles[r["bot"]["sig"]] == "lookup-failed"]
    todo += [r["target"]["sig"] for r in rows_raw if r["target"]["sig"] not in bundles or bundles[r["target"]["sig"]] == "lookup-failed"]
    with ThreadPoolExecutor(4) as ex:
        for s, b in zip(todo, ex.map(jito_bundle, todo)):
            bundles[s] = b
    json.dump(bundles, open(bundle_cache_path, "w"))

    log("geolocating leaders")
    geo = geolocate({r["leader"] for r in rows_raw if r["leader"]})

    rows = []
    for r in sorted(rows_raw, key=lambda r: (r["buyer"], r["bot"]["slot"])):
        b, t = r["bot"], r["target"]
        bot_tips = tips_of(b, b["signers"][0])
        tgt_tips = tips_of(t, t["signers"][0])
        bot_bundle, tgt_bundle = bundles.get(b["sig"], ""), bundles.get(t["sig"], "")
        same_bundle = bool(bot_bundle and bot_bundle not in ("lookup-failed",) and bot_bundle == tgt_bundle)
        if same_bundle:
            bot_route = "Jito bundle (with target)"
        elif bot_bundle and bot_bundle != "lookup-failed":
            bot_route = "Jito bundle (without target)"
        elif bot_tips:
            bot_route = "+".join(sorted(bot_tips))
        else:
            bot_route = "no tip (priority fee only)"
        ip, city, country, hosting, region = geo.get(r["leader"], ("", "unknown", "unknown", "", "unknown"))
        rows.append({
            "buyer_wallet": r["buyer"], "seller_wallet": r["seller"],
            "time_utc": datetime.fromtimestamp(b["blockTime"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "slot": b["slot"], "block_index": r["index"], "block_tx_count": r["block_size"],
            "backrun_tx": b["sig"], "token_mint": r["mint"],
            "buy_sol": round(-pair_sol(b, {r["buyer"], r["seller"]}) / 1e9, 6),
            "backrun_route": bot_route,
            "backrun_swqos_tips": ";".join(f"{k}:{v / 1e9:.6f}" for k, v in sorted(bot_tips.items())),
            "backrun_tx_fee_sol": b["fee"] / 1e9,
            "jito_bundle_id": bot_bundle if bot_bundle != "lookup-failed" else "lookup failed",
            "target_tx": t["sig"], "target_wallet": t["signers"][0],
            "target_platform": platform_of(t),
            "target_swqos_tips": ";".join(f"{k}:{v / 1e9:.6f}" for k, v in sorted(tgt_tips.items())) or "none",
            "target_tx_fee_sol": t["fee"] / 1e9, "target_jitodontfront": t["dontfront"],
            "leader_identity": r["leader"], "leader_ip": ip, "leader_city": city, "leader_country": country,
            "leader_hosting": hosting, "leader_nearest_jito_region": region,
            "token_profit_sol": round(r["token_profit_sol"], 6) if r["token_profit_sol"] is not None else "",
            "position_status": "closed" if r["token_profit_sol"] is not None else "still open at Oct 9 00:30 UTC",
            "sell_tx_count": r["sells"],
        })

    out = "oct8_backruns.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    log(f"wrote {len(rows)} rows to {os.path.abspath(out)}")

    for buyer, seller in PAIRS:
        rs = [r for r in rows if r["buyer_wallet"] == buyer]
        if not rs:
            print(f"\n{buyer[:8]}: no backruns")
            continue
        profit = sum(r["token_profit_sol"] for r in rs if r["token_profit_sol"] != "")
        print(f"\n== {buyer[:8]} / {seller[:8]}: {len(rs)} backruns, profit {profit:+.3f} SOL")
        print("   routes:", Counter(r["backrun_route"] for r in rs).most_common(5))
        print("   target platforms:", Counter(r["target_platform"].split(" (")[0] for r in rs).most_common(8))
        print("   target swqos:", Counter(r["target_swqos_tips"].split(":")[0] for r in rs).most_common(6))
        print("   leader regions:", Counter(r["leader_nearest_jito_region"] for r in rs).most_common(8))


if __name__ == "__main__":
    main()

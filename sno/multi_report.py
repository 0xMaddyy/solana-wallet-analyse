import csv
import json
import math
import sys
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache

from sno.analyze import rpc
from sno.multi_fetch import BUY_END, CSV, END_LABEL, PAIRS, START, out_path, record

WSOL = "So11111111111111111111111111111111111111112"
from sno.paths import label_file, RESULTS
SWQOS = json.load(open(label_file("labels_swqos.json")))
SWQOS = {a: {"BlocxRoute": "bloXroute", "Fast": "Fast (unverified)"}.get(p, p) for a, p in SWQOS.items()}
PLAT = json.load(open(label_file("labels_platforms.json")))
PLAIN_PROGRAMS = {
    "ComputeBudget111111111111111111111111111111", "11111111111111111111111111111111",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb", "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA", "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ",
    "noopb9bkMVfRPU8AsbpTUg8AQkHtKwMYZiFUjNRtMmV", "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
    "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo", "L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95",
}
DEX_NAMES = {"6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pump.fun", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "PumpSwap"}
JITO_REGIONS = {
    "ny": (40.71, -74.01), "slc": (40.76, -111.89), "amsterdam": (52.37, 4.90), "frankfurt": (50.11, 8.68),
    "london": (51.51, -0.13), "dublin": (53.35, -6.26), "singapore": (1.35, 103.82), "tokyo": (35.68, 139.69),
}


def swqos_of(addr):
    if addr in SWQOS:
        return SWQOS[addr]
    low = addr.lower()
    if low.startswith("astra"):
        return "Astralane"
    if low.startswith("noz"):
        return "Nozomi"
    if addr.startswith("axm"):
        return "Nozomi (Axiom private tip)"
    if addr.startswith("bLx"):
        return "bloXroute"
    if low.startswith("nextb"):
        return "NextBlock"
    return None


def fee_platform_of(addr):
    if addr in PLAT["fee_wallets"]:
        return PLAT["fee_wallets"][addr]
    for pre, suf, name in PLAT["fee_wallet_prefix_suffix"]:
        if addr.startswith(pre) and addr.endswith(suf):
            return name
    return None


def program_platform(progs):
    for p in progs:
        if p in PLAT["programs"]:
            return PLAT["programs"][p]
        for pre, name in PLAT["program_prefixes"].items():
            if p.startswith(pre):
                return name
    return None


def pair_sol(t, pair):
    v = sum(t["dsol"].values())
    for k, d in t["tok"].items():
        owner, mint = k.split("|")
        if mint == WSOL and owner in pair:
            v += d
    return v


def pair_mints(t, pair):
    out = {}
    for k, d in t["tok"].items():
        owner, mint = k.split("|")
        if owner in pair and mint != WSOL:
            out[mint] = out.get(mint, 0) + d
    return out


@lru_cache(maxsize=None)
def block_sigs(slot):
    return tuple(rpc("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                         "maxSupportedTransactionVersion": 1}])["signatures"])


@lru_cache(maxsize=None)
def leader_of(slot):
    try:
        return rpc("getSlotLeaders", [slot, 1], retries=2)[0]
    except Exception:
        block = rpc("getBlock", [slot, {"transactionDetails": "none", "rewards": True, "maxSupportedTransactionVersion": 1}])
        return next(r["pubkey"] for r in block["rewards"] if r.get("rewardType") == "Fee")


def target_info(sig):
    t = record(sig, [])
    signer = t["signers"][0]
    bought = {k.split("|")[1] for k, d in t["tok"].items() if d > 0 and k.split("|")[0] == signer and not k.endswith(WSOL)}
    progs = t["programs"] + t["inner_programs"]
    platform = program_platform(progs)
    fee_hits, tips, other = Counter(), defaultdict(int), defaultdict(int)
    for src, dst, lam in t["transfers"]:
        if src != signer:
            continue
        p = fee_platform_of(dst)
        s = swqos_of(dst)
        if p:
            fee_hits[p] += 1
        elif s:
            tips[s] += lam
        else:
            other[dst] += lam
    if not platform and fee_hits:
        platform = fee_hits.most_common(1)[0][0]
    if not platform:
        nonplain = [p for p in t["programs"] if p not in PLAIN_PROGRAMS]
        if not nonplain:
            dex = "/".join(sorted({DEX_NAMES[p] for p in progs if p in DEX_NAMES})) or "unknown DEX"
            platform = f"direct {dex} (no platform router or known fee wallet)"
        else:
            platform = f"unknown router {nonplain[0]}"
    if "axm" in "".join(tips) and platform.startswith("direct"):
        platform = "Axiom (by private tip)"
    dontfront = any(a.startswith("jitodontfront") for a in t["accounts"])
    return {
        "sig": sig, "signer": signer, "bought": bought, "platform": platform,
        "swqos": "; ".join(f"{k} {v / 1e9:.5f}" for k, v in sorted(tips.items())) or "none detected",
        "other_transfers": "; ".join(f"{d} {v / 1e9:.5f}" for d, v in sorted(other.items(), key=lambda kv: -kv[1])[:3]),
        "dontfront": dontfront, "fee": t["fee"],
    }


def analyze_pair(buyer, seller):
    pair = {buyer, seller}
    txs = []
    for line in open(out_path(buyer), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            txs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    txs = sorted((t for t in txs if not t.get("missing")), key=lambda t: (t["slot"], t["blockTime"]))
    mint_sol, mint_tok, first_buy = defaultdict(int), defaultdict(int), {}
    buys = []
    for t in txs:
        if t["err"] is not None:
            continue
        mints = pair_mints(t, pair)
        if not mints:
            continue
        s = pair_sol(t, pair)
        for m, d in mints.items():
            mint_sol[m] += s / len(mints)
            mint_tok[m] += d
        if s < 0 and all(d > 0 for d in mints.values()) and START <= t["blockTime"] < BUY_END:
            buys.append(t)
            for m in mints:
                first_buy.setdefault(m, t["sig"])

    def classify(t):
        sigs = block_sigs(t["slot"])
        i = sigs.index(t["sig"])
        if i == 0:
            return None
        tgt = target_info(sigs[i - 1])
        mints = set(pair_mints(t, pair))
        if tgt["signer"] in pair or not (tgt["bought"] & mints):
            return None
        return {"bot": t, "index": i, "target": tgt}

    with ThreadPoolExecutor(3) as ex:
        found = [r for r in ex.map(classify, buys) if r]
    print(f"{buyer[:8]}: {len(txs)} txs, {len(buys)} in-day buys, {len(found)} backruns", file=sys.stderr, flush=True)
    return found, mint_sol, mint_tok, first_buy, len(buys)


def geolocate(leaders):
    nodes = {n["pubkey"]: n for n in rpc("getClusterNodes", [])}
    ips = {l: nodes[l]["gossip"].rsplit(":", 1)[0] for l in leaders if l in nodes and nodes[l].get("gossip")}
    geo, uniq = {}, sorted(set(ips.values()))
    for i in range(0, len(uniq), 100):
        body = json.dumps([{"query": ip, "fields": "query,status,country,city,lat,lon"} for ip in uniq[i:i + 100]]).encode()
        req = urllib.request.Request("http://ip-api.com/batch", data=body, headers={"Content-Type": "application/json"})
        for g in json.loads(urllib.request.urlopen(req, timeout=60).read()):
            geo[g["query"]] = g

    def nearest(lat, lon):
        def dist(p):
            a1, o1, a2, o2 = map(math.radians, (lat, lon, *p))
            return math.acos(min(1, math.sin(a1) * math.sin(a2) + math.cos(a1) * math.cos(a2) * math.cos(o1 - o2)))
        return min(JITO_REGIONS, key=lambda r: dist(JITO_REGIONS[r]))

    out = {}
    for l in leaders:
        g = geo.get(ips.get(l), {})
        ok = g.get("status") == "success"
        out[l] = {"ip": ips.get(l, ""), "city": g.get("city", "") if ok else "unknown",
                  "country": g.get("country", "") if ok else "unknown",
                  "region": nearest(g["lat"], g["lon"]) if ok else "unknown"}
    return out


def main():
    rows, summary = [], []
    for buyer, seller in PAIRS:
        found, mint_sol, mint_tok, first_buy, n_buys = analyze_pair(buyer, seller)
        pair = {buyer, seller}
        slots = sorted({f["bot"]["slot"] for f in found})
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(leader_of, slots))
        for f in found:
            b, tg = f["bot"], f["target"]
            mint = sorted(pair_mints(b, pair))[0]
            bot_tips = defaultdict(int)
            for src, dst, lam in b["transfers"]:
                if src in pair and swqos_of(dst):
                    bot_tips[swqos_of(dst)] += lam
            is_first = first_buy.get(mint) == b["sig"]
            closed = mint_tok[mint] <= 0
            rows.append({
                "buyer_wallet": buyer, "seller_wallet": seller,
                "time_utc": datetime.fromtimestamp(b["blockTime"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "slot": b["slot"], "block_index": f["index"], "bot_tx": b["sig"], "mint": mint,
                "buy_sol": round(-pair_sol(b, pair) / 1e9, 6),
                "bot_route": "jito bundle" if "Jito" in bot_tips else "direct",
                "bot_swqos": "; ".join(f"{k} {v / 1e9:.5f}" for k, v in sorted(bot_tips.items())) or "none (priority fee only)",
                "bot_priority_fee_sol": round((b["fee"] - 5000 * b["n_sigs"]) / 1e9, 6),
                "target_tx": tg["sig"], "target_wallet": tg["signer"], "target_platform": tg["platform"],
                "target_swqos": tg["swqos"], "target_unlabeled_transfers": tg["other_transfers"],
                "target_jitodontfront": tg["dontfront"],
                "leader": leader_of(b["slot"]),
                "trade_profit_sol": round(mint_sol[mint] / 1e9, 6) if is_first else "",
                "trade_status": ("closed" if closed else f"open at {END_LABEL}") if is_first else f"same trade as {first_buy.get(mint)}",
            })
        summary.append((buyer, n_buys, len(found)))

    geo = geolocate({r["leader"] for r in rows})
    for r in rows:
        g = geo[r["leader"]]
        r["leader_ip"], r["leader_city"], r["leader_country"], r["leader_region"] = g["ip"], g["city"], g["country"], g["region"]

    cols = ["buyer_wallet", "seller_wallet", "time_utc", "slot", "block_index", "bot_tx", "mint", "buy_sol", "bot_route",
            "bot_swqos", "bot_priority_fee_sol", "target_tx", "target_wallet", "target_platform", "target_swqos",
            "target_unlabeled_transfers", "target_jitodontfront", "leader", "leader_ip", "leader_city", "leader_country",
            "leader_region", "trade_profit_sol", "trade_status"]
    with open(CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["buyer_wallet"], r["slot"])))

    print("\n== per pair")
    for buyer, n_buys, n_br in summary:
        rs = [r for r in rows if r["buyer_wallet"] == buyer and r["trade_profit_sol"] != ""]
        prof = sum(r["trade_profit_sol"] for r in rs)
        wins = sum(1 for r in rs if r["trade_profit_sol"] > 0)
        print(f"  {buyer[:8]}  buys {n_buys:4d}  backruns {n_br:4d}  backrun trades {len(rs):4d}  profit {prof:+9.3f} SOL  "
              f"win {wins / max(len(rs), 1) * 100:5.1f}%  open {sum(1 for r in rs if r['trade_status'] != 'closed')}")
    for col in ("target_platform", "target_swqos", "bot_swqos", "bot_route", "leader_region"):
        c = Counter(r[col].split(" 0.")[0] if col.endswith("swqos") else r[col] for r in rows)
        print(f"\n== {col}")
        for k, v in c.most_common(15):
            print(f"  {v:5d}  {k}")
    unl = Counter()
    for r in rows:
        for part in filter(None, r["target_unlabeled_transfers"].split("; ")):
            unl[part.split(" ")[0]] += 1
    print("\n== most common unlabeled destinations in target txs")
    for k, v in unl.most_common(15):
        print(f"  {v:5d}  {k}")
    unk = Counter(r["target_platform"] for r in rows if r["target_platform"].startswith("unknown router"))
    print("\n== unknown routers")
    for k, v in unk.most_common(10):
        print(f"  {v:5d}  {k}")


if __name__ == "__main__":
    main()

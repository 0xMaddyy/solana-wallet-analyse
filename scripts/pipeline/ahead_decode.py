"""Decode a bot attempt that landed before its target vs the bot's successful buy, and the failed copies after it."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import json

from sno.analyze import rpc

rows = list(csv.DictReader(open("backruns_oct13.full.csv", encoding="utf-8-sig")))
r = next(r for r in rows if r["target_tx"].startswith("4UAQZPGyD2Sf"))
bot, tgt, slot = r["buyer_wallet"], r["target_wallet"], int(r["slot"])


def tx(sig):
    return rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])


def show(label, t, sig):
    msg, meta = t["transaction"]["message"], t["meta"]
    keys = [k["pubkey"] for k in msg["accountKeys"]]
    blk = rpc("getBlock", [t["slot"], {"transactionDetails": "signatures", "rewards": False, "maxSupportedTransactionVersion": 1}])
    print(f"\n{label}: {sig[:16]} slot {t['slot']} index {blk['signatures'].index(sig)} err {json.dumps(meta['err'])} fee {meta['fee']}")
    for i, ix in enumerate(msg["instructions"]):
        accs = ix.get("accounts", [])
        tags = [("TARGET" if a == tgt else "MINT" if a == r["mint"] else a[:6]) for a in accs]
        print(f"   ix{i} {ix['programId'][:10]} accounts {tags[:10]} data {str(ix.get('data', ix.get('parsed', '')))[:40]}")
    for l in (meta.get("logMessages") or [])[-4:]:
        print("   log:", l[:140])
    print("   target wallet in account keys:", tgt in keys)


sigs = rpc("getSignaturesForAddress", [tgt, {"before": r["target_tx"], "limit": 50}])
ahead = []
for s in sigs:
    if s["slot"] < slot:
        break
    t = tx(s["signature"])
    if t["transaction"]["message"]["accountKeys"][0]["pubkey"] == bot:
        ahead.append((s["signature"], t))
print("bot", bot[:8], "target", tgt[:8], "attempts ahead in same block:", len(ahead))
show("AHEAD (failed)", ahead[-1][1], ahead[-1][0])
show("TARGET", tx(r["target_tx"]), r["target_tx"])
show("BOT SUCCESS", tx(r["bot_tx"]), r["bot_tx"])
after = rpc("getSignaturesForAddress", [tgt, {"until": r["target_tx"], "limit": 200}])
for s in reversed(after):
    if s["slot"] == slot and s["err"] and s["signature"] != r["bot_tx"]:
        t = tx(s["signature"])
        if t["transaction"]["message"]["accountKeys"][0]["pubkey"] == bot:
            show("AFTER (failed copy)", t, s["signature"])
            break

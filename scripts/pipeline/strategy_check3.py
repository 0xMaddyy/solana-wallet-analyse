"""Inside a block: where do a bot's failed copies sit relative to the target buy and the bot's successful buy?"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv
import sys

from sno.analyze import rpc

rows = list(csv.DictReader(open("backruns_oct13.full.csv", encoding="utf-8-sig")))
picks = [r for r in rows if r["buyer_wallet"][:4] in ("2LSn", "46Zk", "55pb", "D6Fu", "4bHU")]
picks = [next(r for r in picks if r["buyer_wallet"].startswith(p)) for p in ("2LSn", "46Zk", "55pb", "D6Fu")]

for r in picks:
    bot, mint, slot = r["buyer_wallet"], r["mint"], int(r["slot"])
    blk = rpc("getBlock", [slot, {"encoding": "jsonParsed", "transactionDetails": "full", "rewards": False,
                                  "maxSupportedTransactionVersion": 1}])
    events = []
    for i, t in enumerate(blk["transactions"]):
        keys = [k["pubkey"] for k in t["transaction"]["message"]["accountKeys"]]
        if mint not in keys:
            continue
        signer = keys[0]
        meta = t["meta"]
        d = 0
        for side, s in (("preTokenBalances", -1), ("postTokenBalances", 1)):
            for b in meta.get(side) or []:
                if b["mint"] == mint and b.get("owner") == signer:
                    d += s * int(b["uiTokenAmount"]["amount"])
        kind = "buy" if d > 0 else "sell" if d < 0 else "-"
        who = "BOT" if signer == bot else ("TARGET" if signer == r["target_wallet"] else signer[:6])
        events.append((i, who, kind, "FAIL" if meta["err"] else "ok", meta["fee"]))
    print(f"\n{bot[:6]} slot {slot} mint {mint[:6]}  bot_tx index {r['block_index']}  ({len(blk['transactions'])} txs in block)")
    bot_ev = [e for e in events if e[1] == "BOT"]
    print(f"  bot txs touching mint: {len(bot_ev)} (failed {sum(e[3] == 'FAIL' for e in bot_ev)}), "
          f"index range {bot_ev[0][0]}-{bot_ev[-1][0]}" if bot_ev else "  no bot txs")
    for e in events:
        if e[1] != "BOT" or e[3] == "ok" or abs(e[0] - int(r["block_index"])) <= 3:
            print("   ", e)
    sys.stdout.flush()

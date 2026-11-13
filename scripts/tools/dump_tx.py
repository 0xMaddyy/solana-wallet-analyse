import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import sys

from sno.analyze import rpc

sig = sys.argv[1]
tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
msg, meta = tx["transaction"]["message"], tx["meta"]
keys = msg["accountKeys"]
print(f"slot {tx['slot']} blockTime {tx['blockTime']} version {tx.get('version')} err {meta['err']} fee {meta['fee'] / 1e9} "
      f"CU {meta.get('computeUnitsConsumed')}")
print("signers:", [k["pubkey"] for k in keys if k.get("signer")])
print("lookup tables:", [l["accountKey"] for l in msg.get("addressTableLookups") or []])

print("\n== balances (SOL) changed")
for i, k in enumerate(keys):
    d = meta["postBalances"][i] - meta["preBalances"][i]
    if d:
        print(f"  {k['pubkey']}  {d / 1e9:+.9f}  (pre {meta['preBalances'][i] / 1e9:.6f})")

print("\n== token balances")
pre = {(b["accountIndex"], b["mint"]): b for b in meta.get("preTokenBalances") or []}
for b in meta.get("postTokenBalances") or []:
    p = pre.get((b["accountIndex"], b["mint"]))
    before = int(p["uiTokenAmount"]["amount"]) if p else 0
    after = int(b["uiTokenAmount"]["amount"])
    print(f"  acct {keys[b['accountIndex']]['pubkey'][:10]} owner {b.get('owner', '')[:10]} mint {b['mint'][:10]} "
          f"dec {b['uiTokenAmount']['decimals']} {before} -> {after} ({after - before:+d})")

inner = {g["index"]: g["instructions"] for g in meta.get("innerInstructions") or []}
print("\n== instructions")
for i, ix in enumerate(msg["instructions"]):
    print(f"\n#{i} program {ix['programId']}")
    if "parsed" in ix:
        print("   parsed:", json.dumps(ix["parsed"]))
    else:
        print("   data:", ix.get("data"))
        for j, a in enumerate(ix.get("accounts", [])):
            print(f"   acct[{j}] {a}")
    for ii in inner.get(i, []):
        desc = json.dumps(ii["parsed"]) if "parsed" in ii else f"data {ii.get('data')} accts {len(ii.get('accounts', []))}"
        print(f"     inner (h{ii.get('stackHeight')}) {ii['programId'][:12]}: {desc[:300]}")

print("\n== logs")
for l in meta["logMessages"]:
    print("  ", l)

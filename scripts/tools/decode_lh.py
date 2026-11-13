import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import base64
import csv
import struct
import sys

from sno.analyze import rpc

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + ALPHABET.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


sig = sys.argv[1]
checks = [("AfZVeZe4pBorxggbi", "Bm78rv9yPNmGAo9SDqN11U7f4RDZkrv9ss4jJMmVyNy5"),
          ("AffSo4SxrskwA7qnK", "H96Tm1SfYBcsUvT4qA68HkS6pEa9fJjT3dWDXk9SWkSw")]
OPS = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}

for data, acct in checks:
    b = b58decode(data)
    print(f"\nLighthouse data {data} -> {b.hex()} ({len(b)} bytes)")
    value = b[4:12]
    offset = b[2]
    print(f"  discriminator 0x{b[0]:02x}, log_level {b[1]}, offset {offset}, type {b[3]}, "
          f"value u64 {struct.unpack('<Q', value)[0]} (bytes {value.hex()}), operator {OPS.get(b[12], b[12])}")
    info = rpc("getAccountInfo", [acct, {"encoding": "jsonParsed"}])["value"]
    if info and not isinstance(info["data"], dict):
        raw = base64.b64decode(info["data"][0])
        cur = raw[offset:offset + 8]
        print(f"  current bytes at offset {offset}: {cur.hex()} (u64 {struct.unpack('<Q', cur)[0] if len(cur) == 8 else None})")
        print(f"  lamports {info['lamports']}, data len {len(raw)}")
        for o in range(0, min(len(raw), 200), 8):
            print(f"    [{o:3d}] {raw[o:o + 8].hex()}")
    print(f"  account {acct} owner {info['owner'] if info else None}")
    if info and isinstance(info["data"], dict):
        print("  parsed:", info["data"].get("parsed"))
    elif info:
        raw = base64.b64decode(info["data"][0])
        print(f"  raw len {len(raw)} first 64 bytes {raw[:64].hex()}")

rows = list(csv.DictReader(open("backruns_oct8.csv", encoding="utf-8-sig")))
for r in rows:
    if r["bot_tx"] == sig:
        print("\nCSV row:", {k: r[k] for k in ("time_utc", "slot", "block_index", "mint", "buy_sol", "bot_route",
                                                "target_tx", "target_wallet", "target_platform", "target_swqos",
                                                "trade_profit_sol", "trade_status")})

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import struct

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + ALPHABET.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


cb = {
    "3s4Dzsx2mMXM": "ComputeBudget #0",
    "USi5xb": "ComputeBudget #1",
    "GH3hjm": "ComputeBudget #2",
}
for data, label in cb.items():
    b = b58decode(data)
    tag = b[0]
    names = {2: "SetComputeUnitLimit(u32)", 3: "SetComputeUnitPrice(u64 micro-lamports)", 4: "SetLoadedAccountsDataSizeLimit(u32)"}
    val = struct.unpack("<Q", b[1:9])[0] if tag == 3 else struct.unpack("<I", b[1:5])[0]
    print(f"{label}: {names.get(tag, tag)} = {val}")

buy = b58decode("i43WeUBGKA7wsnvVFQs4wZTWLwCy9xzCab")
print("\npump buy raw:", buy.hex())
print("  discriminator", buy[:8].hex(), "amount", struct.unpack("<Q", buy[8:16])[0],
      "max_sol_cost", struct.unpack("<Q", buy[16:24])[0], "rest", buy[24:].hex())

for label, data in (("#3 (Clock)", "HRE1oQ3bxzSvgmgx"), ("#4 (bonding curve 2dvkh7)", "AfTYTrkvBjpa2GAuq"),
                    ("#5 (token acct 2FPasmn)", "AffSo4SxrskwA7qnK"), ("#8 (own new ATA 8zAXRQ)", "AffSqqPGJ7Pmmhi6Y")):
    b = b58decode(data)
    print(f"\nL2TEx {label}: {len(b)} bytes {b.hex()}")
    for off in range(0, len(b) - 7):
        v = struct.unpack("<Q", b[off:off + 8])[0]
        if 10_000 < v < 10 ** 17:
            print(f"   u64 @ byte {off}: {v}")

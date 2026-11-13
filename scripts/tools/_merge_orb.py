import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json

extra = {
    "3BLjRcxWGtR7WRshJ3hL25U3RjWr5Ud98wMcczQqk4Ei": "Sebastian Orellana",
    "3L8RAxLkvwkz4CgHivaVRtq19741FAdGLk5DgjRfc1fW": "Inquixit",
    "3VUNtVtjjx5ckUojT7UocJ5fbuAJRsNUXNfTBnPte9vC": '"buddhaaaaa" on Pump.fun',
    "3WceT9tbWByi16K7xNn5CBpwwzGcZ6bXAM21JPF6bXZJ": '"DAGACHI1" on Pump.fun',
    "3bwkvwoYnyC9GMVFn2EWeAJ2YptCnZDWdc284SdWD2gd": '"Stuneeerrr" on Pump.fun',
    "3fePC1HPWuWKtt1nUHg3xbEF5SfjuyJoG4Y2EpCbQhoi": '"ban" on Pump.fun',
    "3h65MmPZksoKKyEpEjnWU2Yk2iYT5oZDNitGy5cTaxoE": "Jidn @jidn_w",
    "3w8N7ay9pvNaXxYUu7gFeZQ2zHg6FECSgwGWxcWwb8C8": '"abitdelulu" on Pump.fun',
    "3xdXnq1uc6GCh541A6APSFaA9HEDHi1sqANiMnvLa4Cz": '"COPANGA" on Pump.fun',
    "49UQZzvVTbSFienT2pF711iFVyk3ktMetxVV4LJNCW9i": '"Ithrowfaster" on Pump.fun',
    "49fAsUF3Nk8qbfpSrQND2sULKXanemwibYLGk5Jpn9bY": '"agent69420" on Pump.fun',
}
path = "orb_names.json"
data = json.load(open(path, encoding="utf-8"))
data.update(extra)
json.dump(data, open(path, "w", encoding="utf-8"))
print(len(data))

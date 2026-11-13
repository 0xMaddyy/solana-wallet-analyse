import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
extra = {
    "7MxmPPV4LY8tMu1rJ3PMFBuECPGhGpUcmr835meXcytz": '"themrbepis" on Pump.fun',
    "7NAd2EpYGGeFofpyvgehSXhH5vg6Ry6VRMW2Y6jiqCu1": "Cupsey @Cupseyy",
    "7SuVLBv3iijvZ8kF3tgYAvNzfPTGk2ftM44WATb4z6VD": "Drowsy @DrowsyGN",
    "7SuW6rkhC1g7BX7XNW8d34jhkQRxx3VaZZfa2tER8C28": '"Shaizer" on Pump.fun',
    "7YndBV5gp3VvAiBbSfv8M7CoyMhFsiKeGYWkwee49fTg": '"poe" on Pump.fun',
    "7fEXteaTtmX1uR8fpChEXsevM4icH5vq8LNL9dzDupX2": '"croakie" on Pump.fun',
    "7g5CJ754NboeY6D44MDdGwQmVX4Fvu59Q47c9ZKLPMkE": '"zenotterstartli" on Pump.fun',
    "7yuqR9JAgohMibPrB8rpryCzTrQSU9Fprrsuj2Z5VRf7": '"PUNISHEDJINGTAO" on Pump.fun',
    "7zGdmBpkRapRLxfgWYNAzjngp7mFJuD7AhGZ4rHmjn5L": '"lowport_calls" on Pump.fun',
    "831yhv67QpKqLBJjbmw2xoDUeeFHGUx8RnuRj9imeoEs": "Trey @treysocial",
    "89HbgWduLwoxcofWpmn1EiF9wEdpgkNDEyPjzZ72mkDi": '"alxcooks" on Pump.fun',
    "8MaVa9kdt3NW4Q5HyNAm1X5LbR8PQRVDc1W8NMVK88D5": "Daumen @daumeneth",
    "8MoW9mtbEz6z3gPuAdYb1yWhjCAxQSYqpcTb1CQgN5qb": '"Ashtoshiiii" on Pump.fun',
    "8MpJbCLZDXTvbDQUPdBGkZD2kqN2qj1mVkFgyaYMrbN5": '"sambati" on Pump.fun',
    "8PQxd6VmfGPMyg8WPnfkT9jUTmtE7UsnDmvBKXeAVP9z": '"mrkind" on Pump.fun',
    "6PX4xuN4TLPCL2GqtUZf2Q6iTjwfGbc9vcK33sinN3wP": '"tisgambin0" on Pump.fun',
    "6S8GezkxYUfZy9JPtYnanbcZTMB87Wjt1qx3c6ELajKC": "Nyhrox @nyhrox",
    "6W7XRVdo8LC6r5p3GyrHCsvTS5fwxqdNj2sytNuLuTgQ": '"Spookywhale69" on Pump.fun',
    "6Y5urCe3W7CEt2PbbAQFhqoXxeZAKMtBHvNsNh2v5G7y": '"moneypulato" on Pump.fun',
    "6aXFYXbFob1ZKAEDCcqZnX2vooA3TgEqDoy5dAQbeWoV": "Flames @FlamesOnSol",
    "6ikiPyrZ2oyQQrVB4p4d6K3hUVwmBn8zcqXfcDWMKNCd": '"paradox196" on Pump.fun',
    "6j7YuVT3U8u3hnfZJSZKPXtwN8YTtfrew1rqGs8NWLf1": '"6j7yuv" on Pump.fun',
    "6mAHkEZ8iPcPQyXvEF73GeFbXVg6WDqrNe2u1bVsYUUP": '"beverly777" on Pump.fun',
    "6qudAN2kV8mtCcYJxb5QQ6Vr15itdHHdeVbYm99NKMhy": '"thedetective" on Pump.fun',
    "6yVb4pxNwDfr6rovwNnBg3SyKSvDcHGD4WdFPN1JJBqm": '"0xEthan" on Pump.fun',
    "741TyxhtrGgdtHJDmygqtjXyxmSLYGEucu42Bguj1tbg": '"Atexela" on Pump.fun',
    "777DyFhFa4Y6ijfSRW9PFqCDAZzU4snQ7v5kWByWGnex": '"onchainvillain" on Pump.fun',
}
path = "orb_names.json"
data = json.load(open(path, encoding="utf-8"))
data.update(extra)
json.dump(data, open(path, "w", encoding="utf-8"))
print(len(data))

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
base = json.load(open("solscan_names.json", encoding="utf-8"))
base.update(json.load(open("_sol_extra.json", encoding="utf-8")))
extra = {
    "6PX4xuN4TLPCL2GqtUZf2Q6iTjwfGbc9vcK33sinN3wP": '"tisgambin0" on Pump.fun (6PX4x)',
    "6S8GezkxYUfZy9JPtYnanbcZTMB87Wjt1qx3c6ELajKC": '"nyhrox" on Pump.fun (6S8Ge)',
    "6Siu5R8vGtcUwryuEyFJhKdFzHa2P2ogBK719Bmqpwsc": '"Abrawlerjj" on Pump.fun (6Siu5)',
    "6SMMCc4H6DJkPLbziQFursHci2Bs6kEJWPPgKTidz1Ck": '"headstarfish771" on Pump.fun (6SMMC)',
    "6W7XRVdo8LC6r5p3GyrHCsvTS5fwxqdNj2sytNuLuTgQ": '"Spookywhale69" on Pump.fun (6W7XR)',
    "6Xw8XGGTgad5gp8xT8eWK7DcJKNPBsNWfxrY6pufQgG": '"nooneeeeeee" on Pump.fun (6Xw8X)',
    "6Y5urCe3W7CEt2PbbAQFhqoXxeZAKMtBHvNsNh2v5G7y": '"atoshisol" on Pump.fun (6Y5ur)',
    "6aXFYXbFob1ZKAEDCcqZnX2vooA3TgEqDoy5dAQbeWoV": '"Flamesonsol" on Pump.fun (6aXFY)',
    "6ikiPyrZ2oyQQrVB4p4d6K3hUVwmBn8zcqXfcDWMKNCd": '"paradox196" on Pump.fun (6ikiP)',
    "6qtsui7ntgkDyB1YzokZAmDeBRTe1GcWTpT76uKpPBPu": '"alphainuquant" on Pump.fun (6qtsu)',
    "6qudAN2kV8mtCcYJxb5QQ6Vr15itdHHdeVbYm99NKMhy": '"thedetective" on Pump.fun (6qudA)',
    "6yVb4pxNwDfr6rovwNnBg3SyKSvDcHGD4WdFPN1JJBqm": '"0xEthan" on Pump.fun (6yVb4)',
    "741TyxhtrGgdtHJDmygqtjXyxmSLYGEucu42Bguj1tbg": '"Atexela" on Pump.fun (741Ty)',
    "74xVT9FWhn5fGNgHAGmipmUU4W5nUvskEotcDhEuwJqC": '"odysseyyy" on Pump.fun (74xVT)',
    "777DyFhFa4Y6ijfSRW9PFqCDAZzU4snQ7v5kWByWGnex": '"onchainvillain" on Pump.fun (777Dy)',
    "7BVsMqCRoeEtvVeasYGrRhy83gHr5ZSJBnpV7QeCFQs4": '"nevets7x" on Pump.fun (7BVsM)',
    "7F1irRiu2J1LRMYpkjupmuZMwQqq5LHoGbzquYvkF2X7": '"PineSleepyChef" on Pump.fun (7F1ir)',
    "7Fr2JMaEmKVknR3XXvRzXAgximNb1sXpj6GCZAH6WQvM": '"g2tgski" on Pump.fun (7Fr2J)',
    "7Hq5RkxMLR4tDc5GyKaTuxvuZRyhg4Hbczvktei9dbF1": '"onlysquid63231" on Pump.fun (7Hq5R)',
}
base.update(extra)
json.dump(base, open("solscan_names.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(base))

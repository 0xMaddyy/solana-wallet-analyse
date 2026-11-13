from sno.paths import SOURCES, label_file, source_file
import collections
import json
import os
import re

B58 = r"[1-9A-HJ-NP-Za-km-z]{32,44}"

tips = {}

libsam = open(source_file("libsam_swqos.txt"), encoding="utf-8").read()
for addr, agent in re.findall(rf'"({B58})"\s*:\s*enum\.SWQoSAgent(\w+)', libsam):
    tips[addr] = agent

sdk = open(source_file("sol_parser_sdk_tips.txt"), encoding="utf-8").read()
for m in re.finditer(r"pub const (\w+)_TIP_ACCOUNTS[^=]*=\s*&\[(.*?)\];", sdk, re.S):
    for addr in re.findall(rf'pubkey!\("({B58})"\)', m.group(2)):
        tips.setdefault(addr, m.group(1).title())

official = {
    "Jito": ["96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
             "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
             "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
             "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"],
    "HeliusSender": ["4ACfpUFoaSD9bfPdeu6DBt89gB6ENTeHBXCAi87NhDEE", "D2L6yPZ2FmmmTKPgzaMKdhu6EWZcTpLy1Vhx8uvZe7NZ",
                     "9bnz4RShgq1hAnLnZbP8kbgBg1kEmcJBYQq3gQbmnSta", "5VY91ws6B2hMmBFRsXkoAAdsPHBJwRfBht4DXox3xkwn",
                     "2nyhqdwKcJZR2vcqCyrYsaPVdAnFoJjiksCXJ7hfEYgD", "2q5pghRs6arqVjRvT5gfgWfWcHWmw1ZuCzphgd5KfWGJ",
                     "wyvPkWjVZz1M8fHQnMMCDTQDbkManefNNhweYk5WkcF", "3KCKozbAaF75qEU33jtzozcJ29yJuaLJTy2jFdzUY8bT",
                     "4vieeGHPYPG2MmyPRcYjdiDmmhN3ww7hsFNap8pVN3Ey", "4TQLFNWK8AovT1gFvda5jfw2oJeRMKEmw7aH6MGBJ3or"],
    "Nozomi": ["TEMPaMeCRFAS9EKF53Jd6KpHxgL47uWLcpFArU1Fanq", "noz3jAjPiHuBPqiSPkkugaJDkJscPuRhYnSpbi8UvC4",
               "noz3str9KXfpKknefHji8L1mPgimezaiUyCHYMDv1GE", "noz6uoYCDijhu1V7cutCpwxNiSovEwLdRHPwmgCGDNo",
               "noz9EPNcT7WH6Sou3sr3GGjHQYVkN3DNirpbvDkv9YJ", "nozc5yT15LazbLTFVZzoNZCwjh3yUtW86LoUyqsBu4L",
               "nozFrhfnNGoyqwVuwPAW4aaGqempx4PU6g6D9CJMv7Z", "nozievPk7HyK1Rqy1MPJwVQ7qQg2QoJGyP71oeDwbsu",
               "noznbgwYnBLDHu8wcQVCEw6kDrXkPdKkydGJGNXGvL7", "nozNVWs5N8mgzuD3qigrCG2UoKxZttxzZ85pvAQVrbP",
               "nozpEGbwx4BcGp6pvEdAh1JoC2CQGZdU6HbNP1v2p6P", "nozrhjhkCr3zXT3BiT4WCodYCUFeQvcdUkM7MqhKqge",
               "nozrwQtWhEdrA6W8dkbt9gnUaMs52PdAv5byipnadq3", "nozUacTVWub3cL4mJmGCYjKZTnE9RbdY5AP46iQgbPJ",
               "nozWCyTPppJjRuw2fpzDhhWbW355fzosWSzrrMYB1Qk", "nozWNju6dY353eMkMqURqwQEoM3SFgEKC6psLCSfUne",
               "nozxNBgWohjR75vdspfxR5H9ceC7XXH99xpxhVGt3Bb"],
    "0slot": ["Eb2KpSC8uMt9GmzyAEm5Eb1AAAgTjRaXWFjKyFXHZxF3", "FCjUJZ1qozm1e8romw216qyfQMaaWKxWsuySnumVCCNe",
              "ENxTEjSQ1YabmUpXAdCgevnHQ9MHdLv8tzFiuiYJqa13", "6rYLG55Q9RpsPGvqdPNJs4z5WTxJVatMB8zV3WJhs5EK",
              "Cix2bHfqPcKcM233mzxbLk14kSggUUiz2A87fJtGivXr", "6fQaVhYZA4w3MBSXjJ81Vf6W1EDYeUPXpgVQ6UQyU1Av",
              "4HiwLEP2Bzqj3hM2ENxJuzhcPCdsafwiet3oGkMkuQY4", "7toBU3inhmrARGngC7z6SjyP85HgGMmCTEwGNRAcYnEK",
              "8mR3wB1nh4D6J9RUCugxUpc6ya8w38LPxZ3ZjcBhgzws", "6SiVU5WEwqfFapRuYCndomztEwDjvS5xgtEof3PLEGm9",
              "TpdxgNJBWZRL8UXF5mrEsyWxDWx9HQexA9P1eTWQ42p", "D8f3WkQu6dCF33cZxuAsrKHrGsqGP2yvAHf8mX6RXnwf",
              "GQPFicsy3P3NXxB5piJohoxACqTvWE9fKpLgdsMduoHE", "Ey2JEr8hDkgN8qKJGrLf2yFjRhW7rab99HVxwi5rcvJE",
              "4iUgjMT8q2hNZnLuhpqZ1QtiV8deFPy2ajvvjEpKKgsS", "3Rz8uD83QsU8wKvZbgWAPvCNDU6Fy8TSZTMcPm3RB6zt"],
    "Astralane": ["astrazznxsGUhWShqgNtAdfrzP2G83DzcWVJDxwV9bF", "astra4uejePWneqNaJKuFFA8oonqCE1sqF6b45kDMZm",
                  "astra9xWY93QyfG6yM8zwsKsRodscjQ2uU2HKNL5prk", "astraRVUuTHjpwEVvNBeQEgwYx9w9CFyfxjYoobCZhL",
                  "astraEJ2fEj8Xmy6KLG7B3VfbKfsHXhHrNdCQx7iGJK", "astraubkDw81n4LuutzSQ8uzHCv4BhPVhfvTcYv8SKC",
                  "astraZW5GLFefxNPAatceHhYjfA1ciq9gvfEg2S47xk", "astrawVNP4xDBKT7rAdxrLYiTSTdqtUr63fSMduivXK",
                  "AstrA1ejL4UeXC2SBP4cpeEmtcFPZVLxx3XGKXyCW6to", "AsTra79FET4aCKWspPqeSFvjJNyp96SvAnrmyAxqg5b7",
                  "AstrABAu8CBTyuPXpV4eSCJ5fePEPnxN8NqBaPKQ9fHR", "AsTRADtvb6tTmrsqULQ9Wji9PigDMjhfEMza6zkynEvV",
                  "AsTRAEoyMofR3vUPpf9k68Gsfb6ymTZttEtsAbv8Bk4d", "AStrAJv2RN2hKCHxwUMtqmSxgdcNZbihCwc1mCSnG83W",
                  "Astran35aiQUF57XZsmkWMtNCtXGLzs8upfiqXxth2bz", "AStRAnpi6kFrKypragExgeRoJ1QnKH7pbSjLAKQVWUum",
                  "ASTRaoF93eYt73TYvwtsv6fMWHWbGmMUZfVZPo3CRU9C"],
    "bloXroute": ["HWEoBxYs7ssKuudEjzjmpfJVX7Dvi7wescFsVx2L5yoY", "95cfoy472fcQHaw4tPGBTKpn6ZQnfEPfBgDQx6gcRmRg",
                  "3UQUKjhMKaY2S6bjcQD6yHB7utcZt5bfarRCmctpRtUd", "FogxVNs6Mm2w9rnGL1vkARSwJxvLE8mujTv3LK8RnUhF",
                  "bLx7MvxGaKdKL7mEbpk9tC79z6MnBSJoJkuaEAPu6Nd", "bLx7XBqSg3LUPVf1bRgCnkJmgVZR8QEgDJBPqcRLHvp",
                  "bLx8KeZxinPwy6kkUgyzMLeqb2ARNsWjADG1dhSsVba", "bLxADBknoNj8WAGw2W6GBYeq848Xx6ajhaymV1YvrHm",
                  "bLxAc88vRBwvcUQJEgcxNfBLvHPikY4csNsUmPeWea2", "bLxQ88oCiTsL8Xj4YWekKi1hjrgmbE3J3FFZ2xZHR3h",
                  "bLxS7NoLuynNRJ4mCnEE2YbtwJFttYsEyp2ME7rp2yt", "bLxW6mCov7VEbrKc3S9tcBRcfSzRnLCbNp3Dfn3SJG5",
                  "bLxXSGXs4mYPTC5okZXed1qzvjNwNJ48QJ82hT2V7w7", "bLxYi3vojbbB7hVzVDVTdBLVPhp7GJ3ZB3BwdK5sFXi",
                  "bLxhLPgBXtUpX4b1bH3HatuMGMSKT9GnwtuCGiMSAqe", "bLxpY1mniuFW4PgkNA4JiNxoeKHFszryi6tNgyZAiAA",
                  "bLxuETxd2tgWxBALNwPzAfHhsik4BzD3nrEBCiPNZQD", "bLxuL2gK5FW7xfahvwLrxLyW76vcCpNsKQY2CmnE6kV",
                  "bLxv4Hnub7nDJWHs8s17o9bGU65Bnx6Yqp2fqtMgHmm"],
}
for provider, addrs in official.items():
    for a in addrs:
        tips[a] = provider

orb_providers = {"Lunar": "LunarLander", "Temporal": "Nozomi", "Bloxroute": "bloXroute", "Jito": "Jito"}
orb = json.load(open(source_file("orb_tags.json"), encoding="utf-8"))
for addr, (name, kind) in orb.items():
    if kind == "Transaction Sending":
        first = name.split()[0]
        tips[addr] = orb_providers.get(first, first)
for addr, provider in json.load(open(source_file("funder_tips.json"), encoding="utf-8")).items():
    if not addr.startswith("_"):
        tips[addr] = provider

normalize = {"zeroslot": "0slot", "0slot": "0slot", "temporal": "Nozomi", "nozomi": "Nozomi", "jito": "Jito",
             "bloxroute": "bloXroute", "nextblock": "NextBlock", "astralane": "Astralane", "astral": "Astralane",
             "blockrazor": "BlockRazor", "flashblock": "FlashBlock", "node1": "Node1", "helius": "HeliusSender",
             "heliussender": "HeliusSender", "soyas": "Soyas", "speedlanding": "SpeedLanding", "lunarlander": "LunarLander",
             "glaive": "Glaive", "stellium": "Stellium"}
tips = {a: normalize.get(p.lower(), p) for a, p in tips.items()}
print(collections.Counter(tips.values()))
json.dump(tips, open(label_file("labels_swqos.json"), "w"), indent=0)

platforms = {
    "programs": {
        "FLASHX8DrLbgeR8FcfNV1F5krxYcYMUdBkrP1EPBtxB9": "Axiom",
        "BSfD6SHZigAfDWSjzD5Q41jw8LmKwtmjskPH9XW1mrRW": "Photon",
        "GMgnVFR8Jb39LoXsEVzb3DvBy3ywCmdmJquHUy1Lrkqb": "GMGN",
        "GMGNreQcJFufBiCTLDBgKhYEfEe9B454UjpDr5CaSLA1": "GMGN",
        "MaestroAAe9ge5HTc64VbBQZ6fP77pwvrhM8i1XWSAx": "Maestro",
        "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter aggregator",
    },
    "program_prefixes": {"troy": "Trojan", "BANANA": "Banana Gun", "term": "Terminal (pump.fun)", "GMgn": "GMGN"},
    "fee_wallets": {
        **{a: "Axiom" for a in [
            "7LCZckF6XXGQ1hDY6HFXBKWAtiUgL9QY5vj1C4Bn1Qjj", "4V65jvcDG9DSQioUVqVPiUcUY9v6sb6HKtMnsxSKEz5S",
            "CeA3sPZfWWToFEBmw5n1Y93tnV66Vmp8LacLzsVprgxZ", "AaG6of1gbj1pbDumvbSiTuJhRCRkkUNaWVxijSbWvTJW",
            "7oi1L8U9MRu5zDz5syFahsiLUric47LzvJBQX6r827ws", "9kPrgLggBJ69tx1czYAbp7fezuUmL337BsqQTKETUEhP",
            "DKyUs1xXMDy8Z11zNsLnUg3dy9HZf6hYZidB6WodcaGy", "4FobGn5ZWYquoJkxMzh2VUAWvV36xMgxQ3M7uG1pGGhd",
            "76sxKrPtgoJHDJvxwFHqb3cAXWfRHFLe3VpKcLCAHSEf", "H2cDR3EkJjtTKDQKk8SJS48du9mhsdzQhy8xJx5UMqQK",
            "8m5GkL7nVy95G4YVUbs79z873oVKqg2afgKRmqxsiiRm", "4kuG6NsAFJNwqEkac8GFDMMheCGKUPEbaRVHHyFHSwWz",
            "8vFGAKdwpn4hk7kc1cBgfWZzpyW3MEMDATDzVZhddeQb", "86Vh4XGLW2b6nvWbRyDs4ScgMXbuvRCHT7WbUT3RFxKG",
            "DZfEurFKFtSbdWZsKSDTqpqsQgvXxmESpvRtXkAdgLwM", "5L2QKqDn5ukJSWGyqR4RPvFvwnBabKWqAqMzH4heaQNB",
            "DYVeNgXGLAhZdeLMMYnCw1nPnMxkBN7fJnNpHmizTrrF", "Hbj6XdxX6eV4nfbYTseysibp4zZJtVRRPn2J3BhGRuK9",
            "846ah7iBSu9ApuCyEhA5xpnjHHX7d4QJKetWLbwzmJZ8", "5BqYhuD4q1YD3DMAYkc1FeTu9vqQVYYdfBAmkZjamyZg"]},
        "AVUCZyuT35YSuj4RH7fwiyPu82Djn2Hfg7y2ND2XcnZH": "Photon",
        "9yMwSPk9mrXSN7yDHUuZurAh1sjbJsfpUqjZ7SvVtdco": "Trojan",
        **{a: "Trojan Terminal" for a in [
            "92Med3qeK7duC5iiYsHX38H2f2twJfRsSx93oNrza2VH", "2jwHNxavSoMZMEDbT1eV9PcPt5dDcayCqM6MkgaPpmWQ",
            "65gDv7pZQCZELsNpNYSFEBtNFpWZAbxmRFB6BGMqFkHH", "BWgb8wR1FEGiu1jCDSKuHKf752W27b4iN6SvoNCiK4qp",
            "8jgg7moFJkHyTtAv9M6RBSPMp2oXeXhuiUMKW8YbYCWn"]},
    },
    "fee_wallet_prefix_suffix": [
        ["BfFX9r", "CKJike", "Axiom"], ["ByRRgn", "pGBxRy", "GMGN"], ["J5XGHm", "XPvFB5", "Terminal (pump.fun)"],
        ["9yj3zv", "t7djXf", "Phantom"], ["8ckLnP", "mFfigk", "OKX router"],
    ],
    "tip_prefixes": {"axm": "Axiom private tip (Nozomi)"},
}
# Owned by the Axiom program; paid ~1% of the buy inside the FLASHX router call.
for a in ["3Tu1Y9aNveLFN4WTAwnAwXL6tbUp5MMe3RxyybG4jTAS", "3PvqoztjnRxaAiFmLuEfqZkU4GSbjUareks8S2xCZaTa",
          "HkJYryz2BNeMQfuuSWDYktWt5fZLV26eK6nqu7EJycoG", "ECDrSz47nXihe5kyK4oWEePPsPi9qz6u5d6Fa2sDj3uM",
          "2ApLdwLrGayEmxgpLX9BTR47Q2QprfMg5SpjrLeaK8s7", "5vPNE6VFyXmCmzmWotdxmRk57LEWiXxuAfZL3hKbi2LH",
          "EqGzowSp6cKAsMSRyyrFTaBxnZEVeNY81LC18YFy8Cx9"]:
    platforms["fee_wallets"][a] = "Axiom"
orb_fee_names = {"BasedBot": "BasedBot", "GMGN": "GMGN", "Bloom": "Bloom", "Trojan": "Trojan", "Sol": "Sol Trading Bot",
                 "j7tracker": "j7tracker", "Maestro": "Maestro", "Rapid": "Rapid Launch", "BullX": "BullX",
                 "Dexscreener": "Dexscreener", "Bonkbot": "Bonkbot"}
for addr, (name, kind) in orb.items():
    if kind == "Fees":
        platforms["fee_wallets"].setdefault(addr, orb_fee_names.get(name.split()[0], name.split()[0]))
json.dump(platforms, open(label_file("labels_platforms.json"), "w"), indent=1)
print("platform labels saved")

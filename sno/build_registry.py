from sno.paths import RESULTS, SOURCES, LABELS, label_file, source_file, ROOT
import json
import os
import re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources", "registry_src.txt")

EXTRA = {
    "ZEROSLOT": [
        "6fQaVhYZA4w3MBSXjJ81Vf6W1EDYeUPXpgVQ6UQyU1Av", "4HiwLEP2Bzqj3hM2ENxJuzhcPCdsafwiet3oGkMkuQY4",
        "7toBU3inhmrARGngC7z6SjyP85HgGMmCTEwGNRAcYnEK", "8mR3wB1nh4D6J9RUCugxUpc6ya8w38LPxZ3ZjcBhgzws",
        "6SiVU5WEwqfFapRuYCndomztEwDjvS5xgtEof3PLEGm9", "TpdxgNJBWZRL8UXF5mrEsyWxDWx9HQexA9P1eTWQ42p",
        "D8f3WkQu6dCF33cZxuAsrKHrGsqGP2yvAHf8mX6RXnwf", "GQPFicsy3P3NXxB5piJohoxACqTvWE9fKpLgdsMduoHE",
        "Ey2JEr8hDkgN8qKJGrLf2yFjRhW7rab99HVxwi5rcvJE", "4iUgjMT8q2hNZnLuhpqZ1QtiV8deFPy2ajvvjEpKKgsS",
        "3Rz8uD83QsU8wKvZbgWAPvCNDU6Fy8TSZTMcPm3RB6zt",
    ],
    "NOZOMI": [
        "TEMPaMeCRFAS9EKF53Jd6KpHxgL47uWLcpFArU1Fanq", "noz3jAjPiHuBPqiSPkkugaJDkJscPuRhYnSpbi8UvC4",
        "noz3str9KXfpKknefHji8L1mPgimezaiUyCHYMDv1GE", "noz6uoYCDijhu1V7cutCpwxNiSovEwLdRHPwmgCGDNo",
        "noz9EPNcT7WH6Sou3sr3GGjHQYVkN3DNirpbvDkv9YJ", "nozc5yT15LazbLTFVZzoNZCwjh3yUtW86LoUyqsBu4L",
        "nozFrhfnNGoyqwVuwPAW4aaGqempx4PU6g6D9CJMv7Z", "nozievPk7HyK1Rqy1MPJwVQ7qQg2QoJGyP71oeDwbsu",
        "noznbgwYnBLDHu8wcQVCEw6kDrXkPdKkydGJGNXGvL7", "nozNVWs5N8mgzuD3qigrCG2UoKxZttxzZ85pvAQVrbP",
        "nozpEGbwx4BcGp6pvEdAh1JoC2CQGZdU6HbNP1v2p6P", "nozrhjhkCr3zXT3BiT4WCodYCUFeQvcdUkM7MqhKqge",
        "nozrwQtWhEdrA6W8dkbt9gnUaMs52PdAv5byipnadq3", "nozUacTVWub3cL4mJmGCYjKZTnE9RbdY5AP46iQgbPJ",
        "nozWCyTPppJjRuw2fpzDhhWbW355fzosWSzrrMYB1Qk", "nozWNju6dY353eMkMqURqwQEoM3SFgEKC6psLCSfUne",
        "nozxNBgWohjR75vdspfxR5H9ceC7XXH99xpxhVGt3Bb",
    ],
    "BLOXROUTE": [
        "3UQUKjhMKaY2S6bjcQD6yHB7utcZt5bfarRCmctpRtUd", "FogxVNs6Mm2w9rnGL1vkARSwJxvLE8mujTv3LK8RnUhF",
        "bLx7MvxGaKdKL7mEbpk9tC79z6MnBSJoJkuaEAPu6Nd", "bLx7XBqSg3LUPVf1bRgCnkJmgVZR8QEgDJBPqcRLHvp",
        "bLx8KeZxinPwy6kkUgyzMLeqb2ARNsWjADG1dhSsVba", "bLxADBknoNj8WAGw2W6GBYeq848Xx6ajhaymV1YvrHm",
        "bLxAc88vRBwvcUQJEgcxNfBLvHPikY4csNsUmPeWea2", "bLxQ88oCiTsL8Xj4YWekKi1hjrgmbE3J3FFZ2xZHR3h",
        "bLxS7NoLuynNRJ4mCnEE2YbtwJFttYsEyp2ME7rp2yt", "bLxW6mCov7VEbrKc3S9tcBRcfSzRnLCbNp3Dfn3SJG5",
        "bLxXSGXs4mYPTC5okZXed1qzvjNwNJ48QJ82hT2V7w7", "bLxYi3vojbbB7hVzVDVTdBLVPhp7GJ3ZB3BwdK5sFXi",
        "bLxhLPgBXtUpX4b1bH3HatuMGMSKT9GnwtuCGiMSAqe", "bLxpY1mniuFW4PgkNA4JiNxoeKHFszryi6tNgyZAiAA",
        "bLxuETxd2tgWxBALNwPzAfHhsik4BzD3nrEBCiPNZQD", "bLxuL2gK5FW7xfahvwLrxLyW76vcCpNsKQY2CmnE6kV",
        "bLxv4Hnub7nDJWHs8s17o9bGU65Bnx6Yqp2fqtMgHmm",
    ],
}

src = open(SRC, encoding="utf-8").read()
groups = {}
for m in re.finditer(r"pub const (\w+)_TIP_ACCOUNTS: &\[Pubkey\] = &\[(.*?)\];", src, re.S):
    groups[m.group(1)] = re.findall(r'pubkey!\("(\w+)"\)', m.group(2))
for name, accounts in EXTRA.items():
    groups[name] = sorted(set(groups.get(name, [])) | set(accounts))

registry = {acct: name for name, accts in groups.items() for acct in accts}
json.dump(registry, open("tip_registry.json", "w"), indent=0)
print({k: len(v) for k, v in groups.items()})
for probe in ("astrazznxsGUhWShqgNtAdfrzP2G83DzcWVJDxwV9bF", "AsTRAEoyMofR3vUPpf9k68Gsfb6ymTZttEtsAbv8Bk4d",
              "Eb2KpSC8uMt9GmzyAEm5Eb1AAAgTjRaXWFjKyFXHZxF3", "wyvPkWjVZz1M8fHQnMMCDTQDbkManefNNhweYk5WkcF",
              "ste11JV3MLMM7x7EJUM2sXcJC1H7F4jBLnP9a9PG8PH"):
    print(probe[:10], registry.get(probe))

# sno_pair: Solana pump.fun copy/backrun bot research

Research into six buyer/seller wallet pairs that backrun (copy) pump.fun buys, to learn how to build a similar bot.

## Wallet pairs (buyer buys + approves seller as unlimited delegate, seller sells)

| Buyer | Seller |
|---|---|
| 3pDHoZBjQhAf9w5zTWsVyys7NxiQdewbjj6jnZcKP9ya | C8qCb6smwarmisb89kUejVsd8uHHj96AXWT2Ex1XD33i |
| 2PAijCsZGAmG8tVgrAmwyGC5UcXxwktYkAiy57CAXTuy | Bj5PgdHXkZT4bw7YxQXuBeSbjfqqHgMoZAsDxdaYzGSt |
| 5qsuh6KapqaF6WdhdvqBKF8JiQxVmnXD7Uqr8D36iePp | FzwbhYksjD9JJTFwZozcQQmXMKDCmY1uMz71daBAoMsy |
| DTGbH68GcJujkim2BfGG7nHUv5Sox4GBJKsdDRKutANm | Fa9qPovB2gxs67eCxWM9KheYJH9BgyPjGBqj8cL1bLRG |
| CH7GewnUqV8pdnjywGz71QVFRZ549BsDqNnpBxhzREQk | EKn5wiBAQ2UuMTAK94gPmqFabVSMCxWtzHRKxRqMYzP7 |
| 8N4CBW2aX5jzpZuhsvzB5AXwLmfBJZEU8mYnC84KWrxF | HZUCsc7pThddRkSW8CyBfvHo4ZskrHMsg7uK46Mk1nS7 |
| BPKVyybfMjhTEDFWBYa2wDnRV5a4Z3Lks8ZfMec3qUAW | 6AKrfdeLdgsR1NJjSEih7rajxv8AQvrkmmhn9HMuqrcf |
| E7hhZy9v9v2WwPx72yf8gTYF5AcJoVaSWVuJ31tueN5C | GvwYCrHPd4LGLQTTPw7jb4jtEhA4uNBs4nVS9FwqX2WH |
| FaHvzFA7qJzZQ2kc3wA6gM6TyKKakGSfdqSy1vZ5hXB | Bkm31LJnd5DNkvMsdYFJESBCJyVGmTxHAcKkKAV3fSvY |
| TMWwfSM5LjA17HaWAFkvu3WXuwgk1SZ5iTuzEwdoci9 | 85bLtKy9cZ1v2LuWsnDvzF4K9m9wZyy55aMZjQJ21qdA |
| FdBhsbFNpEPQSyme9WMUaUoFWfF4Qfnrc7tBihU6HbkQ | 2fTzkTQJa2WvHnibyqJVQ497paecSnRd278v18XceiBB |

Profits of the 8N4CBW pair are swept to 95ADqy... List also in `config/wallets/wallets_sno_pairs.txt`.

## Wallet `omegoMAe1AMY5MFKQQr3JwXVy8F4eCvmBAfcpo8XAfq`

- Single wallet: buys and sells itself (no Token-2022 delegate seller). Trades pump.fun through executor `7xdwTaV5QModH7HBysseq2AaNXRajLjL7KAwvFwBJzkX` (older txs also hit router `HDk4dSrL…`); some sells via Raydium CLMM. Sample of recent buys: mix of same-block copies and solo entries, not next-tx backruns.
- Nov 9–10 UTC funding PnL (`scripts/pnl/wallet_profit_omego_nov9_10.py`): SOL deposited 4.45 / withdrawn 0; USDC deposited ~0 / withdrawn **9,420.80**. Profit = bal change + withdraw − deposit: **−4.84 SOL** and **+9,420.80 USDC**. Daily: Nov9 +3.81 SOL / +5,434 USDC; Nov10 −8.66 SOL / +3,987 USDC. ~21k succeeded txs in the window. Outputs under `results/wallet_omego_nov9_10_*`.

## Nov 5–8 2026 (UTC) pair FIFO PnL (`scripts/pnl/pair_pnl_nov5_8.py`)

- Realized buy→sell PnL on buyer+seller for buys on Nov 5–8 (sells through Nov 9 04:00). Grand total **+96.59 SOL**.
- Per pair: 3pD +18.0, 8N4 +15.0, CH7 +14.3, FaH +8.1, E7h +7.9, 5qs +7.5, DTG +6.3, BPK +5.8, 2PA +5.7, FdB +5.1, TMW +3.1.
- Daily all-pairs: Nov5 +26.8, Nov6 +33.4, Nov7 +22.1, Nov8 +14.2. Details: `results/pair_pnl_nov5_8.txt`, `results/pair_pnl_nov5_8_daily.csv`.

## Oct 8 2026 (UTC) results, `results/backruns_oct8.csv`

- 2,063 backruns, about +104.6 SOL total on backrun buys (per pair: 3pDH +12.21, 2PAi +17.94, 5qsu +13.96, DTGb +22.26, CH7G +11.18, 8N4C +27.09). Recomputed Oct 11 by `fill_profit.py`; the earlier +99.4 used per-mint attribution (see below).
- A buy is a backrun when the previous transaction in the block is an outside wallet buying the same mint.
- `trade_profit_sol` is per buy: the sells that consumed that buy's tokens (FIFO) minus its cost, fees and tips included, over Oct 8 00:00 to Oct 9 04:00 UTC. The bots sell each buy separately with the exact token amount (2,055 of 2,063 rows close with one sell); all rows are closed. `position_profit_sol` keeps the whole-mint total (all buys incl. non-backrun ones).
- Old per-mint attribution (multi_report.py) left 622 rows blank ("same trade as"), lost 89 rows whose first buy was not a backrun, and split SOL evenly in sells that also received a dust token (halving those sells' proceeds). `fill_profit.py` fixes all three.
- Bot route: 1,165 Jito bundles (target first), 898 direct sends with priority fee only.
- Each target was backrun by only one of the six bots, so it is likely one operator splitting order flow.
- Target platforms: direct pump.fun 906, Axiom 748, pump.fun app 118, GMGN 88, Jupiter 63, Terminal 30, Bloom 25, Trojan 21, others are small (Uxento, j7tracker, Sol Trading Bot etc. identified via Orb fee-wallet labels).
- Target SWQoS (after Orb relabel, Oct 11): LunarLander 658, HeliusSender 161, 0slot 146, Nozomi 142, Astralane 139, Jito 57, GMGN 29, bloXroute 15, small others; none detected 684 (533 of these pay no unlabeled destination at all, i.e. priority fee only).
- Axiom targets send through Hello Moon Lunar Lander: 644 of 748 tip a "Lunar Tip Account" (Orb label, median 0.002 SOL). Our source lists only had 10 of Lunar's 100+ tip accounts.
- The 7 big unlabeled Axiom destinations (3Tu1Y9, 3Pvqoz, HkJYry, ECDrSz, 2ApLdw, 5vPNE6, EqGzow) are accounts owned by the Axiom program, paid ~1.02% of the buy inside the FLASHX router call: Axiom trading fees, not tips. Now labeled as Axiom fee wallets.
- Tip labels come from Orb's `/api/tags/resolve` (saved in `sources/orb_tags.json`); 16 unlabeled AST/asT vanity accounts were attributed to Astralane by first funder 4Hypzh3 (`sources/funder_tips.json`). Still unidentified tip-like vanity accounts: BBtip* (funder 7v4f5g), Cbase*/CBase* (funders 5haVcT, CgM5dk), BLiTZ* (funder pestwAEP).
- Leader regions: frankfurt 834, amsterdam 447, london 384, ny 191, tokyo 99, dublin 44, singapore 39, slc 25 (current IP geolocation via getClusterNodes + ip-api.com batch).
- Leader data centers (`data_center`, from leader_ip org/AS via ip-api): TeraSwitch 708, Latitude.sh 286, Cherry Servers 251, Allnodes 192, Payward/Kraken 132, OVH 82, RETN 70, Galaxy Digital 56, Servers.com 42, Dedicatednodes 40, Twinstake 37, AWS 35, others small. Added by `add_datacenter.py`.
- Leader client (`leader_client_type`, gossip `clientId` from getClusterNodes on Oct 12, so not exactly Oct 8): 869 of 898 direct sends (97%) landed in slots led by HarmonicAgave (653) or HarmonicFiredancer (216) validators, which hold only 25.5% of stake. Bundles are spread close to stake: AgaveBam 343, HarmonicAgave 328, JitoLabs 260, HarmonicFiredancer 131, Firedancer 80. Harmonic leaders account for 64% of all backruns. Added by `add_client.py`.

## Oct 13 2026 (UTC) single-wallet bots, `backruns_oct13.csv` (`backruns_oct13.full.csv` if Excel holds the lock)

- 13 wallets were checked. Ten are bots that sign their own buys and sells, with no delegate seller. 2CQgjc and GXAQ8w had no Oct 13 txs; C7BZwD had 41 txs, all paid by other wallets.
- Most txs fail: each wallet had 4k-6.6k+ txs that day, 75-97% failed. Only successful txs are fetched.
- 206 backruns, +122.5 SOL. Per wallet, as buys / backruns / profit:

  | Wallet | Buys | Backruns | Profit (SOL) |
  |---|---|---|---|
  | D6Fu | 33 | 26 | +20.48 |
  | 7XLv | 34 | 21 | +3.70 |
  | 46Zk | 25 | 15 | +8.40 |
  | Fhbh | 52 | 20 | +17.77 |
  | 4bHU | 24 | 18 | +13.36 |
  | 2LSn | 19 | 8 | +3.90 |
  | 55pb | 37 | 24 | +12.17 |
  | FteN | 30 | 15 | +5.36 |
  | 9qz7 | 1,098 | 56 | +37.98 |
  | BuekUk | 128 | 3 | -0.66 |

- BuekUk is hugely active (78k successful txs) but is mostly a different strategy.
- Fhbh, 9qz7 and BuekUk each had a tx paid by HckQ93; they also trade through programs 9buc3tz and GsaJ3Cw.
- Routing differs from Oct 8: 184 direct sends and 22 Jito bundles.
  - Only 110 of 184 direct sends (60%) landed on Harmonic leaders.
  - Direct sends often carry HeliusSender or Astralane tips.
  - Target SWQoS includes a new provider, Stellium (28).
- These bots often buy and sell in the same block. `fill_profit.py` now orders same-slot txs by position in the block (cached in `block_pos_<tag>.json`).
  - Re-running Oct 8 with this fix changes 11 rows; the total goes from 104.636 to 104.656 SOL (`backruns_oct8.blockorder.csv`).

## Execution style: Oct 8 pairs vs Oct 13 wallets (`strategy_check*.py`)

- **Oct 8 pairs ("anticipate").**
  - 56% of backruns are Jito bundles with the target first, plus Lighthouse checks (76% of buys), including the target nonce check. The bot has the target before execution.
  - Small fixed buys (median 0.94 SOL, about 1.3x the target), sold in one sell about 1 s later (408 in the same second). Win rate 50%, median profit about 0 per trade, small edge on volume.
- **Oct 13 wallets ("react").**
  - Each wallet uses its own pair of custom programs: a gate (first instruction) and an executor, e.g. D6Fu 75EdNS + 9EJzpY, 55pb 3Br67f + Gg9TDp. There is almost no Lighthouse.
  - Inside the block (4 sampled):
    - Target at index N, bot at N+1 with a 0.04 SOL priority fee.
    - Then 4-145 more bot copies later in the same block with falling fees, all failing with gate error Custom 1, most likely "already bought".
    - No bot copy landed before the target in those 4 blocks, even though the bot's fee was far higher than the target's (10k-5M lamports).
  - Correction (Oct 15, `ahead_check.py`, `ahead_block.py`, `ahead_decode.py`):
    - Bot copies do sometimes land before the target. This happened in 17 of 203 backruns (244 failed copies) for the 9 Oct 13 wallets, and in 3 of 269 for CNjo9vq.
    - All of these copies failed cheaply. The executor's check fails with Custom 3 after about 800 CU, most likely "the target hasn't bought yet".
    - So the bot has the target before execution and relies on the on-chain check to avoid frontrunning. It is not purely post-execution.
    - Copies are identical durable-nonce txs, each with its own nonce account.
    - Eight of the wallets put the target wallet in their buy's accounts (144 of 147 buys). 9qz7 and CNjo9vq never do.
  - Bigger targets (median 2.0 SOL, 89% at least 1 SOL; Oct 8 median 1.0). Bigger buys (median 3.0 SOL, about 1.7x the target).
  - Held a median of 14 s and sold in 3-7 pieces. Win rate 70%, median +0.28 SOL per trade.
  - CNjo9vq (Oct 13, `backruns_oct13cnjo.csv`): 269 backruns, -0.92 SOL, 53% win.
  - Oct 14 (`backruns_oct14.csv`, same 9 wallets; CNjo9vq had no txs that day):
    - 243 backruns, +134.3 SOL, every trade closed. 215 direct sends (124 on Harmonic leaders) and 28 Jito bundles.
    - Failed copies landed before the target in 24 backruns (130 copies), all failed (`failed_copies_before_target_oct14*.csv`).
  - Oct 12 (`backruns_oct12.csv`, raw backrun list only, no profit columns; same 9 wallets, CNjo9vq inactive):
    - 242 backruns: 217 direct sends and 25 Jito bundles.
    - Failed copies landed before the target in 23 backruns (328 copies), all failed (`failed_copies_before_target_oct12*.csv`).
  - Early copies cluster on AgaveBam (Jito BAM) leaders:
    - Oct 12: 13 of 23, against AgaveBam's 10% share of backruns.
    - Oct 14: 15 of 24, against AgaveBam's 14% share of backruns.
    - Oct 13: 9 of 22, against an 8% share.
    - So BAM ordering sometimes schedules the bot copy before the target.
  - Oct 15–18 (`failed_copies_before_target_oct15*.csv` through `oct18`; same wallet file, CNjo9vq active only on the 15th):
    - Oct 15: 1,070 backruns, copies ahead on 27 trades (216 copies, 206 failed, 10 success). Earliest-copy leader is AgaveBam on 11 of 27. 18 of those 27 are the same slot as the target.
    - Oct 16: 170 backruns, 599 copies on 12 trades, all failed. D6Fu accounts for 468 copies on 4 trades. AgaveBam 3 of 12. Nine earliest copies are the same slot; the other three are up to 43 slots earlier.
    - Oct 17: 87 backruns, 15 copies on 7 trades, all failed, all the same slot. AgaveBam 2 of 7.
    - Oct 18: 79 backruns, 10 copies on 6 trades, all failed, all the same slot. AgaveBam 0 of 6 (HarmonicAgave 3, FireBAM 2, JitoLabs 1).
    - Oct 19: 82 backruns, 14 copies on 7 trades, all failed, all the same slot. AgaveBam 3 of 7 (HarmonicAgave 2, JitoLabs 2). CNjo9vq had no txs. Six of the seven earliest copies fail Custom 3; 2LSn's fails Custom 1.
    - Oct 20: 112 backruns, 7 copies on 4 trades (6 failed, 1 success). Three earliest copies are the same slot and fail Custom 3. The success is Fhbh, 100 slots earlier, and it does not reference the target wallet. AgaveBam 0 of 4; all four earliest-copy leaders are JitoLabs. CNjo9vq had no txs.
    - Oct 21: 153 backruns, 128 copies on 15 trades (125 failed, 3 success). Twelve of the fifteen earliest copies are the same slot. Two successes are the earliest copy of their trade: 9qz7, 10 slots earlier, and Fhbh, 22 slots earlier; neither references the target wallet. AgaveBam 2 of 15. 4bHU had backruns and no copy ahead. CNjo9vq had no txs.
    - Oct 22: 110 backruns, 134 copies on 13 trades, all failed. Twelve of thirteen earliest copies are the same slot. AgaveBam 3 of 13. CNjo9vq had no txs.
    - Oct 23: 113 backruns, 20 copies on 5 trades (19 failed, 1 success). Three of five earliest copies are the same slot. AgaveBam 2 of 5. CNjo9vq had no txs.
    - Oct 24: 126 backruns, 153 copies on 6 trades (152 failed, 1 success). Three of six earliest copies are the same slot. AgaveBam 1 of 6. CNjo9vq had no txs.
    - Oct 25: 91 backruns, 130 copies on 5 trades (129 failed, 1 success). Four of five earliest copies are the same slot. AgaveBam 1 of 5. CNjo9vq had no txs.
    - Oct 26: 124 backruns, 301 copies on 7 trades, all failed. Five of seven earliest copies are the same slot. AgaveBam 2 of 7. CNjo9vq had no txs.
    - The AgaveBam cluster is strong on Oct 12–14 and weaker after that. Same-slot copies that fail before the target continue through the 26th.
  - Repeated targets: 97 unique wallets in 206 backruns (4vw54B 21, ardinR 17, CyaE1V 15), suggesting a watchlist or wallet scoring.

## Gate program `6gY1osmP4FMSrTgzGjPhaSGTKXZgVZwAE71v6DJc3vFi` (Oct 16, `gate_6gY1_oct16.csv`)

- 24 wallets call it. The instruction is a shared gate: an 8-byte id that must already be in state account `FHaSvKD6`, plus a slot deadline (the landing slot or the next one). The buy then goes through `41Pr4XqE` into pump.fun. Sells are separate transactions, through `4DvQwk6W`, with Lighthouse checks.
- Oct 16 00:00–21:20 UTC: 17,371 buys, +221.4 SOL on closed trades, 39% win. Median trade is about −0.01 SOL; the best 1% carry the day (without them the rest is about −28 SOL). Median buy 0.60 SOL, median hold 9 seconds.
- Sniping after a second pass (`gate_6gY1_relabel.py`): copy same block 7,475 (+95.9 SOL), copy 1+ slots later 5,849 (+42.1), next-transaction backrun 1,145 (+21.1), no recent outside buy found 2,902 (+62.4). Copies are most of the trades and most of the profit. Win rate is 38–43% in every bucket.
- Targets that were identified: direct pump.fun, Axiom, an unlabeled router `6Vo3245`, Terminal, GMGN, Jupiter.

## Copy bots `2H6DwrqA` and `CDXzx7BR` (Oct 16–17, `2h6d_buys_oct16_17.csv`)

- `2H6DwrqAsETL1PjrT5KAX3MAELx71FuDkKVZj18PaeJf` and `CDXzx7BRZbJEYiirxoAJ7sxpftUNpSYRcr4NFifb4raJ`. Successful pump.fun and stonk.fun buys from 2026-10-16 00:00 UTC through about 2026-10-17 19:35 UTC (signature page time, not the full 17th).
- 303 buys: 2H6Dwrq 259 (154 on the 16th, 105 on the 17th), CDXzx7BR 44 (35 / 9). Venues: pump.fun 293, pump.fun AMM 5 (all CDXzx7BR), stonk.fun 5 (all 2H6Dwrq). No stonk.fun graduated (Raydium CPMM) buys.
- 281 of 303 have an outside buy of the same mint within 150 slots. 195 are the same slot (median 113 txs later, minimum 2; none are the next transaction). 72 are one slot later. 22 had no target in that lookback.
- Landing: 249 priority fee only, 42 Nozomi (mostly 0.0012 SOL), 3 Stellium 0.0012, 9 Jito (large, about 0.12–2.88 SOL on the bigger buys). `buy_sol` is the wallet's SOL decrease, so it includes the fee and tip.
- Built by `fetch_2h6d.py` (user Helius URL). Columns include `bot_buy_index`, `target_buy_index`, tip, target wallet/tx/slot/platform, and buy size.

## How the bot is protected (Lighthouse `L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95`)

AssertAccountData layout is 13 bytes: `02 | log_level | offset u8 | type (07 = u64) | value u64 LE | operator`. Operators: 0 ==, 1 !=, 2 >, 3 <, 4 >=, 5 <=. `0f` is AssertSysvarClock.

- Example 5sT2Sz... (2PAi pair, direct send):
  - The target's durable nonce account at offset 40 must be != the nonce the target used, so the target has already executed.
  - The target's token account amount at offset 64 must be >= 1.
  - If the bot lands first, it reverts and loses only the fee, so plain sends are safe without bundles.
- Example 3JN7v2... (8N4C pair):
  - A Clock slot deadline.
  - Bonding-curve virtual SOL reserves (offset 16) within a limit.
  - The target holds the token.
  - A cap on the bot's own token account.

## Order-flow conclusion

The bots get signed target transactions before execution, regardless of the target's platform or SWQoS. That is not possible from preconfirmations or shreds. The leading hypothesis is a Flowra-like stream of signed pending transactions from validator relayers (unproven). Suggested test: compare the leaders of backrun slots against Flowra's connected leaders.

Refinement from `leader_client_type`: the pre-execution claim holds for the target-first Jito bundles. The direct sends are almost all in Harmonic slots, and their Lighthouse nonce check only requires the target to have executed already. They fit a post-execution, mid-slot signal from Harmonic's block builders (for example Harmonic preconfirmations): the bot sees the target executed, and its send lands right after it in the same block. Not yet proven: compare target-to-bot timing in Harmonic slots against Harmonic's preconfirmation stream.

## Wallet `6Z91Dgiz9E44bMW11rQuMBjt1NwwPoQGXFNZieGfVtAb` (Oct 29 – Nov 6 2026)

- Funding P&L (SOL/WSOL/USDC in vs out + bal): about +2,294 SOL and +54,795 USDC. At 1 SOL = 100 USDC that is about +284,168 USDC (`results/wallet_6Z91_daily.csv`, `results/wallet_6Z91_daily_combo.csv`).
- Trade P&L split (`scripts/pnl/wallet_6Z91_strategy.py`): a buy is **launch sniping** if the mint has no activity older than 10 slots before the buy; otherwise **copy trading**. Realized FIFO on closed lots: launch **+735.1 SOL** (+73.5k USDC), copy **+887.1 SOL** (+88.7k USDC), total **+1,622 SOL**. Daily table in `results/wallet_6Z91_strategy_daily.csv`. Trade total is below funding P&L (open lots, fee/tip paths, USDC sweeps).

## Repo layout

| Path | Purpose |
|---|---|
| `sno/` | Library: RPC (`analyze.py`), pipeline helpers (`multi_fetch`, `multi_report`, `fill_profit`, …), `paths.py` |
| `scripts/pipeline/` | Day runs, ahead-copy, gate, fetch/copy bots |
| `scripts/pnl/` | Wallet / pair funding and FIFO PnL |
| `scripts/probes/` | One-off probes |
| `scripts/tools/` | dump/decode/export/merge utilities |
| `config/wallets/` | Wallet list inputs |
| `config/labels/` | `labels_swqos.json`, `labels_platforms.json`, … |
| `config/sources/` | Tip/platform source files for `build_labels` |
| `results/` | All generated CSV/JSONL/logs (gitignored) |
| `botcheck/` | Early 8N4CBW signature analysis |
| `chat_context/` | Prior chat export for research continuity |

Set `SNO_RPC_URL` (see `.env.example`). Run from repo root, e.g. `python -m sno.multi_fetch` or `python scripts/pnl/pair_pnl_nov5_8.py`.

## Scripts

- RPC helpers: `sno/analyze.py` (`rpc`, `get_tx`, `summarize`). No API keys in the repo.
- Pipeline: `sno.multi_fetch` -> `sno.multi_report` -> `sno.relabel_targets` -> `sno.fill_profit` (per-buy profit from cached `results/multi_<…>.jsonl`) -> `sno.add_datacenter` -> `sno.add_client`.
- Other days/wallets: `SNO_DAY=YYYY-MM-DD`, `SNO_WALLETS=<file under config/wallets or absolute>`. Outputs under `results/` (`multi_<tag>_<wallet8>.jsonl`, `backruns_<tag>.csv`). Unset env vars afterwards on PowerShell.
- Target grouping: `scripts/pipeline/fetch_targets.py` -> `results/target_txs.jsonl`; `group_targets.py` -> `results/target_groups.csv`. Labels from `sno/build_labels.py` reading `config/sources/`.
- `scripts/tools/dump_tx.py`, `decode_lh.py`. `botcheck/result.json` is the first 600-sig 8N4CBW analysis.

# sno_pair

Research toolkit for Solana pump.fun copy and backrun bots. It reconstructs how named buyer/seller wallets trade, attributes each buy to a target, and measures realized profit from on-chain history.

The repository holds the analysis code and committed inputs. Generated tables, transaction caches, and logs stay in `results/` and are not tracked.

Findings, wallet pairs, and day-by-day conclusions are in [CONTEXT.md](CONTEXT.md).

## What it measures

A typical bot in this set buys on pump.fun and sells from a second wallet that holds a Token-2022 delegate. The pipeline treats a buy as a backrun when the previous transaction in the same block is an outside wallet buying the same mint. Profit is FIFO: each buy’s token amount is matched to the sells that consume it, with fees and tips included.

A second method is used for wallets that fund and sweep in SOL and USDC. Profit is the change in balance plus withdrawals minus deposits, so trading volume does not get counted as a deposit or a withdrawal.

## Layout

| Path | Role |
|---|---|
| `sno/` | Shared library: RPC client, fetch and report, profit, labels, paths |
| `scripts/pipeline/` | Day-level backrun, ahead-copy, and gate runs |
| `scripts/pnl/` | Pair FIFO profit and wallet funding profit |
| `scripts/probes/` | One-off checks used while researching a wallet |
| `scripts/tools/` | Transaction dumps, Lighthouse decode, exports |
| `config/wallets/` | Wallet lists (`buyer` or `buyer,seller` per line) |
| `config/labels/` | Platform and SWQoS label tables |
| `config/sources/` | Raw tip and tag sources used to rebuild labels |
| `results/` | All generated CSV, JSONL, and logs (gitignored) |

## Requirements

Python 3.10 or newer. Scripts use the standard library only.

You need a Solana JSON-RPC endpoint that supports `getTransactionsForAddress` (Helius) and `maxSupportedTransactionVersion: 1`.

## Setup

From the repository root:

```powershell
copy .env.example .env
```

Set `SNO_RPC_URL` in `.env`, or export it in the shell:

```powershell
$env:SNO_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY"
```

`sno.analyze` also accepts `HELIUS_RPC_URL` or `HELIUS_API_KEY`. Do not commit a key.

Run every script from the repository root so imports and `sno.paths` resolve.

## Common runs

**Backrun day for the default six pairs** (UTC day, sells included through 04:00 the next day):

```powershell
$env:SNO_DAY = "2026-10-08"
python -m sno.multi_fetch
python -m sno.multi_report
python -m sno.relabel_targets
python -m sno.fill_profit
python -m sno.add_datacenter
python -m sno.add_client
Remove-Item Env:SNO_DAY
```

Outputs land in `results/`: `multi_<tag>_<wallet>.jsonl` and `backruns_<tag>.csv`.

**Another wallet file** (filename under `config/wallets/`, or an absolute path):

```powershell
$env:SNO_DAY = "2026-11-05"
$env:SNO_WALLETS = "wallets_sno_pairs.txt"
$env:SNO_TAG = "nov5"
python -m sno.multi_fetch
Remove-Item Env:SNO_DAY, Env:SNO_WALLETS, Env:SNO_TAG
```

On PowerShell, those variables stay set for the session until you remove them.

**Pair FIFO profit** for the wallets in `config/wallets/wallets_sno_pairs.txt`:

```powershell
python scripts/pnl/pair_pnl_nov5_8.py
```

**Funding profit** (SOL, WSOL, and USDC deposits versus withdrawals) for a single wallet script under `scripts/pnl/`.

**Rebuild platform and tip labels** from `config/sources/`:

```powershell
python -m sno.build_labels
```

## Conventions

- Fetch full transactions with `maxSupportedTransactionVersion: 1`.
- Write new scripts as files. Long `python -c` one-liners break under PowerShell quoting.
- New outputs go through `sno.paths.RESULTS`. Committed inputs stay under `config/`.
- When a result changes a conclusion, update `CONTEXT.md`.

## Scope

This is an offline research workspace. It reads public chain data and writes local reports. It does not submit transactions.

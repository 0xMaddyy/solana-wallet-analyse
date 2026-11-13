import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import csv

SOL_USD = 100.0
rows = list(csv.DictReader(open("wallet_6Z91_daily.csv", encoding="utf-8-sig")))
out = []
tot_sol = tot_usdc = tot_combo_usdc = tot_combo_sol = 0.0
print(f"assumption: 1 SOL = {SOL_USD:.0f} USDC\n")
print(f"{'day':<12} {'sol_profit':>12} {'usdc_profit':>14} {'combo_USDC':>14} {'combo_SOL':>12}")
for r in rows:
    sp = float(r["sol_profit"])
    up = float(r["usdc_profit"])
    combo_u = sp * SOL_USD + up
    combo_s = sp + up / SOL_USD
    tot_sol += sp
    tot_usdc += up
    tot_combo_usdc += combo_u
    tot_combo_sol += combo_s
    print(f"{r['day']:<12} {sp:+12.6f} {up:+14.4f} {combo_u:+14.2f} {combo_s:+12.6f}")
    out.append({
        **r,
        "combo_profit_usdc": round(combo_u, 4),
        "combo_profit_sol": round(combo_s, 6),
        "sol_usd_rate": SOL_USD,
    })

# overall from start/end + funding (same as summary file)
overall_sol = 2293.725981
overall_usdc = 54795.1169
overall_combo_u = overall_sol * SOL_USD + overall_usdc
overall_combo_s = overall_sol + overall_usdc / SOL_USD
print()
print(f"sum daily SOL {tot_sol:+.6f}  USDC {tot_usdc:+.4f}")
print(f"sum daily combo  {tot_combo_usdc:+.2f} USDC  =  {tot_combo_sol:+.6f} SOL")
print(f"period overall   {overall_combo_u:+.2f} USDC  =  {overall_combo_s:+.6f} SOL")
print(f"  (from overall SOL {overall_sol:+.6f} + USDC {overall_usdc:+.4f})")

with open("wallet_6Z91_daily_combo.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(out)

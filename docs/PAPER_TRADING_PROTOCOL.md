# Paper Trading Protocol

## Core Unit Rules (applies to XRP Swing + SOL Day)

| Parameter              | Value                          |
|------------------------|--------------------------------|
| **Unit Size**          | Fixed **$2,000** notional      |
| **Max Loss**           | **1R**                         |
| **Take Profit 1**      | **3R** (scale out partial)     |
| **Take Profit 2**      | **5R** (final target)          |

These unit rules are now the standard for all paper (and future live) trades in this research system.

---

## Purpose
Live ongoing paper trades give the formula **new out-of-sample information** for analytics and bootstrap.
Rules stay frozen. Paper fills are logged the same way as live would be.

## When a paper trade opens
Trigger: gate_scan action flips to **BUY** (progress 100%) for a variant.

**Position sizing (new standard):**
- Always use **1 unit = $2,000** notional
- Calculate R from entry price to stop price
- Risk is fixed at 1R per unit

Record in `trades.jsonl`:
- `variant` (BASE / PB8 / HOLD7 / LOOSE)
- `unit_size_usd`: 2000
- `entry_ts`, `entry_px`, `stop_px`
- `r_value` (dollar distance of 1R)
- `tp1_px` (3R), `tp2_px` (5R)
- `status`: OPEN
- `notes`: "PAPER"

## While open
- Track unrealized P&L in R-multiples
- Update MAE / MFE in R terms
- Do **not** change entry rules or stop mid-trade

## Exit Rules
A paper trade closes when **any** of the following occurs:

1. **Stop hit** → -1R (max loss)
2. **TP1 (3R)** → scale out (e.g. 50%)
3. **TP2 (5R)** → close remaining
4. Time-based exit (BASE = 10 trading days) if neither TP nor stop has been hit
5. Daily close under the 200-day regime filter

## After close
1. Log final R-multiple achieved
2. Append analytics / expectancy refresh
3. Outlier check (2 sigma)
4. Bootstrap lab bag grows

## Discipline
- Only paper signals that match frozen gates
- Fixed $2,000 units — no equity-percentage sizing
- Never risk more than 1R per unit
- Lab variants are papered in parallel only when their own gate fires

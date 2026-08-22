# Paper Trading Protocol (BASE + lab variants)

## Purpose
Live ongoing paper trades give the formula **new out-of-sample information** for analytics and bootstrap.
Rules stay frozen. Paper fills are logged the same way as live would be.

## When a paper trade opens
Trigger: gate_scan action flips to **BUY** (progress 100%) for a variant.

Record in trades.jsonl:
- variant (BASE / PB8 / HOLD7 / LOOSE)
- exhaust_ts, entry_ts, entry_px, stop_px (200d * 0.98)
- size_usd from hybrid sizing (optional; can log "full paper unit")
- catalyst_weight at entry
- status: OPEN
- notes: "PAPER"

## While open
- Each gate scan can note unrealized MAE/MFE
- Do not change entry rules mid-trade

## When it closes
Exit on:
1. Hold days reached (BASE=10, HOLD7=7), or
2. Daily close under 200d stop

Update same trade:
- exit_ts, exit_px, ret, mae, mfe, hold_days, status: CLOSED

## After close
1. Append analytics expectancy refresh
2. Outlier check (2 sigma)
3. Co-formation score if logged at entry
4. Bootstrap lab bag grows on next rebuild of empirical arrays

## Discipline
- Only paper signals that match frozen gates
- No moving stop for convenience
- Lab variants papered in parallel only when their own gate would fire

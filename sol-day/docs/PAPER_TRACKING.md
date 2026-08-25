# SOL Day v3 — Paper Trading Tracking

## Files

| File | Role |
|------|------|
| `data/sol_day_open_trades.json` | Currently open paper trade (max 1) |
| `data/sol_day_paper_trades.jsonl` | Closed paper trades (append-only) |
| `schemas/sol_day_paper_trade.schema.json` | Schema |
| `scripts/sol_day_paper_tracker.py` | CLI tracker |

## Quick commands

```bash
# See open / count closed
python scripts/sol_day_paper_tracker.py status

# Open a paper trade from the latest READY signal
python scripts/sol_day_paper_tracker.py open-from-signal --live-url

# Mark-to-market (auto-closes on stop / 3R / 4R)
python scripts/sol_day_paper_tracker.py update-price --price 98.50

# Manual close
python scripts/sol_day_paper_tracker.py close --price 99.20 --reason tp3

# Performance + live Kelly estimate
python scripts/sol_day_paper_tracker.py stats
```

## Rules baked in
- One open trade at a time
- Risk = Quarter-Kelly on $1000 unit (≈ $45) unless signal overrides
- Stop = 1R; targets 3R and 4R
- Signal must be READY and < 90 minutes old to open

## Phone workflow
1. Automation writes READY → `sol_day_latest_signal.json`
2. Open **SOL Day Executor** bot → ask “check”
3. If READY, either:
   - Log mentally / exchange paper order, **or**
   - On computer: `open-from-signal --live-url`
4. When done: `close` or let `update-price` hit stop/target
5. After 20–30 closed trades: `stats` and recalibrate Kelly

## Monthly unit
Always treat the active bank as $1000. Extract excess. Paper P&L is tracked in R and $ so you can see progress toward the $2000 monthly profit goal without mixing live and paper.

# SOL Day — Execution Path (Autonomous Paper → Live)

## Active stack

1. **Grok Automation** `SOL Day v3 Market Watch` (hourly, session window)  
   Cloud scan → writes GitHub `data/sol_day_latest_signal.json` for phone bot.

2. **Autonomous paper runner** `scripts/sol_day_autonomous_runner.py`  
   Always-on local/VPS loop (default every 2 min):
   - Fetches Binance klines
   - Runs locked v3 formula (ChoCh + first FVG ≥ 0.6×ATR)
   - Opens/manages **paper** trades
   - Enforces kill switch + daily −8% loss halt

3. **Phone bot** `SOL Day Executor`  
   Instant “check” → reads GitHub signal.

4. **Paper tracker CLI** `scripts/sol_day_paper_tracker.py`  
   Manual open/close/stats if needed.

## Start autonomy (paper)

```bash
cd xrp-swing-formula
python scripts/sol_day_autonomous_runner.py
```

Kill switch:
```bash
echo ON  > data/KILL_SWITCH.txt
echo OFF > data/KILL_SWITCH.txt
```

See `sol-day/docs/AUTONOMOUS.md` for full details.

## Live (later only)
After 20–30 closed paper trades with stats that match the backtest directionally:
- Restricted Binance API key (no withdrawal, IP allowlist)
- Live flag on a separate execution module
- Same 1R stop, Quarter-Kelly, daily loss limit

## Monthly reset
Restart active unit at $1000. Extract excess to XRP reserve / bills / long-term.

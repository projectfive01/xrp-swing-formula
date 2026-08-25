# SOL Day v3 — Autonomous Paper System

## What runs without you

| Component | Role | Cadence |
|-----------|------|---------|
| **Grok Automation** `SOL Day v3 Market Watch` | Cloud scan + writes GitHub signal | Hourly (session window) |
| **`scripts/sol_day_autonomous_runner.py`** | Local/VPS brain: detect + open/manage paper + risk limits | Every 2 min (configurable) |
| **Kill switch** `data/KILL_SWITCH.txt` | `ON` = no new entries | Manual |
| **Daily loss limit** | −8% of $1000 unit → halt new entries for the day | Automatic |

## Start the autonomous paper loop

On any always-on machine (laptop left open, VPS, Raspberry Pi):

```bash
cd xrp-swing-formula
python scripts/sol_day_autonomous_runner.py
# or
python scripts/sol_day_autonomous_runner.py --poll 60
```

One-shot test:

```bash
python scripts/sol_day_autonomous_runner.py --once
```

## Kill switch

```bash
echo ON  > data/KILL_SWITCH.txt   # stop new paper entries
echo OFF > data/KILL_SWITCH.txt   # resume
```

## Config

`backtest/config/sol_day_runtime.yaml` — equity unit, Kelly %, daily loss limit, poll interval.

## Files the runner owns

- `data/sol_day_latest_signal.json` — current READY/WAIT (local)
- `data/sol_day_open_trades.json` — open paper position
- `data/sol_day_paper_trades.jsonl` — closed paper history
- `data/sol_day_daily_state.json` — day P&amp;L + halt flag
- `data/KILL_SWITCH.txt` — emergency stop

## What is still NOT autonomous (by design)

- **Live exchange orders** — paper only until you explicitly add API keys and a live flag after 20–30 closed paper trades.
- **GitHub signal write from the runner** — the runner writes local files; the Grok automation still updates the public GitHub signal for the phone bot.

## Phone bot

Keep using **SOL Day Executor** for instant “check” status. It reads the GitHub signal that the Grok automation refreshes hourly; the runner is the higher-frequency paper executor.

## Path to live

1. Run autonomous paper for 20–30 closed trades.
2. `python scripts/sol_day_paper_tracker.py stats` — confirm edge directionally matches backtest.
3. Only then add a restricted Binance key + live module (separate change).

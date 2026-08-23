# XRP Swing Formula Research + SOL Day Trading

Frozen **BASE** swing rules for XRP + frozen **BASE** day rules for SOL, plus a research store, paper-trading protocol, probability lab, formula brain flow, JSON Schema validation, and CI.

> Not financial advice. Small historical sample (n=6 XRP). Paper first.

## Standard Unit Rules (XRP Swing + SOL Day)

| Parameter         | Value                    |
|-------------------|--------------------------|
| **Unit Size**     | Fixed **$2,000** notional |
| **Max Loss**      | **1R**                   |
| **Take Profit 1** | **3R** (scale out)       |
| **Take Profit 2** | **5R**                   |

These unit rules apply to both XRP swing trades and SOL day trades.

## BASE formula (frozen) — XRP Swing

1. **Exhaustion:** >=20% rise in <=10 days **and** daily RSI >= 75
2. **Entry:** first >=10% pullback from local high that still holds the 200-day area
3. **Exit / Targets:**
   - Stop = 1R
   - TP1 = 3R
   - TP2 = 5R
   - Time fallback: ~7-10 trading days **or** daily close under 200-day
4. **Size:** Fixed $2,000 unit (1R risk)
5. **Catalyst:** weight only (-1 / 0 / +1) — never opens a trade alone

**Action:** HOLD until load-bar progress = 100% (all gates green).

## BASE formula (frozen) — SOL Day

- **TF:** 15-minute, long-only v1
- **Gates:** Trend (close > 20-EMA + VWAP) → Pullback to EMA/VWAP → Momentum/Trigger (RSI(7) cross or break) → Not chasing (RSI < 75) → Structural/ATR stop defines 1R
- **Targets:** 3R / 5R + time fallback
- Full details: `sol-day/docs/FORMULA_ONEPAGER.md`

**Action:** Same load-bar discipline. Paper only until 100%.

## Layout

```
docs/                 Protocols + one-pager
data/                 Research store (jsonl + variants)
labs/                 Interactive HTML tools
schemas/              JSON Schema contracts
scripts/              validate_store.py + paper_trader.py
sol-day/              SOL day trading research (BASE frozen)
.github/workflows/    CI
```

## Quick start

```bash
python3 scripts/validate_store.py
```

Open in browser:
- `labs/formula_brain_flow.html` — information flow
- `labs/formula_probability_lab.html` — bootstrap histogram lab

## Lab variants (not auto-promoted)

**XRP:** BASE / PB8 / HOLD7 / LOOSE  
**SOL:** BASE (frozen) — shorts / 5m / looser RSI later

Progression: n>=10 closed out-of-sample, median > 0, co-formations, human review.

## Status (seeded)

- 6 historical XRP BASE trades backfilled
- First live XRP gate scan: HOLD (~50%; need $1.28-$1.35 zone)
- SOL Day BASE formula frozen 2026-08-23
- Unit model: fixed $2,000 / 1R / 3R / 5R
- Findings: HIGH warning on small n (XRP)

## CI

On push/PR to main: validate JSONL + BASE freeze + path smoke checks.

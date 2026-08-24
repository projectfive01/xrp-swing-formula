# Multi-Front Trading & Investing System

Three distinct fronts under one research discipline:

| Front | Timeframe | Edge |
|-------|-----------|------|
| **SOL Day** | Intraday | Structure + Quality Score |
| **XRP Swing** | Multi-day | Exhaustion → Pullback → 200d zone |
| **Front Run Invest** | Weeks–months | Real activity + beta vs BTC |

> Not financial advice. Paper first. Small samples.

See **[GAMEPLAN.md](GAMEPLAN.md)** for the full operating plan.

---

## Shared Unit Rules (Trading Fronts Only)

| Parameter | Value |
|-----------|-------|
| **Unit Size** | Fixed **$2,000** notional (paper baseline) |
| **Max Loss** | **1R** |
| **Risk Model** | Structural stop defines 1R |

Front Run Invest uses **% of capital** sizing instead of tight 1R stops.

---

## 1. XRP Swing (BASE Frozen)

1. **Exhaustion:** ≥20% rise in ≤10 days **and** daily RSI ≥ 75
2. **Entry:** first ≥10% pullback from local high that still holds the 200-day area
3. **Exit:** 1R stop / 3R + 5R targets / time or structure invalidation
4. **Action:** HOLD until load-bar = 100%

Details: `docs/FORMULA_ONEPAGER.md`

---

## 2. SOL Day

### Original BASE (Frozen)
15m EMA + VWAP + RSI gates, long-only, 3R/5R targets.  
See `sol-day/docs/FORMULA_ONEPAGER.md`.

### Research Enhancements (Active Development)
- Quality Score 0–10 → only take ≥ 8
- ChoCh + FVG emphasis
- Dynamic ATR regime thresholds
- Runner management (Opposite ChoCh primary exit)
- ATR-based sizing + anti-martingale / Kelly path

See `sol-day/docs/RESEARCH_ENHANCEMENTS.md` and `sol-day/docs/ATR_AND_FVG_THRESHOLDS.md`.

**Policy:** Original BASE stays frozen for continuity. New work follows the Research Enhancements path and promotes only with evidence.

---

## 3. Front Run Invest (New)

Longer-term research & positioning:

- Bitcoin as the anchor
- Higher-beta names with real activity (fees, volume, OI) while market is quiet
- Thesis-based sizing (0.5–3% of invest capital per name)
- Exit on thesis break, not day-trading stops

Details: `front-run-invest/docs/FORMULA_ONEPAGER.md`

---

## Layout

```
GAMEPLAN.md                 Overall three-front plan
docs/                       XRP protocols + one-pager
data/                       Research store (jsonl)
sol-day/                    SOL Day research + enhancements
front-run-invest/           Longer-term investing front
labs/                       Interactive tools
schemas/                    JSON Schema contracts
scripts/                    paper_trader.py + validation
```

---

## Quick Start

```bash
python3 scripts/validate_store.py
```

---

## Status

- XRP Swing BASE frozen, paper process active
- SOL Day original BASE frozen; Research Enhancements documented and in use for new development
- Front Run Invest framework added 2026-08-23
- Shared research discipline across all three fronts

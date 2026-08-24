# Trading & Investing Game Plan

**Last updated:** 2026-08-23

This repository now supports **three distinct fronts**. They share philosophy (defined risk, selectivity, journal feedback) but use different rules and timeframes.

---

## The Three Fronts

| Front | Timeframe | Core Edge | Status |
|-------|-----------|-----------|--------|
| **SOL Day** | Intraday | Structure (ChoCh + FVG) + Quality Score ≥ 8 | Research-enhanced, moving from original EMA BASE |
| **XRP Swing** | Multi-day | Exhaustion → Pullback → 200d zone | BASE frozen |
| **Front Run Invest** | Weeks–months | Real activity + beta vs BTC while market is quiet | New |

---

## Shared Principles

- Defined risk first
- Selectivity over frequency
- Journal everything
- Paper / small size until evidence is strong
- Never mix timeframes on the same position

---

## SOL Day (Current Direction)

**Original frozen BASE** (still in `sol-day/docs/FORMULA_ONEPAGER.md`):  
15m EMA + VWAP + RSI gates, long-only, 3R/5R targets.

**Research Enhancements** (see `sol-day/docs/RESEARCH_ENHANCEMENTS.md`):  
- Quality Score 0–10 (only take ≥ 8)
- ChoCh + FVG emphasis
- Dynamic ATR regime thresholds
- Runner management with Opposite ChoCh as primary exit
- ATR-based position sizing + anti-martingale / Kelly path

**Decision:** Keep the original BASE frozen for paper continuity. New development follows the Research Enhancements path. Promote only after sufficient paper evidence.

---

## XRP Swing

- BASE formula remains frozen
- Load-bar / gate scan system active
- Shared $2,000 unit / 1R model
- Continue paper discipline and research store logging

---

## Front Run Invest (New)

Longer-term research & positioning system:

- Bitcoin as the anchor
- Higher-beta names that already show real activity (fees, volume, OI) while the market is quiet
- Thesis-based sizing (not tight 1R day stops)
- Weekly/bi-weekly review cadence
- Beta / alpha analysis as supporting tools

Structure to be added under `front-run-invest/`.

---

## Operating Rhythm

**Daily**
- SOL Day: session automation + Quality Score checks (NY window)
- XRP Swing: gate scan review
- Journal any closed trades

**Weekly**
- Review R-multiples and Quality Score performance
- Front Run Invest thesis + activity review
- Update research notes

**Monthly / Milestone**
- Assess whether SOL Research Enhancements are ready for promotion
- Kelly review once 30+ high-quality trades exist

---

## Priority Order

1. Keep XRP Swing and original SOL BASE paper process clean
2. Run SOL Day under Research Enhancements rules (Quality Score, ATR regimes, runner exits)
3. Stand up Front Run Invest research log and begin tracking candidates
4. Harden automation (state machine, logging, sizing) only after paper results support it

---

## Non-Negotiables

- Do not apply day-trading stops to investment positions
- Do not turn investment theses into short-term trades
- Do not increase size to recover losses
- Only take SOL Day setups with Quality Score ≥ 8 under the enhanced rules

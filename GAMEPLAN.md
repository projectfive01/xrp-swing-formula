# Trading & Investing Game Plan

**Last updated:** 2026-08-23

This repository supports **three distinct fronts** plus an automated backtest pipeline. They share philosophy (defined risk, selectivity, journal feedback) but use different rules and timeframes.

**Target:** Ready for real capital in ~30 days (build → backtest → paper → small live).

---

## The Three Fronts

| Front | Timeframe | Core Edge | Status |
|-------|-----------|-----------|--------|
| **SOL Day** | Intraday | Structure (ChoCh + FVG) + Quality Score ≥ 8 | Research-enhanced |
| **XRP Swing** | Multi-day | Exhaustion → Pullback → 200d zone | BASE frozen |
| **Front Run Invest** | Weeks–months | Real activity + beta vs BTC while market is quiet | Framework live |

---

## Shared Principles

- Defined risk first
- Selectivity over frequency
- Journal everything
- Paper / small size until evidence is strong
- Never mix timeframes on the same position

---

## 30-Day Path to Capital

| Phase | Days | Focus |
|-------|------|-------|
| Foundation | 1–7 | Lock rules, journals, checklists, data sources |
| Build & Backtest | 8–16 | Detectors, simulator, first honest metrics |
| Paper Trading | 17–25 | Live paper under real conditions |
| Go-Live Prep | 26–30 | Risk limits, size, final go/no-go |

Details live in the backtest README and operating checklists.

---

## Backtest Pipeline

Location: `backtest/`

```
Data → Detector → Quality/Gates → State Machine → Metrics → Store
```

Current skeleton includes:
- `config/sol_day.yaml`
- `core/` (types, ATR, regime)
- `detectors/sol_day.py` (stub)
- `simulation/state_machine.py` (aligned with live logic)
- `analytics/metrics.py`
- `runners/run_sol_day.py`
- `store/` for JSONL results

Implementation priority:
1. Data loader + normalizer
2. Finish SOL Day detector (ChoCh + FVG + Quality Score)
3. Wire simulator end-to-end
4. Produce first performance report by Quality Score
5. Add XRP Swing module

---

## SOL Day

**Original frozen BASE** — `sol-day/docs/FORMULA_ONEPAGER.md`  
**Research Enhancements** — `sol-day/docs/RESEARCH_ENHANCEMENTS.md` + ATR thresholds

Policy: Original BASE stays frozen. New work follows Research Enhancements. Promote only with evidence.

---

## XRP Swing

- BASE frozen
- Gate scan / load-bar active
- Shared 1R unit model
- Continue research store logging

---

## Front Run Invest

- Bitcoin as anchor
- Higher-beta names with real activity while market is quiet
- Thesis-based sizing (not tight day stops)
- See `front-run-invest/docs/FORMULA_ONEPAGER.md`

---

## Operating Rhythm

**Daily**
- SOL Day session checks (Quality Score path)
- XRP Swing gate review
- Journal closed trades

**Weekly**
- R-multiple + Quality Score review
- Front Run thesis/activity review
- Backtest report if rules changed

**Milestone**
- 30+ high-quality closed trades before trusting Kelly sizing
- Explicit go/no-go before real capital

---

## Priority Order

1. Journals + daily checklist
2. SOL Day backtest path producing real numbers
3. Paper trade both trading fronts under strict rules
4. Front Run research log with 5–8 names
5. Small real capital only after paper evidence

---

## Non-Negotiables

- Do not apply day-trading stops to investment positions
- Do not turn investment theses into short-term trades
- Do not increase size to recover losses
- Only take SOL Day setups with Quality Score ≥ 8 under enhanced rules
- No real capital until paper process is boring and metrics are acceptable

# Backtest Pipeline

Automated research and validation system for the three fronts.

**Goal:** Prove mathematical edge, keep formulas honest, and support the 30-day path to real capital.

---

## Purpose

1. Detect setups under frozen / enhanced rules
2. Simulate trades with the same state machine used live
3. Measure expectancy, R-multiples, and breakdowns
4. Store every run so rule versions can be compared
5. Feed the journal and promotion decisions

---

## Quick Architecture

```
Data → Detector → Quality/Gates → Simulator → Metrics → Store + Report
```

---

## Folder Map

```
backtest/
├── config/           Rule parameters
├── core/             Data, ATR, shared types
├── detectors/        SOL Day + XRP Swing logic
├── simulation/       State machine + sizing
├── analytics/        Metrics + breakdowns
├── runners/          CLI entry points
├── store/            JSONL results
└── tests/            Unit tests
```

---

## 30-Day Fit

| Days | Focus |
|------|-------|
| 1–7 | Foundation + journals + this skeleton |
| 8–16 | Implement detectors + simulator + first real backtests |
| 17–25 | Paper trade while backtest reports run weekly |
| 26–30 | Final metrics review + go-live decision |

---

## Design Rules

- No lookahead
- Same exit logic as live (especially SOL Day Opposite ChoCh)
- Quality Score ≥ 8 filter for SOL Day enhanced path
- Every run must record rule version + parameters
- Prefer simple, auditable code over clever abstractions

---

## Status

Skeleton created 2026-08-23. Implementation proceeds in priority order:

1. `core/` (data + ATR)
2. `detectors/sol_day.py`
3. `simulation/state_machine.py`
4. `analytics/metrics.py`
5. `runners/run_sol_day.py`

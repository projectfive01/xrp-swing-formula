# SOL Day Trading Research

Intraday system for SOL under the shared research discipline.

## Two Layers

### 1. Original BASE (Frozen)
- 15-minute, long-only
- EMA + VWAP + RSI gates
- 1R / 3R / 5R framework
- See `docs/FORMULA_ONEPAGER.md`

### 2. Research Enhancements (Active)
Documented in:
- `docs/RESEARCH_ENHANCEMENTS.md`
- `docs/ATR_AND_FVG_THRESHOLDS.md`

Key additions:
- Quality Score 0–10 (only take ≥ 8)
- ChoCh + FVG emphasis
- Dynamic ATR regime thresholds
- Runner management with Opposite ChoCh as primary exit
- ATR-based position sizing
- Path to anti-martingale / Kelly sizing

**Policy:** Original BASE stays frozen for paper continuity. New development and live decision-making follow the Research Enhancements rules. Promotion of any new BASE requires evidence.

---

## Shared Unit Rules (with XRP Swing)

| Parameter | Value |
|-----------|-------|
| **Unit Size** | Fixed **$2,000** notional (paper baseline) |
| **Max Loss** | **1R** |
| **Risk Definition** | Structural stop |

---

## Structure

```
sol-day/
├── README.md
├── docs/
│   ├── FORMULA_ONEPAGER.md          # Original BASE (frozen)
│   ├── RESEARCH_ENHANCEMENTS.md    # Quality Score, ATR regimes, exits
│   └── ATR_AND_FVG_THRESHOLDS.md   # Wilder ATR + FVG size rules
└── (future) data/, scripts/
```

---

## Operating Notes

- Automation: session-restricted hourly scan with Quality Score + levels
- Only act on Quality ≥ 8 under the enhanced rules
- Journal every closed trade (R-multiple, exit reason, Quality Score)
- One trade at a time
- Move to break-even at +1R, then manage as runner

See root `GAMEPLAN.md` for how SOL Day sits alongside XRP Swing and Front Run Invest.

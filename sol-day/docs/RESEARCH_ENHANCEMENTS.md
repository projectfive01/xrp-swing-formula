# SOL Day — Research Enhancements (LOCKED)

**Status: LOCKED** as of 2026-08-23  
These findings come from the Aug 19–22 sample analysis and quality scoring work. They are now official improvements to how we select and manage trades.

## 1. Quality Score Filter (Mandatory)

Every setup is scored 0–10 on:

- Structure Clarity (0–2)
- ChoCh Quality (0–2)
- FVG Quality (0–2)
- Location (0–2)
- Context / Confluence (0–2)

**Rule**: Only take setups with **Quality Score ≥ 8**.

This single filter is the highest-leverage improvement. It removed the weaker Aug 20–21 continuation (Score 6) while keeping the strong Aug 19 long (9) and Aug 22 short (10).

## 2. Dynamic ATR Multipliers (LOCKED)

ATR reference = ATR(14) on the 5-minute (Wilder smoothing).

### Volatility Regime Detection
```
Volatility Ratio = Current ATR(14) / ATR(14) from ~3 days ago
```

| Regime   | Volatility Ratio | FVG Strong | FVG Acceptable | Min Stop | Max Stop |
|----------------------------|------------|----------------|----------|----------|
| Low      | < 0.85              | 0.85× ATR  | 0.50× ATR      | 0.50×    | 1.8×     |
| Normal   | 0.85 – 1.20         | 1.00× ATR  | 0.60× ATR      | 0.60×    | 2.0×     |
| High     | > 1.20              | 1.20× ATR  | 0.75× ATR      | 0.75×    | 2.3×     |

### FVG Quality Scoring (uses the regime thresholds above)
- Strong FVG (≥ regime Strong threshold) → 2 points
- Acceptable FVG (≥ regime Acceptable threshold) → 1 point
- Weak FVG (below Acceptable) → 0 points

Prefer the **first clean FVG** after the ChoCh. Late or already-mitigated FVGs are lower quality.

### Stop Distance Guardrails (uses the regime Min/Max)
- If Structural Stop < regime Min → Reject setup (too tight)
- If Structural Stop > regime Max → Reduce size or skip (too wide)

## 3. Selectivity Over Frequency

Target only **3–4 high-quality setups**.  
It is better to pass on average setups than to force trades. The quality score enforces this automatically.

## 4. Exit Priority (Priced-In Logic)

Primary exit trigger remains:

1. Opposite Change of Character (structure break against the position)

Secondary triggers (only if structure is still intact):
- Clear opposing FVG + rejection
- Measured move completion + failure
- Momentum exhaustion with structure weakening

Do **not** use fixed 3R/5R as the main exit method on high-quality runners. The Aug 19 example showed that fixed targets leave significant R on the table.

## 5. Management Standard

- Risk exactly 1R at entry
- Move stop to break-even once +1R is reached
- Then manage as a runner under the priced-in exit rules
- One trade at a time

## 6. ATR-Based Position Sizing (LOCKED)

**Core Principle**: Risk a fixed dollar amount per trade. Position size is determined by the actual 1R distance.

### Formula
```
Position Size (SOL) = Risk Amount (USD) / 1R Distance (USD)
```

Where:
- **1R Distance** = |Entry Price – Structural Stop|
- **Risk Amount** = Chosen fixed risk (e.g. $50–$100 while paper trading, or a % of account later)

### Paper Trading Note
While paper trading we continue logging the $2,000 notional unit for consistency with the shared engine, while also recording what the ATR-based size would have been.

## Summary of Impact

| Finding                        | Effect on Formula                          |
|--------------------------------|--------------------------------------------|
| Quality Score ≥ 8              | Strongly reduces overtrading               |
| Dynamic ATR multipliers        | Adapts FVG and stop rules to volatility    |
| Prefer first FVG after ChoCh   | Improves entry location                    |
| Opposite ChoCh as primary exit | Captures full runner potential             |
| Strict selectivity             | Aligns with 3–4 high-quality setups goal   |
| ATR-based position sizing      | Keeps dollar risk consistent across volatility |

These rules are now active for all future paper trading and automation logic.

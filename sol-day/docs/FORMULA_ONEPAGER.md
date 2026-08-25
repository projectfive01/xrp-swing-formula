# SOL Day Trading — Formula One-Pager (v3 — LOCKED)

> **Status: LOCKED** as of 2026-08-25  
> Simplified high-RR system for usable sample size + Quarter-Kelly position sizing.  
> Goal alignment: $1,000 active unit → extract excess toward $3,000 monthly target / XRP reserve / living costs.

## Core Philosophy (Mathematical)
- High reward-to-risk (≥ 1:3) means we do **not** need extreme win rates.
- Breakeven at 1:3 is ~25% win rate. Our backtested edge (~35% WR / ~3.9R avg win) produces positive expectancy.
- Frequency over perfection: two hard filters only, so we generate enough trades for statistical validity and daily profit contribution.

## Hard Requirements (both must be true)
1. **Structure Bias + ChoCh** in the same direction (clear swing structure + Change of Character).
2. **First FVG after the ChoCh** that is ≥ 0.6 × ATR(14) on the working timeframe (5m or 15m).

Everything else (location, session, extra confluence) is preference only — not a gate.

## Entry & Risk Rules
- Enter on retracement into the FVG (or limit at FVG mid / favorable edge).
- Stop: beyond the FVG + small buffer, or structural invalidation. This distance = 1R.
- Target: minimum **1:3** measured from entry to stop. Prefer letting winners run to 1:4+ or opposite ChoCh when structure allows.
- One trade at a time.

## Position Sizing — Quarter-Kelly (LOCKED)

Edge used for initial calibration (v3 backtest):
- p ≈ 0.346
- b ≈ 3.89

```
f* = (b·p − q) / b  ≈ 17.8%   (Full Kelly)
Quarter-Kelly = f* / 4 ≈ 4.45%
```

**Live rule:**
- Risk **4.5% of current trading equity** per trade (Quarter-Kelly).
- On the $1,000 monthly unit this is ≈ $45 risk (1R).
- Cap at 5% absolute even if live edge improves.
- Recalculate Kelly monthly (or after ≥ 30 closed trades) using live win rate and average R multiple.
- Optional mild anti-Martingale: after 3 consecutive winners allow temporary Half-Kelly (~8.9%) on the next trade only; any loss resets to Quarter-Kelly.

Position size formula:
```
Risk $ = Current Equity × 0.045
Size (SOL) = Risk $ / |Entry − Stop|
```

## Monthly Goal Math Clarification

Target: turn the $1,000 active unit into $3,000 (i.e. +$2,000 profit) then extract excess.

- Calendar-day view: $2,000 ÷ 30 ≈ **$66.67 per day**.
- Trading-day view (≈ 20–22 days): need roughly **$90–100 average profit per trading day**.

With current calibrated edge + Quarter-Kelly on $1,000:
- Expected value per trade ≈ 0.69 R × $45 ≈ $31
- ≈ 1.25 trades / day → ≈ $39 expected per calendar day

This is **positive and compounding**, but falls short of the aggressive $66+/day target under base assumptions. To close the gap we need either:
- Higher realized expectancy / frequency in live conditions, or
- Gradual equity growth inside the month (compounding the $1,000) so later trades carry larger dollar risk, or
- Acceptance that some months will be extraction months rather than full $2,000 hits.

**Operating rule**: Always restart the next month with the $1,000 unit. Any equity above a soft monthly floor (or the full $3,000) is extracted to XRP swing reserve / long-term investments / bills / rent / car.

## Action
Hard requirements met + FVG fill available → **READY** (size with Quarter-Kelly).  
Otherwise **WAIT**.

## Notes
- Previous Quality Score ≥ 8 and multi-gate systems remain archived research; they produced too few samples.
- Prefer first FVG after ChoCh.
- Paper or live — same rules. Log every trade with R multiple for ongoing Kelly recalibration.
- This version prioritizes sample size and mathematical expectancy while still protecting capital via fractional Kelly and the 1R stop discipline.

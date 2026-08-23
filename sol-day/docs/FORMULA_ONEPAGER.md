# SOL Day Trading — Formula One-Pager (Scaffold)

> Status: **Not yet frozen**. This is the starting framework.
> All trades use the shared unit model: **$2,000 unit / 1R risk / 3R + 5R targets**.

## Session
- Focus: New York session (roughly 13:30–20:00 UTC) or full 24h with session filters
- Timeframe: 5-minute / 15-minute primary

## Setup (proposed BASE day rules)
1. **Trend filter**: Price above or below VWAP + 20 EMA alignment
2. **Momentum**: RSI (5 or 7 period) leaving oversold/overbought
3. **Entry trigger**: Break of opening range or pullback to VWAP/EMA in trend direction
4. **Stop**: Structural (below swing low / above swing high) or ATR-based → defines 1R
5. **Targets**: 3R and 5R (fixed unit model)

## Size
- Fixed **$2,000** notional per unit
- Risk exactly **1R**
- Scale at **3R**, final target **5R**

## Action
Only take trades that meet all gates. No forced trades.

## Notes
- Keep rules extremely simple at first so we can freeze a clean BASE version quickly.
- Once frozen, treat exactly like XRP BASE (paper first, walk-forward, etc.).

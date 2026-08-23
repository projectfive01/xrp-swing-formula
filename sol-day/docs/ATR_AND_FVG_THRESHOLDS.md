# SOL Day — ATR Calculation & FVG Size Thresholds (LOCKED)

**Status: LOCKED** as of 2026-08-23

These definitions are frozen for use in quality scoring and any future ChoCh + FVG based logic.

## ATR Calculation (Wilder Smoothing)

**Method**: Vectorized Wilder ATR  
**Period**: 14  
**Timeframe**: 5-minute (primary reference)

### Formula
True Range (TR) for each candle:
```
TR = max(
    High - Low,
    abs(High - Previous Close),
    abs(Low - Previous Close)
)
```

Wilder ATR:
```python
atr = tr.ewm(alpha=1/period, adjust=False).mean()
```

This is mathematically equivalent to the classic recursive Wilder formula and matches major platforms.

### Python Implementation (Locked)
```python
def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr
```

## FVG Size Thresholds (Relative to ATR)

FVG Size = height of the inefficiency (distance between non-overlapping wicks of the 3-candle pattern).

| Quality Level | Rule                          | Score Points |
|---------------|-------------------------------|--------------|
| Strong        | FVG ≥ 1.0 × ATR(14)           | 2            |
| Acceptable    | FVG ≥ 0.6 × ATR(14)           | 1            |
| Weak          | FVG < 0.6 × ATR(14)           | 0            |

### Additional FVG Quality Rules
- Must form within 3–5 candles after the Change of Character
- At entry, FVG should remain at least 50% unfilled
- Prefer the first clean FVG after ChoCh

---

These thresholds are now the official reference for automated quality scoring.

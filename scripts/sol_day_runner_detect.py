"""ChoCh + first-FVG detector used by the SOL Day autonomous runner."""

from __future__ import annotations

import numpy as np

from scripts.sol_day_runner_io import kline_iso


def calc_atr(high, low, close, period=14):
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    atr = np.full(len(close), np.nan)
    if len(tr) < period:
        return atr
    atr[period] = np.mean(tr[:period])
    for i in range(period + 1, len(close)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i - 1]) / period
    return atr


def find_swings(high, low, left=2, right=2):
    sh, sl = [], []
    for i in range(left, len(high) - right):
        if all(high[i] >= high[j] for j in range(i - left, i + right + 1) if j != i):
            sh.append((i, float(high[i])))
        if all(low[i] <= low[j] for j in range(i - left, i + right + 1) if j != i):
            sl.append((i, float(low[i])))
    return sh, sl


def detect_setup(klines, fvg_min_mult: float) -> dict | None:
    highs = np.array([float(c[2]) for c in klines])
    lows = np.array([float(c[3]) for c in klines])
    closes = np.array([float(c[4]) for c in klines])
    atr = calc_atr(highs, lows, closes)
    swing_highs, swing_lows = find_swings(highs, lows)

    fvgs = []
    for i in range(2, len(closes)):
        if highs[i - 2] < lows[i]:
            fvgs.append(
                {
                    "idx": i,
                    "type": "bull",
                    "top": float(lows[i]),
                    "bot": float(highs[i - 2]),
                    "size": float(lows[i] - highs[i - 2]),
                }
            )
        if lows[i - 2] > highs[i]:
            fvgs.append(
                {
                    "idx": i,
                    "type": "bear",
                    "top": float(lows[i - 2]),
                    "bot": float(highs[i]),
                    "size": float(lows[i - 2] - highs[i]),
                }
            )

    recent_sh, recent_sl = [], []
    last_choch_bull = last_choch_bear = -999
    candidates = []

    start = max(30, len(closes) - 80)
    for i in range(start, len(closes)):
        for sh_idx, sh_p in swing_highs:
            if sh_idx == i:
                recent_sh.append((i, sh_p))
                if len(recent_sh) > 5:
                    recent_sh.pop(0)
        for sl_idx, sl_p in swing_lows:
            if sl_idx == i:
                recent_sl.append((i, sl_p))
                if len(recent_sl) > 5:
                    recent_sl.pop(0)

        if len(recent_sh) >= 2:
            last_sh_idx, last_sh_p = recent_sh[-1]
            if i > last_sh_idx and closes[i] > last_sh_p and last_choch_bull < last_sh_idx:
                if recent_sh[-1][1] < recent_sh[-2][1]:
                    last_choch_bull = i
                    for f in fvgs:
                        if last_choch_bull < f["idx"] <= last_choch_bull + 10 and f["type"] == "bull":
                            a = atr[f["idx"]] if not np.isnan(atr[f["idx"]]) else 0.5
                            if f["size"] < fvg_min_mult * a:
                                continue
                            filled = False
                            for j in range(f["idx"] + 1, min(f["idx"] + 20, len(closes))):
                                if lows[j] <= f["top"] and highs[j] >= f["bot"]:
                                    filled = True
                                    break
                            if not filled and lows[-1] <= f["top"] * 1.002 and highs[-1] >= f["bot"] * 0.998:
                                filled = True
                            if not filled:
                                continue
                            entry = (f["top"] + f["bot"]) / 2
                            stop = f["bot"] - 0.15 * a
                            risk = entry - stop
                            if risk < 0.05:
                                continue
                            candidates.append(
                                {
                                    "direction": "long",
                                    "entry": entry,
                                    "stop": stop,
                                    "fvg_top": f["top"],
                                    "fvg_bot": f["bot"],
                                    "atr": float(a),
                                    "choch_idx": last_choch_bull,
                                    "fvg_idx": f["idx"],
                                    "choch_ts_utc": kline_iso(klines, last_choch_bull),
                                    "fvg_ts_utc": kline_iso(klines, f["idx"]),
                                    "target_3r": entry + 3 * risk,
                                    "target_4r": entry + 4 * risk,
                                    "risk": risk,
                                }
                            )
                            break

        if len(recent_sl) >= 2:
            last_sl_idx, last_sl_p = recent_sl[-1]
            if i > last_sl_idx and closes[i] < last_sl_p and last_choch_bear < last_sl_idx:
                if recent_sl[-1][1] > recent_sl[-2][1]:
                    last_choch_bear = i
                    for f in fvgs:
                        if last_choch_bear < f["idx"] <= last_choch_bear + 10 and f["type"] == "bear":
                            a = atr[f["idx"]] if not np.isnan(atr[f["idx"]]) else 0.5
                            if f["size"] < fvg_min_mult * a:
                                continue
                            filled = False
                            for j in range(f["idx"] + 1, min(f["idx"] + 20, len(closes))):
                                if highs[j] >= f["bot"] and lows[j] <= f["top"]:
                                    filled = True
                                    break
                            if not filled and highs[-1] >= f["bot"] * 0.998 and lows[-1] <= f["top"] * 1.002:
                                filled = True
                            if not filled:
                                continue
                            entry = (f["top"] + f["bot"]) / 2
                            stop = f["top"] + 0.15 * a
                            risk = stop - entry
                            if risk < 0.05:
                                continue
                            candidates.append(
                                {
                                    "direction": "short",
                                    "entry": entry,
                                    "stop": stop,
                                    "fvg_top": f["top"],
                                    "fvg_bot": f["bot"],
                                    "atr": float(a),
                                    "choch_idx": last_choch_bear,
                                    "fvg_idx": f["idx"],
                                    "choch_ts_utc": kline_iso(klines, last_choch_bear),
                                    "fvg_ts_utc": kline_iso(klines, f["idx"]),
                                    "target_3r": entry - 3 * risk,
                                    "target_4r": entry - 4 * risk,
                                    "risk": risk,
                                }
                            )
                            break

    if not candidates:
        return None
    candidates.sort(key=lambda x: x["fvg_idx"], reverse=True)
    return candidates[0]

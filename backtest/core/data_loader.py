"""Binance OHLCV data loader for the backtest pipeline.

Downloads candles, caches them locally as parquet/CSV, and returns a clean DataFrame.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

# Binance valid intervals
VALID_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
}

RAW_DIR = Path("backtest/data/raw")
PROCESSED_DIR = Path("backtest/data/processed")


def _ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _to_dataframe(raw: list) -> pd.DataFrame:
    """Convert Binance kline list to a clean OHLCV DataFrame."""
    if not raw:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])

    df["ts"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)

    df = df[["ts", "open", "high", "low", "close", "volume"]].copy()
    df = df.drop_duplicates(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    return df


def fetch_klines(
    symbol: str = "SOLUSDT",
    interval: str = "5m",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 1000,
    max_pages: int = 50,
    sleep_s: float = 0.15,
) -> pd.DataFrame:
    """
    Fetch OHLCV candles from Binance (paginated).

    Parameters
    ----------
    symbol : str
        e.g. SOLUSDT, XRPUSDT
    interval : str
        Binance interval (5m, 15m, 1h, 1d, ...)
    start, end : datetime, optional
        UTC-aware preferred. If start is None, fetches most recent `limit` bars.
    limit : int
        Max bars per request (Binance max 1000)
    max_pages : int
        Safety cap on pagination
    sleep_s : float
        Pause between pages to respect rate limits
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval '{interval}'. Valid: {sorted(VALID_INTERVALS)}")

    limit = min(max(limit, 1), 1000)
    frames: list[pd.DataFrame] = []

    # Most recent only
    if start is None:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        if end is not None:
            params["endTime"] = _ms(end)

        r = requests.get(BINANCE_KLINES_URL, params=params, timeout=15)
        r.raise_for_status()
        return _to_dataframe(r.json())

    # Paginated historical fetch
    cursor = start
    end_ms = _ms(end) if end is not None else _ms(datetime.now(timezone.utc))

    for _ in range(max_pages):
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": _ms(cursor),
            "endTime": end_ms,
            "limit": limit,
        }
        r = requests.get(BINANCE_KLINES_URL, params=params, timeout=15)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break

        df = _to_dataframe(batch)
        frames.append(df)

        last_ts = df["ts"].iloc[-1].to_pydatetime()
        # Advance past last candle
        cursor = last_ts + timedelta(milliseconds=1)

        if len(batch) < limit:
            break
        if _ms(cursor) >= end_ms:
            break

        time.sleep(sleep_s)

    if not frames:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    return out


def save_candles(df: pd.DataFrame, symbol: str, interval: str, processed: bool = False) -> Path:
    """Save candles to parquet (fallback CSV)."""
    base = PROCESSED_DIR if processed else RAW_DIR
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{symbol.upper()}_{interval}.parquet"

    try:
        df.to_parquet(path, index=False)
    except Exception:
        path = base / f"{symbol.upper()}_{interval}.csv"
        df.to_csv(path, index=False)

    return path


def load_candles(
    symbol: str = "SOLUSDT",
    interval: str = "5m",
    days: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Main entry point: load candles from cache or download from Binance.

    Examples
    --------
    df = load_candles("SOLUSDT", "5m", days=90)
    df = load_candles("XRPUSDT", "1d", days=365)
    """
    cache_path_parquet = RAW_DIR / f"{symbol.upper()}_{interval}.parquet"
    cache_path_csv = RAW_DIR / f"{symbol.upper()}_{interval}.csv"

    if use_cache and not refresh:
        if cache_path_parquet.exists():
            df = pd.read_parquet(cache_path_parquet)
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            return _filter_range(df, days=days, start=start, end=end)
        if cache_path_csv.exists():
            df = pd.read_csv(cache_path_csv)
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            return _filter_range(df, days=days, start=start, end=end)

    # Determine start time
    if start is None and days is not None:
        start = datetime.now(timezone.utc) - timedelta(days=days)

    df = fetch_klines(
        symbol=symbol,
        interval=interval,
        start=start,
        end=end,
    )

    if not df.empty:
        save_candles(df, symbol, interval, processed=False)

    return _filter_range(df, days=days, start=start, end=end)


def _filter_range(
    df: pd.DataFrame,
    days: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    if start is not None:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        out = out[out["ts"] >= pd.Timestamp(start)]
    if end is not None:
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        out = out[out["ts"] <= pd.Timestamp(end)]
    if days is not None and start is None and end is None:
        cutoff = pd.Timestamp(datetime.now(timezone.utc) - timedelta(days=days))
        out = out[out["ts"] >= cutoff]

    return out.reset_index(drop=True)


if __name__ == "__main__":
    # Quick smoke test
    print("Fetching recent SOLUSDT 5m candles...")
    df = load_candles("SOLUSDT", "5m", days=3, refresh=True)
    print(f"Rows: {len(df)}")
    if not df.empty:
        print(df.tail())
        print(f"Range: {df['ts'].iloc[0]} → {df['ts'].iloc[-1]}")

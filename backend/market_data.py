"""
market_data.py
==============

Thin wrapper around Yahoo Finance (via `yfinance`) that returns clean,
JSON-serialisable price history plus derived series (volatility, returns) that
the frontend charts and the music engine both consume.

If the network is unavailable or a symbol is invalid, we fall back to a
deterministic synthetic series so the app always demonstrates end-to-end — a
useful property for a portfolio piece being shown live.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import math

import numpy as np


@dataclass
class MarketSeries:
    symbol: str
    dates: List[str]
    close: List[float]
    volume: List[float]
    # Derived series for visualisation.
    returns: List[float]
    volatility: List[float]   # rolling std of returns
    source: str               # "yfinance" | "synthetic"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _rolling_volatility(close: np.ndarray, window: int = 10) -> List[float]:
    if close.size < 2:
        return [0.0] * close.size
    returns = np.zeros_like(close)
    returns[1:] = np.diff(close) / close[:-1]
    vol = np.zeros_like(close)
    for i in range(close.size):
        lo = max(0, i - window + 1)
        seg = returns[lo:i + 1]
        vol[i] = float(np.std(seg)) if seg.size > 1 else 0.0
    return vol.tolist()


def _returns(close: np.ndarray) -> List[float]:
    r = np.zeros_like(close)
    if close.size >= 2:
        r[1:] = np.diff(close) / close[:-1]
    return r.tolist()


def fetch_market_data(symbol: str, start: str, end: str) -> MarketSeries:
    """
    Fetch daily OHLCV for `symbol` between `start` and `end` (ISO dates).
    Falls back to a synthetic walk if yfinance is unavailable.
    """
    symbol = symbol.strip().upper()
    try:
        import yfinance as yf

        df = yf.download(symbol, start=start, end=end,
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            raise ValueError("empty result")

        # yfinance can return multi-index columns for single tickers.
        close_series = df["Close"]
        vol_series = df["Volume"]
        if hasattr(close_series, "columns"):
            close_series = close_series.iloc[:, 0]
            vol_series = vol_series.iloc[:, 0]

        dates = [d.strftime("%Y-%m-%d") for d in df.index]
        close = np.asarray(close_series.values, dtype=float)
        volume = np.asarray(vol_series.values, dtype=float)

        return MarketSeries(
            symbol=symbol,
            dates=dates,
            close=close.tolist(),
            volume=volume.tolist(),
            returns=_returns(close),
            volatility=_rolling_volatility(close),
            source="yfinance",
        )
    except Exception:
        return _synthetic_series(symbol, start, end)


def _synthetic_series(symbol: str, start: str, end: str,
                      n: int = 180) -> MarketSeries:
    """
    Deterministic pseudo-market series seeded by the symbol, so demos are
    reproducible and every ticker looks different. Not real data — clearly
    labelled as 'synthetic' so the UI can say so.
    """
    seed = sum(ord(c) for c in symbol) or 1
    rng = np.random.default_rng(seed)

    drift = (rng.random() - 0.45) * 0.0015          # slight up/down bias
    vol_base = 0.01 + rng.random() * 0.02
    price = 100.0 + rng.random() * 200.0

    closes, vols = [], []
    for i in range(n):
        shock = rng.normal(0, vol_base)
        # Add a couple of "regime" swings so charts look organic.
        regime = 0.01 * math.sin(i / 18.0) * math.sin(i / 5.0)
        price = max(1.0, price * (1 + drift + shock + regime))
        closes.append(round(price, 2))
        vols.append(float(int((1 + abs(shock) * 30) * (1e6 + rng.random() * 5e6))))

    close = np.asarray(closes, dtype=float)
    volume = np.asarray(vols, dtype=float)

    # Even, synthetic date axis.
    import datetime as _dt
    try:
        d0 = _dt.date.fromisoformat(start)
    except Exception:
        d0 = _dt.date(2024, 1, 1)
    dates = [(d0 + _dt.timedelta(days=i)).isoformat() for i in range(n)]

    return MarketSeries(
        symbol=symbol,
        dates=dates,
        close=close.tolist(),
        volume=volume.tolist(),
        returns=_returns(close),
        volatility=_rolling_volatility(close),
        source="synthetic",
    )

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
from typing import List, Dict, Any, Tuple
import datetime as dt
import json
import math
import urllib.parse
import urllib.request

import numpy as np

# Yahoo rejects the default urllib/python user agent with HTTP 429, so we
# present a browser UA. This is the same public endpoint the finance.yahoo.com
# charts themselves call.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"


@dataclass
class MarketSeries:
    symbol: str
    dates: List[str]
    close: List[float]
    volume: List[float]
    # Derived series for visualisation.
    returns: List[float]
    volatility: List[float]   # rolling std of returns
    source: str               # "yahoo" | "yfinance" | "synthetic"
    # Why we ended up on this source — surfaced in the UI so a synthetic
    # fallback can never be mistaken for real market data.
    note: str = ""
    currency: str = ""

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


def _epoch(iso: str, fallback: dt.date) -> int:
    try:
        d = dt.date.fromisoformat(iso)
    except Exception:
        d = fallback
    return int(dt.datetime(d.year, d.month, d.day,
                           tzinfo=dt.timezone.utc).timestamp())


def _yahoo_chart(symbol: str, start: str, end: str) -> Tuple[List[str], np.ndarray, np.ndarray, str]:
    """
    Call Yahoo's public chart endpoint directly.

    Two things here are deliberate, because both were sources of numbers that
    did not match what finance.yahoo.com shows:

    * We read `quote.close`, NOT `adjclose`. Adjusted closes are back-adjusted
      for dividends and splits, so every historical bar of a dividend payer
      comes out below the "Close" column on the website (~0.9% for AAPL two
      years back, and growing the further back you look).
    * `period2` is pushed one day forward, because Yahoo — like yfinance —
      treats the end of the range as EXCLUSIVE, which silently dropped the
      most recent bar (the one a user is most likely to be checking).
    """
    today = dt.date.today()
    p1 = _epoch(start, today - dt.timedelta(days=183))
    p2 = _epoch(end, today) + 86400          # make `end` inclusive
    url = (_CHART_URL.format(symbol=urllib.parse.quote(symbol))
           + f"?period1={p1}&period2={p2}&interval=1d")

    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.load(resp)

    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise ValueError(str(chart["error"]))
    results = chart.get("result") or []
    if not results:
        raise ValueError("no result for that symbol/range")

    res = results[0]
    meta = res.get("meta") or {}
    stamps = res.get("timestamp") or []
    quote = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    if not stamps or not closes:
        raise ValueError("empty series")

    # Timestamps are the session open in UTC; shift into exchange-local time so
    # the date label matches the row on the Yahoo website.
    offset = int(meta.get("gmtoffset") or 0)

    dates, close, volume = [], [], []
    for i, ts in enumerate(stamps):
        c = closes[i] if i < len(closes) else None
        if c is None:                        # holidays / halted sessions
            continue
        v = volumes[i] if i < len(volumes) else None
        day = dt.datetime.fromtimestamp(ts + offset, tz=dt.timezone.utc).date()
        dates.append(day.isoformat())
        close.append(float(c))
        volume.append(float(v or 0.0))

    if not close:
        raise ValueError("no priced sessions in that range")

    return (dates, np.asarray(close, dtype=float),
            np.asarray(volume, dtype=float), str(meta.get("currency") or ""))


def _yfinance_chart(symbol: str, start: str, end: str):
    """Fallback path. `auto_adjust=False` + inclusive `end`, to match Yahoo's site."""
    import yfinance as yf

    end_excl = end
    try:
        end_excl = (dt.date.fromisoformat(end) + dt.timedelta(days=1)).isoformat()
    except Exception:
        pass

    df = yf.download(symbol, start=start, end=end_excl,
                     progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise ValueError("empty result")

    close_series = df["Close"]
    vol_series = df["Volume"]
    # yfinance can return multi-index columns for single tickers.
    if hasattr(close_series, "columns"):
        close_series = close_series.iloc[:, 0]
        vol_series = vol_series.iloc[:, 0]

    close_series = close_series.dropna()
    vol_series = vol_series.reindex(close_series.index).fillna(0.0)

    dates = [d.strftime("%Y-%m-%d") for d in close_series.index]
    return (dates,
            np.asarray(close_series.values, dtype=float),
            np.asarray(vol_series.values, dtype=float))


def fetch_market_data(symbol: str, start: str, end: str) -> MarketSeries:
    """
    Fetch daily closes for `symbol` between `start` and `end` (ISO dates,
    both inclusive), preferring real Yahoo data.

    Order: Yahoo's chart endpoint -> yfinance -> deterministic synthetic walk.
    Whichever wins is reported in `source`, and any failure reason in `note`,
    so the UI never passes synthetic numbers off as the market.
    """
    symbol = symbol.strip().upper()
    problems: List[str] = []

    try:
        dates, close, volume, currency = _yahoo_chart(symbol, start, end)
        return MarketSeries(
            symbol=symbol, dates=dates,
            close=close.tolist(), volume=volume.tolist(),
            returns=_returns(close), volatility=_rolling_volatility(close),
            source="yahoo", currency=currency,
            note="Unadjusted daily closes from Yahoo Finance.",
        )
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"yahoo: {type(exc).__name__}: {exc}")

    try:
        dates, close, volume = _yfinance_chart(symbol, start, end)
        return MarketSeries(
            symbol=symbol, dates=dates,
            close=close.tolist(), volume=volume.tolist(),
            returns=_returns(close), volatility=_rolling_volatility(close),
            source="yfinance",
            note="Unadjusted daily closes via yfinance.",
        )
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"yfinance: {type(exc).__name__}: {exc}")

    series = _synthetic_series(symbol, start, end)
    series.note = "Live data unavailable (" + "; ".join(problems) + ")"
    return series


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


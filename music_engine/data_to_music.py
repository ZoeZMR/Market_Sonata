"""
data_to_music.py
================

The ANALYSIS layer.

This module never touches MIDI or musical notes. Its only job is to listen to
the market and describe it in a small, expressive vocabulary that a composer
can act on: momentum, volatility, participation (volume) and the overarching
emotional trend (bull / bear).

The output is a `MarketFeatures` object plus a list of `PhraseFeatures` — one
per musical phrase. The composition layer consumes these; it never sees a raw
price again.

Design principle
----------------
We segment the time series into a fixed number of *phrases* rather than mapping
one note per day. A sonata is built from phrases, not from individual samples.
This is the single most important decision separating this project from a naive
"one candle = one note" converter: it gives the music room to breathe, repeat
and develop.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

import numpy as np


# ---------------------------------------------------------------------------
# Feature containers
# ---------------------------------------------------------------------------

@dataclass
class PhraseFeatures:
    """Musical-scale summary of one slice of the market timeline."""

    index: int                 # 0-based phrase position in the piece
    # Normalised contour of price *within* this phrase, values in [-1, 1].
    # This becomes the raw melodic gesture for the phrase.
    contour: List[float]
    momentum: float            # net price change across the phrase, [-1, 1]
    volatility: float          # tension level, [0, 1]
    volume: float              # participation / dynamics, [0, 1]
    brightness: float          # local trend colour, [-1, 1] (bear..bull)

    def describe(self) -> str:
        """Plain-language tag used by the AI analyst."""
        vol = "turbulent" if self.volatility > 0.66 else \
              "restless" if self.volatility > 0.33 else "calm"
        mom = "rising" if self.momentum > 0.15 else \
              "falling" if self.momentum < -0.15 else "sideways"
        return f"{vol}, {mom}"


@dataclass
class MarketFeatures:
    """Whole-piece summary plus the per-phrase breakdown."""

    symbol: str
    start_date: str
    end_date: str
    n_days: int

    trend: float               # overall drift, [-1, 1] (bear..bull)
    avg_volatility: float      # [0, 1]
    avg_volume: float          # [0, 1]
    total_return: float        # raw fractional return over the window
    max_drawdown: float        # worst peak-to-trough, [0, 1]

    phrases: List[PhraseFeatures] = field(default_factory=list)

    # Convenience artistic labels ------------------------------------------
    @property
    def is_bull(self) -> bool:
        return self.trend >= 0

    @property
    def mode_label(self) -> str:
        if self.trend > 0.4:
            return "major"
        if self.trend > 0.05:
            return "major (tentative)"
        if self.trend > -0.05:
            return "modal / ambiguous"
        if self.trend > -0.4:
            return "minor"
        return "minor (dark)"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_bull"] = self.is_bull
        d["mode_label"] = self.mode_label
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_norm(x: np.ndarray) -> np.ndarray:
    """Scale an array into [-1, 1] robustly (ignores flat / degenerate input)."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    lo, hi = np.nanmin(x), np.nanmax(x)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-12:
        return np.zeros_like(x)
    return 2.0 * (x - lo) / (hi - lo) - 1.0


def _clip01(v: float) -> float:
    return float(min(1.0, max(0.0, v)))


def _tanh_scale(v: float, k: float = 1.0) -> float:
    """Squash an unbounded value into [-1, 1] gently."""
    return float(np.tanh(k * v))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_features(
    dates: List[str],
    close: List[float],
    volume: List[float],
    symbol: str,
    n_phrases: int = 12,
) -> MarketFeatures:
    """
    Convert raw market series into a composer-ready `MarketFeatures` object.

    Parameters
    ----------
    dates   : ISO date strings, ascending.
    close   : closing prices aligned with `dates`.
    volume  : trading volume aligned with `dates`.
    symbol  : the ticker, e.g. "AAPL".
    n_phrases : how many musical phrases to carve the timeline into.

    The number of phrases is the "resolution" of the composition. Twelve is a
    good default: enough for an ABA form with development, few enough that each
    phrase carries weight.
    """
    close_arr = np.asarray(close, dtype=float)
    vol_arr = np.asarray(volume, dtype=float)
    n = close_arr.size

    if n < 4:
        raise ValueError("Need at least 4 data points to compose a sonata.")

    # --- Global descriptors ------------------------------------------------
    daily_returns = np.diff(close_arr) / close_arr[:-1]
    total_return = float(close_arr[-1] / close_arr[0] - 1.0)

    # Trend: blend of total return and the sign-consistency of daily moves.
    up_days = np.mean(daily_returns > 0) if daily_returns.size else 0.5
    trend = _tanh_scale(total_return * 3.0) * 0.6 + (up_days - 0.5) * 2.0 * 0.4
    trend = float(np.clip(trend, -1.0, 1.0))

    # Volatility: std of daily returns, squashed to [0, 1].
    raw_vol = float(np.std(daily_returns)) if daily_returns.size else 0.0
    avg_volatility = _clip01(_tanh_scale(raw_vol * 40.0))

    # Volume participation relative to its own history.
    if vol_arr.size and np.nanmax(vol_arr) > 0:
        avg_volume = _clip01(float(np.nanmean(vol_arr) / np.nanmax(vol_arr)))
    else:
        avg_volume = 0.5

    # Max drawdown — the emotional low point of the story.
    running_max = np.maximum.accumulate(close_arr)
    drawdowns = (running_max - close_arr) / running_max
    max_drawdown = float(np.nanmax(drawdowns))

    # --- Per-phrase descriptors -------------------------------------------
    chunks = np.array_split(np.arange(n), n_phrases)
    phrases: List[PhraseFeatures] = []

    global_vol_ref = raw_vol if raw_vol > 1e-9 else 1e-9
    vol_ref = np.nanmax(vol_arr) if vol_arr.size and np.nanmax(vol_arr) > 0 else 1.0

    for i, idx in enumerate(chunks):
        if idx.size == 0:
            continue
        seg_close = close_arr[idx]
        seg_vol = vol_arr[idx] if vol_arr.size else np.array([0.0])

        # Contour: normalised shape of price within the phrase.
        contour = _resample_contour(_safe_norm(seg_close).tolist(), target=8)

        # Local momentum.
        if seg_close.size >= 2 and seg_close[0] != 0:
            seg_ret = seg_close[-1] / seg_close[0] - 1.0
        else:
            seg_ret = 0.0
        momentum = _tanh_scale(seg_ret * 6.0)

        # Local volatility relative to the whole piece.
        if seg_close.size >= 2:
            seg_daily = np.diff(seg_close) / seg_close[:-1]
            local_vol = float(np.std(seg_daily))
        else:
            local_vol = 0.0
        volatility = _clip01(local_vol / (global_vol_ref * 2.5))

        # Local volume / participation.
        volume_level = _clip01(float(np.nanmean(seg_vol) / vol_ref))

        # Brightness: local drift biased by the global trend so the piece keeps
        # a consistent emotional home key even as phrases vary.
        brightness = float(np.clip(0.6 * momentum + 0.4 * trend, -1.0, 1.0))

        phrases.append(
            PhraseFeatures(
                index=i,
                contour=contour,
                momentum=float(momentum),
                volatility=float(volatility),
                volume=float(volume_level),
                brightness=brightness,
            )
        )

    return MarketFeatures(
        symbol=symbol.upper(),
        start_date=dates[0] if dates else "",
        end_date=dates[-1] if dates else "",
        n_days=n,
        trend=trend,
        avg_volatility=avg_volatility,
        avg_volume=avg_volume,
        total_return=total_return,
        max_drawdown=max_drawdown,
        phrases=phrases,
    )


def _resample_contour(contour: List[float], target: int) -> List[float]:
    """Resample a contour to exactly `target` points via linear interpolation."""
    arr = np.asarray(contour, dtype=float)
    if arr.size == 0:
        return [0.0] * target
    if arr.size == target:
        return arr.tolist()
    xp = np.linspace(0.0, 1.0, arr.size)
    x = np.linspace(0.0, 1.0, target)
    return np.interp(x, xp, arr).tolist()

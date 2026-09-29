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

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Tuple
import datetime as dt
import json
import math
import time
import urllib.parse
import urllib.request

import numpy as np

# Yahoo rejects the default urllib/python user agent with HTTP 429, so we
# present a browser UA. This is the same public endpoint the finance.yahoo.com
# charts themselves call.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

# Quote types worth surfacing in the ticker search box. Yahoo's search also
# returns "OPTION", "MUTUALFUND", "FUTURE" etc. that the engine can technically
# chart but that are rarely what someone typing a company name wants.
_SEARCH_TYPES = {"EQUITY", "ETF", "INDEX", "CRYPTOCURRENCY", "CURRENCY",
                 "FUTURE", "MUTUALFUND"}

# Bar sizes the chart endpoint serves, and how far back Yahoo keeps each
# intraday one. A request past the cap is clamped rather than failing outright.
INTERVALS = {"1d", "1wk", "1mo", "1h", "30m", "15m", "5m"}
_INTRADAY_MAX_DAYS = {"1h": 729, "30m": 59, "15m": 59, "5m": 59}
_INTERVAL_WORD = {"1d": "daily", "1wk": "weekly", "1mo": "monthly",
                  "1h": "hourly", "30m": "30-minute", "15m": "15-minute",
                  "5m": "5-minute"}


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
    # Session opens, aligned with `close`. Empty when the source lacks them
    # (synthetic data), in which case no gaps are detected.
    open: List[float] = field(default_factory=list)
    # Bar extremes, aligned with `close` (empty for synthetic data).
    high: List[float] = field(default_factory=list)
    low: List[float] = field(default_factory=list)
    # Bar size actually served: "1d", "1wk", "1mo", "1h", "15m" ...
    interval: str = "1d"
    # Descriptive metadata from Yahoo (name, exchange, instrument type, 52w range).
    info: Dict[str, Any] = field(default_factory=dict)

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


def _get_json(url: str, timeout: float = 15) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _yahoo_chart(symbol: str, start: str, end: str,
                 interval: str = "1d") -> Dict[str, Any]:
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
    cap = _INTRADAY_MAX_DAYS.get(interval)
    if cap is not None:
        now = int(dt.datetime.now(dt.timezone.utc).timestamp())
        p1 = max(p1, now - cap * 86400)
    url = (_CHART_URL.format(symbol=urllib.parse.quote(symbol))
           + f"?period1={p1}&period2={p2}&interval={interval}")

    payload = _get_json(url, timeout=20)

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
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    if not stamps or not closes:
        raise ValueError("empty series")

    # Timestamps are the session open in UTC; shift into exchange-local time so
    # the date label matches the row on the Yahoo website. Intraday bars keep
    # their clock time, since several share one calendar day.
    offset = int(meta.get("gmtoffset") or 0)
    intraday = interval in _INTRADAY_MAX_DAYS
    at = lambda arr, i: arr[i] if i < len(arr) else None  # noqa: E731

    dates, close, volume, open_, high, low = [], [], [], [], [], []
    for i, ts in enumerate(stamps):
        c = at(closes, i)
        if c is None:                        # holidays / halted sessions
            continue
        o, h, lo = at(opens, i), at(highs, i), at(lows, i)
        o = o if o is not None else c
        local = dt.datetime.fromtimestamp(ts + offset, tz=dt.timezone.utc)
        dates.append(local.strftime("%Y-%m-%d %H:%M") if intraday
                     else local.date().isoformat())
        close.append(float(c))
        volume.append(float(at(volumes, i) or 0.0))
        open_.append(float(o))
        high.append(float(h if h is not None else max(c, o)))
        low.append(float(lo if lo is not None else min(c, o)))

    if not close:
        raise ValueError("no priced sessions in that range")

    info = {
        "name": meta.get("longName") or meta.get("shortName") or symbol,
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName") or "",
        "type": meta.get("instrumentType") or "",
        "timezone": meta.get("exchangeTimezoneName") or "",
        "price": meta.get("regularMarketPrice"),
        "high52": meta.get("fiftyTwoWeekHigh"),
        "low52": meta.get("fiftyTwoWeekLow"),
    }
    return {
        "dates": dates,
        "close": np.asarray(close, dtype=float),
        "volume": np.asarray(volume, dtype=float),
        "open": np.asarray(open_, dtype=float),
        "high": np.asarray(high, dtype=float),
        "low": np.asarray(low, dtype=float),
        "currency": str(meta.get("currency") or ""),
        "info": info,
    }


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
    open_series = df["Open"]
    # yfinance can return multi-index columns for single tickers.
    if hasattr(close_series, "columns"):
        close_series = close_series.iloc[:, 0]
        vol_series = vol_series.iloc[:, 0]
        open_series = open_series.iloc[:, 0]

    close_series = close_series.dropna()
    vol_series = vol_series.reindex(close_series.index).fillna(0.0)
    open_series = open_series.reindex(close_series.index).fillna(close_series)

    dates = [d.strftime("%Y-%m-%d") for d in close_series.index]
    return (dates,
            np.asarray(close_series.values, dtype=float),
            np.asarray(vol_series.values, dtype=float),
            np.asarray(open_series.values, dtype=float))


def fetch_market_data(symbol: str, start: str, end: str,
                      interval: str = "1d") -> MarketSeries:
    """
    Fetch daily closes for `symbol` between `start` and `end` (ISO dates,
    both inclusive), preferring real Yahoo data.

    Order: Yahoo's chart endpoint -> yfinance -> deterministic synthetic walk.
    Whichever wins is reported in `source`, and any failure reason in `note`,
    so the UI never passes synthetic numbers off as the market.
    """
    symbol = symbol.strip().upper()
    if interval not in INTERVALS:
        interval = "1d"
    problems: List[str] = []

    try:
        d = _yahoo_chart(symbol, start, end, interval)
        close = d["close"]
        return MarketSeries(
            symbol=symbol, dates=d["dates"],
            close=close.tolist(), volume=d["volume"].tolist(),
            open=d["open"].tolist(), high=d["high"].tolist(), low=d["low"].tolist(),
            returns=_returns(close), volatility=_rolling_volatility(close),
            source="yahoo", currency=d["currency"], interval=interval,
            info=d["info"],
            note=f"Unadjusted {_INTERVAL_WORD[interval]} bars from Yahoo Finance.",
        )
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"yahoo: {type(exc).__name__}: {exc}")

    # yfinance only backs up the daily path; other bar sizes fail over straight
    # to the labelled synthetic series.
    try:
        if interval != "1d":
            raise ValueError(f"fallback serves daily bars only, not {interval}")
        dates, close, volume, open_ = _yfinance_chart(symbol, start, end)
        return MarketSeries(
            symbol=symbol, dates=dates,
            close=close.tolist(), volume=volume.tolist(), open=open_.tolist(),
            returns=_returns(close), volatility=_rolling_volatility(close),
            source="yfinance",
            note="Unadjusted daily closes via yfinance.",
        )
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"yfinance: {type(exc).__name__}: {exc}")

    series = _synthetic_series(symbol, start, end)
    series.note = "Live data unavailable (" + "; ".join(problems) + ")"
    return series


def search_symbols(query: str, limit: int = 20) -> List[Dict[str, str]]:
    """
    Resolve a free-text query (a company name, a partial ticker) to a short
    list of tickers Market Sonata can compose from, via Yahoo's public search
    endpoint. `fetch_market_data` already accepts *any* symbol Yahoo knows —
    this is purely a discovery aid so a user does not need to already know the
    exact ticker (see the "More stocks" quick-pick chips, which only cover a
    couple dozen symbols by hand).
    """
    query = query.strip()
    if not query:
        return []

    url = f"{_SEARCH_URL}?{urllib.parse.urlencode({'q': query, 'quotesCount': limit, 'newsCount': 0})}"
    payload = _get_json(url, timeout=8)

    out: List[Dict[str, str]] = []
    for q in payload.get("quotes") or []:
        symbol = q.get("symbol")
        qtype = (q.get("quoteType") or "").upper()
        if not symbol or qtype not in _SEARCH_TYPES:
            continue
        name = q.get("longname") or q.get("shortname") or symbol
        out.append({
            "symbol": symbol,
            "name": name,
            "exchange": q.get("exchDisp") or q.get("exchange") or "",
            "type": qtype,
        })
        if len(out) >= limit:
            break
    return out


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



# ---------------------------------------------------------------------------
# Discovery: live screeners, trending tickers and batch sparklines.
# These power the market browser; none of them feed the music engine directly.
# ---------------------------------------------------------------------------

_SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
_TRENDING_URL = "https://query1.finance.yahoo.com/v1/finance/trending/{region}"
_SPARK_URL = "https://query2.finance.yahoo.com/v8/finance/spark"

# Yahoo's predefined screeners, as {id: label}. The id is passed straight to
# Yahoo, so only ids in this table are accepted.
SCREENERS = {
    "day_gainers": "Day gainers",
    "day_losers": "Day losers",
    "most_actives": "Most active",
    "small_cap_gainers": "Small-cap gainers",
    "growth_technology_stocks": "Growth tech",
    "undervalued_growth_stocks": "Undervalued growth",
    "undervalued_large_caps": "Undervalued large caps",
    "aggressive_small_caps": "Aggressive small caps",
    "most_shorted_stocks": "Most shorted",
    "all_cryptocurrencies_us": "All crypto",
    "top_mutual_funds": "Top mutual funds",
    "portfolio_anchors": "Portfolio anchors",
    "solid_large_growth_funds": "Large growth funds",
    "high_yield_bond": "High-yield bond funds",
    "conservative_foreign_funds": "Foreign funds",
}

_CACHE: Dict[str, Tuple[float, Any]] = {}


def _cached(key: str, ttl: float, fn):
    """Tiny in-process TTL cache, so browsing the catalog doesn't hammer Yahoo."""
    hit = _CACHE.get(key)
    now = time.time()
    if hit and now - hit[0] < ttl:
        return hit[1]
    val = fn()
    _CACHE[key] = (now, val)
    return val


def fetch_screener(scr_id: str, count: int = 50) -> Dict[str, Any]:
    """One of Yahoo's predefined screens, as a flat list of quote rows."""
    if scr_id not in SCREENERS:
        raise ValueError(f"unknown screener {scr_id!r}")
    count = max(1, min(int(count), 250))

    def load():
        url = f"{_SCREENER_URL}?{urllib.parse.urlencode({'scrIds': scr_id, 'count': count})}"
        payload = _get_json(url)
        res = ((payload.get("finance") or {}).get("result") or [{}])[0]
        rows = []
        for q in res.get("quotes") or []:
            if not q.get("symbol"):
                continue
            rows.append({
                "symbol": q["symbol"],
                "name": q.get("shortName") or q.get("longName") or q["symbol"],
                "price": q.get("regularMarketPrice"),
                "change_pct": q.get("regularMarketChangePercent"),
                "volume": q.get("regularMarketVolume"),
                "market_cap": q.get("marketCap"),
                "currency": q.get("currency") or "",
                "exchange": q.get("fullExchangeName") or q.get("exchange") or "",
                "type": q.get("quoteType") or "",
            })
        return {"id": scr_id, "title": SCREENERS[scr_id],
                "total": res.get("total"), "quotes": rows}

    return _cached(f"scr:{scr_id}:{count}", 120, load)


def fetch_trending(region: str = "US", count: int = 25) -> List[str]:
    region = "".join(ch for ch in region.upper() if ch.isalpha())[:2] or "US"

    def load():
        url = _TRENDING_URL.format(region=region) + f"?count={int(count)}"
        payload = _get_json(url)
        res = ((payload.get("finance") or {}).get("result") or [{}])[0]
        return [q["symbol"] for q in res.get("quotes") or [] if q.get("symbol")]

    return _cached(f"trend:{region}:{count}", 300, load)


def fetch_spark(symbols: List[str], range_: str = "1mo",
                interval: str = "1d") -> Dict[str, Dict[str, Any]]:
    """
    Last price, change and a small close series for many symbols at once.
    Yahoo caps a spark request at 20 symbols, so larger lists are batched.
    """
    if range_ not in {"1d", "5d", "1mo", "3mo", "6mo", "1y", "ytd"}:
        range_ = "1mo"
    if interval not in {"5m", "15m", "1h", "1d"}:
        interval = "1d"
    clean = []
    for s in symbols:
        s = s.strip().upper()
        if s and s not in clean:
            clean.append(s)
    clean = clean[:300]

    out: Dict[str, Dict[str, Any]] = {}
    todo = []
    for s in clean:
        hit = _CACHE.get(f"spark:{s}:{range_}:{interval}")
        if hit and time.time() - hit[0] < 90:
            out[s] = hit[1]
        else:
            todo.append(s)

    for i in range(0, len(todo), 20):
        batch = todo[i:i + 20]
        url = f"{_SPARK_URL}?" + urllib.parse.urlencode(
            {"symbols": ",".join(batch), "range": range_, "interval": interval})
        try:
            payload = _get_json(url)
        except Exception:                                     # noqa: BLE001
            continue
        for sym, d in payload.items():
            if not isinstance(d, dict):
                continue
            closes = [c for c in (d.get("close") or []) if c is not None]
            if not closes:
                continue
            ref = d.get("chartPreviousClose") or d.get("previousClose") or closes[0]
            row = {
                "symbol": sym,
                "price": closes[-1],
                "change_pct": (closes[-1] / ref - 1.0) * 100.0 if ref else None,
                "closes": [round(float(c), 6) for c in closes],
            }
            out[sym] = row
            _CACHE[f"spark:{sym}:{range_}:{interval}"] = (time.time(), row)
    return out


# ---------------------------------------------------------------------------
# The full universe: Yahoo's custom screener over every listed instrument.
# Unlike the predefined screens above, this endpoint needs a session cookie and
# a "crumb" token, which we obtain once and refresh if Yahoo rejects it.
# ---------------------------------------------------------------------------

_SCREEN_POST_URL = "https://query1.finance.yahoo.com/v1/finance/screener"

# Yahoo region codes offered in the explorer, as {code: label}.
REGIONS = {
    "us": "United States", "cn": "China (A-shares)", "hk": "Hong Kong",
    "tw": "Taiwan", "jp": "Japan", "kr": "South Korea", "in": "India",
    "sg": "Singapore", "my": "Malaysia", "th": "Thailand", "id": "Indonesia",
    "au": "Australia", "nz": "New Zealand", "gb": "United Kingdom",
    "de": "Germany", "fr": "France", "nl": "Netherlands", "ch": "Switzerland",
    "it": "Italy", "es": "Spain", "se": "Sweden", "no": "Norway", "dk": "Denmark",
    "fi": "Finland", "be": "Belgium", "at": "Austria", "ie": "Ireland",
    "pt": "Portugal", "pl": "Poland", "gr": "Greece", "tr": "Turkey",
    "il": "Israel", "sa": "Saudi Arabia", "qa": "Qatar", "za": "South Africa",
    "eg": "Egypt", "ca": "Canada", "mx": "Mexico", "br": "Brazil",
    "ar": "Argentina", "cl": "Chile",
}
SECTORS = ["Technology", "Communication Services", "Consumer Cyclical",
           "Consumer Defensive", "Financial Services", "Healthcare",
           "Industrials", "Energy", "Basic Materials", "Real Estate", "Utilities"]
UNIVERSE_TYPES = {"EQUITY": "intradaymarketcap", "ETF": "fundnetassets",
                  "MUTUALFUND": "fundnetassets"}
UNIVERSE_SORTS = {"size", "percentchange", "dayvolume", "intradayprice"}
# US listings on the main exchanges (Nasdaq tiers, NYSE, NYSE American/Arca,
# Cboe) — excludes the thinly traded OTC tail that otherwise tops "% change".
_US_MAIN_EXCHANGES = ["NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS"]


class _YahooSession:
    """Cookie + crumb pair for Yahoo's authenticated JSON endpoints."""

    def __init__(self) -> None:
        import http.cookiejar
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", _UA)]
        self.crumb = ""

    def refresh(self) -> None:
        try:
            self.opener.open("https://fc.yahoo.com", timeout=10)
        except Exception:                                     # noqa: BLE001
            pass    # fc.yahoo.com answers 404 but still sets the cookie
        self.crumb = self.opener.open(
            "https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10
        ).read().decode().strip()
        if not self.crumb or "<" in self.crumb:
            raise ValueError("could not obtain a Yahoo crumb")

    def post_json(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        import urllib.error
        for attempt in range(2):
            if not self.crumb:
                self.refresh()
            req = urllib.request.Request(
                f"{url}?crumb={urllib.parse.quote(self.crumb)}&formatted=false&lang=en-US",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "Accept": "application/json"})
            try:
                with self.opener.open(req, timeout=20) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403) and attempt == 0:
                    self.crumb = ""          # stale crumb: fetch a new one once
                    continue
                raise
        raise RuntimeError("unreachable")


_session: _YahooSession | None = None


def fetch_universe(region: str = "us", sector: str = "", quote_type: str = "EQUITY",
                   sort: str = "size", desc: bool = True, offset: int = 0,
                   size: int = 100, main_only: bool = False) -> Dict[str, Any]:
    """
    One page of every instrument Yahoo lists for a region (optionally one
    sector), sorted server-side. `total` is the full count, so the explorer
    can page through all of it.
    """
    global _session
    region = region if region in REGIONS else "us"
    quote_type = quote_type if quote_type in UNIVERSE_TYPES else "EQUITY"
    sort = sort if sort in UNIVERSE_SORTS else "size"
    sort_field = UNIVERSE_TYPES[quote_type] if sort == "size" else sort
    size = max(1, min(int(size), 250))
    offset = max(0, int(offset))

    ops: List[Dict[str, Any]] = [{"operator": "eq", "operands": ["region", region]}]
    if sector in SECTORS and quote_type == "EQUITY":
        ops.append({"operator": "eq", "operands": ["sector", sector]})
    if main_only and region == "us":
        ops.append({"operator": "or", "operands": [
            {"operator": "eq", "operands": ["exchange", x]} for x in _US_MAIN_EXCHANGES]})
    query = ops[0] if len(ops) == 1 else {"operator": "and", "operands": ops}
    body = {"offset": offset, "size": size, "sortField": sort_field,
            "sortType": "DESC" if desc else "ASC", "quoteType": quote_type,
            "query": query, "userId": "", "userIdType": "guid"}

    def load():
        global _session
        if _session is None:
            _session = _YahooSession()
        payload = _session.post_json(_SCREEN_POST_URL, body)
        fin = payload.get("finance") or {}
        if fin.get("error"):
            raise ValueError(str(fin["error"]))
        res = (fin.get("result") or [{}])[0]
        rows = []
        for q in res.get("quotes") or []:
            if not q.get("symbol"):
                continue
            rows.append({
                "symbol": q["symbol"],
                "name": q.get("longName") or q.get("shortName") or q["symbol"],
                "price": q.get("regularMarketPrice"),
                "change_pct": q.get("regularMarketChangePercent"),
                "volume": q.get("regularMarketVolume"),
                "market_cap": q.get("marketCap") or q.get("netAssets"),
                "currency": q.get("currency") or "",
                "exchange": q.get("fullExchangeName") or q.get("exchange") or "",
                "type": q.get("quoteType") or quote_type,
            })
        return {"total": res.get("total") or 0, "offset": offset, "quotes": rows}

    key = f"uni:{region}:{sector}:{quote_type}:{sort_field}:{desc}:{offset}:{size}:{main_only}"
    return _cached(key, 120, load)

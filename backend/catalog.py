"""
catalog.py
==========

The browsable market universe behind the market explorer.

These are hand-picked groups of well-known instruments across asset classes and
regions. Live prices and sparklines for them come from `market_data.fetch_spark`;
the live, ever-changing lists (gainers, losers, most active, trending, ...) come
from Yahoo's screeners instead of this file. Anything not listed here is still
reachable through the search box, which resolves any symbol Yahoo knows.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# (symbol, display name)
Entry = Tuple[str, str]

CATALOG: List[Dict[str, object]] = [
    {"id": "tech", "label": "Tech", "group": "US stocks", "items": [
        ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
        ("GOOGL", "Alphabet"), ("AMZN", "Amazon"), ("META", "Meta Platforms"),
        ("TSLA", "Tesla"), ("AVGO", "Broadcom"), ("ORCL", "Oracle"),
        ("AMD", "AMD"), ("CRM", "Salesforce"), ("ADBE", "Adobe"),
        ("INTC", "Intel"), ("QCOM", "Qualcomm"), ("CSCO", "Cisco"),
        ("IBM", "IBM"), ("NFLX", "Netflix"), ("PLTR", "Palantir"),
        ("MU", "Micron"), ("ARM", "Arm Holdings"), ("TSM", "TSMC (ADR)"),
        ("ASML", "ASML (ADR)"), ("SHOP", "Shopify"), ("UBER", "Uber"),
        ("SNOW", "Snowflake"),
    ]},
    {"id": "finance", "label": "Finance", "group": "US stocks", "items": [
        ("JPM", "JPMorgan Chase"), ("BAC", "Bank of America"), ("WFC", "Wells Fargo"),
        ("GS", "Goldman Sachs"), ("MS", "Morgan Stanley"), ("C", "Citigroup"),
        ("BLK", "BlackRock"), ("SCHW", "Charles Schwab"), ("BRK-B", "Berkshire Hathaway"),
        ("V", "Visa"), ("MA", "Mastercard"), ("AXP", "American Express"),
        ("PYPL", "PayPal"), ("COIN", "Coinbase"),
    ]},
    {"id": "health", "label": "Healthcare", "group": "US stocks", "items": [
        ("LLY", "Eli Lilly"), ("JNJ", "Johnson & Johnson"), ("UNH", "UnitedHealth"),
        ("PFE", "Pfizer"), ("MRK", "Merck"), ("ABBV", "AbbVie"),
        ("NVO", "Novo Nordisk (ADR)"), ("AMGN", "Amgen"), ("TMO", "Thermo Fisher"),
        ("ISRG", "Intuitive Surgical"), ("MRNA", "Moderna"),
    ]},
    {"id": "consumer", "label": "Consumer", "group": "US stocks", "items": [
        ("WMT", "Walmart"), ("COST", "Costco"), ("KO", "Coca-Cola"),
        ("PEP", "PepsiCo"), ("MCD", "McDonald's"), ("SBUX", "Starbucks"),
        ("NKE", "Nike"), ("DIS", "Disney"), ("HD", "Home Depot"),
        ("TGT", "Target"), ("PG", "Procter & Gamble"), ("LULU", "Lululemon"),
        ("CMG", "Chipotle"),
    ]},
    {"id": "industrial", "label": "Energy & industry", "group": "US stocks", "items": [
        ("XOM", "Exxon Mobil"), ("CVX", "Chevron"), ("COP", "ConocoPhillips"),
        ("SLB", "Schlumberger"), ("OXY", "Occidental"), ("BA", "Boeing"),
        ("CAT", "Caterpillar"), ("GE", "GE Aerospace"), ("LMT", "Lockheed Martin"),
        ("RTX", "RTX"), ("DE", "Deere"), ("UPS", "UPS"),
        ("F", "Ford"), ("GM", "General Motors"),
    ]},
    {"id": "china_adr", "label": "China ADRs", "group": "US stocks", "items": [
        ("BABA", "Alibaba"), ("PDD", "PDD Holdings"), ("JD", "JD.com"),
        ("BIDU", "Baidu"), ("NIO", "NIO"), ("LI", "Li Auto"),
        ("XPEV", "XPeng"), ("TCOM", "Trip.com"), ("BILI", "Bilibili"),
    ]},
    {"id": "etf", "label": "ETFs", "group": "Funds", "items": [
        ("SPY", "S&P 500 ETF"), ("QQQ", "Nasdaq-100 ETF"), ("DIA", "Dow Jones ETF"),
        ("IWM", "Russell 2000 ETF"), ("VTI", "Total US Market"), ("VOO", "Vanguard S&P 500"),
        ("ARKK", "ARK Innovation"), ("XLK", "Tech Select Sector"), ("XLF", "Financial Select Sector"),
        ("XLE", "Energy Select Sector"), ("XLV", "Health Care Select Sector"),
        ("SMH", "Semiconductor ETF"), ("GLD", "Gold ETF"), ("SLV", "Silver ETF"),
        ("TLT", "20+ Year Treasury"), ("HYG", "High Yield Corporate Bond"),
        ("EEM", "Emerging Markets"), ("EFA", "Developed ex-US"),
        ("VNQ", "Real Estate"), ("USO", "US Oil Fund"), ("IBIT", "iShares Bitcoin Trust"),
    ]},
    {"id": "indices", "label": "World indices", "group": "Indices", "items": [
        ("^GSPC", "S&P 500"), ("^DJI", "Dow Jones"), ("^IXIC", "Nasdaq Composite"),
        ("^RUT", "Russell 2000"), ("^VIX", "VIX volatility"), ("^GSPTSE", "S&P/TSX"),
        ("^BVSP", "Bovespa"), ("^FTSE", "FTSE 100"), ("^GDAXI", "DAX"),
        ("^FCHI", "CAC 40"), ("^STOXX50E", "Euro Stoxx 50"), ("^N225", "Nikkei 225"),
        ("^HSI", "Hang Seng"), ("000001.SS", "SSE Composite"), ("399001.SZ", "Shenzhen Component"),
        ("^KS11", "KOSPI"), ("^TWII", "Taiwan Weighted"), ("^BSESN", "BSE Sensex"),
        ("^NSEI", "Nifty 50"), ("^AXJO", "ASX 200"),
    ]},
    {"id": "crypto", "label": "Crypto", "group": "Crypto & FX", "items": [
        ("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"), ("SOL-USD", "Solana"),
        ("BNB-USD", "BNB"), ("XRP-USD", "XRP"), ("ADA-USD", "Cardano"),
        ("DOGE-USD", "Dogecoin"), ("AVAX-USD", "Avalanche"), ("DOT-USD", "Polkadot"),
        ("LINK-USD", "Chainlink"), ("LTC-USD", "Litecoin"), ("TRX-USD", "TRON"),
    ]},
    {"id": "fx", "label": "Currencies", "group": "Crypto & FX", "items": [
        ("DX-Y.NYB", "US Dollar Index"), ("EURUSD=X", "EUR / USD"), ("GBPUSD=X", "GBP / USD"),
        ("USDJPY=X", "USD / JPY"), ("USDCNY=X", "USD / CNY"), ("USDHKD=X", "USD / HKD"),
        ("AUDUSD=X", "AUD / USD"), ("USDCAD=X", "USD / CAD"), ("USDCHF=X", "USD / CHF"),
        ("NZDUSD=X", "NZD / USD"), ("EURJPY=X", "EUR / JPY"),
    ]},
    {"id": "commodities", "label": "Commodities", "group": "Commodities & rates", "items": [
        ("GC=F", "Gold"), ("SI=F", "Silver"), ("PL=F", "Platinum"), ("HG=F", "Copper"),
        ("CL=F", "Crude oil (WTI)"), ("BZ=F", "Brent crude"), ("NG=F", "Natural gas"),
        ("ZC=F", "Corn"), ("ZW=F", "Wheat"), ("ZS=F", "Soybeans"),
        ("KC=F", "Coffee"), ("CC=F", "Cocoa"), ("SB=F", "Sugar"),
    ]},
    {"id": "rates", "label": "Treasury yields", "group": "Commodities & rates", "items": [
        ("^IRX", "13-week T-bill"), ("^FVX", "5-year yield"),
        ("^TNX", "10-year yield"), ("^TYX", "30-year yield"),
    ]},
    {"id": "cn", "label": "China A-shares", "group": "Asia & Europe", "items": [
        ("600519.SS", "Kweichow Moutai"), ("601318.SS", "Ping An Insurance"),
        ("600036.SS", "China Merchants Bank"), ("601398.SS", "ICBC"),
        ("600900.SS", "China Yangtze Power"), ("300750.SZ", "CATL"),
        ("000858.SZ", "Wuliangye"), ("002594.SZ", "BYD"),
    ]},
    {"id": "hk", "label": "Hong Kong", "group": "Asia & Europe", "items": [
        ("0700.HK", "Tencent"), ("9988.HK", "Alibaba"), ("3690.HK", "Meituan"),
        ("1810.HK", "Xiaomi"), ("9618.HK", "JD.com"), ("1211.HK", "BYD"),
        ("0005.HK", "HSBC"), ("1299.HK", "AIA Group"), ("0941.HK", "China Mobile"),
    ]},
    {"id": "jp", "label": "Japan", "group": "Asia & Europe", "items": [
        ("7203.T", "Toyota"), ("6758.T", "Sony"), ("9984.T", "SoftBank Group"),
        ("7974.T", "Nintendo"), ("8306.T", "Mitsubishi UFJ"), ("6861.T", "Keyence"),
        ("8035.T", "Tokyo Electron"),
    ]},
    {"id": "eu", "label": "Europe", "group": "Asia & Europe", "items": [
        ("ASML.AS", "ASML"), ("SAP.DE", "SAP"), ("SIE.DE", "Siemens"),
        ("MC.PA", "LVMH"), ("RMS.PA", "Hermès"), ("OR.PA", "L'Oréal"),
        ("NESN.SW", "Nestlé"), ("NOVO-B.CO", "Novo Nordisk"),
        ("SHEL.L", "Shell"), ("AZN.L", "AstraZeneca"), ("HSBA.L", "HSBC"),
    ]},
]


def catalog() -> List[Dict[str, object]]:
    """JSON-ready catalog: each item as {symbol, name}."""
    return [
        {"id": c["id"], "label": c["label"], "group": c["group"],
         "items": [{"symbol": s, "name": n} for s, n in c["items"]]}  # type: ignore[union-attr]
        for c in CATALOG
    ]

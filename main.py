import yfinance as yf

def get_stock_price(ticker="AAPL"):
    stock = yf.Ticker(ticker)
    history = stock.history(period="5d")

    print(f"\nLast 5 days of {ticker}:\n")
    print(history[["Open", "High", "Low", "Close", "Volume"]])

if __name__ == "__main__":
    get_stock_price("AAPL")
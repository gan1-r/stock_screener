import yfinance as yf
import mplfinance as mpf

def get_candlestick_chart(ticker, interval="1d", period="6mo"):
    # Download data from Yahoo Finance
    df = yf.download(ticker, interval=interval, period=period, group_by="ticker", auto_adjust=False)

    # Reshape ke format long
    df = df.stack(level=0, future_stack=True).reset_index()
    df = df.rename(columns={"level_1": "Ticker"})

    # Set Date sebagai index dulu (wajib untuk resample)
    df = df.set_index("Date")

    # Resample per ticker (group_keys biar Ticker tetap ada di hasil)
    weekly = (
        df.groupby("Ticker")
          .resample("W-FRI")
          .agg({
              "Open": "first",
              "High": "max",
              "Low": "min",
              "Close": "last",
              "Volume": "sum"
          })
    )

    # Optional: rapikan index jadi kolom biasa lagi
    df = weekly.reset_index()
    return df



tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
df = get_candlestick_chart(tickers, interval="1wk", period="6mo")
df = df[df['Ticker'] == 'AAPL']
df_candle = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
print(df_candle)
# mpf.plot(df_candle, type="candle", volume=True, style="yahoo", title="GOOGL Weekly Candlestick")

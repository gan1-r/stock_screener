import yfinance as yf
import mplfinance as mpf
from datetime import datetime
import numpy as np
import os


def get_candlestick_chart(ticker, interval="1d", period="6mo", resample_weekly=False):
    
    raw = yf.download(ticker, interval=interval, period=period,
                    group_by="ticker", auto_adjust=False)

    long_df = raw.stack(level=0, future_stack=True).reset_index()
    long_df = long_df.rename(columns={"level_1": "Ticker"})
    long_df = long_df.set_index("Date")

    if resample_weekly:
        long_df = (
            long_df.groupby("Ticker")
            .resample("W-FRI")
            .agg({"Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"})
            .reset_index()
            .set_index("Date")
        )
        # Buang baris minggu yang kosong (misal minggu tanpa hari trading
        # untuk ticker tertentu, hasil agregasi jadi NaN semua)
        long_df = long_df.dropna(subset=["Open", "High", "Low", "Close"], how="all")

    return long_df


def get_chart_image(df_ticker, ticker, folder='default'):

    if df_ticker.empty or len(df_ticker) < 2:
        print(f"{ticker}: dilewati saat plotting, data terlalu sedikit.")
        return False

    buy_marker = np.where(df_ticker["Buy"], df_ticker["Low"] * 0.995, np.nan)
    sell_marker = np.where(df_ticker["Sell"], df_ticker["High"] * 1.005, np.nan)

    # mplfinance error kalau sebuah addplot seluruhnya NaN (misal MA dengan
    # periode > jumlah baris data, umum terjadi setelah resample mingguan
    # dengan rentang waktu pendek). Skip addplot yang kosong secara otomatis.
    apds = []
    if df_ticker["MA1"].notna().any():
        apds.append(mpf.make_addplot(df_ticker["MA1"], color="blue", width=1.2))
    else:
        print(f"{ticker}: MA1 dilewati (semua NaN, periode {MA1_PERIOD} > jumlah baris {len(df_ticker)}).")

    if df_ticker["MA2"].notna().any():
        apds.append(mpf.make_addplot(df_ticker["MA2"], color="orange", width=1.2))
    else:
        print(f"{ticker}: MA2 dilewati (semua NaN, periode {MA2_PERIOD} > jumlah baris {len(df_ticker)}).")

    if df_ticker["ATR_Stop"].notna().any():
        apds.append(mpf.make_addplot(df_ticker["ATR_Stop"], color="gray", width=1.0, linestyle="dotted"))

    if not np.all(np.isnan(buy_marker)):
        apds.append(mpf.make_addplot(buy_marker, type="scatter", markersize=80, marker="^", color="green"))

    if not np.all(np.isnan(sell_marker)):
        apds.append(mpf.make_addplot(sell_marker, type="scatter", markersize=80, marker="v", color="red"))

    os.makedirs(f"image/{folder}", exist_ok=True)

    mpf.plot(
        df_ticker,
        type="candle",
        style="yahoo",
        addplot=apds,
        volume=True,
        title=f"{ticker} - UT Bot MA",
        figsize=(14, 8),
        savefig=f"image/{folder}/ut_bot_{ticker}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    )

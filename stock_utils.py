import yfinance as yf
import mplfinance as mpf
from datetime import datetime
import numpy as np
import os

import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt


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
        print(f"{ticker}: MA1 dilewati (semua NaN, periode > jumlah baris {len(df_ticker)}).")

    if df_ticker["MA2"].notna().any():
        apds.append(mpf.make_addplot(df_ticker["MA2"], color="orange", width=1.2))
    else:
        print(f"{ticker}: MA2 dilewati (semua NaN, periode > jumlah baris {len(df_ticker)}).")

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


def get_chart_image_turtle(df_ticker, ticker, folder='default', dpi=150, pad_bars=8):

    if df_ticker.empty or len(df_ticker) < 2:
        print(f"{ticker}: dilewati saat plotting, data terlalu sedikit.")
        return False

    BLUE = "#2196F3"
    RED = "#F23645"
    GREEN = "#4CAF50"

    def add_line(apds, col, **kwargs):
        if df_ticker[col].notna().any():
            apds.append(mpf.make_addplot(df_ticker[col], **kwargs))
        else:
            print(f"{ticker}: {col} dilewati (semua NaN, periode > jumlah baris {len(df_ticker)}).")

    def add_marker(apds, mask_col, price_col, color, size=45):
        m = np.where(df_ticker[mask_col], df_ticker[price_col], np.nan)
        if not np.all(np.isnan(m)):
            apds.append(mpf.make_addplot(m, type="scatter", markersize=size, marker="o", color=color))

    apds = []

    # Channel entry (biru tipis) & trend line (merah)
    add_line(apds, "Upper", color=BLUE, width=0.5)
    add_line(apds, "Lower", color=BLUE, width=0.5)
    add_line(apds, "TrendLine", color=RED, width=0.5)

    # Exit line sebagai titik-titik kecil (style=6 di Pine)
    if df_ticker["ExitLine"].notna().any():
        apds.append(mpf.make_addplot(df_ticker["ExitLine"], type="scatter",
                                     markersize=6, marker="o", color=BLUE))

    # Marker entry/exit diletakkan di level channel, seperti di TradingView
    add_marker(apds, "LongEntry", "Lower", GREEN)
    add_marker(apds, "ShortEntry", "Upper", RED)
    add_marker(apds, "LongExit", "Upper", BLUE, size=15)
    add_marker(apds, "ShortExit", "Lower", BLUE, size=15)

    # Highlighter
    fills = []
    long_zone = (df_ticker["Pos"] == 1).values
    short_zone = (df_ticker["Pos"] == -1).values
    if long_zone.any():
        fills.append(dict(y1=df_ticker["Upper"].values, y2=df_ticker["ExitLine"].values,
                          where=long_zone, alpha=0.12, color="green"))
    if short_zone.any():
        fills.append(dict(y1=df_ticker["Lower"].values, y2=df_ticker["ExitLine"].values,
                          where=short_zone, alpha=0.12, color="red"))

    # Style: candle hitam-putih, latar putih, tanpa grid
    mc = mpf.make_marketcolors(up="white", down="black", edge="black",
                               wick="black", volume="black")
    style = mpf.make_mpf_style(marketcolors=mc, facecolor="white", figcolor="white",
                               gridstyle="", edgecolor="white")

    os.makedirs(f"image/{folder}", exist_ok=True)
    filename = f"image/{folder}/turtle_{ticker}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"

    plot_kwargs = dict(
        type="candle",
        style=style,
        addplot=apds,
        volume=False,
        axisoff=True,
        figsize=(10.44, 5.33),
        tight_layout=True,
        returnfig=True,               # wajib agar mpf.plot mengembalikan (fig, axes)
    )                                 # savefig dihapus, disimpan manual di bawah
    if fills:
        plot_kwargs["fill_between"] = fills

    fig, axes = mpf.plot(df_ticker, **plot_kwargs)

    # Ruang kosong di sisi kanan (dalam jumlah bar)
    left, right = axes[0].get_xlim()
    axes[0].set_xlim(left, right + pad_bars)

    # Judul di pojok kiri atas area chart
    axes[0].text(0.01, 0.98, f"{ticker} · 1D",
                 transform=axes[0].transAxes,
                 fontsize=14, fontweight="bold",
                 va="top", ha="left", color="black")

    fig.savefig(filename, dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return True
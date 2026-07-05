"""
UT Bot MA - Multi Ticker Edition
Konversi dari Pine Script v4, terintegrasi dengan workflow multi-ticker
(fetch -> reshape long format -> resample opsional -> UT Bot per ticker -> plot).
"""

import numpy as np
import pandas as pd
import yfinance as yf
import mplfinance as mpf


# ============================================================
# 1. MOVING AVERAGE FUNCTIONS (setara getMA() di Pine)
# ============================================================

def sma(series, period):
    return series.rolling(period).mean()


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def wma(series, period):
    weights = np.arange(1, period + 1)

    def _wma(x):
        return np.dot(x, weights) / weights.sum()

    return series.rolling(period).apply(_wma, raw=True)


def vwma(price, volume, period):
    return (price * volume).rolling(period).sum() / volume.rolling(period).sum()


def smma(series, period):
    return series.ewm(alpha=1 / period, adjust=False).mean()


def dema(series, period):
    e1 = ema(series, period)
    e2 = ema(e1, period)
    return 2 * e1 - e2


def tema(series, period):
    e1 = ema(series, period)
    e2 = ema(e1, period)
    e3 = ema(e2, period)
    return 3 * e1 - 3 * e2 + e3


def hma(series, period):
    half = int(period / 2)
    sqrt_p = int(round(np.sqrt(period)))
    return wma(2 * wma(series, half) - wma(series, period), sqrt_p)


def lsma(series, period):
    def _linreg(x):
        x_idx = np.arange(len(x))
        slope, intercept = np.polyfit(x_idx, x, 1)
        return intercept + slope * (len(x) - 1)

    return series.rolling(period).apply(_linreg, raw=True)


def get_price(df, price_type):
    price_type = price_type.lower()
    if price_type == "open":
        return df["Open"]
    if price_type == "high":
        return df["High"]
    if price_type == "low":
        return df["Low"]
    if price_type == "hl2":
        return (df["High"] + df["Low"]) / 2
    if price_type == "hlc3":
        return (df["High"] + df["Low"] + df["Close"]) / 3
    if price_type == "ohlc4":
        return (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    return df["Close"]


def get_ma(df, method, price_type, period):
    src = get_price(df, price_type)
    method = method.upper()
    fn_map = {
        "SMA": lambda: sma(src, period),
        "EMA": lambda: ema(src, period),
        "WMA": lambda: wma(src, period),
        "VWMA": lambda: vwma(src, df["Volume"], period),
        "SMMA": lambda: smma(src, period),
        "DEMA": lambda: dema(src, period),
        "TEMA": lambda: tema(src, period),
        "HMA": lambda: hma(src, period),
        "LSMA": lambda: lsma(src, period),
    }
    return fn_map.get(method, fn_map["SMA"])()


# ============================================================
# 2. ATR (Wilder)
# ============================================================

def atr_wilder(df, period):
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


# ============================================================
# 3. UT BOT CORE LOGIC (per satu ticker / satu dataframe OHLCV)
# ============================================================

def ut_bot(df, key_value=1, atr_period=10):
    df = df.copy()
    src = df["Close"].values
    n = len(src)

    xatr = atr_wilder(df, atr_period).values
    nloss = key_value * xatr

    stop = np.zeros(n)
    pos = np.zeros(n)

    for i in range(n):
        if i == 0 or np.isnan(nloss[i]):
            stop[i] = src[i]
            continue

        prev_stop = stop[i - 1]
        prev_src = src[i - 1]

        if src[i] > prev_stop and prev_src > prev_stop:
            stop[i] = max(prev_stop, src[i] - nloss[i])
        elif src[i] < prev_stop and prev_src < prev_stop:
            stop[i] = min(prev_stop, src[i] + nloss[i])
        elif src[i] > prev_stop:
            stop[i] = src[i] - nloss[i]
        else:
            stop[i] = src[i] + nloss[i]

        if prev_src < prev_stop and src[i] > stop[i]:
            pos[i] = 1
        elif prev_src > prev_stop and src[i] < stop[i]:
            pos[i] = -1
        else:
            pos[i] = pos[i - 1]

    df["ATR_Stop"] = stop
    df["Pos"] = pos

    prev_src = df["Close"].shift(1)
    prev_stop = df["ATR_Stop"].shift(1)

    df["Buy"] = (prev_src <= prev_stop) & (df["Close"] > df["ATR_Stop"])
    df["Sell"] = (prev_src >= prev_stop) & (df["Close"] < df["ATR_Stop"])

    return df


# ============================================================
# 4. FETCH MULTI-TICKER -> RESHAPE LONG FORMAT
#    (mengikuti workflow yang sudah dibahas sebelumnya)
# ============================================================

TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA"]
PERIOD = "6mo"
INTERVAL = "1d"          # ambil harian dulu, resample manual kalau perlu mingguan
RESAMPLE_WEEKLY = True   # set True kalau mau agregasi ke mingguan (W-FRI)

# Parameter UT Bot & MA (samakan dengan default Pine Script)
KEY_VALUE = 1
ATR_PERIOD = 10
MA1_METHOD, MA1_PRICE, MA1_PERIOD = "SMA", "high", 20
MA2_METHOD, MA2_PRICE, MA2_PERIOD = "SMA", "low", 20

raw = yf.download(TICKERS, interval=INTERVAL, period=PERIOD,
                   group_by="ticker", auto_adjust=False)

long_df = raw.stack(level=0, future_stack=True).reset_index()
long_df = long_df.rename(columns={"level_1": "Ticker"})
long_df = long_df.set_index("Date")

if RESAMPLE_WEEKLY:
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

print(long_df.head())

# ============================================================
# 5. TERAPKAN UT BOT + MA PER TICKER
# ============================================================

results = {}  # simpan dataframe hasil olahan per ticker

for ticker in TICKERS:
    df_ticker = long_df[long_df["Ticker"] == ticker].drop(columns=["Ticker"]).sort_index()
    df_ticker = df_ticker.dropna(subset=["Close"])

    if df_ticker.empty:
        print(f"{ticker}: dilewati, tidak ada data setelah cleaning.")
        continue

    df_ticker = ut_bot(df_ticker, key_value=KEY_VALUE, atr_period=ATR_PERIOD)
    df_ticker["MA1"] = get_ma(df_ticker, MA1_METHOD, MA1_PRICE, MA1_PERIOD)
    df_ticker["MA2"] = get_ma(df_ticker, MA2_METHOD, MA2_PRICE, MA2_PERIOD)

    results[ticker] = df_ticker

    n_buy = int(df_ticker["Buy"].sum())
    n_sell = int(df_ticker["Sell"].sum())
    last_signal = "BUY" if df_ticker["Buy"].iloc[-1] else "SELL" if df_ticker["Sell"].iloc[-1] else "-"
    print(f"{ticker}: {n_buy} buy signal, {n_sell} sell signal | sinyal candle terakhir: {last_signal}")


# ============================================================
# 6. PLOT PER TICKER (candlestick + MA + marker buy/sell)
# ============================================================

for ticker, df_ticker in results.items():
    if df_ticker.empty or len(df_ticker) < 2:
        print(f"{ticker}: dilewati saat plotting, data terlalu sedikit.")
        continue

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

    mpf.plot(
        df_ticker,
        type="candle",
        style="yahoo",
        addplot=apds,
        volume=True,
        title=f"{ticker} - UT Bot MA ({'Weekly' if RESAMPLE_WEEKLY else INTERVAL})",
        figsize=(14, 8),
        savefig=f"./ut_bot_{ticker}.png"
    )

print("\nSelesai. Chart tersimpan per ticker di folder outputs.")


# ============================================================
# 7. (OPSIONAL) GABUNGKAN SEMUA HASIL JADI SATU DATAFRAME LONG
#    - berguna untuk screening sinyal terbaru di semua ticker sekaligus
# ============================================================

all_signals = []
for ticker, df_ticker in results.items():
    tmp = df_ticker[["Close", "ATR_Stop", "Buy", "Sell"]].copy()
    tmp["Ticker"] = ticker
    all_signals.append(tmp)

signal_summary = pd.concat(all_signals).reset_index()
latest_signals = signal_summary.sort_values("Date").groupby("Ticker").tail(1)
print("\nSinyal terakhir per ticker:")
print(latest_signals[["Ticker", "Date", "Close", "Buy", "Sell"]])
import numpy as np
import pandas as pd
import yfinance as yf


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


def applied_utbot(df, ticker, key_value=1, atr_period=10, ma1_method="SMA", ma1_price="high", ma1_period=20, ma2_method="SMA", ma2_price="low", ma2_period=20):
    df_ticker = df[df["Ticker"] == ticker].drop(columns=["Ticker"]).sort_index()
    df_ticker = df_ticker.dropna(subset=["Close"])

    if df_ticker.empty:
        print(f"{ticker}: dilewati, tidak ada data setelah cleaning.")
        return False

    df_ticker = ut_bot(df_ticker, key_value=key_value, atr_period=atr_period)
    df_ticker["MA1"] = get_ma(df_ticker, ma1_method, ma1_price, ma1_period)
    df_ticker["MA2"] = get_ma(df_ticker, ma2_method, ma2_price, ma2_period)

    # results[ticker] = df_ticker

    n_buy = int(df_ticker["Buy"].sum())
    n_sell = int(df_ticker["Sell"].sum())
    last_signal = "BUY" if df_ticker["Buy"].iloc[-1] else "SELL" if df_ticker["Sell"].iloc[-1] else "-"
    print(f"{ticker}: {n_buy} buy signal, {n_sell} sell signal | sinyal candle terakhir: {last_signal}")

    return df_ticker

# ============================================================
# TURTLE TRADE CHANNELS (per satu ticker / satu dataframe OHLCV)
# ============================================================
import numpy as np
import pandas as pd

BIG = 10**9  # penanda "belum pernah terjadi" (pengganti na pada barssince)


def barssince(cond):
    """Jumlah bar sejak kondisi terakhir True (0 = bar ini). BIG jika belum pernah."""
    cond = np.asarray(cond, dtype=bool)
    out = np.full(len(cond), BIG, dtype=np.int64)
    last = -1
    for i in range(len(cond)):
        if cond[i]:
            last = i
        if last >= 0:
            out[i] = i - last
    return out


def crossover(a, b):
    """Pine crossover(a, b): a > b sekarang dan a <= b di bar sebelumnya."""
    return (a > b) & (a.shift(1) <= b.shift(1))


def turtle(df, length=20, len2=10):
    df = df.copy()
    high, low, close = df["High"], df["Low"], df["Close"]

    # Channel (Pine: highest/lowest = rolling termasuk bar saat ini)
    upper = high.rolling(length).max()
    lower = low.rolling(length).min()
    sup = high.rolling(len2).max()
    sdown = low.rolling(len2).min()

    # Trend Line (K1) & Exit Line (K2)
    bs_hi = barssince(high >= upper.shift(1))
    bs_lo = barssince(low <= lower.shift(1))
    long_regime = (bs_hi <= bs_lo) & (bs_hi < BIG)

    df["Upper"] = upper
    df["Lower"] = lower
    df["TrendLine"] = np.where(long_regime, lower, upper)
    df["ExitLine"] = np.where(long_regime, sdown, sup)

    # Raw signals
    u1, l1 = upper.shift(1), lower.shift(1)
    sd1, su1 = sdown.shift(1), sup.shift(1)

    buy_sig = (high == u1) | crossover(high, u1)
    sell_sig = (low == l1) | crossover(l1, low)
    buy_exit = (low == sd1) | crossover(sd1, low)
    sell_exit = (high == su1) | crossover(high, su1)

    O1 = barssince(buy_sig)
    O2 = barssince(sell_sig)
    O3 = barssince(buy_exit)
    O4 = barssince(sell_exit)

    def prev(a):  # a[1]
        return np.concatenate(([BIG], a[:-1]))

    def more_recent(a, b_prev):
        # a < b[1]; jika keduanya belum pernah terjadi, sinyal pertama dibolehkan
        return (a < b_prev) | ((a == BIG) & (b_prev == BIG))

    df["LongEntry"] = buy_sig.values & more_recent(O3, prev(O1))
    df["ShortEntry"] = sell_sig.values & more_recent(O4, prev(O2))
    df["LongExit"] = buy_exit.values & more_recent(O1, prev(O3))
    df["ShortExit"] = sell_exit.values & more_recent(O2, prev(O4))

    # Highlighter: 1 = zona long (hijau), -1 = zona short (merah), 0 = netral
    m1 = np.minimum.reduce([O1, O2, O3])
    m2 = np.minimum.reduce([O1, O2, O4])
    df["Pos"] = np.where((m1 == O1) & (O1 < BIG), 1,
                 np.where((m2 == O2) & (O2 < BIG), -1, 0))

    return df


def applied_turtle(df, ticker, length=20, len2=10, filter_turtle=False):
    df_ticker = df[df["Ticker"] == ticker].sort_index()
    df_ticker = df_ticker.dropna(subset=["Close"])

    if df_ticker.empty:
        print(f"{ticker}: dilewati, tidak ada data setelah cleaning.")
        return pd.DataFrame()

    df_ticker = turtle(df_ticker, length=length, len2=len2)

    n_le = int(df_ticker["LongEntry"].sum())
    n_se = int(df_ticker["ShortEntry"].sum())
    n_lx = int(df_ticker["LongExit"].sum())
    n_sx = int(df_ticker["ShortExit"].sum())

    last = df_ticker.iloc[-1]
    last_signal = ("LONG ENTRY" if last["LongEntry"] else
                   "SHORT ENTRY" if last["ShortEntry"] else
                   "LONG EXIT" if last["LongExit"] else
                   "SHORT EXIT" if last["ShortExit"] else "-")
    print(f"{ticker}: {n_le} long entry, {n_se} short entry, "
          f"{n_lx} long exit, {n_sx} short exit | sinyal candle terakhir: {last_signal}")

    df_ticker = df_ticker.reset_index()
    if filter_turtle:
        return df_ticker if last_signal == "LONG ENTRY" else pd.DataFrame()
    return df_ticker
import indicator as ind
import stock_utils as sp
import numpy as np
import mplfinance as mpf

TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA"]
PERIOD = "6mo"
INTERVAL = "1d"          # ambil harian dulu, resample manual kalau perlu mingguan
RESAMPLE_WEEKLY = True   # set True kalau mau agregasi ke mingguan (W-FRI)

# Parameter UT Bot & MA (samakan dengan default Pine Script)
KEY_VALUE = 1
ATR_PERIOD = 10
MA1_METHOD, MA1_PRICE, MA1_PERIOD = "SMA", "high", 20
MA2_METHOD, MA2_PRICE, MA2_PERIOD = "SMA", "low", 20


df = sp.get_candlestick_chart(TICKERS, interval=INTERVAL, period=PERIOD, resample_weekly=RESAMPLE_WEEKLY)

results = {}  # simpan dataframe hasil olahan per ticker

for ticker in TICKERS:
    results[ticker] = ind.applied_utbot(df, ticker, key_value=KEY_VALUE, atr_period=ATR_PERIOD, 
                                        ma1_method=MA1_METHOD, ma1_price=MA1_PRICE, ma1_period=MA1_PERIOD, 
                                        ma2_method=MA2_METHOD, ma2_price=MA2_PRICE, ma2_period=MA2_PERIOD)

# ============================================================
# 6. PLOT PER TICKER (candlestick + MA + marker buy/sell)
# ============================================================

for ticker, df_ticker in results.items():
    sp.get_chart_image(df_ticker, ticker)
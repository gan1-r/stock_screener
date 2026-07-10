import indicator as ind
import stock_utils as sp
import numpy as np
import mplfinance as mpf
import pandas as pd
from datetime import datetime


# df_all_stock = pd.read_csv("data/all_stock.csv")

TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']  # contoh ticker, bisa diganti sesuai kebutuhan
PERIOD = "5y"
INTERVAL = "1d"          # ambil harian dulu, resample manual kalau perlu mingguan
RESAMPLE_WEEKLY = True   # set True kalau mau agregasi ke mingguan (W-FRI)

# Parameter UT Bot & MA (samakan dengan default Pine Script)
KEY_VALUE = 1
ATR_PERIOD = 10
MA1_METHOD, MA1_PRICE, MA1_PERIOD = "SMA", "high", 20
MA2_METHOD, MA2_PRICE, MA2_PERIOD = "SMA", "low", 20


df = sp.get_candlestick_chart(TICKERS, interval=INTERVAL, period=PERIOD, resample_weekly=RESAMPLE_WEEKLY)

results = pd.DataFrame()  # simpan dataframe hasil olahan per ticker

for ticker in TICKERS:
    _df_utbot = ind.applied_utbot(df, ticker, key_value=KEY_VALUE, atr_period=ATR_PERIOD, 
                                  ma1_method=MA1_METHOD, ma1_price=MA1_PRICE, ma1_period=MA1_PERIOD, 
                                  ma2_method=MA2_METHOD, ma2_price=MA2_PRICE, ma2_period=MA2_PERIOD,
                                  filter_utbot=False)
    results = pd.concat([results, _df_utbot])

# results = results.reset_index()  # pindahkan index Date ke kolom biasa
# results.to_csv(f"../data/results/results_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv", index=False)
# ============================================================
# 6. PLOT PER TICKER (candlestick + MA + marker buy/sell)
# ============================================================

for ticker in results['Ticker'].unique():
    _df_ticker = results[results['Ticker'] == ticker]
    _df_ticker = _df_ticker.set_index("Date")  # pindahkan kolom Date ke index, karena mplfinance expect index sebagai datetime
    sp.get_chart_image(_df_ticker, ticker)
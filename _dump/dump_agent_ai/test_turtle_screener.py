import pandas as pd

from turtle_screener import (
    TurtleConfig,
    add_turtle_indicators,
    load_symbols,
    resample_daily_to_weekly,
)


def make_daily_frame():
    dates = pd.date_range("2026-01-01", periods=25, freq="B")
    close = pd.Series(range(100, 125), index=dates, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 1,
            "High": close + 2,
            "Low": close - 2,
            "Close": close,
            "Adj Close": close,
            "Volume": 1_000,
        },
        index=dates,
    )


def test_weekly_resample_is_built_from_daily_ohlcv():
    daily = make_daily_frame()
    weekly = resample_daily_to_weekly(daily)

    assert len(weekly) == 6
    first_week_dates = daily.index[daily.index <= weekly.index[0]]
    assert weekly.iloc[0]["Open"] == daily.loc[first_week_dates[0], "Open"]
    assert weekly.iloc[0]["High"] == daily.loc[first_week_dates, "High"].max()
    assert weekly.iloc[0]["Low"] == daily.loc[first_week_dates, "Low"].min()
    assert weekly.iloc[0]["Close"] == daily.loc[first_week_dates[-1], "Close"]
    assert weekly.iloc[0]["Volume"] == 2_000


def test_turtle_pine_channels_use_close_entry_and_high_low_exit_channels():
    df = make_daily_frame()
    cfg = TurtleConfig(entry_period=5, exit_period=3, atr_period=3)
    result = add_turtle_indicators(df, cfg)

    assert result.loc[result.index[5], "Upper"] == df["Close"].iloc[1:6].max()
    assert result.loc[result.index[5], "Lower"] == df["Close"].iloc[1:6].min()
    assert result.loc[result.index[5], "Up"] == df["High"].iloc[1:6].max()
    assert result.loc[result.index[5], "Down"] == df["Low"].iloc[1:6].min()
    assert result["Trend_Line"].notna().any()
    assert result["Exit_Line"].notna().any()
    assert result["Buy_Signal"].dtype == bool
    assert result["Sell_Signal"].dtype == bool


def test_signal_candle_parameter_accepts_current_or_h1():
    assert TurtleConfig(signal_candle="current").signal_candle == "current"
    assert TurtleConfig(signal_candle="h-1").signal_candle == "h-1"

    try:
        TurtleConfig(signal_candle="h-2")
    except ValueError:
        pass
    else:
        raise AssertionError("signal_candle selain current/h-1 harus ditolak")


def test_load_symbols_deduplicates_and_removes_empty_symbols(tmp_path):
    path = tmp_path / "all_stock.csv"
    pd.DataFrame({"symbol": ["AAPL", "", "AAPL", None, "MSFT"]}).to_csv(path, index=False)

    assert load_symbols(path) == ["AAPL", "MSFT"]

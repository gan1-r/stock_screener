#!/usr/bin/env python3
"""Scan all symbols in all_stock.csv with a Turtle Trading breakout setup.

Yahoo Finance is queried with daily candles. Weekly candles are always built
locally from those daily candles, so the weekly calculation is not delegated to
Yahoo Finance's weekly interval aggregation.
"""

from __future__ import annotations

import argparse
import logging
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import mplfinance as mpf
import numpy as np
import pandas as pd
import yfinance as yf

LOGGER = logging.getLogger("turtle_screener")


@dataclass(frozen=True)
class TurtleConfig:
    timeframe: str = "daily"
    entry_period: int = 20
    exit_period: int = 10
    atr_period: int = 20
    atr_stop_multiple: float = 2.0
    signal_candle: str = "current"

    def __post_init__(self) -> None:
        if self.timeframe not in {"daily", "weekly"}:
            raise ValueError("timeframe harus daily atau weekly")
        if self.signal_candle not in {"current", "h-1"}:
            raise ValueError("signal_candle harus current atau h-1")
        for name in ("entry_period", "exit_period", "atr_period"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} harus >= 1")
        if self.atr_stop_multiple <= 0:
            raise ValueError("atr_stop_multiple harus > 0")


def load_symbols(csv_path: str | Path) -> list[str]:
    """Read, clean, and de-duplicate symbols while preserving file order."""
    df = pd.read_csv(csv_path, usecols=["symbol"], dtype={"symbol": "string"})
    symbols: list[str] = []
    seen: set[str] = set()
    for value in df["symbol"].dropna():
        symbol = str(value).strip().upper()
        if symbol and symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
    return symbols


def _normalise_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Return a single-ticker OHLCV dataframe with a clean DatetimeIndex."""
    result = df.copy()
    if isinstance(result.columns, pd.MultiIndex):
        levels = [set(map(str, result.columns.get_level_values(i))) for i in range(result.columns.nlevels)]
        price_level = next((i for i, values in enumerate(levels) if {"Open", "High", "Low", "Close", "Volume"}.issubset(values)), None)
        if price_level is not None:
            result.columns = result.columns.get_level_values(price_level)
        else:
            result.columns = [str(col[-1]) for col in result.columns]
    result.columns = [str(col).title() for col in result.columns]
    needed = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in needed if col not in result.columns]
    if missing:
        raise ValueError(f"data OHLCV tidak lengkap: {missing}")
    result = result[needed].apply(pd.to_numeric, errors="coerce").dropna(subset=needed)
    result.index = pd.to_datetime(result.index).tz_localize(None)
    return result[~result.index.duplicated(keep="last")].sort_index()


def resample_daily_to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily OHLCV into Friday-ending weekly candles locally."""
    daily = _normalise_ohlcv(daily)
    return (
        daily.resample("W-FRI", label="right", closed="right")
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna(subset=["Open", "High", "Low", "Close"])
    )


def _atr_wilder(df: pd.DataFrame, period: int) -> pd.Series:
    previous_close = df["Close"].shift(1)
    true_range = pd.concat(
        [df["High"] - df["Low"], (df["High"] - previous_close).abs(), (df["Low"] - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _bars_since(condition: pd.Series) -> pd.Series:
    """Pine-compatible barssince: zero on event, NaN before first event."""
    values: list[float] = []
    count: float | None = None
    for event in condition.fillna(False).astype(bool):
        if event:
            count = 0.0
        elif count is not None:
            count += 1.0
        values.append(np.nan if count is None else count)
    return pd.Series(values, index=condition.index, dtype="float64")


def _crossover(left: pd.Series, right: pd.Series) -> pd.Series:
    """Pine crossover(left, right), without lookahead."""
    return (left > right) & (left.shift(1) <= right.shift(1))


def add_turtle_indicators(df: pd.DataFrame, config: TurtleConfig) -> pd.DataFrame:
    """Replicate the Pine TuTCI Turtle Trade Channels indicator."""
    result = _normalise_ohlcv(df)

    # Pine lowest()/highest() without an explicit source use close.
    result["Lower"] = result["Close"].rolling(config.entry_period, min_periods=config.entry_period).min()
    result["Upper"] = result["Close"].rolling(config.entry_period, min_periods=config.entry_period).max()
    result["Up"] = result["High"].rolling(config.entry_period, min_periods=config.entry_period).max()
    result["Down"] = result["Low"].rolling(config.entry_period, min_periods=config.entry_period).min()
    result["Sup"] = result["High"].rolling(config.exit_period, min_periods=config.exit_period).max()
    result["Sdown"] = result["Low"].rolling(config.exit_period, min_periods=config.exit_period).min()

    since_up_break = _bars_since(result["High"] >= result["Up"].shift(1))
    since_down_break = _bars_since(result["Low"] <= result["Down"].shift(1))
    choose_down = since_up_break <= since_down_break
    both_missing = since_up_break.isna() & since_down_break.isna()

    result["Trend_Line"] = result["Down"].where(choose_down, result["Up"])
    result.loc[both_missing, "Trend_Line"] = np.nan
    result["Exit_Line"] = result["Sdown"].where(choose_down, result["Sup"])
    result.loc[both_missing, "Exit_Line"] = np.nan
    result["K3"] = result["Down"].where(result["Close"] > result["Trend_Line"])
    result["K4"] = result["Up"].where(result["Close"] < result["Trend_Line"])

    upper_previous = result["Upper"].shift(1)
    lower_previous = result["Lower"].shift(1)
    sdown_previous = result["Sdown"].shift(1)
    sup_previous = result["Sup"].shift(1)
    result["Raw_Buy_Signal"] = (result["High"] == upper_previous) | _crossover(result["High"], upper_previous)
    result["Raw_Sell_Signal"] = (result["Low"] == lower_previous) | _crossover(lower_previous, result["Low"])
    result["Raw_Buy_Exit"] = (result["Low"] == sdown_previous) | _crossover(sdown_previous, result["Low"])
    result["Raw_Sell_Exit"] = (result["High"] == sup_previous) | _crossover(result["High"], sup_previous)

    o1 = _bars_since(result["Raw_Buy_Signal"])
    o2 = _bars_since(result["Raw_Sell_Signal"])
    o3 = _bars_since(result["Raw_Buy_Exit"])
    o4 = _bars_since(result["Raw_Sell_Exit"])
    result["O1"] = o1
    result["O2"] = o2
    result["O3"] = o3
    result["O4"] = o4
    result["Buy_Signal"] = result["Raw_Buy_Signal"] & (o3 < o1.shift(1))
    result["Sell_Signal"] = result["Raw_Sell_Signal"] & (o4 < o2.shift(1))
    result["Buy_Exit"] = result["Raw_Buy_Exit"] & (o1 < o3.shift(1))
    result["Sell_Exit"] = result["Raw_Sell_Exit"] & (o2 < o4.shift(1))
    result["Position"] = np.select(
        [result["Buy_Signal"], result["Sell_Signal"], result["Buy_Exit"] | result["Sell_Exit"]],
        [1, -1, 0],
        default=0,
    )

    # Compatibility aliases retained for existing CSV consumers.
    result["Entry_High"] = upper_previous
    result["Exit_Low"] = lower_previous
    result["ATR"] = _atr_wilder(result, config.atr_period)
    result["ATR_Stop"] = result["Close"] - config.atr_stop_multiple * result["ATR"]
    return result


def _download_batch(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    """Download daily data for a batch and split yfinance's MultiIndex result."""
    raw = yf.download(
        tickers=symbols,
        period=period,
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    if raw.empty:
        return {}
    output: dict[str, pd.DataFrame] = {}
    if len(symbols) == 1:
        try:
            output[symbols[0]] = _normalise_ohlcv(raw)
        except ValueError:
            pass
        return output
    if not isinstance(raw.columns, pd.MultiIndex):
        return output
    first_level = set(raw.columns.get_level_values(0))
    for symbol in symbols:
        if symbol not in first_level:
            continue
        try:
            output[symbol] = _normalise_ohlcv(raw[symbol])
        except (KeyError, ValueError):
            LOGGER.warning("%s: data OHLCV tidak valid", symbol)
    return output


def _safe_filename(symbol: str) -> str:
    return "".join(char if char.isalnum() or char in {".", "-", "_"} else "_" for char in symbol)


def plot_turtle_chart(df: pd.DataFrame, symbol: str, output_path: Path, config: TurtleConfig) -> None:
    """Save a TuTCI-style chart with channels, fills, and entry/exit markers."""
    data = df.tail(250).copy()
    data.index.name = "Date"
    long_entry = np.where(data["Buy_Signal"], data["Down"], np.nan)
    short_entry = np.where(data["Sell_Signal"], data["Up"], np.nan)
    long_exit = np.where(data["Buy_Exit"], data["Up"], np.nan)
    short_exit = np.where(data["Sell_Exit"], data["Down"], np.nan)
    addplots = [
        mpf.make_addplot(data["Upper"], color="#0094FF", width=1.0),
        mpf.make_addplot(data["Lower"], color="#0094FF", width=1.0),
        mpf.make_addplot(data["Trend_Line"], color="red", width=2.0),
        mpf.make_addplot(data["Exit_Line"], color="blue", width=1.0, linestyle="dashed"),
    ]
    marker_specs = [
        (long_entry, "^", "green"),
        (short_entry, "v", "red"),
        (long_exit, "v", "#1976d2"),
        (short_exit, "^", "#1976d2"),
    ]
    for values, marker, color in marker_specs:
        if not np.isnan(values).all():
            addplots.append(mpf.make_addplot(values, type="scatter", marker=marker, markersize=75, color=color))

    latest = data.iloc[-1] if config.signal_candle == "current" else data.iloc[-2]
    last_signal = (
        "LONG ENTRY" if bool(latest["Buy_Signal"])
        else "SHORT ENTRY" if bool(latest["Sell_Signal"])
        else "EXIT LONG" if bool(latest["Buy_Exit"])
        else "EXIT SHORT" if bool(latest["Sell_Exit"])
        else "-"
    )
    title = f"{symbol} | TuTCI {config.timeframe} | signal={config.signal_candle} | last={last_signal}"
    fig, axes = mpf.plot(
        data[["Open", "High", "Low", "Close", "Volume"]],
        type="candle",
        style="yahoo",
        addplot=addplots,
        volume=True,
        title=title,
        ylabel="Price",
        figsize=(15, 9),
        tight_layout=True,
        returnfig=True,
    )
    price_axis = axes[0]
    x = np.arange(len(data))
    color1 = data[["O1", "O2", "O3"]].min(axis=1).eq(data["O1"])
    color2 = data[["O1", "O2", "O4"]].min(axis=1).eq(data["O2"])
    price_axis.fill_between(x, data["Upper"].to_numpy(float), data["Exit_Line"].to_numpy(float), where=color1.to_numpy(bool), color="green", alpha=0.10, interpolate=True)
    price_axis.fill_between(x, data["Lower"].to_numpy(float), data["Exit_Line"].to_numpy(float), where=color2.to_numpy(bool), color="red", alpha=0.10, interpolate=True)
    fig.savefig(output_path, dpi=140, bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)


def scan(
    input_csv: str | Path,
    output_root: str | Path,
    config: TurtleConfig,
    period: str = "2y",
    batch_size: int = 50,
    delay_seconds: float = 0.0,
    only_buy: bool = False,
) -> Path:
    symbols = load_symbols(input_csv)
    if not symbols:
        raise ValueError("Tidak ada symbol pada file input")
    run_id = datetime.now().strftime("turtle_%Y%m%d_%H%M%S")
    run_dir = Path(output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    summaries: list[dict[str, object]] = []
    for start in range(0, len(symbols), batch_size):
        batch = symbols[start : start + batch_size]
        try:
            prices = _download_batch(batch, period)
        except Exception as exc:  # one failed batch must not discard the whole scan
            LOGGER.exception("Batch %s gagal: %s", batch[0], exc)
            prices = {}
        for symbol in batch:
            try:
                daily = prices.get(symbol)
                if daily is None or daily.empty:
                    raise ValueError("tidak ada data Yahoo Finance")
                candles = resample_daily_to_weekly(daily) if config.timeframe == "weekly" else daily
                result = add_turtle_indicators(candles, config)
                if result.empty:
                    raise ValueError("data kosong setelah indikator")
                if len(result) < (2 if config.signal_candle == "h-1" else 1):
                    raise ValueError("data tidak cukup untuk signal_candle yang dipilih")
                signal_row = result.iloc[-1] if config.signal_candle == "current" else result.iloc[-2]
                buy = bool(signal_row["Buy_Signal"])
                sell = bool(signal_row["Sell_Signal"])
                summary = {
                    "Ticker": symbol,
                    "Date": result.index[-1 if config.signal_candle == "current" else -2].date().isoformat(),
                    "Signal_Candle": config.signal_candle,
                    "Close": float(signal_row["Close"]),
                    "Entry_High": float(signal_row["Entry_High"]) if pd.notna(signal_row["Entry_High"]) else math.nan,
                    "Exit_Low": float(signal_row["Exit_Low"]) if pd.notna(signal_row["Exit_Low"]) else math.nan,
                    "ATR": float(signal_row["ATR"]) if pd.notna(signal_row["ATR"]) else math.nan,
                    "Buy_Signal": buy,
                    "Sell_Signal": sell,
                    "Buy_Exit": bool(signal_row["Buy_Exit"]),
                    "Sell_Exit": bool(signal_row["Sell_Exit"]),
                    "Bars": len(result),
                    "Error": "",
                }
                summaries.append(summary)
                if not only_buy or buy:
                    plot_turtle_chart(result, symbol, run_dir / f"turtle_{_safe_filename(symbol)}.png", config)
            except Exception as exc:  # continue scanning the remaining symbols
                LOGGER.warning("%s dilewati: %s", symbol, exc)
                summaries.append({"Ticker": symbol, "Error": str(exc)})
        if delay_seconds:
            time.sleep(delay_seconds)
    summary_path = run_dir / "scan_results.csv"
    pd.DataFrame(summaries).to_csv(summary_path, index=False)
    (run_dir / "config.json").write_text(pd.Series({**asdict(config), "period": period}).to_json(indent=2), encoding="utf-8")
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/all_stock.csv", help="CSV dengan kolom symbol")
    parser.add_argument("--output-root", default="image", help="folder induk output")
    parser.add_argument("--timeframe", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--period", default="2y", help="periode Yahoo Finance, contoh 1y, 2y, 5y, max")
    parser.add_argument("--entry-period", type=int, default=20, help="Donchian entry lookback")
    parser.add_argument("--exit-period", type=int, default=10, help="Donchian exit lookback")
    parser.add_argument("--atr-period", type=int, default=20, help="periode Wilder ATR")
    parser.add_argument("--atr-stop-multiple", type=float, default=2.0, help="jarak ATR stop")
    parser.add_argument("--signal-candle", choices=["current", "h-1"], default="current", help="candle yang dipakai untuk status sinyal")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--delay", type=float, default=0.0, help="delay antar batch dalam detik")
    parser.add_argument("--only-buy", action="store_true", help="simpan chart hanya jika candle sinyal menghasilkan BUY")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    config = TurtleConfig(
        timeframe=args.timeframe,
        entry_period=args.entry_period,
        exit_period=args.exit_period,
        atr_period=args.atr_period,
        atr_stop_multiple=args.atr_stop_multiple,
        signal_candle=args.signal_candle,
    )
    run_dir = scan(args.input, args.output_root, config, args.period, args.batch_size, args.delay, args.only_buy)
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

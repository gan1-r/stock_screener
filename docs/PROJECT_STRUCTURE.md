# Stock Screener Project

A Python project for screening and analyzing stocks using technical indicators and candlestick charting.

## Project Structure

```
stock_screener/
├── src/                          # Main source code
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # Main entry point
│   ├── indicator.py             # Technical indicators (SMA, EMA, ATR, etc.)
│   ├── stock_utils.py           # Stock utility functions
│   └── scrapping_stocks.py      # Web scraping utilities
│
├── tests/                        # Unit tests
│   ├── __init__.py
│   └── test.py                  # Test file
│
├── scripts/                      # Experimental/utility scripts
│   ├── exp_price_stock.py
│   └── stock_price.py
│
├── data/                         # Data directory
│   ├── raw/                     # Input data (CSV files)
│   │   ├── all_stock.csv
│   │   └── all_etf.csv
│   └── results/                 # Output results
│       └── results_*.csv
│
├── images/                       # Generated charts and visualizations
│   └── ut_bot_*.png
│
├── docs/                         # Documentation
│   ├── README.md
│   └── notes.txt
│
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore file
└── This README
```

## Running the Project

### Prerequisites
- Python 3.7+
- See `requirements.txt` for dependencies

### Installation
```bash
pip install -r requirements.txt
```

### Running Main Script
```bash
cd src
python main.py
```

### Running Tests
```bash
python -m pytest tests/
```

## Key Modules

### `indicator.py`
Contains technical indicator functions:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- WMA, VWMA, SMMA
- DEMA, TEMA, HMA, LSMA
- ATR (Average True Range)
- UT Bot MA strategy

### `stock_utils.py`
Utility functions:
- `get_candlestick_chart()` - Download and prepare price data
- `get_chart_image()` - Generate trading charts with indicators

### `scrapping_stocks.py`
Web scraping utilities for fetching stock data

## Configuration

Main script configuration in `src/main.py`:
- `TICKERS` - Stock symbols to analyze
- `PERIOD` - Historical period (e.g., "5y", "1mo")
- `INTERVAL` - Data interval (e.g., "1d", "1h")
- `RESAMPLE_WEEKLY` - Aggregate to weekly data
- `MA1_PERIOD`, `MA2_PERIOD` - Moving average periods
- `ATR_PERIOD` - ATR calculation period

## Notes
- Image output path: `images/`
- CSV results output path: `data/results/`
- Raw input data: `data/raw/`

## References
- Technical Indicators: Pine Script UT Bot MA strategy
- Data Source: yfinance


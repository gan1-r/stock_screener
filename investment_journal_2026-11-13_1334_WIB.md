# Investment Journal — 2026-11-13 13:34 WIB

## Session metadata
- Analysis ID: IJ-20261113-1334-WIB
- Methodology: Turtle Screener (script defaults; no script changes)
- Scan command: `venv/bin/python turtle_screener.py --only-buy --verbose`
- Scan output: `image/turtle_20261113_132758/`
- Config: daily candles; 20-bar entry channel; 10-bar exit channel; Wilder ATR(20); 2-year Yahoo Finance period; `signal_candle=current`; `--only-buy` restricts chart generation, not CSV rows.
- Scan result: 981 input tickers, 976 valid rows, 5 data errors, 8 Buy_Signal=True.
- Signal date: 2026-11-12 (last completed US regular session available at scan time).

## Screen-positive snapshots (Yahoo scan; USD)
Ticker,Close,Entry_High,ATR
AMD,585.30,578.44,36.9642
RTX,198.36,203.82,5.1404
CSX,52.40,52.27,1.1306
CEG,282.40,276.09,13.3354
SWKS,90.03,89.43,4.2926
VIG,251.80,252.70,2.6134
SCHD,35.93,36.21,0.4202
AMDY,46.24,45.92,2.8242

## Current portfolio snapshot (Pluang, USD)
- Holding: VTRS, 81.2736 shares; average cost $17.83; market value $1,680.74; unrealized P/L +$231.63 (+15.98%). Position query: sellable quantity 81.2736; pending sell 0.
- U.S. stock buying power: $2,021.46; USD cash balance $2,021.47.
- Latest reference mid at retrieval: VTRS $20.68; market closed regular session, overnight market open. This is not an execution quote.
- Most recent transaction history includes VTRS sell market order for 81.2736 marked Cancelled (2026-11-13T04:57:41Z); no VTRS order marked open in returned 20 rows. History is partial (20 of 68 total).

## Candidate review and current decision status
- No numeric fundamental/technical/combined scores assigned: requested growth, cash-flow, peer, and indicator inputs are incomplete for a comparable, auditable score across all eight; ETF fundamentals are not returned by Pluang's stock fundamentals feed.
- No new buy order recommended or executed in this journal entry. The scan signal is a screen, not itself a trade approval.
- Working interpretation: favor further confirmation in CSX and CEG; monitor AMD; avoid chasing SWKS pending post-Qorvo integration review; RTX lacks a close above its scan entry threshold. VIG, SCHD, AMDY are ETFs, not operating-company stocks, and have no standard company financial ratios.
- Existing VTRS position: HOLD / do not add pending review; reason: still profitable and moving averages/price trend positive, but reported negative net income and overbought short-term oscillators create mixed evidence. This is a proposed review stance, not an order.

## Status / limits
- No purchases or sales executed. Proposed recommendation status: PROPOSED/monitor only.
- Historical accuracy, trade outcomes, realized P/L, and portfolio performance cannot yet be calculated because this journal is the first saved snapshot and the prior trade/benchmark series is incomplete.
- Persistent journal established as an append-only dated Markdown snapshot; no pre-existing journal database/export was found in the project search. Preserve this file and create a new dated file for subsequent sessions; do not overwrite.
- Source data is time-sensitive. Refresh prices and portfolio before any future action.

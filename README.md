# AUDNZD H1 trading strategy — portable package

## Run
Python 3.10 or later. Install dependencies, then run from this folder:

```sh
python -m pip install -r requirements.txt
python audnzd_strategy.py
python audnzd_strategy.py --filter SMA --exit MA --cost-bps 0
python audnzd_strategy.py --filter SMA --exit 4 --cost-bps 2
```

Default: the latest revised ten 8-bar filters, MA exit, 2 bp round-trip cost. ALLAVERAGES_JMA is excluded from that selection and MCGINLEY replaces it, matching the prior request. Other saved filters can be selected by name. Output: results/summary.csv and results/trades.csv. No downloads or original Windows paths are required by audnzd_strategy.py.

## Data and rules
- data/AUDNZD_H1.csv: original on-disk bid H1 OHLC data, including available earlier history for ATR initialization, through November 1, 2026. UTC timestamps label bar OPEN time. All observed bars are accepted.
- data/saved_filters_window8.csv: all 34 previously computed 8-bar filters, exported at full floating-point precision. These are reused, not recalculated. The legacy filter timestamps have been corrected before export.
- Test signals begin April 1, 2021; April 2020 onward supplies trailing training history. At each month start, estimate signed price-minus-filter 10th/90th percentiles from the preceding year, with at least 3,000 valid observations. Buy negative deviations below the lower threshold; sell positive deviations above the upper threshold.
- Signal-bar opening labels must be Tuesday, Wednesday or Thursday, 17–21 UTC inclusive. Enter at the next actual consecutive hourly open, after the signal close is known. One trade at a time.
- Fixed stop = 2 × ATR(20) at entry; here ATR is the SIMPLE rolling mean of true range, matching the original AUDNZD engine (not the Wilder ATR used in the later 28-pair experiment).
- Start at 10,000 NZD. Risk 2% of current equity before costs: units AUD = 0.02 × equity NZD / stop distance. This is a quote-currency account, not USD. No leverage or margin cap.
- MA exit: target updates from the previous observed completed bar's saved filter. Stop wins if both stop and target are touched in a bar. Gaps through stops fill at the open. Alternative exits are 1, 2, 4 or 12 elapsed hours, at the next available open at/after the deadline.
- Cost matches the historical AUDNZD report: a single round-trip deduction of cost_bps/10,000 × ENTRY price × units, at exit. Thus 2 bp is not 2 pips. This differs from the later 28-pair engine's separate entry/exit-notional cost calculation.

Gross columns in summary.csv are the original engine statistics; net columns are explicitly prefixed net_. Drawdown in this runner is CLOSED-TRADE drawdown, not the marked-to-market drawdown in the archived reference statistics. No financing or additional slippage. Historical ranking is in sample.

## Source and reference results
audnzd_strategy.py is the portable adaptation. original_source/ contains the unmodified historical engine and reporting scripts, including strategy_test.py. Those archival scripts retain old local paths and are supplied for inspection; use the portable runner above. The original engine also searched lengths 6–100. This ZIP intentionally includes the latest window-8 filters only, not the entire multi-gigabyte filter library.

reference_results/ contains the latest revised table, ordering, plot and methodology. A separate reproduction check records whether the portable runner matches the archived final equities and trade counts. Price CSV is exported from the original disk archive, not the earlier chat attachment. SHA256SUMS.json records bundled-file hashes.

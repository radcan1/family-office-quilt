# Spec: valuations and backtest (November 2026)

Two additions to the monthly read.

1. **Valuations.** Is each major equity market cheap or expensive against its own history?
2. **Backtest.** Would the dashboard's signals have helped in the past?

Market data only. Nothing here reads `private/` or family holdings.

---

## Part 1: Valuations (`valuation.py`)

### Questions it answers
- For each major market, where does today's trailing P/E sit in its own history?
- Do shares or government bonds pay more right now? This uses the earnings yield minus the local 10-year yield.
- Within India, which sectors are cheap or expensive against their own history?

### Markets and sources

| Id | Market | P/E history | Cross-check | 10Y yield for the gap |
|---|---|---|---|---|
| IN_LARGE | Nifty 50 | NSE Indices, daily, from 2005 | MSCI India ETF (INDA), worldperatio and Yahoo | India 10Y (monthly, from 2011) |
| IN_MID | Nifty Midcap 150 | NSE Indices, from 2017 | none | India 10Y |
| IN_SMALL | Nifty Smallcap 250 | NSE Indices | none | India 10Y |
| US_LARGE | S&P 500 | worldperatio (SPY), monthly from 1990s | Yahoo SPY today; Shiller S&P 500 P/E to 2024 | US 10Y |
| US_TECH | Nasdaq 100 | worldperatio (QQQ) | Yahoo QQQ | US 10Y |
| GL_CN_LARGE | China large caps | worldperatio (FXI) | Yahoo FXI | China 10Y (from 2020) |
| GL_HK | Hong Kong | worldperatio (EWH) | Yahoo EWH | US 10Y (HKD is pegged) |
| GL_JP | Japan | worldperatio (EWJ) | Yahoo EWJ | Japan 10Y |
| GL_KR | Korea | worldperatio (EWY) | Yahoo EWY | none |
| GL_TW | Taiwan | worldperatio (EWT) | Yahoo EWT | none |
| GL_DE | Germany | worldperatio (EWG) | Yahoo EWG | Germany 10Y |
| GL_UK | UK | worldperatio (EWU) | Yahoo EWU | UK 10Y |
| EM | Emerging markets | worldperatio (EEM) | Yahoo EEM | none |
| GL_EZ, GL_CN_TECH, GL_CN_A | Euro area, China tech, China A-shares | Yahoo, today's value only; history builds month by month | none | Germany 10Y for the euro area |

India sectors use NSE Indices daily P/E and P/B for the ten sectors in the sector quilt.

### Method
- **P/E** is trailing 12-month earnings. Forward P/E is not used: it needs analyst forecasts, which are paid data.
- **Percentile** is where this month's P/E sits among month-end readings over the last 20 years, or all available history if shorter.
  - At least 5 years of history is needed; otherwise the percentile is blank and the market is marked "Short history".
- **Label** comes from the percentile:

  | Percentile | Label |
  |---|---|
  | 20 or below | Cheap |
  | 20–40 | Below average |
  | 40–60 | Average |
  | 60–80 | Above average |
  | 80 or above | Expensive |

- **Shares vs bonds gap** = 100 / P/E − the local 10-year yield, in percentage points.
  - A higher gap means shares pay more relative to bonds.
  - The gap also gets its own percentile where the yield history allows.
- **NSE method break.** On 31 March 2021 NSE switched index P/E from standalone to consolidated earnings. The Nifty 50 P/E fell 18% overnight, and the Midcap 150 P/E fell 45%.
  - To keep history comparable, P/E before the break is scaled by each index's own ratio at the break.
  - P/B did not change at the break. It gives an unadjusted check on the P/E reading.
- **Price vs earnings.** For each month, the change in P/E is split into the price move and the implied change in earnings.
  - If P/E moves by more than 15% while the price moves by less than 5%, the figure is flagged as a likely data revision rather than a market move.

### Checks (health gate)
- Every P/E is between 3 and 100. P/B is between 0.3 and 20.
- Each market's latest month is current: the read month or the month to date.
- worldperatio vs Yahoo today agree within 15% for each ETF. Yahoo's ETF P/B is unreliable (it shows SPY near 1.7) and is not used.
- worldperatio's SPY P/E history vs Shiller's S&P 500 P/E: median gap under 15%.
- Nifty 50 P/E percentile and P/B percentile disagree by more than 40 points: WARN, noted in the facts.

### Outputs
- `data/valuation/pe_monthly.csv`: market, month, P/E, P/B, dividend yield, source.
- `data/valuation/valuation.csv`: the latest reading per market, with percentile, label, gap and history start.
- `data/valuation/yahoo_snapshots.csv`: today's Yahoo P/E for every ETF, appended on each run, so history builds up.
- `data/export/valuation.json` for the page.
- Facts under a new "valuation" question in `analysis.py`.

### Not done (known limits)
- **Forward P/E:** no free source.
- **Shiller CAPE:** the free file stopped updating in September 2024.
- **ETF-based P/E** reflects each fund's holdings, which can differ from the headline index. For example, EWH is not the Hang Seng.

---

## Part 2: Backtest (`backtest.py`)

### Rules
- **No look-ahead.** Each signal uses only data available at that month-end, and returns are measured from the next month onward.
- **Overlapping windows** (for example, 12-month returns measured every month) overstate the evidence. Each result reports how many non-overlapping periods it rests on.
- **Results with fewer than 5 independent events** are labelled "too few to judge".
- **Results are descriptive,** not a trading strategy. There are no costs, taxes or leverage.

### Tests

1. **Valuation and later returns.**
   - **Nifty 50** (2005 onward, rupees) and **S&P 500** (1990s onward, dollars): starting P/E percentile vs the next 1-, 3- and 5-year annualised total return. Results are bucketed by percentile, and the correlation is reported.
   - **Across countries:** each month, rank markets by their P/E percentile against their own history. Compare the next-12-month dollar return of the cheapest third with the most expensive third.
2. **Regime gauge.** The same 6 votes as `analysis.py`, rebuilt for each past month from long histories.
   - Votes: copper/gold, equal-weight vs S&P 500, high yield vs Treasuries, US cyclicals vs defensives, and the high-yield spread.
   - The Indian sector vote is included where the data exists.
   - Measured: the next-1- and 3-month returns of the S&P 500, the Nifty 50 in rupees, and a global 60/40 mix, by regime.
3. **Momentum and persistence** (the quilt's premise). Does a top-third 3-month return predict the next month across the world equity markets and asset classes?
   - Measured: hit rate and average spread.
4. **Watchlist alerts.** For each alert with enough history, take the first trigger after at least 3 quiet months. Compare the next-1-, 3- and 6-month Nifty 50 return (and the relevant asset) with the average of all months.
   - Alerts tested:
     - VIX above 30
     - VIX curve inverted
     - US high-yield spread above 4%
     - Yen up 4% in a month
     - Japan 10Y above its threshold
     - China beats India by 10pp over 3 months
     - India–US yield gap below 2pp
     - Brent up 15% in a month
     - Rupee down 2% in a month
     - Foreign selling for 3 months running, where history allows

### Outputs
- `data/backtest/results.json`: every table with sample sizes.
- `data/export/backtest.json` for the page.
- A short plain-language verdict per signal:
  - **Useful:** consistent effect with enough events.
  - **Weak:** effect present but small or inconsistent.
  - **No evidence:** no effect found.
  - **Too few to judge.**

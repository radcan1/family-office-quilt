# Monthly read: questions and rules

Phase two turns the quilt into a monthly read for the investment committee.
The work is split in two so that every sentence can be checked:

1. **Facts (code).** `analysis.py` works out a fixed set of findings for the
   latest completed month and writes them to `data/analysis/facts_<month>.json`.
   Each finding carries its numbers and the rule that produced it.
2. **Memo (written from the facts).** The monthly memo in `memos/<month>.json`
   uses only findings from that file. If a claim isn't in the facts, it isn't
   in the memo.

Everything here is market data. Family office holdings, weights and amounts
never enter this repo; they live in the git-ignored `private/` folder, and
`build_site.py` refuses to publish if a private file is tracked.

## The six questions

### 1. Regime: what is the market rewarding?
Four regime ratios each vote risk-on when rising over three months:
copper/gold, Midcap 150/FMCG, high yield/Treasuries, equal-weight/cap-weight
S&P 500. Two further votes come from defensive versus cyclical sector
leadership (US and India) and from the high-yield spread (narrowing is
risk-on). The label is:

- **Risk-on:** at least 4 of 6 votes risk-on
- **Defensive:** at most 2 of 6 votes risk-on
- **Mixed:** anything else

The memo always names which votes went which way.

### 2. Persistence: which trends are real?
- **Persistent leader or laggard:** in the top 5 or bottom 5 on both the 1-month and 3-month rankings.
- **Leadership turnover:** how many of last month's top 5 are still in the top 5, and the rank correlation between the two months.
- **Biggest movers:** the largest rank changes up and down.

### 3. Divergences: where do the signals disagree?
Each of these is flagged when its condition holds:

- **Equities up, liquidity down:** global equities rose over 3 months while both Fed net liquidity and G3 central-bank assets fell.
- **Equities up, credit worse:** the S&P 500 rose over 3 months while the high-yield spread widened by 0.5pp or more.
- **Equities up, fear up:** the S&P 500 rose this month while the VIX rose 3 points or more.
- **India IT vs global semis:** SMH (in rupees) and Nifty IT differed by 10pp or more this month.
- **Prediction markets moving:** any catalyst outcome repriced 20 points or more in 30 days.

### 4. Currency: how much did the rupee matter?
The USD/INR move this month and over 12 months, and the average gap between
rupee and dollar returns on the dollar assets.

### 5. Risks: what is being priced?
The most likely outcome for each catalyst; any major repricings; any outcome
where Polymarket and Kalshi disagree by more than 10 points; VIX and India
VIX levels and changes; assets stretched beyond ±2 on trend.

### 6. Breadth and dispersion: how broad was the month?
How many of the 19 assets rose and how many beat INR cash; the spread between
best and worst; the cross-asset dispersion against its 12-month median.

## What the memo does not do
- It gives no trade instructions. Its last section lists questions for the committee.
- It doesn't call a finding a signal until a backtest supports it. Until then, findings are observations.
- It never mentions the family's own positions or amounts. That analysis, when added, stays private.

# Family Office Asset Quilt

A monthly multi-asset quilt for an INR-based family office: 19 strategic asset
classes ranked by total return (in rupees and local currency), Indian and US
sector rotation, world equity markets ranked in rupees, currencies against the
rupee, global bond yields, a macro and liquidity backdrop, positioning, and
prediction-market catalysts from Polymarket, cross-checked against Kalshi.

**Live site:** https://radcan1.github.io/family-office-quilt/

## Monthly refresh

```bash
pip install -r requirements.txt
python3 run.py             # fetch and validate every series, plus prediction markets (~1 minute)
python3 positioning.py     # CFTC, NSDL, NSE and options positioning (NSE files fetched politely, cached)
python3 quilt.py           # monthly returns, ranks, Layer 1 indicators
python3 analysis.py        # facts for the latest completed month (and the month before, for changes)
# then, by hand: research the news (memos/<month>_context.json), write the memo
# (memos/<month>.json) and implications (memos/<month>_implications.json) from the facts
python3 export.py          # data files for the page; refreshes the watchlist
python3 build_site.py      # runs checks.py and refuses to publish on any failure
git add -A && git commit -m "Monthly read $(date +%F)" && git push
```

`build_site.py` runs every check in `checks.py` first: freshness of each source,
accuracy cross-checks, positioning ranges, prediction-market staleness, news
sourcing rules, and an audit that every number in the memo and implications
traces back to the computed facts, the sourced news or the watchlist. Any
failure stops the publish. The results appear on the page under "Data health".
Watchlist levels live in `watchlist.json`; edit them freely.

## How it fits together

| File | What it does |
|---|---|
| `registry.py` | Every series: provider, ID, units, return basis, frequency |
| `sources.py` | One fetcher per provider, with caching |
| `catalysts.py` | Polymarket (Gamma + CLOB price history) and Kalshi cross-check |
| `validate.py` | Freshness, total-return basis and cross-source checks |
| `run.py` | Fetches everything, writes `data/daily/` and the quality report |
| `quilt.py` | Monthly returns, ranks, 3-month persistence, trend stretch, Layer 1 |
| `analysis.py` | Facts engine: regime, persistence, divergences, currency, global markets, risks, breadth, positioning |
| `watch.py` / `watchlist.json` | What we track and the levels that trigger attention |
| `checks.py` | The health gate run before every publish |
| `export.py` | Packages the tables as JSON for the page |
| `page/index.html` | The page design (shared with the Claude dashboard version) |
| `build_site.py` | Wraps the page into the standalone site in `docs/` |

## Data sources

All keyless and public:

- **Indian indices:** official total-return series from NSE Indices (niftyindices.com)
- **US and global ETFs, Bitcoin, VIX:** dividend-adjusted prices from Yahoo Finance
- **USD/INR:** the Fed's H.10 noon rate (FRED), with Yahoo for the days since the last print
- **Fed liquidity, US M2, rates:** FRED
- **Global M2:** ECB, Bank of Japan, and PBoC (via akshare)
- **World equity markets:** US-listed country ETFs (CQQQ, FXI, ASHR, EWH, EWJ, EWY, EWT, EWG, FEZ, EWU) from Yahoo, with headline indices (Hang Seng, Nikkei, KOSPI, TAIEX, DAX, Euro Stoxx 50, FTSE 100) alongside; CSI 300 from Sina via akshare
- **Global 10Y yields:** Bundesbank (Germany), Japan Ministry of Finance, Bank of England, ChinaBond (via akshare), FRED (US); each checked against the OECD monthly figure
- **Currencies vs the rupee:** the Fed's H.10 rates (FRED), with Yahoo for the days since the last print; AED from its fixed dollar peg
- **RBI net liquidity:** the RBI's daily Money Market Operations release
- **Catalysts:** Polymarket and Kalshi public APIs

## Known limits

- **RBI net liquidity:** history starts November 2026 and builds up with each run. The RBI has no bulk archive.
- **India 10Y yield and 3M rate:** monthly averages only. There is no free daily feed, so the India–US yield gap uses monthly averages.
- **World markets:** ranked on country ETFs rather than the headline indices, so dividends and currency are treated the same everywhere. Hong Kong's ETF (EWH) holds local companies only, unlike the Hang Seng.
- **India M3:** not yet included.
- **Gold tile:** international gold in INR. Indian gold differs because of import duty and the local premium; the data checks report the gap.

For information and discussion only. Nothing here is investment advice.

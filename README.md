# Family Office Asset Quilt

A monthly multi-asset quilt for an INR-based family office: 19 strategic asset
classes ranked by total return (in rupees and local currency), Indian and US
sector rotation, a macro and liquidity backdrop, and prediction-market
catalysts from Polymarket, cross-checked against Kalshi.

**Live site:** https://radcan1.github.io/family-office-quilt/

## Monthly refresh

```bash
pip install -r requirements.txt
python3 run.py          # fetch and validate every series (~1 minute)
python3 quilt.py        # monthly returns, ranks, Layer 1 indicators
python3 export.py       # data files for the page
python3 build_site.py   # rebuild docs/ for GitHub Pages
git add -A && git commit -m "Data refresh $(date +%F)" && git push
```

Check `data/quality_report_<date>.md` before publishing. Every series is
checked for freshness, total-return basis and agreement across sources.

## How it fits together

| File | What it does |
|---|---|
| `registry.py` | Every series: provider, ID, units, return basis, frequency |
| `sources.py` | One fetcher per provider, with caching |
| `catalysts.py` | Polymarket (Gamma + CLOB price history) and Kalshi cross-check |
| `validate.py` | Freshness, total-return basis and cross-source checks |
| `run.py` | Fetches everything, writes `data/daily/` and the quality report |
| `quilt.py` | Monthly returns, ranks, 3-month persistence, trend stretch, Layer 1 |
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
- **RBI net liquidity:** the RBI's daily Money Market Operations release
- **Catalysts:** Polymarket and Kalshi public APIs

## Known limits

- **RBI net liquidity:** history starts November 2026 and builds up with each run. The RBI has no bulk archive.
- **India 10Y yield and 3M rate:** monthly averages only. There is no free daily feed.
- **India M3:** not yet included.
- **Gold tile:** international gold in INR. Indian gold differs because of import duty and the local premium; the data checks report the gap.

For information and discussion only. Nothing here is investment advice.

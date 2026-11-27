"""
registry.py — the single source of truth for every series the quilt uses.

Each series declares WHERE it comes from, WHAT it measures (basis), its UNITS
and how often it updates. Every downstream number is traceable to one row here.

basis values:
  total_return  — dividends/coupons reinvested; the only basis used for ranking
  price         — price only; kept for cross-checks and moving averages
  level         — an economic level (balance sheet, money stock)
  yield_pct     — a rate in percent
  fx            — an exchange rate
  probability   — a prediction-market price in [0, 1]

scale converts the raw value to the unit named in `units` (raw * scale).
"""

# ── Layer 2: strategic asset classes (ranked) ────────────────────────────────
# Indian total-return indices come from niftyindices.com (NSE Indices Ltd, the
# index owner). US/global series use Yahoo's dividend-adjusted close.
LAYER2 = [
    # id,            name,                         source,   source_id,                      ccy,   basis
    ("IN_LARGE",    "Nifty 50 TRI",               "nifty_tri",  "NIFTY 50",                    "INR", "total_return"),
    ("IN_MID",      "Nifty Midcap 150 TRI",       "nifty_tri",  "NIFTY MIDCAP 150",            "INR", "total_return"),
    ("IN_SMALL",    "Nifty Smallcap 250 TRI",     "nifty_tri",  "NIFTY SMALLCAP 250",          "INR", "total_return"),
    ("US_LARGE",    "S&P 500 (SPY)",              "yahoo_tr",   "SPY",                         "USD", "total_return"),
    ("US_TECH",     "Nasdaq 100 (QQQ)",           "yahoo_tr",   "QQQ",                         "USD", "total_return"),
    ("US_SMALL",    "Russell 2000 (IWM)",         "yahoo_tr",   "IWM",                         "USD", "total_return"),
    ("DM_EXUS",     "Developed ex-US (EFA)",      "yahoo_tr",   "EFA",                         "USD", "total_return"),
    ("EM",          "Emerging Markets (EEM)",     "yahoo_tr",   "EEM",                         "USD", "total_return"),
    ("IN_GSEC10",   "Nifty 10Y Benchmark G-Sec",  "nifty_px",   "NIFTY 10 YR BENCHMARK G-SEC", "INR", "total_return"),
    ("US_LT_TSY",   "US 20Y+ Treasuries (TLT)",   "yahoo_tr",   "TLT",                         "USD", "total_return"),
    ("US_HY",       "US High Yield (HYG)",        "yahoo_tr",   "HYG",                         "USD", "total_return"),
    ("IN_CASH",     "Nifty 1D Rate Index",        "nifty_px",   "NIFTY 1D RATE INDEX",         "INR", "total_return"),
    ("US_CASH",     "US T-Bills 1-3M (BIL)",      "yahoo_tr",   "BIL",                         "USD", "total_return"),
    ("IN_REIT",     "Nifty REITs & InvITs TRI",   "nifty_tri",  "NIFTY REITS & INVITS",        "INR", "total_return"),
    # Decision 2026-11-27: the Gold tile is INTERNATIONAL gold converted to INR
    # (GLD × USDINR), for comparability with the other global tiles. The Indian
    # local premium (import duty, local demand) is reported as a note by
    # validate.py from Gold BeES, not used in the ranking.
    ("GOLD",        "Gold (GLD)",                 "yahoo_tr",   "GLD",                         "USD", "total_return"),
    ("SILVER",      "Silver (SLV)",               "yahoo_tr",   "SLV",                         "USD", "total_return"),
    ("COPPER",      "Copper (CPER)",              "yahoo_tr",   "CPER",                        "USD", "total_return"),
    ("BRENT",       "Brent Crude (BNO)",          "yahoo_tr",   "BNO",                         "USD", "total_return"),
    ("BTC",         "Bitcoin",                    "yahoo_tr",   "BTC-USD",                     "USD", "total_return"),
]

# ── Layer 3: sectors (ranked separately) ─────────────────────────────────────
LAYER3_INDIA = [
    ("IN_BANK",   "Nifty Bank TRI",                 "nifty_tri", "NIFTY BANK"),
    ("IN_FINXB",  "Nifty Fin Services ex-Bank TRI", "nifty_tri", "NIFTY FINANCIAL SERVICES EX-BANK"),
    ("IN_IT",     "Nifty IT TRI",                   "nifty_tri", "NIFTY IT"),
    ("IN_AUTO",   "Nifty Auto TRI",                 "nifty_tri", "NIFTY AUTO"),
    ("IN_FMCG",   "Nifty FMCG TRI",                 "nifty_tri", "NIFTY FMCG"),
    ("IN_PHARMA", "Nifty Pharma TRI",               "nifty_tri", "NIFTY PHARMA"),
    ("IN_METAL",  "Nifty Metal TRI",                "nifty_tri", "NIFTY METAL"),
    ("IN_ENERGY", "Nifty Energy TRI",               "nifty_tri", "NIFTY ENERGY"),
    ("IN_INFRA",  "Nifty Infrastructure TRI",       "nifty_tri", "NIFTY INFRASTRUCTURE"),
    ("IN_REALTY", "Nifty Realty TRI",               "nifty_tri", "NIFTY REALTY"),
]
LAYER3_US = [
    ("US_XLK", "Info Tech (XLK)", "yahoo_tr", "XLK"),
    ("US_SMH", "Semiconductors (SMH)", "yahoo_tr", "SMH"),
    ("US_XLC", "Comm Services (XLC)", "yahoo_tr", "XLC"),
    ("US_XLY", "Cons Discretionary (XLY)", "yahoo_tr", "XLY"),
    ("US_XLF", "Financials (XLF)", "yahoo_tr", "XLF"),
    ("US_XLI", "Industrials (XLI)", "yahoo_tr", "XLI"),
    ("US_XLV", "Health Care (XLV)", "yahoo_tr", "XLV"),
    ("US_XLP", "Cons Staples (XLP)", "yahoo_tr", "XLP"),
    ("US_XLE", "Energy (XLE)", "yahoo_tr", "XLE"),
    ("US_XLB", "Materials (XLB)", "yahoo_tr", "XLB"),
    ("US_XLU", "Utilities (XLU)", "yahoo_tr", "XLU"),
    ("US_XLRE", "Real Estate (XLRE)", "yahoo_tr", "XLRE"),
]

# ── Layer 1: macro, liquidity, rates, FX, vol, ratio inputs (unranked) ───────
# (id, name, source, source_id, units, scale, frequency, basis)
LAYER1 = [
    # Fed net liquidity inputs. Units verified against live values 2026-11-27:
    # WALCL and WTREGEN are $ millions, RRPONTSYD is $ billions.
    ("FED_ASSETS", "Fed total assets",              "fred", "WALCL",      "USD bn", 1e-3, "W", "level"),
    ("FED_TGA",    "Treasury General Account",      "fred", "WTREGEN",    "USD bn", 1e-3, "W", "level"),
    ("FED_RRP",    "Overnight reverse repo",        "fred", "RRPONTSYD",  "USD bn", 1.0,  "D", "level"),
    ("ECB_ASSETS", "ECB total assets",              "fred", "ECBASSETSW", "EUR bn", 1e-3, "W", "level"),
    ("BOJ_ASSETS", "BoJ total assets",              "fred", "JPNASSETS",  "JPY bn", 0.1,  "M", "level"),  # raw unit: 100mn yen
    ("EURUSD",     "EUR/USD (FRED)",                "fred", "DEXUSEU",    "USD per EUR", 1.0, "D", "fx"),
    ("USDJPY",     "USD/JPY (FRED)",                "fred", "DEXJPUS",    "JPY per USD", 1.0, "D", "fx"),
    # Money supply — direct from each central bank (FRED's OECD copies for
    # India/China/Japan/Euro area stopped updating between 2018 and 2023).
    ("M2_US",      "US M2",                         "fred", "M2SL",       "USD bn", 1.0,  "M", "level"),
    ("M2_EA",      "Euro area M2",                  "ecb",  "BSI/M.U2.Y.V.M20.X.1.U2.2300.Z01.E", "EUR bn", 1e-3, "M", "level"),
    ("M2_JP",      "Japan M2 (avg outstanding)",    "boj",  "MD02:MAM1NAM2M2MO", "JPY bn", 0.1, "M", "level"),
    ("M2_CN",      "China M2",                      "akshare_cn_m2", "M2",  "CNY bn", 0.1, "M", "level"),  # raw unit: 100mn yuan
    ("USDCNY",     "USD/CNY",                       "yahoo_px", "USDCNY=X", "CNY per USD", 1.0, "D", "fx"),
    # Rates
    ("US10Y",      "US 10Y Treasury yield",         "fred", "DGS10",      "%", 1.0, "D", "yield_pct"),
    ("US2Y",       "US 2Y Treasury yield",          "fred", "DGS2",       "%", 1.0, "D", "yield_pct"),
    ("US_HY_OAS",  "US HY option-adjusted spread",  "fred", "BAMLH0A0HYM2", "%", 1.0, "D", "yield_pct"),
    # India has no free daily 1Y G-Sec yield feed; the curve uses 10Y minus the
    # 3M interbank rate (both OECD monthly averages via FRED, currently live).
    ("IN10Y",      "India 10Y G-Sec yield (monthly avg)", "fred", "INDIRLTLT01STM", "%", 1.0, "M", "yield_pct"),
    ("IN3M",       "India 3M interbank rate (monthly avg)", "fred", "INDIR3TIB01STM", "%", 1.0, "M", "yield_pct"),
    # India liquidity: RBI daily Money Market Operations release, line F
    # "Net liquidity injected (outstanding incl. today's operations)".
    ("RBI_NETLIQ", "RBI net liquidity (LAF+MSF+SLF-SDF)", "rbi_mmo", "F", "INR cr", 1.0, "D", "level"),
    # FX & vol
    # USD/INR used for every INR conversion. Built in run.py: the Fed's H.10
    # noon rate (FRED DEXINUS, official, published weekly) for all dates it
    # covers, with Yahoo filling only the days after FRED's last print. Yahoo
    # alone showed month-end prints up to 1.1% off (e.g. May 2026).
    ("USDINR",     "USD/INR (FRED H.10, Yahoo for latest days)", "spliced", "X_USDINR_FRED+X_USDINR_YAHOO", "INR per USD", 1.0, "D", "fx"),
    ("DXY",        "US Dollar Index",               "yahoo_px", "DX-Y.NYB", "index", 1.0, "D", "level"),
    ("VIX",        "CBOE VIX",                      "yahoo_px", "^VIX",     "index", 1.0, "D", "level"),
    ("INDIAVIX",   "India VIX",                     "yahoo_px", "^INDIAVIX", "index", 1.0, "D", "level"),
    # Ratio inputs (price basis is correct for ratios of levels)
    ("COPPER_FUT", "Copper front future",           "yahoo_px", "HG=F", "USD/lb", 1.0, "D", "price"),
    ("BRENT_FUT",  "Brent crude front future",      "yahoo_px", "BZ=F", "USD/bbl", 1.0, "D", "price"),
    ("GOLD_FUT",   "Gold front future",             "yahoo_px", "GC=F", "USD/oz", 1.0, "D", "price"),
    ("HYG_PX",     "HYG",                           "yahoo_tr", "HYG",  "index", 1.0, "D", "total_return"),
    ("TLT_PX",     "TLT",                           "yahoo_tr", "TLT",  "index", 1.0, "D", "total_return"),
    ("RSP_PX",     "Equal-weight S&P 500 (RSP)",    "yahoo_tr", "RSP",  "index", 1.0, "D", "total_return"),
    ("SPY_PX",     "SPY",                           "yahoo_tr", "SPY",  "index", 1.0, "D", "total_return"),
]

# ── Cross-check series (not shown in the quilt; used only by validate.py) ────
CROSSCHECK = [
    ("X_NIFTY_PX",   "Nifty 50 price (Yahoo)",   "yahoo_px", "^NSEI"),
    ("X_NIFTY_PXNI", "Nifty 50 price (NSE)",     "nifty_px", "NIFTY 50"),
    ("X_MID_PXNI",   "Midcap 150 price (NSE)",   "nifty_px", "NIFTY MIDCAP 150"),
    ("X_FMCG_PXNI",  "Nifty FMCG price (NSE)",   "nifty_px", "NIFTY FMCG"),
    ("X_GSEC_CLEAN", "10Y G-Sec clean price",    "nifty_px", "NIFTY 10 YR BENCHMARK G-SEC (CLEAN PRICE)"),
    ("X_USDINR_FRED", "USD/INR (FRED noon NY)",  "fred",     "DEXINUS"),
    ("X_USDINR_YAHOO", "USD/INR (Yahoo)",        "yahoo_px", "USDINR=X"),
    ("X_GOLDBEES",   "Gold BeES (INR gold ETF)", "yahoo_tr", "GOLDBEES.NS"),
    ("X_SPY_PRICE",  "SPY price only",           "yahoo_px", "SPY"),
    ("X_HYG_PRICE",  "HYG price only",           "yahoo_px", "HYG"),
]


def all_series():
    """Flatten every registry row into dicts with a common shape."""
    out = []
    for i, n, src, sid, ccy, basis in LAYER2:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy=ccy, basis=basis,
                        layer="L2", units="index", scale=1.0, freq="D"))
    for i, n, src, sid in LAYER3_INDIA:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy="INR", basis="total_return",
                        layer="L3_IN", units="index", scale=1.0, freq="D"))
    for i, n, src, sid in LAYER3_US:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy="USD", basis="total_return",
                        layer="L3_US", units="index", scale=1.0, freq="D"))
    for i, n, src, sid, units, scale, freq, basis in LAYER1:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy=None, basis=basis,
                        layer="L1", units=units, scale=scale, freq=freq))
    for i, n, src, sid in CROSSCHECK:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy=None, basis="check",
                        layer="X", units="raw", scale=1.0, freq="D"))
    return out


# ── Layer 1 Group D: forward catalysts ───────────────────────────────────────
# Contracts are FOUND each run by search + rules, never by a hard-coded slug:
# Polymarket slugs carry creation timestamps and roll over as contracts resolve.
#   query       — Polymarket public-search text
#   slug_has    — every token must appear in the event slug
#   pick        — "nearest": soonest end date still open; "largest": most liquid
#   min_liq     — event liquidity (USD) below this is flagged THIN
#   kalshi      — optional Kalshi series ticker for an independent cross-check
CATALYSTS = [
    dict(key="FOMC_NEXT", label="Next FOMC decision", query="fed decision in",
         slug_has=["fed-decision-in"], pick="nearest", min_liq=250_000, kalshi="KXFEDDECISION"),
    dict(key="FED_CUTS_YR", label="Number of Fed cuts this year", query="how many fed rate cuts",
         slug_has=["fed-rate-cuts"], pick="largest", min_liq=250_000),
    dict(key="RBI_NEXT", label="Next RBI policy decision", query="reserve bank of india decision",
         slug_has=["reserve-bank-of-india-decision"], pick="nearest", min_liq=50_000),
    dict(key="US_RECESSION", label="US recession by year-end", query="us recession by end of",
         slug_has=["us-recession-by-end-of"], pick="nearest", min_liq=50_000, kalshi="KXRECSSNBER"),
    dict(key="TARIFF_CHINA", label="US tariff rate on China at year-end", query="us tariff rate on china",
         slug_has=["tariff-rate-on-china"], pick="nearest", min_liq=25_000),
    dict(key="BTC_YE", label="Bitcoin price hit before year-end", query="what price will bitcoin hit before",
         slug_has=["bitcoin-hit-before"], pick="largest", min_liq=250_000),
    dict(key="GOLD_YE", label="Gold (GC) hit by end of December", query="what will gold gc hit by end of",
         slug_has=["gold-gc-hit"], pick="largest", min_liq=100_000),
    dict(key="OIL_ATH", label="Crude oil all-time high", query="crude oil all time high",
         slug_has=["crude-oil-all-time-high"], pick="largest", min_liq=50_000),
    dict(key="AI_BUBBLE", label="AI bubble burst", query="ai bubble burst",
         slug_has=["ai-bubble-burst"], pick="largest", min_liq=50_000),
]

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

# ── Layer 3 (global): world equity markets, ranked in INR ────────────────────
# US-listed country ETFs (dividend-adjusted, in USD) so every market is on the
# same total-return basis and converts to INR the same way as the other tiles.
# `index` is the headline index (GLOBAL_INDICES) shown alongside in its own
# currency; None where no free headline series exists.
# (id, name, source, source_id, region, headline index id)
LAYER3_GLOBAL = [
    ("GL_CN_TECH", "China tech (CQQQ)",        "yahoo_tr", "CQQQ", "China",       None),
    ("GL_CN_LARGE", "China large caps (FXI)",  "yahoo_tr", "FXI",  "China",       "GI_HSCEI"),
    ("GL_CN_A",    "China A-shares (ASHR)",    "yahoo_tr", "ASHR", "China",       "GI_CSI300"),
    ("GL_HK",      "Hong Kong (EWH)",          "yahoo_tr", "EWH",  "Hong Kong",   "GI_HSI"),
    ("GL_JP",      "Japan (EWJ)",              "yahoo_tr", "EWJ",  "Japan",       "GI_N225"),
    ("GL_KR",      "Korea (EWY)",              "yahoo_tr", "EWY",  "Korea",       "GI_KOSPI"),
    ("GL_TW",      "Taiwan (EWT)",             "yahoo_tr", "EWT",  "Taiwan",      "GI_TAIEX"),
    ("GL_DE",      "Germany (EWG)",            "yahoo_tr", "EWG",  "Germany",     "GI_DAX"),
    ("GL_EZ",      "Euro area (FEZ)",          "yahoo_tr", "FEZ",  "Euro area",   "GI_SX5E"),
    ("GL_UK",      "UK (EWU)",                 "yahoo_tr", "EWU",  "UK",          "GI_FTSE"),
]
# Reference rows ranked alongside the global markets (already loaded in Layer 2).
GLOBAL_REFERENCE = [("IN_LARGE", "India (Nifty 50 TRI)", "India"), ("US_LARGE", "US (S&P 500, SPY)", "US")]

# Headline indices in local currency. Price indices except the DAX, which is a
# total-return index by construction. CSI 300 comes from Sina via akshare:
# Yahoo's 000300.SS had one row and a level about 4% off on 2026-11-27.
# (id, name, source, source_id, currency, basis)
GLOBAL_INDICES = [
    ("GI_HSI",    "Hang Seng",               "yahoo_px",      "^HSI",       "HKD", "price"),
    ("GI_HSCEI",  "Hang Seng China Enterprises", "yahoo_px",  "^HSCE",      "HKD", "price"),
    ("GI_CSI300", "CSI 300",                 "akshare_index", "sh000300",   "CNY", "price"),
    ("GI_N225",   "Nikkei 225",              "yahoo_px",      "^N225",      "JPY", "price"),
    ("GI_KOSPI",  "KOSPI",                   "yahoo_px",      "^KS11",      "KRW", "price"),
    ("GI_TAIEX",  "Taiwan TAIEX",            "yahoo_px",      "^TWII",      "TWD", "price"),
    ("GI_DAX",    "DAX",                     "yahoo_px",      "^GDAXI",     "EUR", "total_return"),
    ("GI_SX5E",   "Euro Stoxx 50",           "yahoo_px",      "^STOXX50E",  "EUR", "price"),
    ("GI_FTSE",   "FTSE 100",                "yahoo_px",      "^FTSE",      "GBP", "price"),
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
    # Global 10Y government bond yields, each from its official publisher (daily).
    ("DE10Y",      "Germany 10Y Bund yield",        "bbk", "BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A", "%", 1.0, "D", "yield_pct"),
    ("JP10Y",      "Japan 10Y JGB yield",           "mof_jgb", "10Y",      "%", 1.0, "D", "yield_pct"),
    ("UK10Y",      "UK 10Y gilt yield",             "boe", "IUDMNPY",      "%", 1.0, "D", "yield_pct"),
    ("CN10Y",      "China 10Y government bond yield", "akshare_cn_yield", "中国国债收益率10年", "%", 1.0, "D", "yield_pct"),
    # Global bond funds (shown in the rates panel with INR returns, not ranked).
    ("BWX_TR",     "International govt bonds (BWX)", "yahoo_tr", "BWX",   "index", 1.0, "D", "total_return"),
    ("EMB_TR",     "EM dollar bonds (EMB)",         "yahoo_tr", "EMB",    "index", 1.0, "D", "total_return"),
    # Currencies against the rupee. Same rule as USD/INR: the Fed's H.10 rate
    # (FRED) wherever it exists, Yahoo only for the days after its last print.
    ("GBPUSD",     "GBP/USD (FRED H.10, Yahoo for latest days)", "spliced", "X_GBPUSD_FRED+X_GBPUSD_YAHOO", "USD per GBP", 1.0, "D", "fx"),
    ("EURUSD_SP",  "EUR/USD (FRED H.10, Yahoo for latest days)", "spliced", "EURUSD+X_EURUSD_YAHOO", "USD per EUR", 1.0, "D", "fx"),
    ("USDJPY_SP",  "USD/JPY (FRED H.10, Yahoo for latest days)", "spliced", "USDJPY+X_USDJPY_YAHOO", "JPY per USD", 1.0, "D", "fx"),
    ("USDCNY_SP",  "USD/CNY (FRED H.10, Yahoo for latest days)", "spliced", "X_USDCNY_FRED+USDCNY", "CNY per USD", 1.0, "D", "fx"),
    ("USDSGD",     "USD/SGD (FRED H.10, Yahoo for latest days)", "spliced", "X_USDSGD_FRED+X_USDSGD_YAHOO", "SGD per USD", 1.0, "D", "fx"),
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
    # Inputs to the spliced currency series above
    ("X_GBPUSD_FRED",  "GBP/USD (FRED)",  "fred",     "DEXUSUK"),
    ("X_GBPUSD_YAHOO", "GBP/USD (Yahoo)", "yahoo_px", "GBPUSD=X"),
    ("X_EURUSD_YAHOO", "EUR/USD (Yahoo)", "yahoo_px", "EURUSD=X"),
    ("X_USDJPY_YAHOO", "USD/JPY (Yahoo)", "yahoo_px", "JPY=X"),
    ("X_USDCNY_FRED",  "USD/CNY (FRED)",  "fred",     "DEXCHUS"),
    ("X_USDSGD_FRED",  "USD/SGD (FRED)",  "fred",     "DEXSIUS"),
    ("X_USDSGD_YAHOO", "USD/SGD (Yahoo)", "yahoo_px", "SGD=X"),
    # Used only to convert headline indices to USD for the ETF tracking check
    ("X_USDKRW_YAHOO", "USD/KRW (Yahoo)", "yahoo_px", "KRW=X"),
    ("X_USDTWD_YAHOO", "USD/TWD (Yahoo)", "yahoo_px", "TWD=X"),
    # OECD monthly-average 10Y yields: an independent check on the daily feeds
    ("X_DE10Y_OECD", "Germany 10Y (OECD monthly avg)", "fred", "IRLTLT01DEM156N", "M"),
    ("X_JP10Y_OECD", "Japan 10Y (OECD monthly avg)",   "fred", "IRLTLT01JPM156N", "M"),
    ("X_UK10Y_OECD", "UK 10Y (OECD monthly avg)",      "fred", "IRLTLT01GBM156N", "M"),
]

# AED is pegged to the dollar by the UAE central bank at 3.6725 per USD.
AED_PER_USD = 3.6725


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
    for i, n, src, sid, region, _ in LAYER3_GLOBAL:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy="USD", basis="total_return",
                        layer="L3_GL", units="index", scale=1.0, freq="D", region=region))
    for i, n, src, sid, ccy, basis in GLOBAL_INDICES:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy=ccy, basis=basis,
                        layer="GI", units=ccy, scale=1.0, freq="D"))
    for i, n, src, sid, units, scale, freq, basis in LAYER1:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy=None, basis=basis,
                        layer="L1", units=units, scale=scale, freq=freq))
    for i, n, src, sid, *freq in CROSSCHECK:
        out.append(dict(id=i, name=n, source=src, source_id=sid, ccy=None, basis="check",
                        layer="X", units="raw", scale=1.0, freq=freq[0] if freq else "D"))
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

# ── Valuations (valuation.py) ────────────────────────────────────────────────
# Trailing P/E for each major equity market, compared with its own history.
# source: "nse" = NSE Indices daily P/E, P/B, dividend yield (official, from the
# index owner); "wpr" = worldperatio.com monthly P/E history for the ETF in
# `etf` (estimated from fund holdings); "yahoo" = Yahoo's current fund P/E only
# (no history: it builds up from the first run). `etf` is also the Yahoo
# cross-check. `y10` is the local 10-year yield used for the shares-vs-bonds gap.
# (id, name, group, source, source_id, etf, y10)
VALUATION = [
    ("IN_LARGE",    "India: Nifty 50",            "Markets", "nse",   "NIFTY 50",          "INDA", "IN10Y"),
    ("IN_MID",      "India: Midcap 150",          "Markets", "nse",   "NIFTY MIDCAP 150",  None,   "IN10Y"),
    ("IN_SMALL",    "India: Smallcap 250",        "Markets", "nse",   "NIFTY SMLCAP 250",  None,   "IN10Y"),
    ("US_LARGE",    "US: S&P 500",                "Markets", "wpr",   "index/sp-500",      "SPY",  "US10Y"),
    ("US_TECH",     "US: Nasdaq 100",             "Markets", "wpr",   "index/nasdaq-100",  "QQQ",  "US10Y"),
    ("GL_CN_LARGE", "China large caps",           "Markets", "wpr",   "area/china",        "FXI",  "CN10Y"),
    ("GL_CN_TECH",  "China tech",                 "Markets", "yahoo", "CQQQ",              "CQQQ", "CN10Y"),
    ("GL_CN_A",     "China A-shares",             "Markets", "yahoo", "ASHR",              "ASHR", "CN10Y"),
    ("GL_HK",       "Hong Kong",                  "Markets", "wpr",   "area/hong-kong",    "EWH",  "US10Y"),
    ("GL_JP",       "Japan",                      "Markets", "wpr",   "area/japan",        "EWJ",  "JP10Y"),
    ("GL_KR",       "Korea",                      "Markets", "wpr",   "area/south-korea",  "EWY",  None),
    ("GL_TW",       "Taiwan",                     "Markets", "wpr",   "area/taiwan",       "EWT",  None),
    ("GL_DE",       "Germany",                    "Markets", "wpr",   "area/germany",      "EWG",  "DE10Y"),
    ("GL_EZ",       "Euro area",                  "Markets", "yahoo", "FEZ",               "FEZ",  "DE10Y"),
    ("GL_UK",       "UK",                         "Markets", "wpr",   "area/united-kingdom", "EWU", "UK10Y"),
    ("EM",          "Emerging markets",           "Markets", "wpr",   "area/emerging-markets", "EEM", None),
    ("IN_BANK",     "Bank",                       "India sectors", "nse", "NIFTY BANK",   None, "IN10Y"),
    ("IN_FINXB",    "Fin ex-Bank",                "India sectors", "nse", "NIFTY FINSEREXBNK", None, "IN10Y"),
    ("IN_IT",       "IT",                         "India sectors", "nse", "NIFTY IT",     None, "IN10Y"),
    ("IN_AUTO",     "Auto",                       "India sectors", "nse", "NIFTY AUTO",   None, "IN10Y"),
    ("IN_FMCG",     "FMCG",                       "India sectors", "nse", "NIFTY FMCG",   None, "IN10Y"),
    ("IN_PHARMA",   "Pharma",                     "India sectors", "nse", "NIFTY PHARMA", None, "IN10Y"),
    ("IN_METAL",    "Metal",                      "India sectors", "nse", "NIFTY METAL",  None, "IN10Y"),
    ("IN_ENERGY",   "Energy",                     "India sectors", "nse", "NIFTY ENERGY", None, "IN10Y"),
    ("IN_INFRA",    "Infra",                      "India sectors", "nse", "NIFTY INFRA", None, "IN10Y"),
    ("IN_REALTY",   "Realty",                     "India sectors", "nse", "NIFTY REALTY", None, "IN10Y"),
]
# Context only: the MSCI India fund's P/E, to cross-check the NSE Nifty 50 history.
VALUATION_XCHECK = [("X_INDA", "India (MSCI India, INDA)", "wpr", "area/india", "INDA")]

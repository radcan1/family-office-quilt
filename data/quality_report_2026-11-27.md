# Data quality report — 2026-11-27

**Series:** 120 pass · 2 warn · 0 fail  

## Basis and cross-source checks

| Check | Status | Detail |
|---|---|---|
| Nifty 50 TRI includes dividends | PASS | 12m TRI−price gap 1.03pp (expect 0.5–2.5), worst month +0.000pp |
| Midcap 150 TRI includes dividends | PASS | 12m gap 0.66pp |
| 10Y G-Sec index is total return (not clean price) | PASS | 12m TR−clean gap 6.82pp (≈ coupon accrual, expect 5–8.5) |
| SPY adjusted close includes distributions | PASS | 12m adj−price gap 1.05pp (expect 0.8–2.0) |
| HYG adjusted close includes distributions | PASS | 12m adj−price gap 5.87pp (expect 4.0–8.0) |
| Nifty 50 price: Yahoo vs NSE | PASS | max monthly diff 0.000pp over 12m |
| USD/INR: Yahoo vs FRED (same day) | PASS | median diff 0.19%, max 1.97% on 2026-08-26 — quilt uses FRED; Yahoo only fills the days after FRED's last print |
| Indian gold premium vs international (note only) | INFO | last completed month Indian gold +2.22pp vs international; 12m range -7.23 to +5.68pp. A move beyond ±3pp in a month usually means an import-duty change or a local-premium swing |
| Global ETFs track their headline index (9 markets) | WARN | Low correlation: Hong Kong (EWH) 0.78. Monthly correlation in USD over 24 months: China large caps 0.95, China A-shares 0.98, Hong Kong 0.78, Japan 0.86, Korea 0.98, Taiwan 0.95, Germany 0.99, Euro area 0.99, UK 0.97 |
| Global 10Y yields: daily feeds vs OECD monthly averages | WARN | Germany max gap 0.08pp (to Oct 2026), Japan max gap 0.21pp (to Oct 2026), UK max gap 0.00pp (to Oct 2026) over the last 6 months (limit 0.15pp) |
| FED_NETLIQ_USD_BN | PASS | 5,824.51 (plausible 3,000–9,000) |
| G3_CB_USD_TN | PASS | 17.19 (plausible 10–30) |
| GLOBAL_M2_USD_TN | PASS | 104.10 (plausible 60–140) |

## Derived Layer 1 values (latest)

- **FED_NETLIQ_USD_BN**: 5,824.51
- **FED_NETLIQ_ASOF**: 2026-11-18
- **G3_CB_USD_TN**: 17.19
- **GLOBAL_M2_USD_TN**: 104.10
- **GLOBAL_M2_ASOF**: 2026-10-31

## Series

| Layer | ID | Name | Source | Status | Detail |
|---|---|---|---|---|---|
| L2 | IN_LARGE | Nifty 50 TRI | nifty_tri:NIFTY 50 | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L2 | IN_MID | Nifty Midcap 150 TRI | nifty_tri:NIFTY MIDCAP 150 | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L2 | IN_SMALL | Nifty Smallcap 250 TRI | nifty_tri:NIFTY SMALLCAP 250 | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L2 | US_LARGE | S&P 500 (SPY) | yahoo_tr:SPY | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | US_TECH | Nasdaq 100 (QQQ) | yahoo_tr:QQQ | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | US_SMALL | Russell 2000 (IWM) | yahoo_tr:IWM | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | DM_EXUS | Developed ex-US (EFA) | yahoo_tr:EFA | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | EM | Emerging Markets (EEM) | yahoo_tr:EEM | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | IN_GSEC10 | Nifty 10Y Benchmark G-Sec | nifty_px:NIFTY 10 YR BENCHMARK G-SEC | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L2 | US_LT_TSY | US 20Y+ Treasuries (TLT) | yahoo_tr:TLT | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | US_HY | US High Yield (HYG) | yahoo_tr:HYG | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | IN_CASH | Nifty 1D Rate Index | nifty_px:NIFTY 1D RATE INDEX | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L2 | US_CASH | US T-Bills 1-3M (BIL) | yahoo_tr:BIL | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | IN_REIT | Nifty REITs & InvITs TRI | nifty_tri:NIFTY REITS & INVITS | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L2 | GOLD | Gold (GLD) | yahoo_tr:GLD | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | SILVER | Silver (SLV) | yahoo_tr:SLV | WARN | last obs 2026-11-25 (2d old, limit 5d); one-day jumps >8σ on 2026-01-30 (-28.5%) |
| L2 | COPPER | Copper (CPER) | yahoo_tr:CPER | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | BRENT | Brent Crude (BNO) | yahoo_tr:BNO | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L2 | BTC | Bitcoin | yahoo_tr:BTC-USD | PASS | last obs 2026-11-27 (0d old, limit 2d) |
| L3_IN | IN_BANK | Nifty Bank TRI | nifty_tri:NIFTY BANK | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_FINXB | Nifty Fin Services ex-Bank TRI | nifty_tri:NIFTY FINANCIAL SERVICES EX-BANK | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_IT | Nifty IT TRI | nifty_tri:NIFTY IT | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_AUTO | Nifty Auto TRI | nifty_tri:NIFTY AUTO | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_FMCG | Nifty FMCG TRI | nifty_tri:NIFTY FMCG | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_PHARMA | Nifty Pharma TRI | nifty_tri:NIFTY PHARMA | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_METAL | Nifty Metal TRI | nifty_tri:NIFTY METAL | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_ENERGY | Nifty Energy TRI | nifty_tri:NIFTY ENERGY | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_INFRA | Nifty Infrastructure TRI | nifty_tri:NIFTY INFRASTRUCTURE | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_IN | IN_REALTY | Nifty Realty TRI | nifty_tri:NIFTY REALTY | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L3_US | US_XLK | Info Tech (XLK) | yahoo_tr:XLK | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_SMH | Semiconductors (SMH) | yahoo_tr:SMH | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLC | Comm Services (XLC) | yahoo_tr:XLC | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLY | Cons Discretionary (XLY) | yahoo_tr:XLY | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLF | Financials (XLF) | yahoo_tr:XLF | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLI | Industrials (XLI) | yahoo_tr:XLI | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLV | Health Care (XLV) | yahoo_tr:XLV | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLP | Cons Staples (XLP) | yahoo_tr:XLP | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLE | Energy (XLE) | yahoo_tr:XLE | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLB | Materials (XLB) | yahoo_tr:XLB | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLU | Utilities (XLU) | yahoo_tr:XLU | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_US | US_XLRE | Real Estate (XLRE) | yahoo_tr:XLRE | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_CN_TECH | China tech (CQQQ) | yahoo_tr:CQQQ | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_CN_LARGE | China large caps (FXI) | yahoo_tr:FXI | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_CN_A | China A-shares (ASHR) | yahoo_tr:ASHR | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_HK | Hong Kong (EWH) | yahoo_tr:EWH | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_JP | Japan (EWJ) | yahoo_tr:EWJ | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_KR | Korea (EWY) | yahoo_tr:EWY | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_TW | Taiwan (EWT) | yahoo_tr:EWT | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_DE | Germany (EWG) | yahoo_tr:EWG | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_EZ | Euro area (FEZ) | yahoo_tr:FEZ | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L3_GL | GL_UK | UK (EWU) | yahoo_tr:EWU | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| GI | GI_HSI | Hang Seng | yahoo_px:^HSI | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| GI | GI_HSCEI | Hang Seng China Enterprises | yahoo_px:^HSCE | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| GI | GI_CSI300 | CSI 300 | akshare_index:sh000300 | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| GI | GI_N225 | Nikkei 225 | yahoo_px:^N225 | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| GI | GI_KOSPI | KOSPI | yahoo_px:^KS11 | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| GI | GI_TAIEX | Taiwan TAIEX | yahoo_px:^TWII | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| GI | GI_DAX | DAX | yahoo_px:^GDAXI | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| GI | GI_SX5E | Euro Stoxx 50 | yahoo_px:^STOXX50E | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| GI | GI_FTSE | FTSE 100 | yahoo_px:^FTSE | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L1 | FED_ASSETS | Fed total assets | fred:WALCL | PASS | last obs 2026-11-18 (9d old, limit 12d) |
| L1 | FED_TGA | Treasury General Account | fred:WTREGEN | PASS | last obs 2026-11-18 (9d old, limit 12d) |
| L1 | FED_RRP | Overnight reverse repo | fred:RRPONTSYD | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L1 | ECB_ASSETS | ECB total assets | fred:ECBASSETSW | PASS | last obs 2026-11-20 (7d old, limit 12d) |
| L1 | BOJ_ASSETS | BoJ total assets | fred:JPNASSETS | PASS | last obs 2026-10-01 (57d old, limit 75d) |
| L1 | EURUSD | EUR/USD (FRED) | fred:DEXUSEU | PASS | last obs 2026-11-20 (7d old, limit 10d) |
| L1 | USDJPY | USD/JPY (FRED) | fred:DEXJPUS | PASS | last obs 2026-11-20 (7d old, limit 10d) |
| L1 | M2_US | US M2 | fred:M2SL | PASS | last obs 2026-10-01 (57d old, limit 75d) |
| L1 | M2_EA | Euro area M2 | ecb:BSI/M.U2.Y.V.M20.X.1.U2.2300.Z01.E | PASS | last obs 2026-10-31 (27d old, limit 75d) |
| L1 | M2_JP | Japan M2 (avg outstanding) | boj:MD02:MAM1NAM2M2MO | PASS | last obs 2026-10-31 (27d old, limit 75d) |
| L1 | M2_CN | China M2 | akshare_cn_m2:M2 | PASS | last obs 2026-10-31 (27d old, limit 75d) |
| L1 | USDCNY | USD/CNY | yahoo_px:USDCNY=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | US10Y | US 10Y Treasury yield | fred:DGS10 | PASS | last obs 2026-11-24 (3d old, limit 5d) |
| L1 | US2Y | US 2Y Treasury yield | fred:DGS2 | PASS | last obs 2026-11-24 (3d old, limit 5d) |
| L1 | US_HY_OAS | US HY option-adjusted spread | fred:BAMLH0A0HYM2 | PASS | last obs 2026-11-24 (3d old, limit 5d) |
| L1 | IN10Y | India 10Y G-Sec yield (monthly avg) | fred:INDIRLTLT01STM | PASS | last obs 2026-10-01 (57d old, limit 75d) |
| L1 | IN3M | India 3M interbank rate (monthly avg) | fred:INDIR3TIB01STM | PASS | last obs 2026-10-01 (57d old, limit 75d) |
| L1 | RBI_NETLIQ | RBI net liquidity (LAF+MSF+SLF-SDF) | rbi_mmo:F | WARN | last obs 2026-11-26 (1d old, limit 5d); 11 obs in last 365d — history accumulates from first run (RBI has no bulk archive) |
| L1 | DE10Y | Germany 10Y Bund yield | bbk:BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L1 | JP10Y | Japan 10Y JGB yield | mof_jgb:10Y | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L1 | UK10Y | UK 10Y gilt yield | boe:IUDMNPY | PASS | last obs 2026-11-24 (3d old, limit 5d) |
| L1 | CN10Y | China 10Y government bond yield | akshare_cn_yield:中国国债收益率10年 | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L1 | BWX_TR | International govt bonds (BWX) | yahoo_tr:BWX | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L1 | EMB_TR | EM dollar bonds (EMB) | yahoo_tr:EMB | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L1 | GBPUSD | GBP/USD (FRED H.10, Yahoo for latest days) | spliced:X_GBPUSD_FRED+X_GBPUSD_YAHOO | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | EURUSD_SP | EUR/USD (FRED H.10, Yahoo for latest days) | spliced:EURUSD+X_EURUSD_YAHOO | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | USDJPY_SP | USD/JPY (FRED H.10, Yahoo for latest days) | spliced:USDJPY+X_USDJPY_YAHOO | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | USDCNY_SP | USD/CNY (FRED H.10, Yahoo for latest days) | spliced:X_USDCNY_FRED+USDCNY | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | USDSGD | USD/SGD (FRED H.10, Yahoo for latest days) | spliced:X_USDSGD_FRED+X_USDSGD_YAHOO | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | USDINR | USD/INR (FRED H.10, Yahoo for latest days) | spliced:X_USDINR_FRED+X_USDINR_YAHOO | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | DXY | US Dollar Index | yahoo_px:DX-Y.NYB | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | VIX | CBOE VIX | yahoo_px:^VIX | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| L1 | INDIAVIX | India VIX | yahoo_px:^INDIAVIX | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | COPPER_FUT | Copper front future | yahoo_px:HG=F | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | BRENT_FUT | Brent crude front future | yahoo_px:BZ=F | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | GOLD_FUT | Gold front future | yahoo_px:GC=F | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| L1 | HYG_PX | HYG | yahoo_tr:HYG | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L1 | TLT_PX | TLT | yahoo_tr:TLT | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L1 | RSP_PX | Equal-weight S&P 500 (RSP) | yahoo_tr:RSP | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| L1 | SPY_PX | SPY | yahoo_tr:SPY | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| X | X_NIFTY_PX | Nifty 50 price (Yahoo) | yahoo_px:^NSEI | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_NIFTY_PXNI | Nifty 50 price (NSE) | nifty_px:NIFTY 50 | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| X | X_MID_PXNI | Midcap 150 price (NSE) | nifty_px:NIFTY MIDCAP 150 | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| X | X_FMCG_PXNI | Nifty FMCG price (NSE) | nifty_px:NIFTY FMCG | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| X | X_GSEC_CLEAN | 10Y G-Sec clean price | nifty_px:NIFTY 10 YR BENCHMARK G-SEC (CLEAN PRICE) | PASS | last obs 2026-11-26 (1d old, limit 5d) |
| X | X_USDINR_FRED | USD/INR (FRED noon NY) | fred:DEXINUS | PASS | last obs 2026-11-20 (7d old, limit 10d) |
| X | X_USDINR_YAHOO | USD/INR (Yahoo) | yahoo_px:USDINR=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_GOLDBEES | Gold BeES (INR gold ETF) | yahoo_tr:GOLDBEES.NS | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_SPY_PRICE | SPY price only | yahoo_px:SPY | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| X | X_HYG_PRICE | HYG price only | yahoo_px:HYG | PASS | last obs 2026-11-25 (2d old, limit 5d) |
| X | X_GBPUSD_FRED | GBP/USD (FRED) | fred:DEXUSUK | PASS | last obs 2026-11-20 (7d old, limit 10d) |
| X | X_GBPUSD_YAHOO | GBP/USD (Yahoo) | yahoo_px:GBPUSD=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_EURUSD_YAHOO | EUR/USD (Yahoo) | yahoo_px:EURUSD=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_USDJPY_YAHOO | USD/JPY (Yahoo) | yahoo_px:JPY=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_USDCNY_FRED | USD/CNY (FRED) | fred:DEXCHUS | PASS | last obs 2026-11-20 (7d old, limit 10d) |
| X | X_USDSGD_FRED | USD/SGD (FRED) | fred:DEXSIUS | PASS | last obs 2026-11-20 (7d old, limit 10d) |
| X | X_USDSGD_YAHOO | USD/SGD (Yahoo) | yahoo_px:SGD=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_USDKRW_YAHOO | USD/KRW (Yahoo) | yahoo_px:KRW=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_USDTWD_YAHOO | USD/TWD (Yahoo) | yahoo_px:TWD=X | PASS | last obs 2026-11-27 (0d old, limit 5d) |
| X | X_DE10Y_OECD | Germany 10Y (OECD monthly avg) | fred:IRLTLT01DEM156N | PASS | last obs 2026-10-01 (57d old, limit 75d) |
| X | X_JP10Y_OECD | Japan 10Y (OECD monthly avg) | fred:IRLTLT01JPM156N | PASS | last obs 2026-10-01 (57d old, limit 75d) |
| X | X_UK10Y_OECD | UK 10Y (OECD monthly avg) | fred:IRLTLT01GBM156N | PASS | last obs 2026-10-01 (57d old, limit 75d) |

## Catalysts

| Catalyst | Outcome | Prob | 30d Δ | Kalshi | Liquidity | Flags |
|---|---|---|---|---|---|---|
| Next FOMC decision | No change | 3.4% | -17.1pp | 4.5% | $4,430,968 |  |
| Next FOMC decision | 25 bps increase | 94.5% | +18.0pp | 92.5% | $4,430,968 |  |
| Next FOMC decision | 50+ bps increase | 2.1% | -0.1pp | 2.5% | $4,430,968 |  |
| Number of Fed cuts this year | 0 (0 bps) | 98.5% | +2.5pp | — | $3,104,276 |  |
| Next RBI policy decision | 50+ bps increase | 7.4% | +0.9pp | — | $23,077 | THIN |
| Next RBI policy decision | 25 bps increase | 88.0% | +11.0pp | — | $23,077 | THIN |
| Next RBI policy decision | No Change | 3.0% | -11.5pp | — | $23,077 | THIN |
| Next RBI policy decision | 25 bps decrease | 0.1% | -2.2pp | — | $23,077 | THIN |
| Next RBI policy decision | 50+ bps decrease | 0.1% | -0.3pp | — | $23,077 | THIN |
| US recession by year-end | US recession by end of 2026? | 3.3% | -4.2pp | 2.5% | $52,780 |  |
| US tariff rate on China at year-end | 5–15% | 83.5% | -3.5pp | — | $33,755 | WIDE SPREAD |
| US tariff rate on China at year-end | 15–25% | 9.5% | -0.5pp | — | $33,755 |  |
| US tariff rate on China at year-end | 35%+ | 2.2% | -1.7pp | — | $33,755 |  |
| Bitcoin price hit before year-end | ↑ 95,000 | 1.9% | -24.6pp | — | $4,242,508 | MAJOR REPRICING |
| Bitcoin price hit before year-end | ↓ 55,000 | 45.5% | +35.0pp | — | $4,242,508 | MAJOR REPRICING |
| Bitcoin price hit before year-end | ↓ 45,000 | 11.2% | +7.0pp | — | $4,242,508 |  |
| Bitcoin price hit before year-end | ↓ 35,000 | 5.1% | +2.8pp | — | $4,242,508 |  |
| Bitcoin price hit before year-end | ↓ 50,000 | 27.4% | +19.9pp | — | $4,242,508 |  |
| Bitcoin price hit before year-end | ↓ 40,000 | 8.1% | +5.2pp | — | $4,242,508 |  |
| Bitcoin price hit before year-end | ↓ 30,000 | 3.0% | +1.3pp | — | $4,242,508 |  |
| Bitcoin price hit before year-end | ↑ 90,000 | 3.0% | -41.4pp | — | $4,242,508 | MAJOR REPRICING |
| Gold (GC) hit by end of December | ↓ $3,500 | 62.5% | +51.5pp | — | $741,926 | MAJOR REPRICING |
| Gold (GC) hit by end of December | ↓ $3,000 | 6.7% | +3.8pp | — | $741,926 |  |
| Crude oil all-time high | December 31 | 2.2% | -11.3pp | — | $244,445 |  |
| Crude oil all-time high | March 31, 2027 | 13.5% | -13.0pp | — | $244,445 |  |
| AI bubble burst | December 31, 2026 | 17.2% | +9.2pp | — | $114,386 |  |
| AI bubble burst | June 30, 2027 | 38.0% | +15.5pp | — | $114,386 |  |

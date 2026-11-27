# Data quality report — 2026-11-27

**Series:** 78 pass · 2 warn · 0 fail  

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

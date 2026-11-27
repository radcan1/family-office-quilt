#!/usr/bin/env python3
"""
positioning.py — how money is positioned, from four free sources.

  1. Options and volatility (Yahoo): VIX term structure (VIX3M / VIX), SKEW,
     MOVE; and options-implied moves by expiry for SPY (yfinance chain, today
     only) and Nifty (NSE daily F&O file, month-ends back to Aug 2024).
  2. US futures positioning (CFTC Commitments of Traders, weekly since 2020):
     speculators' net position as % of open interest.
  3. India flows: FPI net equity investment by month (NSDL), and FIIs' long
     share of index futures (NSE participant-wise open interest, month-ends).

Writes data/positioning/:
  gauges.csv     long table: gauge, date, value (full history per gauge)
  implied.csv    implied move and put/call ratio by expiry (Nifty history + SPY snapshot)
Raw downloads are cached under data/raw/positioning/ and fetched once.

Politeness: NSE archive files one at a time, PAUSE seconds apart, and the run
stops NSE fetching at the first 403 (NSE has blocked this machine before).

    python3 positioning.py
"""

import datetime as dt
import io
import json
import os
import re
import time
import zipfile

import numpy as np
import pandas as pd
from curl_cffi import requests as http

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "positioning")
RAW = os.path.join(HERE, "data", "raw", "positioning")
os.makedirs(OUT, exist_ok=True)
os.makedirs(RAW, exist_ok=True)
PAUSE = 1.5
S = http.Session(impersonate="chrome")


class NseBlocked(Exception):
    pass


# ── Gauge definitions ────────────────────────────────────────────────────────
# high / low: what a reading in the top or bottom 10% of its 3-year range means.
GAUGES = {
    # CFTC disaggregated: managed money (hedge funds, CTAs)
    "COT_WTI":    dict(name="Crude oil (WTI): hedge-fund net long", group="US futures positioning", asset="BRENT",
                       src=("72hh-3qpy", "067651", "m_money"), high="Most bullish in 3 years", low="Most bearish in 3 years"),
    "COT_GOLD":   dict(name="Gold: hedge-fund net long", group="US futures positioning", asset="GOLD",
                       src=("72hh-3qpy", "088691", "m_money"), high="Most bullish in 3 years", low="Most bearish in 3 years"),
    "COT_SILVER": dict(name="Silver: hedge-fund net long", group="US futures positioning", asset="SILVER",
                       src=("72hh-3qpy", "084691", "m_money"), high="Most bullish in 3 years", low="Most bearish in 3 years"),
    "COT_COPPER": dict(name="Copper: hedge-fund net long", group="US futures positioning", asset="COPPER",
                       src=("72hh-3qpy", "085692", "m_money"), high="Most bullish in 3 years", low="Most bearish in 3 years"),
    # CFTC financial futures: leveraged funds for equities and the dollar, asset managers for bonds
    "COT_SPX":    dict(name="S&P 500 futures: leveraged-fund net", group="US futures positioning", asset="US_LARGE",
                       src=("gpe5-46if", "13874A", "lev_money"), high="Most bullish in 3 years", low="Most bearish in 3 years"),
    "COT_NDX":    dict(name="Nasdaq 100 futures: leveraged-fund net", group="US futures positioning", asset="US_TECH",
                       src=("gpe5-46if", "209742", "lev_money"), high="Most bullish in 3 years", low="Most bearish in 3 years"),
    "COT_UST":    dict(name="US Treasury bond futures: asset-manager net", group="US futures positioning", asset="US_LT_TSY",
                       src=("gpe5-46if", "020601", "asset_mgr"), high="Most bullish in 3 years", low="Most bearish in 3 years"),
    "COT_USD":    dict(name="US dollar index: leveraged-fund net", group="US futures positioning", asset=None,
                       src=("gpe5-46if", "098662", "lev_money"), high="Most bullish on the dollar in 3 years", low="Most bearish on the dollar in 3 years"),
    # Volatility (Yahoo)
    "VOL_TERM":   dict(name="VIX term structure (3-month ÷ 1-month)", group="Options and volatility", asset=None,
                       high="Calm: near-term fear low", low="Stress: near-term fear above longer-term"),
    "VOL_SKEW":   dict(name="CBOE SKEW (cost of crash protection)", group="Options and volatility", asset=None,
                       high="Crash protection expensive", low="Crash protection cheap"),
    "VOL_MOVE":   dict(name="MOVE (US bond volatility)", group="Options and volatility", asset=None,
                       high="Bond market stressed", low="Bond market calm"),
    "NIFTY_PCR":  dict(name="Nifty options put/call ratio (next monthly expiry)", group="Options and volatility", asset="IN_LARGE",
                       high="Heavy put buying: defensive", low="Light on puts: complacent"),
    "NIFTY_MOVE": dict(name="Nifty implied move to next monthly expiry", group="Options and volatility", asset="IN_LARGE",
                       high="Large move priced", low="Small move priced"),
    # India flows
    "FPI_EQ":     dict(name="FPI net equity investment (month, ₹ crore)", group="India flows", asset="IN_LARGE",
                       high="Heavy foreign buying", low="Heavy foreign selling"),
    "FII_IDXFUT": dict(name="FII long share of index futures", group="India flows", asset="IN_LARGE",
                       high="FIIs crowded long", low="FIIs crowded short"),
}


def value_text(gid, v):
    """How a gauge's latest value is written on the page."""
    if gid == "FPI_EQ":
        return f"−₹{-v:,.0f} cr" if v < 0 else f"+₹{v:,.0f} cr"
    if gid in ("VOL_TERM", "NIFTY_PCR"):
        return f"{v:.2f}"
    if gid == "NIFTY_MOVE":
        return f"±{v:.1f}%"
    if gid in ("VOL_SKEW", "VOL_MOVE"):
        return f"{v:.0f}"
    if gid.startswith("COT"):
        return f"{v:+.1f}% of OI"
    return f"{v:.0f}%"


# ── 1. CFTC ──────────────────────────────────────────────────────────────────
def cftc(dataset, code, who):
    longs, shorts = (f"{who}_positions_long_all", f"{who}_positions_short_all") if who == "m_money" else \
                    (f"{who}_positions_long", f"{who}_positions_short")
    rows = S.get(f"https://publicreporting.cftc.gov/resource/{dataset}.json",
                 params={"$where": f"cftc_contract_market_code='{code}' AND report_date_as_yyyy_mm_dd >= '2020-01-01'",
                         "$select": f"report_date_as_yyyy_mm_dd,{longs},{shorts},open_interest_all",
                         "$order": "report_date_as_yyyy_mm_dd", "$limit": 2000}, timeout=60).json()
    df = pd.DataFrame(rows)
    d = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    net = (df[longs].astype(float) - df[shorts].astype(float)) / df["open_interest_all"].astype(float) * 100
    return pd.Series(net.values, index=d)


# ── 2. Volatility (Yahoo) ────────────────────────────────────────────────────
def vol():
    import yfinance as yf
    import warnings
    warnings.filterwarnings("ignore")
    d = yf.download(["^VIX", "^VIX3M", "^SKEW", "^MOVE"], start="2020-01-01", progress=False, auto_adjust=False)["Close"]
    d.index = pd.to_datetime(d.index).tz_localize(None)
    return {"VOL_TERM": (d["^VIX3M"] / d["^VIX"]).dropna(), "VOL_SKEW": d["^SKEW"].dropna(), "VOL_MOVE": d["^MOVE"].dropna()}


# ── 3. NSE archive files ─────────────────────────────────────────────────────
def nse_file(url, cache_name):
    p = os.path.join(RAW, cache_name)
    if os.path.exists(p):
        return open(p, "rb").read() or None
    r = S.get(url, timeout=60)
    time.sleep(PAUSE)
    if r.status_code == 403:
        raise NseBlocked(url)
    data = r.content if r.status_code == 200 and len(r.content) > 200 else b""
    open(p, "wb").write(data)              # empty file = holiday / missing, never refetched
    return data or None


def trading_day_file(day, fmt_url, fmt_cache, back=5):
    """Try `day` and up to `back` days earlier (holidays); return (date, bytes)."""
    for k in range(back + 1):
        d = day - dt.timedelta(days=k)
        if d.weekday() >= 5:
            continue
        b = nse_file(fmt_url(d), fmt_cache(d))
        if b:
            return d, b
    return None, None


def month_ends(start, end):
    return [m.date() for m in pd.date_range(start, end, freq="ME")]


def nifty_options(day_bytes):
    """Implied move and put/call ratio for the next three monthly Nifty expiries."""
    z = zipfile.ZipFile(io.BytesIO(day_bytes))
    df = pd.read_csv(z.open(z.namelist()[0]))
    o = df[(df.TckrSymb == "NIFTY") & (df.FinInstrmTp == "IDO")].copy()
    o["XpryDt"] = pd.to_datetime(o["XpryDt"])
    trade = pd.to_datetime(df["TradDt"].iloc[0])
    o = o[o.XpryDt > trade]
    monthly = o.groupby(o.XpryDt.dt.to_period("M"))["XpryDt"].max().sort_values().head(3)
    out = []
    for exp in monthly:
        e = o[o.XpryDt == exp]
        spot = float(e.UndrlygPric.iloc[0])
        strikes = e.StrkPric.unique()
        atm = strikes[np.argmin(np.abs(strikes - spot))]
        ce = e[(e.StrkPric == atm) & (e.OptnTp == "CE")].SttlmPric
        pe = e[(e.StrkPric == atm) & (e.OptnTp == "PE")].SttlmPric
        put_oi, call_oi = e[e.OptnTp == "PE"].OpnIntrst.sum(), e[e.OptnTp == "CE"].OpnIntrst.sum()
        out.append(dict(underlying="NIFTY", as_of=trade.date(), expiry=exp.date(), spot=spot, atm=float(atm),
                        implied_move=float(ce.iloc[0] + pe.iloc[0]) / spot if len(ce) and len(pe) else np.nan,
                        pcr=put_oi / call_oi if call_oi else np.nan, days=(exp - trade).days))
    return out


def participant_fii(text):
    """FII long share of index futures from NSE's participant-wise OI file."""
    lines = [l for l in text.splitlines() if l.strip()]
    rows = list(pd.read_csv(io.StringIO("\n".join(lines[1:]))).itertuples(index=False))
    for r in rows:
        if str(r[0]).strip().upper() == "FII":
            lng, sht = float(r[1]), float(r[2])
            return lng / (lng + sht) * 100
    return None


# ── 4. NSDL FPI monthly flows ────────────────────────────────────────────────
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def nsdl_fpi(years):
    u = "https://www.fpi.nsdl.co.in/web/Reports/Yearwise.aspx?RptType=6"
    page = S.get(u, timeout=60).text
    out = {}
    for y in years:
        f = {m[0]: m[1] for m in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]+" value="([^"]*)"', page)}
        f.update({"__EVENTTARGET": "ddl", "ddl": str(y)})
        p = S.post(u, data=f, timeout=60).text
        t = pd.read_html(io.StringIO(p))[1]
        t.columns = [str(c[-1]) if isinstance(c, tuple) else str(c) for c in t.columns]
        for _, r in t.iterrows():
            name = str(r.iloc[0]).strip()
            if name in MONTHS:
                v = pd.to_numeric(str(r.iloc[1]).replace(",", ""), errors="coerce")
                if pd.notna(v):
                    out[pd.Timestamp(y, MONTHS.index(name) + 1, 1) + pd.offsets.MonthEnd(0)] = float(v)
        time.sleep(1.0)
    return pd.Series(out).sort_index()


# ── 5. SPY options snapshot ──────────────────────────────────────────────────
def spy_options():
    import yfinance as yf
    tk = yf.Ticker("SPY")
    spot = float(tk.history(period="5d")["Close"].iloc[-1])
    out, today = [], dt.date.today()
    monthly = [e for e in tk.options if dt.date.fromisoformat(e).weekday() == 4 and 15 <= dt.date.fromisoformat(e).day <= 21]
    for e in monthly[:3]:
        ch = tk.option_chain(e)
        c, p = ch.calls, ch.puts
        k = c.strike.iloc[(c.strike - spot).abs().argmin()]
        def mid(df):
            r = df[df.strike == k].iloc[0]
            return (r.bid + r.ask) / 2 if r.bid > 0 and r.ask > 0 else r.lastPrice
        out.append(dict(underlying="SPY", as_of=today, expiry=dt.date.fromisoformat(e), spot=spot, atm=float(k),
                        implied_move=(mid(c) + mid(p)) / spot, pcr=p.openInterest.sum() / max(c.openInterest.sum(), 1),
                        days=(dt.date.fromisoformat(e) - today).days))
    return out


def main():
    today = dt.date.today()
    series, implied, notes = {}, [], []

    for gid, g in GAUGES.items():
        if "src" in g:
            try:
                series[gid] = cftc(*g["src"])
            except Exception as e:
                notes.append(f"{gid}: {e}")
    try:
        series.update(vol())
    except Exception as e:
        notes.append(f"vol: {e}")

    # NSE archives: month-ends (plus the latest trading day) — polite and cached.
    fo_url = lambda d: f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
    fo_cache = lambda d: f"fo_{d:%Y%m%d}.zip"
    po_url = lambda d: f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv"
    po_cache = lambda d: f"poi_{d:%Y%m%d}.csv"
    pcr, move, fii = {}, {}, {}
    try:
        for me in month_ends("2024-08-01", today) + [today]:
            d, b = trading_day_file(min(me, today), fo_url, fo_cache)
            if b:
                opts = nifty_options(b)
                if opts:
                    implied += opts
                    pcr[pd.Timestamp(d)], move[pd.Timestamp(d)] = opts[0]["pcr"], opts[0]["implied_move"] * 100
        for me in month_ends("2023-08-01", today) + [today]:
            d, b = trading_day_file(min(me, today), po_url, po_cache)
            if b:
                v = participant_fii(b.decode("utf-8", "ignore"))
                if v is not None:
                    fii[pd.Timestamp(d)] = v
    except NseBlocked as e:
        notes.append(f"NSE blocked at {e}; stopped NSE fetching, kept what was cached")
    series["NIFTY_PCR"], series["NIFTY_MOVE"], series["FII_IDXFUT"] = pd.Series(pcr), pd.Series(move), pd.Series(fii)

    try:
        series["FPI_EQ"] = nsdl_fpi(range(today.year - 3, today.year + 1))
    except Exception as e:
        notes.append(f"NSDL: {e}")
    try:
        implied += spy_options()
    except Exception as e:
        notes.append(f"SPY options: {e}")

    rows = []
    for gid, s in series.items():
        s = s.dropna().sort_index()
        rows += [dict(gauge=gid, date=d.date(), value=float(v)) for d, v in s.items()]
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "gauges.csv"), index=False)
    pd.DataFrame(implied).drop_duplicates(["underlying", "as_of", "expiry"]).to_csv(os.path.join(OUT, "implied.csv"), index=False)
    json.dump(dict(run=str(today), notes=notes), open(os.path.join(OUT, "run.json"), "w"), indent=2)
    for gid in GAUGES:
        s = series.get(gid)
        print(f"{gid:11} {'MISSING' if s is None or s.empty else f'{len(s):5} obs, last {s.index.max().date()} = {s.iloc[-1]:.2f}'}")
    for n in notes:
        print("NOTE:", n)


if __name__ == "__main__":
    main()

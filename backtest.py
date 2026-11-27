#!/usr/bin/env python3
"""
backtest.py — would the dashboard's signals have helped in the past?
(spec: SPEC-valuation-backtest.md, part 2)

Four tests, each on long public histories:
  1. Valuation    starting P/E (vs own history) against later returns:
                  Nifty 50 and S&P 500 over 1, 3 and 5 years; and across world
                  markets, cheapest third vs most expensive third over 12 months
  2. Regime       the analysis.py regime gauge (6 votes) rebuilt month by month,
                  against the next 1 and 3 months' returns
  3. Momentum     does a top-third 3-month return carry on next month?
                  (the premise behind the quilt's persistence flags)
  4. Alerts       the watchlist's alerts: what happened after each first trigger

Rules:
  - No look-ahead: a signal uses only data up to its date; returns start after it.
  - Overlapping windows overstate the evidence, so every result reports the number
    of independent periods it rests on (months ÷ horizon, or separate events).
  - Verdicts:   Useful         |t| ≥ 2 on independent periods and the same sign in
                               both halves of the sample
                Weak           |t| ≥ 1 with the same sign in both halves, or |t| ≥ 2
                               but the halves disagree
                No evidence    otherwise
                Too few        fewer than 5 independent periods
  - Descriptive only: no costs, taxes or leverage. Not a trading strategy.

Writes data/backtest/results.json (every table, with sample sizes).
Usage: python3 backtest.py            (fetches long histories, cached)
       python3 backtest.py --offline  (cached data only)
Market data only. Nothing here reads private/ or family holdings.
"""

import datetime as dt
import json
import math
import os
import sys
import time
import functools
print = functools.partial(print, flush=True)

import numpy as np
import pandas as pd

import registry
import sources

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "backtest")
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
OFFLINE = "--offline" in sys.argv
LONG_START = "1993-01-01"

YAHOO_LONG = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "HYG", "GLD", "SLV", "BNO", "BTC-USD", "RSP",
              "XLK", "XLY", "XLI", "XLF", "XLP", "XLU", "XLV",
              "FXI", "EWH", "EWJ", "EWY", "EWT", "EWG", "EWU", "INDA",
              "HG=F", "GC=F", "BZ=F", "^VIX", "^VIX3M", "USDINR=X"]
NIFTY_LONG = {"IN_LARGE": "NIFTY 50", "IN_MID": "NIFTY MIDCAP 150", "IN_SMALL": "NIFTY SMALLCAP 250",
              "IN_FMCG": "NIFTY FMCG", "IN_PHARMA": "NIFTY PHARMA", "IN_BANK": "NIFTY BANK",
              "IN_AUTO": "NIFTY AUTO", "IN_METAL": "NIFTY METAL", "IN_REALTY": "NIFTY REALTY"}
FRED_LONG = {"USDINR": "DEXINUS", "USDJPY": "DEXJPUS", "HY_OAS": "BAMLH0A0HYM2", "BAA10Y": "BAA10Y", "US10Y": "DGS10",
             "IN10Y": "INDIRLTLT01STM", "JP10Y_M": "IRLTLT01JPM156N"}


# ── Data ─────────────────────────────────────────────────────────────────────
def _csv(name):
    return os.path.join(RAW, f"{name.replace('^', '_').replace('=', '_')}.csv")


def _read(name):
    p = _csv(name)
    if not os.path.exists(p):
        return None
    s = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"].astype(float)
    return s[~s.index.duplicated(keep="last")].sort_index()


def _fresh(name, days=3):
    p = _csv(name)
    return os.path.exists(p) and (time.time() - os.path.getmtime(p)) < days * 86400


def yahoo_long():
    need = [t for t in YAHOO_LONG if OFFLINE is False and not _fresh(t)]
    if need:
        import warnings
        import yfinance as yf
        warnings.filterwarnings("ignore")
        d = yf.download(need, start=LONG_START, auto_adjust=False, progress=False, group_by="column", threads=True)
        for t in need:
            try:
                s = d["Adj Close"][t].dropna()
            except KeyError:
                continue
            s.index = pd.to_datetime(s.index).tz_localize(None)
            if len(s):
                s.rename("value").rename_axis("date").to_csv(_csv(t))
    return {t: _read(t) for t in YAHOO_LONG}


def nifty_long():
    """Nifty total-return indices from April 2005: older chunks from niftyindices,
    joined to the pipeline's own cache from 2020 (one request at a time)."""
    out = {}
    for qid, name in NIFTY_LONG.items():
        old = _read(f"nifty_tri_{qid}")
        if old is None and not OFFLINE:
            rows, a = {}, dt.date(2005, 4, 1)
            while a < dt.date(2020, 1, 15):
                b = min(a + dt.timedelta(days=360), dt.date(2020, 1, 15))
                for rec in sources._ni_post("getTotalReturnIndexString", name, a, b):
                    try:
                        rows[pd.Timestamp(dt.datetime.strptime(rec["Date"].strip(), "%d %b %Y"))] = float(str(rec["TotalReturnsIndex"]).replace(",", ""))
                    except (ValueError, KeyError, AttributeError):
                        continue
                a = b + dt.timedelta(days=1)
            old = pd.Series(rows, dtype=float).sort_index()
            old.rename("value").rename_axis("date").to_csv(_csv(f"nifty_tri_{qid}"))
        new = sources._load_cache("nifty_tri", name)
        if old is None or old.empty:
            out[qid] = new
            continue
        # Same index, same provider: check the overlap matches, then join.
        ov = old.index.intersection(new.index)
        if len(ov):
            ratio = (new[ov] / old[ov]).median()
            if abs(ratio - 1) > 0.002:
                print(f"  {qid}: old/new levels differ by {ratio - 1:+.3%}; rescaling the old chunk")
                old = old * ratio
        out[qid] = pd.concat([old[old.index < new.index.min()], new]) if len(new) else old
    return out


def fred_long():
    out = {}
    for k, sid in FRED_LONG.items():
        try:
            out[k] = sources._load_cache("fred", sid) if OFFLINE else sources.fred(sid)
        except Exception:
            out[k] = sources._load_cache("fred", sid)
    return out


def fpi_long():
    """NSDL FPI net equity investment by month (₹ crore), 2005 onward (cached)."""
    s = _read("fpi_eq")
    if (s is None or s.index.min().year > 2005) and not OFFLINE:
        import positioning
        for attempt in range(2):
            try:
                s = positioning.nsdl_fpi(range(2005, dt.date.today().year + 1))
                s.rename("value").rename_axis("date").to_csv(_csv("fpi_eq"))
                break
            except Exception as e:      # NSDL sometimes resets connections; fall back to recent history
                print(f"  NSDL FPI history not fetched ({type(e).__name__}); attempt {attempt + 1}", flush=True)
                s = None
                time.sleep(20)
    g = os.path.join(HERE, "data", "positioning", "gauges.csv")
    if os.path.exists(g):
        gg = pd.read_csv(g, parse_dates=["date"])
        cur = gg[gg.gauge == "FPI_EQ"].set_index("date")["value"]
        s = cur if s is None else pd.concat([s[~s.index.isin(cur.index)], cur]).sort_index()
    return s


def me(s):
    return s.resample("ME").last().dropna()


# ── Statistics ───────────────────────────────────────────────────────────────
def verdict(effect_series, n_indep, first_half, second_half):
    """effect_series: per-period effects (already independent-ish sample);
    returns (verdict, t)."""
    e = pd.Series(effect_series).dropna()
    if n_indep < 5 or len(e) < 2:
        return "Too few to judge", None
    sd = e.std()
    t = e.mean() / (sd / math.sqrt(n_indep)) if sd > 0 else 0.0
    same = (first_half is not None and second_half is not None and np.sign(first_half) == np.sign(second_half) != 0)
    if abs(t) >= 2 and same:
        return "Useful", t
    if (abs(t) >= 1 and same) or abs(t) >= 2:
        return "Weak", t
    return "No evidence", t


def fwd(level_me, months):
    """Annualised forward total return from each month-end over `months`."""
    r = level_me.shift(-months) / level_me - 1
    return (1 + r) ** (12 / months) - 1 if months >= 12 else r


def r4(x):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else round(float(x), 4)


# ── 1. Valuation ─────────────────────────────────────────────────────────────
def test_valuation(tri, yh, usdinr_me):
    vh = pd.read_csv(os.path.join(HERE, "data", "valuation", "valuation_hist.csv"), parse_dates=["month"])
    res = {"single": [], "cross": None}
    for vid, name, lvl, ccy in [("IN_LARGE", "Nifty 50", me(tri["IN_LARGE"]), "INR"), ("US_LARGE", "S&P 500", me(yh["SPY"]), "USD")]:
        v = vh[vh.id == vid].set_index("month")
        for h, lab in [(12, "1 year"), (36, "3 years"), (60, "5 years")]:
            f = fwd(lvl, h)
            d = pd.concat([v["pe"], v["pctl"], f.rename("fwd")], axis=1).dropna(subset=["pe", "fwd"])
            if len(d) < 24:
                continue
            corr_pe = d["pe"].rank().corr(d["fwd"].rank())   # Spearman (no scipy)
            buckets = []
            dp = d.dropna(subset=["pctl"])
            for lo, hi, bl in [(0, 20, "Cheap (≤20th)"), (20, 40, "20–40th"), (40, 60, "40–60th"), (60, 80, "60–80th"), (80, 101, "Expensive (≥80th)")]:
                x = dp[(dp.pctl >= lo) & (dp.pctl < hi)]
                buckets.append(dict(bucket=bl, n_months=len(x), avg_fwd=r4(x.fwd.mean()) if len(x) else None))
            # Effect: cheap half minus expensive half of the market's own history (percentile < 50 vs ≥ 50),
            # judged on non-overlapping start months (one every `h` months) so each period counts once.
            base = dp
            if len(base) < 24:
                continue
            cheap, dear = base[base.pctl < 50].fwd, base[base.pctl >= 50].fwd
            mid = base.index[len(base) // 2]
            h1, h2 = base[base.index < mid], base[base.index >= mid]
            e1 = h1[h1.pctl < 50].fwd.mean() - h1[h1.pctl >= 50].fwd.mean()
            e2 = h2[h2.pctl < 50].fwd.mean() - h2[h2.pctl >= 50].fwd.mean()
            ts = []
            for off in range(h):                      # every offset, then average: uses all months, counts each period once
                smp = base.iloc[off::h]
                a, b = smp[smp.pctl < 50].fwd, smp[smp.pctl >= 50].fwd
                if len(a) >= 2 and len(b) >= 2 and (a.var() + b.var()) > 0:
                    ts.append((a.mean() - b.mean()) / math.sqrt(a.var() / len(a) + b.var() / len(b)))
            n_ind = max(1, len(base) // h)
            t = float(np.mean(ts)) if ts else None
            if n_ind < 5 or t is None:
                vd = "Too few to judge"
            else:
                same = np.sign(e1) == np.sign(e2) != 0
                vd = "Useful" if abs(t) >= 2 and same else "Weak" if (abs(t) >= 1 and same) or abs(t) >= 2 else "No evidence"
            d = base
            res["single"].append(dict(market=name, ccy=ccy, horizon=lab, months=len(d), start=str(d.index.min().date()),
                                      end=str(d.index.max().date()), independent=n_ind, spearman_pe_vs_fwd=r4(corr_pe),
                                      cheap_minus_dear=r4(cheap.mean() - dear.mean()), first_half=r4(e1), second_half=r4(e2),
                                      buckets=buckets, verdict=vd, t=r4(t)))
    # Cross-country: each month, cheapest third vs most expensive third by own-history percentile; next 12 months in USD
    mk = {"US_LARGE": yh["SPY"], "GL_CN_LARGE": yh["FXI"], "GL_HK": yh["EWH"], "GL_JP": yh["EWJ"], "GL_KR": yh["EWY"],
          "GL_TW": yh["EWT"], "GL_DE": yh["EWG"], "GL_UK": yh["EWU"]}
    lv = {k: me(s) for k, s in mk.items() if s is not None}
    lv["IN_LARGE"] = (me(tri["IN_LARGE"]) / usdinr_me.reindex(me(tri["IN_LARGE"]).index, method="ffill")).dropna()
    P = vh[vh.id.isin(lv)].pivot(index="month", columns="id", values="pctl")
    F12 = pd.DataFrame({k: s.shift(-12) / s - 1 for k, s in lv.items()})
    rows = []
    for d, p in P.iterrows():
        p = p.dropna()
        if len(p) < 6 or d not in F12.index:
            continue
        f = F12.loc[d, p.index].dropna()
        p = p[f.index]
        if len(p) < 6:
            continue
        k = len(p) // 3
        cheap, dear = p.nsmallest(k).index, p.nlargest(k).index
        rows.append(dict(month=d, cheap=f[cheap].mean(), dear=f[dear].mean(), n=len(p)))
    if rows:
        X = pd.DataFrame(rows).set_index("month")
        X["spread"] = X.cheap - X.dear
        n_ind = len(X) // 12
        mid = X.index[len(X) // 2]
        e1, e2 = X[X.index < mid].spread.mean(), X[X.index >= mid].spread.mean()
        blocks = X.groupby(np.arange(len(X)) // 12).spread.mean()
        vd, t = verdict(blocks, n_ind, e1, e2)
        res["cross"] = dict(months=len(X), start=str(X.index.min().date()), end=str(X.index.max().date()), independent=n_ind,
                            markets_per_month=r4(X.n.mean()), avg_cheap=r4(X.cheap.mean()), avg_dear=r4(X.dear.mean()),
                            spread=r4(X.spread.mean()), hit_rate=r4((X.spread > 0).mean()), first_half=r4(e1), second_half=r4(e2),
                            verdict=vd, t=r4(t))
    return res


# ── 2. Regime ────────────────────────────────────────────────────────────────
def test_regime(tri, yh, fr):
    def chg3(s):
        m = me(s)
        return m / m.shift(3) - 1
    cu_au = chg3((yh["HG=F"] / yh["GC=F"]).dropna())
    rsp = chg3((yh["RSP"] / yh["SPY"]).dropna())
    hyt = chg3((yh["HYG"] / yh["TLT"]).dropna())
    mid_fmcg = chg3((tri["IN_MID"] / tri["IN_FMCG"]).dropna())
    us_cyc = pd.concat([chg3(yh[t]) for t in ["XLK", "XLY", "XLI", "XLF"]], axis=1).mean(axis=1)
    us_def = pd.concat([chg3(yh[t]) for t in ["XLP", "XLU", "XLV"]], axis=1).mean(axis=1)
    in_cyc = pd.concat([chg3(tri[t]) for t in ["IN_BANK", "IN_AUTO", "IN_METAL", "IN_REALTY"]], axis=1).mean(axis=1)
    in_def = pd.concat([chg3(tri[t]) for t in ["IN_FMCG", "IN_PHARMA"]], axis=1).mean(axis=1)
    sec = ((us_cyc - us_def) + (in_cyc - in_def)) / 2
    # FRED keeps only three years of the ICE high-yield spread, so before that the backtest uses
    # Moody's Baa corporate spread over 10-year Treasuries (BAA10Y, from 1986) for this vote. Over the three
    # years both exist, their 3-month changes point the same way about 80% of the time.
    baa = me(fr["BAA10Y"])
    hyo = me(fr["HY_OAS"])
    hy3 = (hyo - hyo.shift(3)).dropna().combine_first(baa - baa.shift(3))   # the real spread wherever it exists
    V = pd.concat([cu_au > 0, mid_fmcg > 0, hyt > 0, rsp > 0, sec > 0, hy3 < 0], axis=1,
                  keys=["cu_au", "mid_fmcg", "hyg_tlt", "rsp_spy", "sectors", "hy_spread"])
    raw = pd.concat([cu_au, mid_fmcg, hyt, rsp, sec, hy3], axis=1).dropna()
    V = V.loc[raw.index]
    score = V.sum(axis=1)
    regime = pd.Series(np.where(score >= 4, "Risk-on", np.where(score <= 2, "Defensive", "Mixed")), index=score.index)
    usdinr = me(fr["USDINR"])
    assets = {"S&P 500 (USD)": me(yh["SPY"]), "Nifty 50 (INR)": me(tri["IN_LARGE"]),
              "Global 60/40 (USD)": None}
    spy_r, tlt_r = me(yh["SPY"]).pct_change(), me(yh["TLT"]).pct_change()
    assets["Global 60/40 (USD)"] = (1 + (0.6 * spy_r + 0.4 * tlt_r).dropna()).cumprod()
    out = dict(start=str(regime.index.min().date()), end=str(regime.index.max().date()), months=len(regime),
               share={k: r4((regime == k).mean()) for k in ["Risk-on", "Mixed", "Defensive"]}, rows=[], verdicts=[])
    for aname, lvl in assets.items():
        for h in [1, 3]:
            f = (lvl.shift(-h) / lvl - 1).reindex(regime.index)
            d = pd.DataFrame({"reg": regime, "f": f}).dropna()
            allm = d.f.mean()
            row = dict(asset=aname, horizon=f"{h} month{'s' if h > 1 else ''}", all=r4(allm), n=len(d))
            for k in ["Risk-on", "Mixed", "Defensive"]:
                x = d[d.reg == k].f
                row[k] = r4(x.mean()) if len(x) else None
                row[f"n_{k}"] = len(x)
                row[f"hit_{k}"] = r4((x > 0).mean()) if len(x) else None
            # Effect: risk-on minus defensive, on non-overlapping months
            dd = d.iloc[::h]
            mid = dd.index[len(dd) // 2]
            def spread(z):
                a, b = z[z.reg == "Risk-on"].f, z[z.reg == "Defensive"].f
                return a.mean() - b.mean() if len(a) and len(b) else np.nan
            e1, e2 = spread(dd[dd.index < mid]), spread(dd[dd.index >= mid])
            on, de = dd[dd.reg == "Risk-on"].f, dd[dd.reg == "Defensive"].f
            n_ind = min(len(on), len(de))
            if n_ind >= 5 and on.std() > 0 and de.std() > 0:
                se = math.sqrt(on.var() / len(on) + de.var() / len(de))
                t = (on.mean() - de.mean()) / se
                same = np.sign(e1) == np.sign(e2) != 0
                vd = "Useful" if abs(t) >= 2 and same else "Weak" if (abs(t) >= 1 and same) or abs(t) >= 2 else "No evidence"
            else:
                t, vd = None, "Too few to judge"
            row.update(on_minus_def=r4(on.mean() - de.mean()), first_half=r4(e1), second_half=r4(e2), t=r4(t), verdict=vd,
                       independent=n_ind)
            out["rows"].append(row)
    out["latest"] = dict(month=str(regime.index[-1].date()), regime=regime.iloc[-1], score=int(score.iloc[-1]))
    # Check: the rebuilt regime should match analysis.py for the months both cover
    chk = []
    for f in sorted(os.listdir(os.path.join(HERE, "data", "analysis"))):
        if f.startswith("facts_") and f.endswith(".json"):
            fx = json.load(open(os.path.join(HERE, "data", "analysis", f)))
            r = [x for x in fx["facts"] if x["id"] == "regime"]
            m = pd.Timestamp(fx["month"]) + pd.offsets.MonthEnd(0)
            if r and m in regime.index:
                chk.append(dict(month=fx["month"], analysis=r[0]["numbers"]["regime"], rebuilt=regime[m],
                                analysis_score=r[0]["numbers"]["score"], rebuilt_score=int(score[m])))
    out["matches_analysis"] = chk
    return out, regime


# ── 3. Momentum ──────────────────────────────────────────────────────────────
def test_momentum(tri, yh, usdinr_me):
    def inr(s):
        m = me(s)
        return (m * usdinr_me.reindex(m.index, method="ffill")).dropna()
    universes = {
        "Asset classes (in rupees)": {"Nifty 50": me(tri["IN_LARGE"]), "Midcap 150": me(tri["IN_MID"]), "Smallcap 250": me(tri["IN_SMALL"]),
                                      "S&P 500": inr(yh["SPY"]), "Nasdaq 100": inr(yh["QQQ"]), "Russell 2000": inr(yh["IWM"]),
                                      "Dev ex-US": inr(yh["EFA"]), "Emerging": inr(yh["EEM"]), "UST 20Y+": inr(yh["TLT"]),
                                      "US HY": inr(yh["HYG"]), "Gold": inr(yh["GLD"]), "Silver": inr(yh["SLV"]),
                                      "Brent": inr(yh["BNO"]), "Bitcoin": inr(yh["BTC-USD"])},
        "World equity markets (in dollars)": {"India": (me(tri["IN_LARGE"]) / usdinr_me.reindex(me(tri["IN_LARGE"]).index, method="ffill")).dropna(),
                                              "US": me(yh["SPY"]), "China": me(yh["FXI"]), "Hong Kong": me(yh["EWH"]),
                                              "Japan": me(yh["EWJ"]), "Korea": me(yh["EWY"]), "Taiwan": me(yh["EWT"]),
                                              "Germany": me(yh["EWG"]), "UK": me(yh["EWU"])},
    }
    out = []
    for uname, U in universes.items():
        L = pd.DataFrame({k: v for k, v in U.items() if v is not None})
        L = L[L.index >= "2005-05-31"]
        r3 = L / L.shift(3) - 1
        n1 = L.shift(-1) / L - 1
        rows = []
        for d in L.index:
            a = r3.loc[d].dropna()
            b = n1.loc[d].reindex(a.index).dropna()
            a = a[b.index]
            if len(a) < 6:
                continue
            k = len(a) // 3
            top, bot = a.nlargest(k).index, a.nsmallest(k).index
            rows.append(dict(month=d, top=b[top].mean(), bottom=b[bot].mean(), n=len(a)))
        X = pd.DataFrame(rows).set_index("month")
        X["spread"] = X.top - X.bottom
        mid = X.index[len(X) // 2]
        e1, e2 = X[X.index < mid].spread.mean(), X[X.index >= mid].spread.mean()
        vd, t = verdict(X.spread, len(X), e1, e2)
        out.append(dict(universe=uname, months=len(X), start=str(X.index.min().date()), end=str(X.index.max().date()),
                        independent=len(X), assets_per_month=r4(X.n.mean()), avg_top=r4(X.top.mean()), avg_bottom=r4(X.bottom.mean()),
                        spread=r4(X.spread.mean()), hit_rate=r4((X.spread > 0).mean()), first_half=r4(e1), second_half=r4(e2),
                        verdict=vd, t=r4(t)))
    return out


# ── 4. Watchlist alerts ──────────────────────────────────────────────────────
def first_triggers(cond, quiet_days=91):
    """Dates when cond turns true after at least `quiet_days` calendar days with it false."""
    cond = cond.dropna().astype(bool)
    events, last_true, seen_false = [], None, False
    for d, v in cond.items():
        if not v:
            seen_false = True
            continue
        # A trigger is a crossing: the condition was false before, and quiet for `quiet_days`.
        if seen_false and (last_true is None or (d - last_true).days > quiet_days):
            events.append(d)
        last_true = d
    return events


NOTES = {
    "hyoas": "FRED now publishes only the last three years of this series.",
    "brent": "Several of these spikes came as markets recovered from a fall (early 2009, early 2016, mid-2020), so part of the "
             "later gain reflects the recovery rather than oil itself.",
}


def gt(s, x, eq=False):
    return (s >= x) if eq else (s > x)


def lt(s, x):
    return s <= x


def test_alerts(tri, yh, fr, fpi):
    nifty = tri["IN_LARGE"].dropna()
    spy = yh["SPY"].dropna()
    mid = tri["IN_MID"].dropna()
    usdinr = fr["USDINR"].dropna()
    vix, vix3m = yh["^VIX"], yh["^VIX3M"]
    usdjpy = fr["USDJPY"].dropna()
    fxi_inr = (yh["FXI"] * usdinr.reindex(yh["FXI"].index, method="ffill")).dropna()
    brent = yh["BZ=F"].dropna()
    in10, us10 = fr["IN10Y"].dropna(), fr["US10Y"].dropna()
    us10m = us10.resample("MS").mean()
    in_us = (in10 - us10m.reindex(in10.index)).dropna()
    in_us.index = in_us.index + pd.offsets.MonthEnd(0)
    jp = fr["JP10Y_M"].dropna()
    rel = (fxi_inr.pct_change(63) - nifty.reindex(fxi_inr.index, method="ffill").pct_change(63)).dropna()
    alerts = [
        ("vix", "VIX closes above 30", vix > 30, "S&P 500", spy),
        ("vixterm", "VIX curve inverts (VIX above 3-month VIX)", gt((vix / vix3m.reindex(vix.index)).dropna(), 1.0), "S&P 500", spy),
        ("hyoas", "US high-yield spread above 4%", fr["HY_OAS"] > 4.0, "S&P 500", spy),
        ("yen", "Yen gains 4% or more against the dollar in a month", lt(usdjpy.pct_change(21).dropna(), -0.04), "S&P 500", spy),
        ("jp10y", "Japan 10Y yield above 3%", jp > 3.0, "S&P 500", spy),
        ("cn_in", "China large caps beat the Nifty 50 by 10pp over 3 months", rel > 0.10, "Midcap 150", mid),
        ("in_us", "India 10Y falls to less than 2pp above the US", in_us < 2.0, "Midcap 150", mid),
        ("brent", "Brent rises 15% or more in a month", gt(brent.pct_change(21).dropna(), 0.15, eq=True), "Midcap 150", mid),
        ("rupee", "Rupee falls 2% or more against the dollar in a month", gt(usdinr.pct_change(21).dropna(), 0.02, eq=True), "Midcap 150", mid),
    ]
    if fpi is not None and len(fpi):
        neg = fpi < 0
        streak = neg.groupby((~neg).cumsum()).cumsum()
        alerts.append(("fpi_streak", "Foreign investors net sellers for 3 months running", streak >= 3, "Midcap 150", mid))
        alerts.append(("fpi_big", "Foreign selling above ₹25,000 crore in a month", fpi < -25000, "Midcap 150", mid))
    horizons = [(21, 1), (63, 3), (126, 6)]

    def fwd_after(px, d, days):
        px = px[px.index > d]          # start the day after the signal (monthly signals: the next month)
        if len(px) <= days:
            return np.nan
        return px.iloc[days] / px.iloc[0] - 1

    def base_rate(px, days, start):
        p = px[px.index >= start]
        r = p.shift(-days) / p - 1
        return r.dropna().mean()

    out = []
    for aid, name, cond, other_name, other in alerts:
        cond = cond.dropna()
        if cond.empty:
            continue
        monthly = cond.index.to_series().diff().dt.days.median() > 20
        ev = first_triggers(cond, quiet_days=91)
        start = max(cond.index.min(), nifty.index.min())
        ev = [d for d in ev if d >= start]
        row = dict(id=aid, alert=name, events=len(ev), first=str(ev[0].date()) if ev else None, last=str(ev[-1].date()) if ev else None,
                   data_from=str(pd.Timestamp(start).date()), other=other_name, horizons=[],
                   note=NOTES.get(aid, ""))
        for days, mlab in horizons:
            for lab, px in [("Nifty 50", nifty), (other_name, other)]:
                rs = [fwd_after(px, d + (pd.offsets.MonthEnd(0) if monthly else pd.Timedelta(0)), days) for d in ev]
                rs = pd.Series(rs, index=ev).dropna()
                base = base_rate(px, days, start)
                if len(rs) == 0:
                    row["horizons"].append(dict(months=mlab, asset=lab, n=0))
                    continue
                excess = rs - base
                mid = len(excess) // 2
                e1 = excess.iloc[:mid].mean() if mid else None
                e2 = excess.iloc[mid:].mean() if mid else None
                vd, t = verdict(excess, len(excess), e1, e2)
                row["horizons"].append(dict(months=mlab, asset=lab, n=len(rs), avg=r4(rs.mean()), median=r4(rs.median()),
                                            base=r4(base), excess=r4(rs.mean() - base), hit=r4((rs > 0).mean()),
                                            worst=r4(rs.min()), first_half=r4(e1), second_half=r4(e2), verdict=vd, t=r4(t)))
        row["event_dates"] = [str(d.date()) for d in ev]
        out.append(row)
    return out


# ── Plain-language summary ───────────────────────────────────────────────────
def pctx(x, d=1):
    return "n/a" if x is None else f"{x*100:+.{d}f}%"


def summarise(R):
    S = []
    # Valuation
    for r in R["valuation"]["single"]:
        if r["horizon"] in ("1 year", "5 years"):
            cheap = next((b for b in r["buckets"] if b["bucket"].startswith("Cheap")), None)
            dear = next((b for b in r["buckets"] if b["bucket"].startswith("Expensive")), None)
            S.append(dict(test="Valuation", signal=f"{r['market']}: starting P/E vs the next {r['horizon']}", verdict=r["verdict"],
                          text=(f"From {r['start'][:4]} to {r['end'][:4]}, months in the cheaper half of the {r['market']}'s own P/E history were followed by "
                                f"{abs(r['cheap_minus_dear'] or 0)*100:.1f}% a year {'more' if (r['cheap_minus_dear'] or 0) >= 0 else 'less'} than months in the more expensive half, over the next {r['horizon']}. "
                                + (f"Cheapest fifth: {pctx(cheap['avg_fwd'])} a year ({cheap['n_months']} months); most expensive fifth: {pctx(dear['avg_fwd'])} ({dear['n_months']} months). "
                                   if cheap and dear and cheap["n_months"] >= 6 and dear["n_months"] >= 6 else "")
                                + f"Rests on about {r['independent']} independent {r['horizon'].replace('1 year', 'one-year').replace('3 years', 'three-year').replace('5 years', 'five-year')} periods."),
                          n=r["independent"]))
    c = R["valuation"]["cross"]
    if c:
        S.append(dict(test="Valuation", signal="World markets: cheapest third vs most expensive third (next 12 months)", verdict=c["verdict"],
                      text=(f"Each month from {c['start'][:4]}, the third of about {c['markets_per_month']:.0f} markets that were cheapest against their own history returned "
                            f"{pctx(c['avg_cheap'])} over the next 12 months in dollars, against {pctx(c['avg_dear'])} for the most expensive third "
                            f"(cheap beat expensive in {c['hit_rate']*100:.0f}% of months). About {c['independent']} independent years."),
                      n=c["independent"]))
    # Regime
    for r in R["regime"]["rows"]:
        if r["horizon"] == "3 months":
            S.append(dict(test="Regime", signal=f"Regime gauge vs the next 3 months: {r['asset']}", verdict=r["verdict"],
                          text=(f"After a Risk-on reading the next 3 months averaged {pctx(r['Risk-on'])} ({r['n_Risk-on']} months); after Defensive "
                                f"{pctx(r['Defensive'])} ({r['n_Defensive']} months); after Mixed {pctx(r['Mixed'])}. All months: {pctx(r['all'])}."),
                          n=r["independent"]))
    # Momentum
    for r in R["momentum"]:
        S.append(dict(test="Momentum", signal=f"Top third on 3-month return, next month: {r['universe']}", verdict=r["verdict"],
                      text=(f"From {r['start'][:4]}, the top third by 3-month return went on to return {pctx(r['avg_top'], 2)} the next month against "
                            f"{pctx(r['avg_bottom'], 2)} for the bottom third, beating it in {r['hit_rate']*100:.0f}% of {r['months']} months."),
                      n=r["independent"]))
    # Alerts
    for a in R["alerts"]:
        h = [x for x in a["horizons"] if x["months"] == 3 and x.get("n")]
        if not a["events"]:
            S.append(dict(test="Alerts", signal=a["alert"], verdict="Too few to judge",
                          text=f"Has not triggered since {a['data_from'][:4]}." + (f" {a['note']}" if a.get("note") else ""), n=0))
            continue
        parts = [f"{x['asset']} {pctx(x['avg'])} on average over the next 3 months (normal: {pctx(x['base'])}), up in {x['hit']*100:.0f}% of cases, worst {pctx(x['worst'])}"
                 for x in h]
        best = max(h, key=lambda x: abs(x["t"] or 0)) if h else None
        S.append(dict(test="Alerts", signal=a["alert"], verdict=best["verdict"] if best else "Too few to judge",
                      text=f"Triggered {a['events']} separate time{'s' if a['events'] != 1 else ''} since {a['data_from'][:4]}"
                           + (f" ({', '.join(sorted({d[:4] for d in a['event_dates']}))})" if a["events"] <= 30 else "")
                           + (". After a trigger: " + "; ".join(parts) + "." if parts else ".") + (f" {a['note']}" if a.get("note") else ""),
                      n=a["events"]))
    return S


def main():
    print("Loading long histories…")
    yh = yahoo_long()
    tri = nifty_long()
    fr = fred_long()
    fpi = fpi_long()
    usdinr_me = me(fr["USDINR"])
    R = {"generated": dt.date.today().isoformat()}
    print("1. Valuation"); R["valuation"] = test_valuation(tri, yh, usdinr_me)
    print("2. Regime"); R["regime"], _ = test_regime(tri, yh, fr)
    print("3. Momentum"); R["momentum"] = test_momentum(tri, yh, usdinr_me)
    print("4. Alerts"); R["alerts"] = test_alerts(tri, yh, fr, fpi)
    R["summary"] = summarise(R)
    R["data"] = {k: dict(start=str(v.index.min().date()), end=str(v.index.max().date())) for k, v in
                 {**{f"yahoo:{t}": s for t, s in yh.items() if s is not None and len(s)}, **{f"nifty:{k}": s for k, s in tri.items() if s is not None and len(s)},
                  **{f"fred:{k}": s for k, s in fr.items() if s is not None and len(s)}, **({"nsdl:FPI": fpi} if fpi is not None else {})}.items()}
    json.dump(R, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=str)
    for s in R["summary"]:
        print(f"[{s['verdict']}] {s['signal']}\n    {s['text']}")


if __name__ == "__main__":
    main()

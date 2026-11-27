#!/usr/bin/env python3
"""
valuation.py — is each major equity market cheap or expensive against its own
history? (spec: SPEC-valuation-backtest.md, part 1)

For every market in registry.VALUATION it builds a month-end trailing P/E
history (plus P/B and dividend yield for Indian indices), then for each month:

  pctl        where that month's P/E sits among month-end readings over the
              previous 20 years (or all history if shorter, minimum 5 years).
              Uses only data up to that month, so the backtest can reuse it.
  label       Cheap ≤20 · Below average 20–40 · Average 40–60 ·
              Above average 60–80 · Expensive ≥80 (percentile)
  ey_gap      earnings yield (100 / P/E) minus the local 10-year yield, in pp:
              how much more (or less) shares earn than government bonds
  gap_pctl    percentile of ey_gap in its own history, same window rules

NSE switched index P/E from standalone to consolidated earnings on 31 March
2021 (Nifty 50 P/E fell 18% overnight, Midcap 150 45%). Earlier NSE P/E values
are scaled by each index's own ratio across that day, so history stays
comparable. P/B did not change at the break and is kept unadjusted.

Writes data/valuation/:
  pe_monthly.csv        id, month, pe, pe_raw, pb, dy, source
  valuation_hist.csv    the full monthly table with percentiles and gaps
  valuation.csv         the latest completed month and today's reading per market
  yahoo_snapshots.csv   today's Yahoo fund P/E (appended each run; builds history)
  checks.json           cross-checks for checks.py

Usage: python3 valuation.py            (fetch, then compute)
       python3 valuation.py --offline  (compute from cached data only)
Market data only. Nothing here reads private/ or family holdings.
"""

import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

import registry
import sources

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "valuation")
DAILY = os.path.join(HERE, "data", "daily")
os.makedirs(OUT, exist_ok=True)

WINDOW_YEARS, MIN_YEARS = 20, 5
NSE_BREAK = pd.Timestamp("2021-03-31")
WPR_START = pd.Timestamp("1995-01-01")
SPLICE_RANGE = (0.8, 1.25)    # NSE break ratios outside this range: use P/E history from April 2021 only
PE_MAX = 100                  # P/E above this means earnings near zero; left out of history and percentiles
SHILLER_URL = "https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/ie_data.xls"
NSE_START = {"Markets": dt.date(2005, 1, 1), "India sectors": dt.date(2010, 1, 1)}
# Long monthly yield history: OECD monthly averages (FRED) before the daily feeds start.
Y10_LONG = {"DE10Y": "X_DE10Y_OECD", "JP10Y": "X_JP10Y_OECD", "UK10Y": "X_UK10Y_OECD"}


def label(p):
    if p is None or pd.isna(p):
        return "Short history"
    return "Cheap" if p <= 20 else "Below average" if p < 40 else "Average" if p < 60 else "Above average" if p < 80 else "Expensive"


def rolling_pctl(s, window_years=WINDOW_YEARS, min_years=MIN_YEARS):
    """Percentile of each month's value among the month-ends of the trailing window
    (strictly below, ×100), using only data up to that month."""
    s = s.dropna()
    out = pd.Series(np.nan, index=s.index)
    for i, (d, v) in enumerate(s.items()):
        w = s[(s.index > d - pd.DateOffset(years=window_years)) & (s.index <= d)]
        if w.index[0] <= d - pd.DateOffset(years=min_years) + pd.DateOffset(days=40):
            out[d] = float((w < v).mean() * 100)
    return out


def load_daily(i):
    p = os.path.join(DAILY, f"{i}.csv")
    if not os.path.exists(p):
        return None
    s = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"].astype(float)
    return s[~s.index.duplicated(keep="last")].sort_index()


def y10_monthly(key):
    """Monthly 10-year yield: monthly mean of the daily feed, with the OECD monthly
    average for months before the daily feed starts."""
    if key is None:
        return None
    s = load_daily(key)
    if s is None:
        return None
    m = s.resample("ME").mean().dropna()
    if key in Y10_LONG:
        o = load_daily(Y10_LONG[key])
        if o is not None:
            o.index = o.index + pd.offsets.MonthEnd(0)
            m = pd.concat([o[o.index < m.index.min()], m])
    return m


def nse_frame(sid, group, offline):
    if offline:
        p = sources._cache_path("nifty_pepb", sid)
        df = pd.read_csv(p, parse_dates=["date"]).set_index("date") if os.path.exists(p) else None
    else:
        df = sources.nifty_pepb(sid, NSE_START[group])
    if df is None or df.empty:
        return None
    df = df.sort_index()
    df["pe_raw"] = df["pe"]
    ratio = None
    if df.index.min() < NSE_BREAK:
        before = df.loc[df.index < NSE_BREAK, "pe"].dropna()
        after = df.loc[df.index >= NSE_BREAK, "pe"].dropna()
        if len(before) and len(after):
            ratio = after.iloc[0] / before.iloc[-1]
            if SPLICE_RANGE[0] <= ratio <= SPLICE_RANGE[1]:
                df.loc[df.index < NSE_BREAK, "pe"] = df.loc[df.index < NSE_BREAK, "pe"] * ratio
            else:
                # Standalone and consolidated earnings differ too much (e.g. Auto, where big groups
                # report overseas subsidiaries only in consolidated results): one day's ratio cannot
                # stand in for 15 years, so the P/E history starts at the switch.
                df.loc[df.index < NSE_BREAK, "pe"] = np.nan
    df.loc[df["pe"] > PE_MAX, "pe"] = np.nan
    me = df.resample("ME").last().dropna(subset=["pe", "pb"], how="all")
    me["obs_date"] = df["pe"].dropna().index.to_series().resample("ME").last().reindex(me.index)
    return me, ratio


def main():
    offline = "--offline" in sys.argv
    today = pd.Timestamp(dt.date.today())
    rows, meta, notes = [], {}, {}
    # Yahoo snapshot: today's fund P/E for every ETF we name (cross-check and short-history funds)
    tickers = sorted({e for *_, e, _ in registry.VALUATION if e} | {x[4] for x in registry.VALUATION_XCHECK})
    snap_f = os.path.join(OUT, "yahoo_snapshots.csv")
    snap = pd.read_csv(snap_f, parse_dates=["date"]) if os.path.exists(snap_f) else pd.DataFrame(columns=["date", "ticker", "pe"])
    if not offline:
        y = sources.yahoo_pe(tickers)
        new = pd.DataFrame([dict(date=today, ticker=t, pe=v) for t, v in y.items() if v])
        snap = pd.concat([snap[snap.date != today], new]).sort_values(["date", "ticker"])
        snap.to_csv(snap_f, index=False)
    ylatest = snap.sort_values("date").groupby("ticker").tail(1).set_index("ticker")

    wpr_series = {}
    for vid, name, group, src, sid, etf, y10 in registry.VALUATION:
        if src == "nse":
            got = nse_frame(sid, group, offline)
            if got is None:
                print(f"{vid}: no NSE data")
                continue
            me, ratio = got
            for d, r in me.iterrows():
                rows.append(dict(id=vid, month=d, pe=r.pe, pe_raw=r.pe_raw, pb=r.pb, dy=r.dy, source="NSE Indices",
                                 obs_date=r.obs_date))
            if ratio and SPLICE_RANGE[0] <= ratio <= SPLICE_RANGE[1]:
                notes[vid] = f"P/E before 31 Mar 2021 scaled by {ratio:.3f} for NSE's switch to consolidated earnings"
            elif ratio:
                notes[vid] = (f"P/E history starts in April 2021: NSE's switch to consolidated earnings changed this index's P/E "
                              f"by a factor of {ratio:.2f} overnight, too much to splice; P/B history is unaffected")
            else:
                notes[vid] = ""
        elif src == "wpr":
            s = sources._load_cache("worldperatio", sid) if offline else sources.worldperatio(sid)[0]
            # The site's S&P 500 page is Shiller's GAAP P/E before 1995 and the SPY-based
            # estimate after; keep only the fund-based era (1995 on) for every market.
            s = s[s.index >= WPR_START]
            wpr_series[vid] = s
            for d, v in s.items():
                rows.append(dict(id=vid, month=d, pe=v, pe_raw=v, pb=None, dy=None, source=f"worldperatio ({etf})",
                                 obs_date=min(d, today)))
        else:   # yahoo: today's value plus any earlier snapshots, one per month (latest in month)
            h = snap[snap.ticker == sid].copy()
            h["month"] = h.date + pd.offsets.MonthEnd(0)
            h = h.sort_values("date").groupby("month").tail(1)
            for r in h.itertuples():
                rows.append(dict(id=vid, month=r.month, pe=r.pe, pe_raw=r.pe, pb=None, dy=None, source=f"Yahoo ({sid})",
                                 obs_date=r.date))
        meta[vid] = dict(name=name, group=group, src=src, sid=sid, etf=etf, y10=y10)

    pe = pd.DataFrame(rows)
    pe["month"] = pd.to_datetime(pe["month"])
    pe.to_csv(os.path.join(OUT, "pe_monthly.csv"), index=False)

    # Percentiles, gaps, price-vs-earnings split
    hist = []
    for vid, g in pe.groupby("id"):
        g = g.set_index("month").sort_index()
        m = meta[vid]
        g.loc[g["pe"] > PE_MAX, "pe"] = np.nan
        g["pctl"] = rolling_pctl(g["pe"])
        g["pb_pctl"] = rolling_pctl(g["pb"]) if g["pb"].notna().any() else np.nan
        g["median_pe"] = [g["pe"][(g.index > d - pd.DateOffset(years=WINDOW_YEARS)) & (g.index <= d)].median() for d in g.index]
        yy = y10_monthly(m["y10"])
        g["y10"] = yy.reindex(g.index) if yy is not None else np.nan
        g["ey"] = 100 / g["pe"]
        g["ey_gap"] = g["ey"] - g["y10"]
        g["gap_pctl"] = rolling_pctl(g["ey_gap"]) if g["ey_gap"].notna().sum() else np.nan
        g["pe_chg_1"] = g["pe"].pct_change(fill_method=None)
        g["first_month"] = g["pe"].dropna().index.min() if g["pe"].notna().any() else g.index.min()
        g["id"] = vid
        hist.append(g.reset_index())
    H = pd.concat(hist)
    H["label"] = H["pctl"].map(label)
    H["name"] = H["id"].map(lambda i: meta[i]["name"])
    H["group"] = H["id"].map(lambda i: meta[i]["group"])
    H["etf"] = H["id"].map(lambda i: meta[i]["etf"])
    H["note"] = H["id"].map(lambda i: notes.get(i, ""))

    # Price move behind each month's P/E change (local-currency price):
    # implied earnings change = (1 + price change) / (1 + P/E change) − 1.
    px = {}
    for vid, m in meta.items():
        if m["src"] == "nse":
            pid = {"IN_LARGE": "X_NIFTY_PXNI", "IN_MID": "X_MID_PXNI"}.get(vid)
            s = load_daily(pid) if pid else None
        else:
            p = sources._cache_path("yahoo_px", m["etf"])
            s = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"] if os.path.exists(p) else None
        if s is not None:
            px[vid] = s.resample("ME").last().pct_change()
    H["px_chg_1"] = [px[i].get(d, np.nan) if i in px else np.nan for i, d in zip(H.id, H.month)]
    H["earn_chg_1"] = (1 + H["px_chg_1"]) / (1 + H["pe_chg_1"]) - 1
    H["revision"] = (H["pe_chg_1"].abs() > 0.15) & (H["px_chg_1"].abs() < 0.05)
    H.to_csv(os.path.join(OUT, "valuation_hist.csv"), index=False)

    # Latest completed month (the month the read covers) and today's reading
    M = today - pd.offsets.MonthEnd(1)
    latest = []
    for vid, g in H.groupby("id"):
        g = g.sort_values("month")
        cur = g[g.month == M]
        now = g.iloc[-1]
        r = cur.iloc[0].to_dict() if len(cur) else {k: None for k in g.columns} | dict(id=vid, name=now["name"], group=now["group"], etf=now["etf"], note=now["note"], label="Short history")
        r["read_month"] = M
        r["pe_now"] = now["pe"]
        r["pe_now_date"] = now["obs_date"] if pd.notna(now["obs_date"]) else now["month"]
        r["pctl_now"] = now["pctl"]
        r["yahoo_pe"] = ylatest["pe"].get(meta[vid]["etf"]) if meta[vid]["etf"] in ylatest.index else None
        r["source"] = g["source"].iloc[-1]
        pe_months = g.loc[g.pe.notna(), "month"]
        r["first_month"] = pe_months.min() if len(pe_months) else g.month.min()
        r["years"] = round((pe_months.max() - pe_months.min()).days / 365.25, 1) if len(pe_months) else 0.0
        latest.append(r)
    L = pd.DataFrame(latest)
    order = {v[0]: i for i, v in enumerate(registry.VALUATION)}
    L = L.sort_values("id", key=lambda s: s.map(order))
    L.to_csv(os.path.join(OUT, "valuation.csv"), index=False)

    write_checks(H, L, wpr_series, ylatest, meta, offline, today)
    show = L[["name", "pe", "pctl", "label", "ey_gap", "gap_pctl", "pb", "pb_pctl", "pe_now", "yahoo_pe", "years"]]
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(show.round(2).to_string(index=False))


def write_checks(H, L, wpr, ylatest, meta, offline, today):
    """Cross-checks read by checks.py (each: name, status, detail)."""
    out = []
    # 1. Range and freshness
    bad = L[(L.pe.notna()) & ((L.pe < 3) | (L.pe > 100))]
    badpb = L[(L.pb.notna()) & ((L.pb < 0.3) | (L.pb > 20))]
    M = L.read_month.iloc[0]
    stale = [r["name"] for _, r in L.iterrows() if meta[r["id"]]["src"] != "yahoo" and pd.isna(r["pe"])]
    out.append(dict(check="Valuations: every P/E and P/B in a sane range and current",
                    status="FAIL" if len(bad) or len(badpb) or stale else "PASS",
                    detail=(f"{L.pe.notna().sum()} markets with a {pd.Timestamp(M):%B %Y} P/E (3–100) and P/B (0.3–20)"
                            + (f"; out of range: {', '.join(bad.name)}" if len(bad) else "")
                            + (f"; P/B out of range: {', '.join(badpb.name)}" if len(badpb) else "")
                            + (f"; no reading for the month: {', '.join(stale)}" if stale else ""))))
    # 2. worldperatio vs Yahoo today
    diffs = []
    for vid, s in wpr.items():
        e = meta[vid]["etf"]
        if e in ylatest.index and len(s):
            diffs.append((e, s.iloc[-1], ylatest.loc[e, "pe"]))
    if diffs:
        far = [f"{e} {a:.1f} vs {b:.1f}" for e, a, b in diffs if abs(a / b - 1) > 0.15]
        out.append(dict(check="Valuations: worldperatio vs Yahoo fund P/E today",
                        status="WARN" if far else "PASS",
                        detail=(f"Differ by more than 15%: {', '.join(far)}. " if far else "")
                        + "Gaps: " + ", ".join(f"{e} {(a / b - 1) * 100:+.0f}%" for e, a, b in diffs)))
    # 3. SPY history vs Shiller S&P 500 P/E (independent long history, to Sept 2024)
    try:
        sh = shiller_pe(offline)
        s = wpr.get("US_LARGE")
        j = pd.concat([s, sh], axis=1, join="inner").dropna()
        # Fund-based P/E sits below Shiller's GAAP P/E (different earnings measure), so
        # compare how the two move (rank correlation), and report the typical ratio.
        c = j.iloc[:, 0].rank().corr(j.iloc[:, 1].rank())
        ratio = (j.iloc[:, 0] / j.iloc[:, 1]).median()
        out.append(dict(check="Valuations: S&P 500 P/E history vs Shiller's S&P 500 P/E",
                        status="PASS" if c > 0.6 else "WARN",
                        detail=f"{len(j)} months from {j.index.min():%b %Y} to {j.index.max():%b %Y}: rank correlation {c:.2f} (limit 0.6); "
                               f"the fund-based P/E is typically {ratio:.2f}× Shiller's, which uses reported (GAAP) earnings. "
                               "Shiller's file stopped updating in Sept 2024"))
    except Exception as e:  # informational; a download failure should not block publishing
        out.append(dict(check="Valuations: S&P 500 P/E history vs Shiller's S&P 500 P/E", status="WARN", detail=f"could not run: {e}"))
    # 4. Nifty 50 (NSE) vs MSCI India fund (INDA) P/E history
    try:
        sid = registry.VALUATION_XCHECK[0][3]
        inda = sources._load_cache("worldperatio", sid) if offline else sources.worldperatio(sid)[0]
        n50 = H[H.id == "IN_LARGE"].set_index("month")["pe"]
        j = pd.concat([n50, inda], axis=1, join="inner").dropna()
        c = j.iloc[:, 0].corr(j.iloc[:, 1])
        out.append(dict(check="Valuations: Nifty 50 P/E (NSE) moves with the MSCI India fund P/E",
                        status="PASS" if c > 0.6 else "WARN",
                        detail=f"correlation {c:.2f} over {len(j)} months since {j.index.min():%b %Y}; latest Nifty 50 {j.iloc[-1, 0]:.1f}, INDA {j.iloc[-1, 1]:.1f}"))
    except Exception as e:
        out.append(dict(check="Valuations: Nifty 50 P/E (NSE) moves with the MSCI India fund P/E", status="WARN", detail=f"could not run: {e}"))
    # 5. Nifty 50 P/E percentile vs P/B percentile (P/B is unaffected by the 2021 method change)
    n = L[L.id == "IN_LARGE"]
    if len(n) and pd.notna(n.pctl.iloc[0]) and pd.notna(n.pb_pctl.iloc[0]):
        d = abs(n.pctl.iloc[0] - n.pb_pctl.iloc[0])
        # Both can be right (P/B also moves with returns on equity), so a gap is reported, not failed.
        out.append(dict(check="Valuations: Nifty 50 P/E and P/B readings compared",
                        status="PASS",
                        detail=f"P/E {n.pctl.iloc[0]:.0f}th percentile of its history, P/B {n.pb_pctl.iloc[0]:.0f}th"
                               + (f": {d:.0f} points apart, so the read reports both" if d > 40 else ": consistent")))
    # 6. Likely data revisions in the read month (P/E jump not explained by price)
    rv = H[(H.month == M) & H.revision]
    out.append(dict(check="Valuations: month's P/E changes match price moves",
                    status="WARN" if len(rv) else "PASS",
                    detail=("P/E moved more than 15% with a price move under 5%, likely an earnings-data update rather than "
                            "a market move: " + ", ".join(f"{r['name']} P/E {r.pe_chg_1*100:+.0f}%, price {r.px_chg_1*100:+.1f}%" for _, r in rv.iterrows())
                            ) if len(rv) else "no unexplained P/E jumps"))
    json.dump(out, open(os.path.join(OUT, "checks.json"), "w"), indent=1, default=str)
    for c in out:
        print(f"{c['status']:4} {c['check']}: {c['detail'][:200]}")


def shiller_pe(offline):
    """Robert Shiller's S&P 500 monthly price / trailing 12-month earnings (cached)."""
    import xlrd
    p = os.path.join(sources.CACHE, "shiller_ie_data.xls")
    if not os.path.exists(p) or (not offline and (dt.datetime.now().timestamp() - os.path.getmtime(p)) > 30 * 86400):
        open(p, "wb").write(sources.session().get(SHILLER_URL, timeout=60).content)
    sh = xlrd.open_workbook(p).sheet_by_name("Data")
    out = {}
    for r in range(8, sh.nrows):
        d, P, E = sh.cell_value(r, 0), sh.cell_value(r, 1), sh.cell_value(r, 3)
        if isinstance(d, float) and isinstance(P, float) and isinstance(E, float) and E > 0:
            y, mth = int(d), int(round((d - int(d)) * 100))
            out[pd.Timestamp(y, mth, 1) + pd.offsets.MonthEnd(0)] = P / E
    return pd.Series(out)


if __name__ == "__main__":
    main()

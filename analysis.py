#!/usr/bin/env python3
"""
analysis.py — the facts engine for the monthly read (see ANALYSIS.md).

Reads the quilt tables (data/quilt/*.csv, from quilt.py) and the latest
catalyst snapshot, and works out a fixed set of findings for one completed
month. Every finding carries its numbers and is produced by a written rule,
so the memo can be checked line by line.

Writes:
  data/analysis/facts_<YYYY-MM>.json   machine-readable findings
  data/analysis/facts_<YYYY-MM>.md     the same findings as plain text

Usage:  python3 analysis.py            (latest completed month)
        python3 analysis.py 2026-09    (a specific month)

Market data only. Nothing here reads private/ or family holdings.
"""

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

from export import FAMILY, SHORT

HERE = os.path.dirname(os.path.abspath(__file__))
Q = os.path.join(HERE, "data", "quilt")
OUT = os.path.join(HERE, "data", "analysis")
os.makedirs(OUT, exist_ok=True)

US_DEF, US_CYC = ["US_XLP", "US_XLU", "US_XLV"], ["US_XLK", "US_XLY", "US_XLI", "US_XLF"]
IN_DEF, IN_CYC = ["IN_FMCG", "IN_PHARMA"], ["IN_BANK", "IN_AUTO", "IN_METAL", "IN_REALTY"]
RATIOS = {"CU_AU": "copper/gold", "MID_FMCG": "Midcap 150/FMCG", "HYG_TLT": "high yield/Treasuries",
          "RSP_SPY": "equal-weight/cap-weight S&P 500"}


def pct(x, d=1):
    return "n/a" if x is None or pd.isna(x) else f"{x*100:+.{d}f}%"


def pp(x, d=1):
    return "n/a" if x is None or pd.isna(x) else f"{x*100:+.{d}f}pp"


def ordinal(x):
    n = int(round(x))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def f(x, d=2):
    return None if x is None or pd.isna(x) else round(float(x), d)


class Facts:
    def __init__(self):
        self.items = []

    def add(self, question, fid, text, flag=False, **numbers):
        self.items.append(dict(question=question, id=fid, text=text, flag=bool(flag),
                               numbers={k: (f(v, 4) if isinstance(v, (float, np.floating)) else v) for k, v in numbers.items()}))


def main():
    l2 = pd.read_csv(os.path.join(Q, "layer2.csv"), parse_dates=["month"])
    l3i = pd.read_csv(os.path.join(Q, "layer3_in.csv"), parse_dates=["month"])
    l3u = pd.read_csv(os.path.join(Q, "layer3_us.csv"), parse_dates=["month"])
    l1 = pd.read_csv(os.path.join(Q, "layer1.csv"), parse_dates=["month"])
    for df in (l2, l3i, l3u):
        df["flags"] = df["flags"].fillna("")

    done = sorted(l2.loc[~l2["mtd"], "month"].unique())
    if len(sys.argv) > 1:
        M = pd.Timestamp(sys.argv[1]) + pd.offsets.MonthEnd(0)
    else:
        M = pd.Timestamp(done[-1])
    P = M - pd.offsets.MonthEnd(1)
    label = M.strftime("%B %Y")
    cur = l2[l2.month == M].copy()
    prev = l2[l2.month == P].copy()
    cur["family"] = cur["id"].map(FAMILY)
    n = len(cur)
    F = Facts()

    def ind(key, month=M):
        r = l1[(l1.month == month) & (l1.key == key)]
        return r.iloc[0] if len(r) else None

    def sector(df, ids, col="ret_3m"):
        return df[(df.month == M) & (df.id.isin(ids))][col].mean()

    # ── 6. Breadth and dispersion (computed first; others refer to it) ──────
    up = int((cur.ret_inr > 0).sum())
    cash = cur.loc[cur.id == "IN_CASH", "ret_inr"].iloc[0]
    beat_cash = int((cur.ret_inr > cash).sum())            # cash never beats itself
    disp = cur.ret_inr.std()
    hist = [l2[l2.month == m].ret_inr.std() for m in done if P - pd.DateOffset(months=12) < pd.Timestamp(m) <= P]
    disp_med = float(np.median(hist)) if hist else np.nan
    best, worst = cur.nsmallest(1, "rank").iloc[0], cur.nlargest(1, "rank").iloc[0]
    F.add("breadth", "breadth",
          f"{up} of {n} assets rose in rupee terms in {label}; {beat_cash} of {n-1} beat INR cash ({pct(cash, 2)}).",
          flag=up <= n // 3, up=up, of=n, beat_cash=beat_cash, cash=cash)
    F.add("breadth", "dispersion",
          f"Best to worst spread was {(best.ret_inr - worst.ret_inr)*100:.1f}pp ({best['name']} {pct(best.ret_inr)} to "
          f"{worst['name']} {pct(worst.ret_inr)}). Cross-asset dispersion was {disp*100:.1f}% against a 12-month median of {disp_med*100:.1f}%.",
          flag=disp > 1.25 * disp_med, spread=best.ret_inr - worst.ret_inr, dispersion=disp, dispersion_median_12m=disp_med)

    # ── 1. Regime ────────────────────────────────────────────────────────────
    votes = []
    for k, name in RATIOS.items():
        r = ind(k)
        on = r is not None and r.chg_3 > 0
        votes.append(dict(vote=name, risk_on=bool(on), detail=f"{name} {pct(r.chg_3) if r is not None else 'n/a'} over 3 months"))
    us_spread = sector(l3u, US_CYC) - sector(l3u, US_DEF)
    in_spread = sector(l3i, IN_CYC) - sector(l3i, IN_DEF)
    sec_on = (us_spread + in_spread) / 2 > 0
    votes.append(dict(vote="cyclical vs defensive sectors", risk_on=bool(sec_on),
                      detail=f"cyclicals minus defensives over 3 months: US {pp(us_spread)}, India {pp(in_spread)}"))
    hy = ind("US_HY_OAS")
    hy_on = hy is not None and hy.chg_3 < 0
    votes.append(dict(vote="high-yield spread", risk_on=bool(hy_on),
                      detail=f"US high-yield spread {hy.value:.2f}% ({hy.chg_3:+.2f}pp over 3 months)" if hy is not None else "n/a"))
    score = sum(v["risk_on"] for v in votes)
    regime = "Risk-on" if score >= 4 else "Defensive" if score <= 2 else "Mixed"
    fam = cur.groupby("family").ret_inr.mean().sort_values(ascending=False)
    F.add("regime", "regime",
          f"Regime: {regime} ({score} of 6 votes risk-on). " + "; ".join(v["detail"] for v in votes) + ".",
          flag=regime != "Mixed", regime=regime, score=score, votes=votes)
    F.add("regime", "families",
          "Average rupee return by family: " + ", ".join(f"{k} {pct(v)}" for k, v in fam.items()) + ".",
          families={k: f(v, 4) for k, v in fam.items()})
    top3 = cur.nsmallest(3, "rank")
    bot3 = cur.nlargest(3, "rank").iloc[::-1]
    F.add("regime", "leaders",
          "Top three: " + ", ".join(f"{r['name']} {pct(r.ret_inr)}" for _, r in top3.iterrows()) +
          ". Bottom three: " + ", ".join(f"{r['name']} {pct(r.ret_inr)}" for _, r in bot3.iterrows()) + ".",
          top=top3[["id", "ret_inr"]].to_dict("records"), bottom=bot3[["id", "ret_inr"]].to_dict("records"))

    # ── 2. Persistence ───────────────────────────────────────────────────────
    lead = cur[cur["flags"].str.contains("LEADER")]
    lag = cur[cur["flags"].str.contains("LAGGARD")]
    F.add("persistence", "persistent",
          "Persistent leaders (top 5 on 1M and 3M): " + (", ".join(f"{r['name']} (3M {pct(r.ret_3m)})" for _, r in lead.iterrows()) or "none") +
          ". Persistent laggards: " + (", ".join(f"{r['name']} (3M {pct(r.ret_3m)})" for _, r in lag.iterrows()) or "none") + ".",
          leaders=lead.id.tolist(), laggards=lag.id.tolist())
    top5_now, top5_prev = set(cur.nsmallest(5, "rank").id), set(prev.nsmallest(5, "rank").id)
    kept = top5_now & top5_prev
    j = cur.set_index("id")["rank"].to_frame("now").join(prev.set_index("id")["rank"].to_frame("prev")).dropna()
    rho = j["now"].rank().corr(j["prev"].rank())   # Spearman = Pearson on ranks
    F.add("persistence", "turnover",
          f"{len(kept)} of last month's top 5 stayed in the top 5 ({', '.join(SHORT[i] for i in kept) or 'none'}). "
          f"Rank correlation with last month: {rho:+.2f} (near +1 = same order, near −1 = reversal).",
          flag=rho < 0, kept=sorted(kept), rank_correlation=rho)
    mv = cur.dropna(subset=["rank_change"]).sort_values("rank_change")
    ups, downs = mv.tail(3).iloc[::-1], mv.head(3)
    F.add("persistence", "movers",
          "Biggest climbers: " + ", ".join(f"{r['name']} ({int(r.rank_change):+d} places)" for _, r in ups.iterrows()) +
          ". Biggest fallers: " + ", ".join(f"{r['name']} ({int(r.rank_change):+d})" for _, r in downs.iterrows()) + ".",
          up=ups[["id", "rank_change"]].to_dict("records"), down=downs[["id", "rank_change"]].to_dict("records"))

    # ── 3. Divergences ───────────────────────────────────────────────────────
    gl3 = cur[cur.family == "Global equity"].ret_3m.mean()
    nl, g3 = ind("FED_NETLIQ"), ind("G3_CB")
    cond = gl3 > 0 and nl is not None and g3 is not None and nl.chg_3 < 0 and g3.chg_3 < 0
    F.add("divergence", "eq_vs_liquidity",
          f"Global equities averaged {pct(gl3)} over 3 months; Fed net liquidity {pct(nl.chg_3)} and G3 central-bank assets {pct(g3.chg_3)}. "
          + ("Equities rose while liquidity fell." if cond else "No equity-versus-liquidity divergence."),
          flag=cond, global_equity_3m=gl3, fed_netliq_3m=nl.chg_3, g3_3m=g3.chg_3)
    spy3 = cur.loc[cur.id == "US_LARGE", "ret_3m"].iloc[0]
    spy1 = cur.loc[cur.id == "US_LARGE", "ret_local"].iloc[0]
    cond = spy3 > 0 and hy is not None and hy.chg_3 >= 0.5
    F.add("divergence", "eq_vs_credit",
          f"S&P 500 3-month rupee return {pct(spy3)}; high-yield spread {hy.chg_3:+.2f}pp over 3 months. "
          + ("Equities rose while credit spreads widened sharply." if cond else
             "Credit spreads widened sharply while equities fell, so the two agree." if hy.chg_3 >= 0.5 else "No equity-versus-credit divergence."),
          flag=cond or hy.chg_3 >= 0.5, spy_3m=spy3, hy_oas_3m=hy.chg_3)
    vix = ind("VIX")
    cond = spy1 > 0 and vix.chg_1 >= 3
    F.add("divergence", "eq_vs_vix",
          f"S&P 500 {pct(spy1)} in dollars this month; VIX {vix.value:.1f} ({vix.chg_1:+.1f} points). "
          + ("Equities rose while fear rose." if cond else "No equity-versus-volatility divergence."),
          flag=cond, spy_1m=spy1, vix=vix.value, vix_1m=vix.chg_1)
    smh = l3u[(l3u.month == M) & (l3u.id == "US_SMH")].ret_inr.iloc[0]
    nit = l3i[(l3i.month == M) & (l3i.id == "IN_IT")].ret_local.iloc[0]
    F.add("divergence", "semis_vs_india_it",
          f"Semiconductors (SMH) {pct(smh)} in rupees against Nifty IT {pct(nit)}: a gap of {(smh - nit)*100:+.1f}pp.",
          flag=abs(smh - nit) >= 0.10, smh_inr=smh, nifty_it=nit)

    # ── 4. Currency ──────────────────────────────────────────────────────────
    fx = ind("USDINR")
    fx12 = ind("USDINR", M - pd.offsets.MonthEnd(12))
    fx12c = fx.value / fx12.value - 1 if fx12 is not None else np.nan
    usd = cur[cur.ccy == "USD"]
    gap = (usd.ret_inr - usd.ret_local).mean()
    F.add("currency", "rupee",
          f"USD/INR {fx.value:.2f}: the rupee {'weakened' if fx.chg_1 > 0 else 'strengthened'} {abs(fx.chg_1)*100:.1f}% this month and "
          f"{'weakened' if fx12c > 0 else 'strengthened'} {abs(fx12c)*100:.1f}% over 12 months. Rupee returns on dollar assets were "
          f"{gap*100:+.2f}pp versus their dollar returns on average this month.",
          flag=abs(fx.chg_1) >= 0.02, usdinr=fx.value, usdinr_1m=fx.chg_1, usdinr_12m=fx12c, avg_fx_gap=gap)

    # ── 5. Risks ─────────────────────────────────────────────────────────────
    stretched = cur[cur.stretch.abs() >= 2]
    watch = cur[(cur.stretch.abs() >= 1.5) & (cur.stretch.abs() < 2)]
    F.add("risks", "stretch",
          "Stretched beyond ±2 on trend: " + (", ".join(f"{r['name']} ({r.stretch:+.1f})" for _, r in stretched.iterrows()) or "none") +
          ". Nearing it (±1.5 to 2): " + (", ".join(f"{r['name']} ({r.stretch:+.1f})" for _, r in watch.iterrows()) or "none") + ".",
          flag=len(stretched) > 0, stretched=stretched.id.tolist(), watch=watch.id.tolist())
    ivix = ind("INDIAVIX")
    F.add("risks", "volatility",
          f"VIX {vix.value:.1f} ({vix.chg_1:+.1f} on the month, {vix.chg_3:+.1f} over 3 months); India VIX {ivix.value:.1f} ({ivix.chg_1:+.1f}, {ivix.chg_3:+.1f}).",
          flag=vix.value >= 25 or ivix.value >= 20, vix=vix.value, india_vix=ivix.value)
    cat_file = sorted(glob.glob(os.path.join(HERE, "data", "catalysts_*.csv")))[-1]
    cat = pd.read_csv(cat_file)
    cat = cat[cat.status == "OK"].copy()
    cat["flags"] = cat["flags"].fillna("")
    as_of = os.path.basename(cat_file)[len("catalysts_"):-4]
    likely = cat.sort_values("prob", ascending=False).groupby("label").head(1)
    F.add("risks", "catalysts_likely",
          f"Most likely outcomes (prediction markets, as of {as_of}): " +
          "; ".join(f"{r.label}: {r.outcome} {r.prob*100:.0f}%" + (" (thin market)" if "THIN" in r["flags"] else "") for _, r in likely.iterrows()) + ".",
          as_of=as_of, outcomes=[dict(event=r.label, outcome=r.outcome, prob=f(r.prob, 3)) for _, r in likely.iterrows()])
    rep = cat[cat["flags"].str.contains("REPRICING")]
    F.add("risks", "catalysts_repricing",
          "Moves of 20 points or more in 30 days: " +
          ("; ".join(f"{r.label}: {r.outcome} {r.prob_30d_ago*100:.0f}% to {r.prob*100:.0f}%" for _, r in rep.iterrows()) or "none") + ".",
          flag=len(rep) > 0, repricings=[dict(event=r.label, outcome=r.outcome, was=f(r.prob_30d_ago, 3), now=f(r.prob, 3)) for _, r in rep.iterrows()])
    big = cat[(cat.delta_30d.abs() >= 0.10) & ~cat["flags"].str.contains("REPRICING") & (cat.prob >= 0.05)]
    if len(big):
        F.add("risks", "catalysts_shifts",
              "Other shifts of 10 to 20 points: " + "; ".join(f"{r.label}: {r.outcome} {r.prob_30d_ago*100:.0f}% to {r.prob*100:.0f}%" for _, r in big.iterrows()) + ".",
              shifts=[dict(event=r.label, outcome=r.outcome, was=f(r.prob_30d_ago, 3), now=f(r.prob, 3)) for _, r in big.iterrows()])
    dis = cat[cat.kalshi_prob.notna() & ((cat.kalshi_prob - cat.prob).abs() > 0.10)]
    chk = cat[cat.kalshi_prob.notna()]
    F.add("risks", "venues",
          f"Polymarket and Kalshi checked on {len(chk)} outcomes; " +
          (f"{len(dis)} differ by more than 10 points." if len(dis) else "all agree within 10 points."),
          flag=len(dis) > 0, checked=len(chk), disagree=len(dis))

    # Liquidity backdrop (context for regime and divergence)
    m2 = ind("GLOBAL_M2")
    rbi = l1[(l1.key == "RBI_NETLIQ") & (l1.month <= M)].sort_values("month").tail(1)   # only readings from this month or earlier
    F.add("regime", "liquidity",
          f"Fed net liquidity ${nl.value:,.0f}bn ({pct(nl.chg_1)} on the month, {pct(nl.chg_3)} over 3 months); "
          f"Global M2 {pct(m2.chg_1)} year on year, {pct(m2.chg_3)} annualised over 3 months"
          + (f"; RBI net liquidity ₹{rbi.value.iloc[0]:,.0f} crore {'injection' if rbi.value.iloc[0] > 0 else 'absorption'} as of {rbi.obs_date.iloc[0]}" if len(rbi) else "")
          + ".", fed_netliq=nl.value, fed_netliq_1m=nl.chg_1, global_m2_yoy=m2.chg_1, global_m2_3m_ann=m2.chg_3)

    # Sectors
    def top_bottom(df, col):
        d = df[df.month == M].sort_values("rank")
        return d.iloc[0], d.iloc[-1]
    it, ib = top_bottom(l3i, "ret_local")
    ut, ub = top_bottom(l3u, "ret_local")
    F.add("regime", "sectors",
          f"India sectors: {it['name']} led ({pct(it.ret_local)}), {ib['name']} lagged ({pct(ib.ret_local)}). "
          f"US sectors: {ut['name']} led ({pct(ut.ret_local)}), {ub['name']} lagged ({pct(ub.ret_local)}).")

    # ── 7. Positioning: how money is placed (positioning.py) ─────────────────
    gfile = os.path.join(HERE, "data", "positioning", "gauges.csv")
    if os.path.exists(gfile):
        from positioning import GAUGES
        g = pd.read_csv(gfile, parse_dates=["date"])
        readings = []
        for gid, meta in GAUGES.items():
            s = g[g.gauge == gid].set_index("date")["value"].sort_index()
            s = s[s.index <= M]
            if s.empty:
                continue
            v, d = s.iloc[-1], s.index[-1]
            win = s[s.index > M - pd.DateOffset(years=3)]
            pctl = float((win < v).mean() * 100) if len(win) >= 12 else None
            lab = "Not enough history" if pctl is None else meta["high"] if pctl >= 90 else meta["low"] if pctl <= 10 else "Normal"
            readings.append(dict(id=gid, name=meta["name"], group=meta["group"], asset=meta["asset"], value=float(v),
                                 date=str(d.date()), pctl=pctl, label=lab, n=len(win)))
        R = {r["id"]: r for r in readings}

        def fmt(r):
            v = r["value"]
            val = ((f"₹{v:,.0f} crore net buying" if v >= 0 else f"₹{-v:,.0f} crore net selling") if r["id"] == "FPI_EQ" else f"{v:.2f}" if r["id"] in ("VOL_TERM", "NIFTY_PCR")
                   else f"±{v:.1f}%" if r["id"] == "NIFTY_MOVE" else f"{v:.0f}" if r["id"] in ("VOL_SKEW", "VOL_MOVE")
                   else f"{v:+.1f}% of open interest" if r["id"].startswith("COT") else f"{v:.0f}%")
            where = "percentile n/a" if r["pctl"] is None else f"{ordinal(r['pctl'])} percentile of 3 years"
            return f"{r['name']} {val} ({where}: {r['label']})"

        for grp in ["US futures positioning", "India flows", "Options and volatility"]:
            rs = [r for r in readings if r["group"] == grp]
            if rs:
                F.add("positioning", "pos_" + grp.split()[0].lower(), f"{grp}: " + "; ".join(fmt(r) for r in rs) + ".",
                      flag=any(r["label"] not in ("Normal", "Not enough history") for r in rs), readings=rs)

        # Clashes between positioning and price action
        rets = cur.set_index("id")
        clashes = []
        for r in readings:
            if not r["asset"] or r["pctl"] is None or r["asset"] not in rets.index or not r["id"].startswith("COT"):
                continue
            a = rets.loc[r["asset"]]
            who, mkt = r["name"].split(": ")[1].replace(" net long", "").replace(" net", ""), r["name"].split(":")[0]
            who = who.replace("hedge-fund", "hedge funds").replace("leveraged-fund", "leveraged funds").replace("asset-manager", "asset managers")
            # Same thresholds as the labels: top or bottom 10% of three years.
            if r["pctl"] >= 90 and (a.ret_local < -0.05 or "LAGGARD" in a["flags"]):
                clashes.append(f"In {mkt}, {who} are the most bullish they have been in 3 years ({ordinal(r['pctl'])} percentile), "
                               f"yet it fell {abs(a.ret_local)*100:.1f}% this month: if they cut those positions, selling could deepen")
            if r["pctl"] <= 10 and a.ret_local > 0.05:
                clashes.append(f"In {mkt}, {who} are the most bearish they have been in 3 years ({ordinal(r['pctl'])} percentile), "
                               f"yet it rose {a.ret_local*100:.1f}% this month: if they turn, their buying could add to the rise")
        fpi, nifty = R.get("FPI_EQ"), rets.loc["IN_LARGE"].ret_local if "IN_LARGE" in rets.index else None
        if fpi and nifty is not None and fpi["date"][:7] == M.strftime("%Y-%m"):
            if fpi["value"] < 0 and nifty > 0:
                clashes.append(f"Foreign investors sold a net ₹{-fpi['value']:,.0f} crore of Indian equities while the Nifty 50 rose {nifty*100:.1f}%: domestic buying carried the market")
            elif fpi["value"] > 0 and nifty < 0:
                clashes.append(f"Foreign investors bought a net ₹{fpi['value']:,.0f} crore while the Nifty 50 fell {nifty*100:.1f}%")
            fs = g[g.gauge == "FPI_EQ"].set_index("date")["value"].sort_index()
            fs = fs[fs.index <= M]
            streak = 0
            for v in fs.iloc[::-1]:
                if v < 0:
                    streak += 1
                else:
                    break
            if streak >= 3:
                clashes.append(f"Foreign investors have been net sellers of Indian equities for {streak} months running")
        fomc = cat[(cat["key"] == "FOMC_NEXT")].sort_values("prob", ascending=False).head(1)
        ust = R.get("COT_UST")
        if len(fomc) and "increase" in str(fomc.outcome.iloc[0]).lower() and fomc.prob.iloc[0] >= 0.8 and ust and ust["pctl"] is not None and ust["pctl"] >= 90:
            clashes.append(f"Asset managers are the most bullish on Treasury bonds in 3 years ({ordinal(ust['pctl'])} percentile) while markets price a {fomc.prob.iloc[0]*100:.0f}% chance of a Fed hike")
        term = R.get("VOL_TERM")
        if term and term["value"] < 1:
            clashes.append(f"The VIX curve is inverted ({term['value']:.2f}): near-term fear is above longer-term fear, a sign of acute stress")
        F.add("positioning", "pos_clashes",
              ("Positioning clashes: " + "; ".join(clashes) + ".") if clashes else "No clashes between positioning and price action.",
              flag=bool(clashes), clashes=clashes)

        # Forward-looking implied moves (latest snapshot, not month-end)
        ifile = os.path.join(HERE, "data", "positioning", "implied.csv")
        if os.path.exists(ifile):
            im = pd.read_csv(ifile, parse_dates=["as_of", "expiry"])
            parts = []
            for u in ["NIFTY", "SPY"]:
                x = im[im.underlying == u]
                if len(x):
                    x = x[x.as_of == x.as_of.max()].sort_values("expiry")
                    parts.append(f"{'Nifty' if u == 'NIFTY' else 'S&P 500 (SPY)'} as of {x.as_of.iloc[0].date()}: "
                                 + ", ".join(f"±{r.implied_move*100:.1f}% by {r.expiry:%d %b} (put/call {r.pcr:.2f})" for r in x.itertuples()))
            if parts:
                F.add("positioning", "implied_moves", "Options-implied moves to the next monthly expiries: " + "; ".join(parts) + ".",
                      moves=im[im.as_of == im.groupby("underlying").as_of.transform("max")]       # latest snapshot per market
                      .sort_values(["underlying", "expiry"])
                      .assign(as_of=lambda d: d.as_of.astype(str), expiry=lambda d: d.expiry.astype(str)).to_dict("records"))

    facts = dict(month=M.strftime("%Y-%m"), label=label, generated_from="data/quilt/*.csv and " + os.path.basename(cat_file),
                 facts=F.items)
    key = M.strftime("%Y-%m")
    json.dump(facts, open(os.path.join(OUT, f"facts_{key}.json"), "w"), indent=2, default=str)
    order = ["regime", "persistence", "divergence", "currency", "risks", "breadth", "positioning"]
    lines = [f"# Facts for {label}", ""]
    for q in order:
        lines.append(f"## {q.capitalize()}")
        lines += [f"- {'**[flag]** ' if it_['flag'] else ''}{it_['text']}" for it_ in F.items if it_["question"] == q]
        lines.append("")
    open(os.path.join(OUT, f"facts_{key}.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
quilt.py — turn the validated daily series (data/daily/*.csv, written by
run.py) into the monthly quilt tables.

Outputs (data/quilt/):
  layer2.csv     18 asset classes × months: local and INR returns, ranks,
                 3-month return and rank, rank change, volatility, trend stretch
  layer3_in.csv  10 Indian sectors (INR)
  layer3_us.csv  12 US sectors (USD) + the SMH-vs-Nifty IT spread in INR
  layer1.csv     macro / liquidity / rates / FX / vol / ratio indicators
  summary.json   the latest month's facts the IC memo is written from

Definitions (also printed on the page):
  INR return      (1 + local return) × (1 + USD/INR return) − 1 for USD assets
  3M return       compounded return over the last three month-ends
  Rank change     last month's rank − this month's rank (positive = moved up)
  Volatility      annualised stdev of daily returns, trailing 252 days
  Trend stretch   ln(price / 200-day average) ÷ (daily vol × √100). The 200-day
                  average lags price by about 100 days, so this is roughly a
                  z-score of the gap. |stretch| ≥ 2 is flagged STRETCHED.
  Persistent      top 5 (or bottom 5) on BOTH the 1-month and 3-month ranking
These are diagnostics for discussion. Nothing here is a trade instruction.
"""

import datetime as dt
import json
import math
import os

import numpy as np
import pandas as pd

import registry

HERE = os.path.dirname(os.path.abspath(__file__))
DAILY = os.path.join(HERE, "data", "daily")
OUT = os.path.join(HERE, "data", "quilt")
os.makedirs(OUT, exist_ok=True)
NO_TREND = {"IN_CASH", "US_CASH"}


def load(i):
    p = os.path.join(DAILY, f"{i}.csv")
    s = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"].astype(float)
    return s[~s.index.duplicated(keep="last")].sort_index()


def month_end(s):
    return s.resample("ME").last()


def asset_metrics(s):
    """Per-month trailing metrics from a daily total-return series."""
    r = s.pct_change()
    vol = r.rolling(252, min_periods=180).std() * math.sqrt(252)
    ma200 = s.rolling(200, min_periods=180).mean()
    sd_d = r.rolling(252, min_periods=180).std()
    stretch = np.log(s / ma200) / (sd_d * math.sqrt(100))
    return pd.DataFrame({"vol": month_end(vol), "stretch": month_end(stretch)})


def build_panel(ids, names, usd_ids, fx_me):
    """Long table: month, id, returns (local, INR), trailing metrics."""
    frames = []
    for i in ids:
        s = load(i)
        me = month_end(s)
        last_obs = s.index.to_series().resample("ME").last()
        df = pd.DataFrame({"level": me, "obs_date": last_obs})
        df["ret_local"] = df["level"].pct_change()
        if i in usd_ids:
            fx_r = fx_me.pct_change().reindex(df.index)
            df["ret_inr"] = (1 + df["ret_local"]) * (1 + fx_r) - 1
        else:
            df["ret_inr"] = df["ret_local"]
        df = df.join(asset_metrics(s))
        if i in NO_TREND:
            df["stretch"] = np.nan      # accrual indices rise every day; a trend gap means nothing
        df["id"], df["name"] = i, names[i]
        df["ccy"] = "USD" if i in usd_ids else "INR"
        frames.append(df.reset_index(names="month"))
    p = pd.concat(frames, ignore_index=True)
    return p.dropna(subset=["ret_local"])


def add_ranks(p, col):
    """Ranks within each month on `col` (1 = best), plus 3M and rank change."""
    p = p.sort_values(["id", "month"]).copy()
    g = p.groupby("id")[col]
    p["ret_3m"] = g.transform(lambda x: (1 + x).rolling(3).apply(np.prod, raw=True) - 1)
    p["rank"] = p.groupby("month")[col].rank(ascending=False, method="min")
    p["rank_3m"] = p.groupby("month")["ret_3m"].rank(ascending=False, method="min")
    p["rank_change"] = p.groupby("id")["rank"].shift(1) - p["rank"]
    n = p.groupby("month")["id"].transform("count")
    p["ret_per_vol_3m"] = p["ret_3m"] / (p["vol"] * math.sqrt(3 / 12))
    flags = []
    for _, r in p.iterrows():
        f = []
        if pd.notna(r["rank_3m"]):
            if r["rank"] <= 5 and r["rank_3m"] <= 5:
                f.append("PERSISTENT LEADER")
            if r["rank"] > n[_] - 5 and r["rank_3m"] > n[_] - 5:
                f.append("PERSISTENT LAGGARD")
        if pd.notna(r["stretch"]) and r["stretch"] >= 2:
            f.append("STRETCHED HIGH")
        if pd.notna(r["stretch"]) and r["stretch"] <= -2:
            f.append("STRETCHED LOW")
        flags.append("; ".join(f))
    p["flags"] = flags
    return p.sort_values(["month", "rank"])


# ── Layer 1 ─────────────────────────────────────────────────────────────────
def at(s, when):
    s = s[s.index <= when].dropna()
    return (s.iloc[-1], s.index[-1]) if len(s) else (np.nan, pd.NaT)


def layer1(months):
    S = {i: load(i) for i in [
        "FED_ASSETS", "FED_TGA", "FED_RRP", "ECB_ASSETS", "BOJ_ASSETS", "EURUSD", "USDJPY",
        "M2_US", "M2_EA", "M2_JP", "M2_CN", "USDCNY", "US10Y", "US2Y", "US_HY_OAS", "IN10Y", "IN3M",
        "RBI_NETLIQ", "USDINR", "DXY", "VIX", "INDIAVIX", "COPPER_FUT", "GOLD_FUT",
        "HYG_PX", "TLT_PX", "RSP_PX", "SPY_PX", "IN_MID", "IN_FMCG"]}

    # Fed net liquidity on the Fed's weekly (Wednesday) dates.
    w = S["FED_ASSETS"].index
    netliq = pd.Series([S["FED_ASSETS"][d] - at(S["FED_TGA"], d)[0] - at(S["FED_RRP"], d)[0] for d in w], index=w)
    # G3 central-bank assets in USD trillions, on ECB weekly dates (BoJ is monthly → last known).
    e = S["ECB_ASSETS"].index
    g3 = pd.Series([(at(S["FED_ASSETS"], d)[0] + S["ECB_ASSETS"][d] * at(S["EURUSD"], d)[0]
                     + at(S["BOJ_ASSETS"], d)[0] / at(S["USDJPY"], d)[0]) / 1000 for d in e], index=e)
    # Global M2 (US + euro area + Japan + China) in USD trillions, monthly, only
    # for months where all four have reported.
    m2_months = sorted(set.intersection(*[set(month_end(S[k]).dropna().index) for k in ["M2_US", "M2_EA", "M2_JP", "M2_CN"]]))
    gm2 = pd.Series([(at(S["M2_US"], m)[0] + at(S["M2_EA"], m)[0] * at(S["EURUSD"], m)[0]
                      + at(S["M2_JP"], m)[0] / at(S["USDJPY"], m)[0] + at(S["M2_CN"], m)[0] / at(S["USDCNY"], m)[0]) / 1000
                     for m in m2_months], index=pd.DatetimeIndex(m2_months))
    us_curve = (S["US10Y"] - S["US2Y"].reindex(S["US10Y"].index)).dropna()
    in_curve = (S["IN10Y"] - S["IN3M"].reindex(S["IN10Y"].index)).dropna()

    def ratio(a, b):
        j = pd.concat([S[a], S[b]], axis=1, join="inner").dropna()
        return j.iloc[:, 0] / j.iloc[:, 1]

    ind = [
        # (key, group, label, series, units, how to show change, note)
        ("FED_NETLIQ", "Liquidity", "US Fed net liquidity", netliq, "USD bn", "pct",
         "Fed assets − Treasury account − reverse repo"),
        ("G3_CB", "Liquidity", "G3 central-bank assets", g3, "USD tn", "pct", "Fed + ECB + BoJ in USD"),
        ("GLOBAL_M2", "Liquidity", "Global M2 (US, EA, JP, CN)", gm2, "USD tn", "yoy",
         "In USD, so a weaker dollar raises it; 3M figure annualised"),
        ("M2_US", "Liquidity", "US M2", S["M2_US"], "USD bn", "yoy", ""),
        ("RBI_NETLIQ", "Liquidity", "RBI net liquidity", S["RBI_NETLIQ"], "INR cr", "level",
         "Positive = RBI injecting; history starts 2026-11"),
        ("US_CURVE", "Rates", "US 10Y − 2Y", us_curve, "pp", "diff", ""),
        ("IN_CURVE", "Rates", "India 10Y − 3M", in_curve, "pp", "diff", "Monthly averages (no free daily 1Y feed)"),
        ("US10Y", "Rates", "US 10Y yield", S["US10Y"], "%", "diff", ""),
        ("IN10Y", "Rates", "India 10Y yield", S["IN10Y"], "%", "diff", "Monthly average"),
        ("US_HY_OAS", "Rates", "US high-yield spread", S["US_HY_OAS"], "%", "diff", ""),
        ("USDINR", "FX & volatility", "USD/INR", S["USDINR"], "INR", "pct", "Up = rupee weaker"),
        ("DXY", "FX & volatility", "US Dollar Index", S["DXY"], "index", "pct", ""),
        ("VIX", "FX & volatility", "CBOE VIX", S["VIX"], "index", "diff", ""),
        ("INDIAVIX", "FX & volatility", "India VIX", S["INDIAVIX"], "index", "diff", ""),
        ("CU_AU", "Regime ratios", "Copper / Gold", ratio("COPPER_FUT", "GOLD_FUT") * 1000, "×1000", "pct",
         "Rising = growth over safety"),
        ("MID_FMCG", "Regime ratios", "Midcap 150 / FMCG", ratio("IN_MID", "IN_FMCG"), "ratio", "pct",
         "Rising = Indian risk appetite"),
        ("HYG_TLT", "Regime ratios", "High yield / Treasuries", ratio("HYG_PX", "TLT_PX"), "ratio", "pct",
         "Rising = credit appetite"),
        ("RSP_SPY", "Regime ratios", "Equal-weight / cap-weight S&P", ratio("RSP_PX", "SPY_PX"), "ratio", "pct",
         "Rising = broader US market"),
    ]
    rows = []
    for key, grp, label, s, units, how, note in ind:
        s = s.dropna()
        for m in months:
            v, d = at(s, m)
            if pd.isna(v):
                continue
            v1, _ = at(s, m - pd.offsets.MonthEnd(1))
            v3, _ = at(s, m - pd.offsets.MonthEnd(3))
            v12, _ = at(s, m - pd.offsets.MonthEnd(12))
            if how == "pct":
                c1, c3 = v / v1 - 1, v / v3 - 1
            elif how == "yoy":
                c1, c3 = v / v12 - 1, (v / v3) ** 4 - 1          # YoY, and 3M annualised
            elif how == "diff":
                c1, c3 = v - v1, v - v3
            else:
                c1 = c3 = np.nan
            rows.append(dict(month=m, key=key, group=grp, label=label, value=v, obs_date=d,
                             units=units, change_type=how, chg_1=c1, chg_3=c3, note=note))
    return pd.DataFrame(rows)


def main():
    today = pd.Timestamp(dt.date.today())
    fx_me = month_end(load("USDINR"))

    l2_names = {i: n for i, n, *_ in registry.LAYER2}
    usd = {i for i, _, _, _, ccy, _ in registry.LAYER2 if ccy == "USD"}
    l2 = add_ranks(build_panel(list(l2_names), l2_names, usd, fx_me), "ret_inr")
    # Local-currency rank alongside, for the "INR vs local" toggle.
    l2["rank_local"] = l2.groupby("month")["ret_local"].rank(ascending=False, method="min")

    in_names = {i: n for i, n, *_ in registry.LAYER3_INDIA}
    l3i = add_ranks(build_panel(list(in_names), in_names, set(), fx_me), "ret_local")
    us_names = {i: n for i, n, *_ in registry.LAYER3_US}
    l3u = add_ranks(build_panel(list(us_names), us_names, set(us_names), fx_me), "ret_local")

    # Cross-market spread in ONE currency: SMH in INR minus Nifty IT (INR).
    smh = l3u[l3u.id == "US_SMH"].set_index("month")["ret_inr"]
    nit = l3i[l3i.id == "IN_IT"].set_index("month")["ret_local"]
    spread = (smh - nit).dropna().rename("smh_inr_minus_nifty_it")

    months = sorted(l2["month"].unique())
    l1 = layer1([pd.Timestamp(m) for m in months])

    for df, name in [(l2, "layer2"), (l3i, "layer3_in"), (l3u, "layer3_us"), (l1, "layer1")]:
        df["mtd"] = pd.to_datetime(df["month"]) > today
        df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
    spread.to_csv(os.path.join(OUT, "spread_smh_vs_nifty_it.csv"))

    # Latest COMPLETED month for the memo; MTD shown separately.
    done = [m for m in months if pd.Timestamp(m) <= today]
    last = done[-1]
    cur = l2[l2.month == last]
    summary = dict(
        as_of=str(today.date()), month=str(pd.Timestamp(last).date()),
        top=cur.nsmallest(4, "rank")[["name", "ret_inr", "ret_local"]].to_dict("records"),
        bottom=cur.nlargest(4, "rank")[["name", "ret_inr", "ret_local"]].to_dict("records"),
        flagged=cur[cur["flags"] != ""][["name", "flags", "stretch"]].to_dict("records"),
        usdinr_month_ret=float(fx_me.pct_change().loc[last]),
        smh_minus_nifty_it=float(spread.loc[last]) if last in spread.index else None,
    )
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
export.py — package the quilt tables as the data files the published page
reads. Each file is JSON {rows, meta}: the rows, plus the code that produced
them, so a reader can check how every number was worked out.

Writes data/export/{layer2,layer3_in,layer3_us,layer3_gl,layer1,valuation,backtest,catalysts,quality,...}.json.
Run after run.py and quilt.py.
"""

import datetime as dt
import glob
import json
import math
import os
import re

import pandas as pd

import registry
import validate

HERE = os.path.dirname(os.path.abspath(__file__))
Q = os.path.join(HERE, "data", "quilt")
OUT = os.path.join(HERE, "data", "export")
os.makedirs(OUT, exist_ok=True)
MONTHS = 13          # 12 completed months + the current month to date

SHORT = {
    "IN_LARGE": "Nifty 50", "IN_MID": "Midcap 150", "IN_SMALL": "Smallcap 250",
    "US_LARGE": "S&P 500", "US_TECH": "Nasdaq 100", "US_SMALL": "Russell 2000",
    "DM_EXUS": "Dev ex-US", "EM": "Emerging", "IN_GSEC10": "India 10Y", "US_LT_TSY": "UST 20Y+",
    "US_HY": "US HY", "IN_CASH": "INR cash", "US_CASH": "USD cash", "IN_REIT": "REITs/InvITs",
    "GOLD": "Gold", "SILVER": "Silver", "COPPER": "Copper", "BRENT": "Brent", "BTC": "Bitcoin",
    "IN_BANK": "Bank", "IN_FINXB": "Fin ex-Bank", "IN_IT": "IT", "IN_AUTO": "Auto", "IN_FMCG": "FMCG",
    "IN_PHARMA": "Pharma", "IN_METAL": "Metal", "IN_ENERGY": "Energy", "IN_INFRA": "Infra",
    "IN_REALTY": "Realty", "US_XLK": "Tech", "US_SMH": "Semis", "US_XLC": "Comm Svcs",
    "US_XLY": "Cons Disc", "US_XLF": "Financials", "US_XLI": "Industrials", "US_XLV": "Health Care",
    "US_XLP": "Staples", "US_XLE": "Energy", "US_XLB": "Materials", "US_XLU": "Utilities",
    "US_XLRE": "Real Estate",
    "GL_CN_TECH": "China tech", "GL_CN_LARGE": "China large", "GL_CN_A": "China A", "GL_HK": "Hong Kong",
    "GL_JP": "Japan", "GL_KR": "Korea", "GL_TW": "Taiwan", "GL_DE": "Germany", "GL_EZ": "Euro area", "GL_UK": "UK",
}
# World markets are coloured by region so India and China stand out.
REGION_FAMILY = {"India": "India", "China": "China & HK", "Hong Kong": "China & HK", "Japan": "Other Asia",
                 "Korea": "Other Asia", "Taiwan": "Other Asia", "Germany": "Europe", "Euro area": "Europe", "UK": "Europe",
                 "US": "US"}
FAMILY = {
    **dict.fromkeys(["IN_LARGE", "IN_MID", "IN_SMALL"], "Indian equity"),
    **dict.fromkeys(["US_LARGE", "US_TECH", "US_SMALL", "DM_EXUS", "EM"], "Global equity"),
    **dict.fromkeys(["IN_GSEC10", "US_LT_TSY", "US_HY", "IN_CASH", "US_CASH"], "Bonds & cash"),
    **dict.fromkeys(["IN_REIT", "GOLD", "SILVER", "COPPER", "BRENT"], "Real assets"),
    "BTC": "Crypto",
}


def code(name):
    return open(os.path.join(HERE, name)).read()


def clean(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (pd.Timestamp, dt.date)):
        return str(v)[:10]
    return v


def write(name, df, meta):
    rows = [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]
    json.dump({"rows": rows, "meta": meta}, open(os.path.join(OUT, f"{name}.json"), "w"), default=str)
    print(f"{name}: {len(rows)} rows")


def last_months(df):
    keep = sorted(df["month"].unique())[-MONTHS:]
    return df[df["month"].isin(keep)].copy()


def quilt_table(path, family=None):
    df = last_months(pd.read_csv(path))
    df["m"] = df["month"].str[:7]
    df["key"] = df["m"] + "|" + df["id"]
    df["short"] = df["id"].map(SHORT)
    if family:
        df["family"] = df["id"].map(family)
    df["flags"] = df["flags"].fillna("")
    cols = ["key", "m", "mtd", "id", "name", "short", "ccy", "ret_local", "ret_inr", "rank", "ret_3m",
            "rank_3m", "rank_change", "vol", "stretch", "flags", "obs_date"]
    cols += [c for c in ["family", "rank_local"] if c in df.columns]
    if "region" in df.columns:
        df["short"] = df["short"].fillna(df["id"].map({"IN_LARGE": "India", "US_LARGE": "US"}))
        df["family"] = df["region"].map(REGION_FAMILY)
        cols += ["region", "family", "idx_name", "idx_ccy", "idx_basis", "idx_ret"]
    return df[cols]


def main():
    meta_q = [{"label": "quilt.py", "value": code("quilt.py"), "type": "code", "lang": "python"},
              {"label": "Input", "value": "Daily series fetched and validated by run.py, as listed in registry.py"}]
    write("layer2", quilt_table(os.path.join(Q, "layer2.csv"), FAMILY), meta_q)
    write("layer3_in", quilt_table(os.path.join(Q, "layer3_in.csv")), meta_q)
    us = quilt_table(os.path.join(Q, "layer3_us.csv"))
    sp = pd.read_csv(os.path.join(Q, "spread_smh_vs_nifty_it.csv"))
    sp["m"] = sp["month"].str[:7]
    us = us.merge(sp[["m", "smh_inr_minus_nifty_it"]], on="m", how="left")
    us.loc[us["id"] != "US_SMH", "smh_inr_minus_nifty_it"] = None
    write("layer3_us", us, meta_q)
    write("layer3_gl", quilt_table(os.path.join(Q, "layer3_gl.csv")), meta_q)

    l1 = last_months(pd.read_csv(os.path.join(Q, "layer1.csv")))
    l1["m"] = l1["month"].str[:7]
    l1["key"] = l1["m"] + "|" + l1["key"]
    write("layer1", l1[["key", "m", "mtd", "group", "label", "value", "units", "change_type", "chg_1", "chg_3",
                        "chg_12", "obs_date", "note"]], meta_q)

    cat_file = sorted(glob.glob(os.path.join(HERE, "data", "catalysts_*.csv")))[-1]
    cat = pd.read_csv(cat_file)
    cat = cat[cat["status"] == "OK"].copy()
    cat["flags"] = cat["flags"].fillna("")
    # Near-zero brackets add rows without information; keep any that moved or are flagged.
    cat = cat[(cat["prob"] >= 0.02) | (cat["flags"] != "") | (cat["delta_30d"].abs() >= 0.05)]
    cat["key"] = cat["key"] + "|" + cat["outcome"]
    write("catalysts", cat[["key", "label", "outcome", "prob", "prob_date", "prob_30d_ago", "delta_30d",
                            "kalshi_prob", "event_liquidity", "event_end", "event_slug", "flags"]],
          [{"label": "catalysts.py", "value": code("catalysts.py"), "type": "code", "lang": "python"},
           {"label": "Input", "value": f"Polymarket Gamma + CLOB price history; Kalshi trade API ({os.path.basename(cat_file)})"}])

    # Data quality: re-run the checks on the saved daily series.
    store = {}
    for p in glob.glob(os.path.join(HERE, "data", "daily", "*.csv")):
        s = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"]
        store[os.path.basename(p)[:-4]] = s
    today = dt.date.today()
    rows = [dict(check=c, status=st, detail=d) for c, st, d in validate.basis_checks(store)]
    n = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for m in registry.all_series():
        res = validate.hygiene(m, store.get(m["id"]), today)
        worst = "FAIL" if any(s == "FAIL" for s, _ in res) else "WARN" if any(s == "WARN" for s, _ in res) else "PASS"
        n[worst] += 1
        if worst != "PASS":
            rows.append(dict(check=f"Series: {m['name']}", status=worst, detail="; ".join(d for _, d in res)))
    rows.insert(0, dict(check="Series fetched and fresh", status="PASS" if n["FAIL"] == 0 else "FAIL",
                        detail=f"{n['PASS']} pass, {n['WARN']} warn, {n['FAIL']} fail of {sum(n.values())}"))
    write("quality", pd.DataFrame(rows),
          [{"label": "validate.py", "value": code("validate.py"), "type": "code", "lang": "python"}])


    # Valuations: each market's P/E against its own history (valuation.py)
    vf = os.path.join(HERE, "data", "valuation", "valuation.csv")
    if os.path.exists(vf):
        v = pd.read_csv(vf)
        v["key"] = "val|" + v["id"]
        v["order"] = range(len(v))
        for c in ["first_month", "read_month", "pe_now_date", "obs_date"]:
            if c in v.columns:
                v[c] = v[c].astype(str).str[:10].replace({"nan": None, "NaT": None, "None": None})
        cols = ["key", "order", "id", "name", "group", "read_month", "pe", "pctl", "label", "median_pe", "pb", "pb_pctl", "dy",
                "y10", "ey", "ey_gap", "gap_pctl", "pe_chg_1", "px_chg_1", "earn_chg_1", "revision", "pe_now", "pe_now_date",
                "yahoo_pe", "source", "first_month", "years", "note", "etf"]
        write("valuation", v[[c for c in cols if c in v.columns]],
              [{"label": "valuation.py", "value": code("valuation.py"), "type": "code", "lang": "python"},
               {"label": "Sources", "value": "NSE Indices daily P/E, P/B and dividend yield (niftyindices.com); worldperatio.com monthly "
                                             "P/E history for US-listed country funds; Yahoo fund P/E (today, cross-check); 10-year yields as in the rates panel"}])
    # Backtest: would the signals have helped in the past? (backtest.py)
    bf = os.path.join(HERE, "data", "backtest", "results.json")
    if os.path.exists(bf):
        B = json.load(open(bf))
        brow = [dict(kind="meta", key="meta", order=0, generated=B["generated"],
                     text=f"Run on {B['generated']}. Indian tests start in 2005 (NSE total-return indices), US and world-market tests in the "
                          "1990s or 2000s, the regime gauge in 2007, and some alerts later, when their data begins. Foreign-flow alerts use NSDL "
                          "data from 2023 only for now.")]
        for i, x in enumerate(B["summary"]):
            brow.append(dict(kind="summary", key=f"sum|{i}", order=10 + i, test=x["test"], signal=x["signal"], verdict=x["verdict"],
                             text=x["text"], n=x["n"]))
        for r in B["valuation"]["single"]:
            if r["horizon"] == "5 years":
                for j, b in enumerate(r["buckets"]):
                    brow.append(dict(kind="bucket", key=f"bkt|{r['market']}|{j}", order=200 + j, market=r["market"], ccy=r["ccy"],
                                     bucket=b["bucket"], avg_fwd=b["avg_fwd"], n=b["n_months"], start=r["start"], end=r["end"]))
        for i, a in enumerate(B["alerts"]):
            h = {(x["asset"], x["months"]): x for x in a["horizons"] if x.get("n")}
            nf, ot = h.get(("Nifty 50", 3)), h.get((a["other"], 3))
            vds = [x.get("verdict") for x in (nf, ot) if x]
            rank = {"Useful": 3, "Weak": 2, "No evidence": 1, "Too few to judge": 0}
            brow.append(dict(kind="alert", key=f"alert|{a['id']}", order=300 + i, signal=a["alert"], events=a["events"],
                             data_from=a["data_from"], other=a["other"],
                             nifty_avg=nf["avg"] if nf else None, nifty_base=nf["base"] if nf else None, nifty_hit=nf["hit"] if nf else None,
                             other_avg=ot["avg"] if ot else None, other_base=ot["base"] if ot else None, other_hit=ot["hit"] if ot else None,
                             verdict=max(vds, key=lambda z: rank[z]) if vds else "Too few to judge"))
        write("backtest", pd.DataFrame(brow),
              [{"label": "backtest.py", "value": code("backtest.py"), "type": "code", "lang": "python"},
               {"label": "Full results (every table, with sample sizes)", "value": json.dumps({k: B[k] for k in B if k != "summary"}, indent=1, default=str)[:200000]}])

    # Monthly read: the latest memo, written only from that month's facts file.
    # Memo files are memos/<YYYY-MM>.json; companions (_context, _implications) are read alongside.
    memos = sorted(p for p in glob.glob(os.path.join(HERE, "memos", "*.json")) if re.fullmatch(r"\d{4}-\d{2}\.json", os.path.basename(p)))
    if memos:
        memo = json.load(open(memos[-1]))
        rows = [dict(order=0, kind="headline", month=memo["month"], title=memo["label"], body=memo["headline"])]
        rows += [dict(order=i, kind="section", month=memo["month"], title=s["title"], body=s["body"])
                 for i, s in enumerate(memo["sections"], start=1)]
        rows += [dict(order=100 + i, kind="question", month=memo["month"], title="", body=q)
                 for i, q in enumerate(memo["questions"], start=1)]
        rows += [dict(order=50 + i, kind="know", month=memo["month"], title="", body=k)
                 for i, k in enumerate(memo.get("know", []), start=1)]
        # What changed since last month: worked out by rule in changes.py.
        import changes
        prev = (pd.Period(memo["month"], "M") - 1).strftime("%Y-%m")
        if os.path.exists(os.path.join(HERE, "data", "analysis", f"facts_{prev}.json")):
            ch = changes.compare(memo["month"])
            json.dump(ch, open(os.path.join(HERE, "data", "analysis", f"changes_{memo['month']}.json"), "w"), indent=2)
            rows += [dict(order=200 + i, kind="change", month=memo["month"], title=ch["compared_label"],
                          body=c["text"], direction=c["direction"], importance=c["importance"])
                     for i, c in enumerate(ch["changes"], start=1)]
        facts_md = os.path.join(HERE, "data", "analysis", f"facts_{memo['month']}.md")
        import context
        ctx = context.latest()
        if ctx and ctx["month"] == memo["month"]:
            write("context", pd.DataFrame(context.rows_for_page(ctx)),
                  [{"label": "Researched context (sources in each row)", "value": json.dumps(ctx, indent=1, ensure_ascii=False)},
                   {"label": "context.py", "value": code("context.py"), "type": "code", "lang": "python"}])
        # Positioning: gauges, clashes and implied moves from that month's facts.
        ff = os.path.join(HERE, "data", "analysis", f"facts_{memo['month']}.json")
        if os.path.exists(ff):
            from positioning import value_text
            facts = {x["id"]: x for x in json.load(open(ff))["facts"]}
            prow, i = [], 0
            for fid in ["pos_us", "pos_india", "pos_options"]:
                for g in facts.get(fid, {}).get("numbers", {}).get("readings", []):
                    prow.append(dict(kind="gauge", key=f"gauge|{g['id']}", order=i, group=g["group"], name=g["name"],
                                     value=g["value"], value_text=value_text(g["id"], g["value"]), pctl=g["pctl"],
                                     label=g["label"], date=g["date"], asset=g["asset"]))
                    i += 1
            for j, c in enumerate(facts.get("pos_clashes", {}).get("numbers", {}).get("clashes", [])):
                prow.append(dict(kind="clash", key=f"clash|{j}", order=100 + j, text=c))
            for j, m in enumerate(facts.get("implied_moves", {}).get("numbers", {}).get("moves", [])):
                prow.append(dict(kind="implied", key=f"implied|{m['underlying']}|{str(m['expiry'])[:10]}", order=200 + j,
                                 underlying=m["underlying"], as_of=str(m["as_of"])[:10], expiry=str(m["expiry"])[:10],
                                 implied_move_pct=round(m["implied_move"] * 100, 2), pcr=round(m["pcr"], 2), days=m["days"]))
            if prow:
                write("positioning", pd.DataFrame(prow),
                      [{"label": "positioning.py", "value": code("positioning.py"), "type": "code", "lang": "python"},
                       {"label": "Sources", "value": "CFTC Commitments of Traders (publicreporting.cftc.gov); CBOE indices via Yahoo; "
                                                     "SPY options via Yahoo; NSE F&O bhavcopy and participant-wise open interest; NSDL FPI monthly report"}])
        # What this means for us, and the watchlist (refreshed against the latest data).
        imp_f = os.path.join(HERE, "memos", f"{memo['month']}_implications.json")
        if os.path.exists(imp_f):
            imp = json.load(open(imp_f))
            irows = [dict(kind="disclaimer", key="disclaimer", order=0, title="", body=imp["disclaimer"], note="")]
            irows += [dict(kind="implication", key=f"imp|{i}", order=10 + i, title=x["area"], body=x["data"], note=x["why"])
                      for i, x in enumerate(imp["implications"])]
            irows += [dict(kind="action", key=f"act|{i}", order=100 + i, title=a["title"], body=a["consider"], note=a["revisit"])
                      for i, a in enumerate(imp["actions"])]
            write("implications", pd.DataFrame(irows),
                  [{"label": "Written from", "value": f"facts_{memo['month']}, the news context and the watchlist; every number is audited by checks.py"}])
        import watch
        w = watch.run(memo["month"])
        write("watch", pd.DataFrame([dict(key=f"watch|{r['id']}", order=i, **{k: v for k, v in r.items() if k != "value"})
                                     for i, r in enumerate(w["items"])]),
              [{"label": "watchlist.json (levels you can edit)", "value": open(os.path.join(HERE, "watchlist.json")).read()},
               {"label": "watch.py", "value": code("watch.py"), "type": "code", "lang": "python"}])
        write("read", pd.DataFrame(rows),
              [{"label": "Facts the memo is written from", "value": open(facts_md).read() if os.path.exists(facts_md) else "missing"},
               {"label": "analysis.py", "value": code("analysis.py"), "type": "code", "lang": "python"}])


if __name__ == "__main__":
    main()

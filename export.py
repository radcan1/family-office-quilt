#!/usr/bin/env python3
"""
export.py — package the quilt tables as the data files the published page
reads. Each file is JSON {rows, meta}: the rows, plus the code that produced
them, so a reader can check how every number was worked out.

Writes data/export/{layer2,layer3_in,layer3_us,layer1,catalysts,quality}.json.
Run after run.py and quilt.py.
"""

import datetime as dt
import glob
import json
import math
import os

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
}
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

    l1 = last_months(pd.read_csv(os.path.join(Q, "layer1.csv")))
    l1["m"] = l1["month"].str[:7]
    l1["key"] = l1["m"] + "|" + l1["key"]
    write("layer1", l1[["key", "m", "mtd", "group", "label", "value", "units", "change_type", "chg_1", "chg_3",
                        "obs_date", "note"]], meta_q)

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

    # Monthly read: the latest memo, written only from that month's facts file.
    memos = sorted(p for p in glob.glob(os.path.join(HERE, "memos", "*.json")) if not p.endswith("_context.json"))
    if memos:
        memo = json.load(open(memos[-1]))
        rows = [dict(order=0, kind="headline", month=memo["month"], title=memo["label"], body=memo["headline"])]
        rows += [dict(order=i, kind="section", month=memo["month"], title=s["title"], body=s["body"])
                 for i, s in enumerate(memo["sections"], start=1)]
        rows += [dict(order=100 + i, kind="question", month=memo["month"], title="", body=q)
                 for i, q in enumerate(memo["questions"], start=1)]
        facts_md = os.path.join(HERE, "data", "analysis", f"facts_{memo['month']}.md")
        import context
        ctx = context.latest()
        if ctx and ctx["month"] == memo["month"]:
            write("context", pd.DataFrame(context.rows_for_page(ctx)),
                  [{"label": "Researched context (sources in each row)", "value": json.dumps(ctx, indent=1, ensure_ascii=False)},
                   {"label": "context.py", "value": code("context.py"), "type": "code", "lang": "python"}])
        write("read", pd.DataFrame(rows),
              [{"label": "Facts the memo is written from", "value": open(facts_md).read() if os.path.exists(facts_md) else "missing"},
               {"label": "analysis.py", "value": code("analysis.py"), "type": "code", "lang": "python"}])


if __name__ == "__main__":
    main()

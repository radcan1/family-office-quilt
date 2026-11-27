#!/usr/bin/env python3
"""
run.py — fetch every registered series, validate it, and write:

  data/daily/<id>.csv                  scaled daily series (one file per id)
  data/month_end_panel.csv             long table: month_end, id, value, obs_date, age_days
  data/catalysts_<date>.csv            prediction-market outcomes with flags
  data/catalysts_raw_<date>.json       raw Polymarket event payloads (audit trail)
  data/quality_report_<date>.md        PASS/WARN/FAIL for every series and check

Usage:  python3 run.py              (everything)
        python3 run.py --no-catalysts
"""

import datetime as dt
import json
import os
import sys
import time
import traceback

T0 = time.time()


def log(msg):
    print(f"[{time.time()-T0:5.0f}s] {msg}", flush=True)

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalysts
import registry
import sources
import validate

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
os.makedirs(os.path.join(OUT, "daily"), exist_ok=True)


def at_or_before(s, when):
    s = s[s.index <= when]
    return (s.iloc[-1], s.index[-1]) if len(s) else (None, None)


def main():
    today = dt.date.today()
    series = registry.all_series()
    store, status = {}, {}

    # 1. Yahoo in one batch
    ytickers = [m["source_id"] for m in series if m["source"].startswith("yahoo")]
    log(f"Yahoo: {len(set(ytickers))} tickers…")
    yb = sources.yahoo_batch(ytickers)

    # 2. Everything else, one provider call per unique (source, id)
    raw_cache = {}
    fell_back = set()
    # Spliced series are built from other registry rows, so they go last.
    ordered = [m for m in series if m["source"] != "spliced"] + [m for m in series if m["source"] == "spliced"]
    for m in ordered:
        key = (m["source"], m["source_id"])
        try:
            if m["source"] == "spliced":
                # Primary up to its last date, secondary only after it.
                prim, sec = (store[x] for x in m["source_id"].split("+"))
                s = pd.concat([prim, sec[sec.index > prim.index.max()]])
            elif m["source"] == "yahoo_tr":
                s = yb[m["source_id"]][0]
            elif m["source"] == "yahoo_px":
                s = yb[m["source_id"]][1]
            else:
                if key not in raw_cache:
                    log(f"{m['source']}: {m['source_id']}…")
                    try:
                        raw_cache[key] = sources.FETCHERS[m["source"]](m["source_id"])
                    except Exception as ex:
                        # Fall back to the last saved copy and say so, rather than drop the series.
                        cached = sources._load_cache(m["source"], m["source_id"])
                        if cached.empty:
                            raise
                        log(f"  fetch failed ({type(ex).__name__}); using cached data to {cached.index.max().date()}")
                        raw_cache[key] = cached
                        fell_back.add(m["id"])
                s = raw_cache[key]
            s = (s * m["scale"]).dropna().sort_index()
            store[m["id"]] = s
            s.rename("value").rename_axis("date").to_csv(os.path.join(OUT, "daily", f"{m['id']}.csv"))
            status[m["id"]] = validate.hygiene(m, s, today)
            if m["id"] in fell_back or any(x in fell_back for x in m["source_id"].split("+")):
                status[m["id"]].append(("WARN", "live fetch failed this run; using the last saved copy"))
        except Exception as ex:
            status[m["id"]] = [("FAIL", f"fetch error: {type(ex).__name__}: {str(ex)[:160]}")]
            traceback.print_exc(limit=1)

    # 3. Month-end panel (last 36 months + current month-to-date)
    months = pd.date_range(end=pd.Timestamp(today) + pd.offsets.MonthEnd(0), periods=37, freq="ME")
    rows = []
    for m in series:
        s = store.get(m["id"])
        if s is None or s.empty:
            continue
        for me in months:
            v, d = at_or_before(s, me)
            if v is None:
                continue
            rows.append(dict(month_end=me.date(), id=m["id"], layer=m["layer"], value=v,
                             obs_date=d.date(), age_days=(min(me, pd.Timestamp(today)) - d).days,
                             mtd=me.date() > today))
    panel = pd.DataFrame(rows)
    panel.to_csv(os.path.join(OUT, "month_end_panel.csv"), index=False)

    # 4. Derived Layer 1 numbers (latest), used for unit sanity
    def last(i):
        return store[i].iloc[-1] if i in store and len(store[i]) else None
    derived = {}
    try:
        w = store["FED_ASSETS"].index.max()
        derived["FED_NETLIQ_USD_BN"] = (at_or_before(store["FED_ASSETS"], w)[0]
                                       - at_or_before(store["FED_TGA"], w)[0]
                                       - at_or_before(store["FED_RRP"], w)[0])
        derived["FED_NETLIQ_ASOF"] = str(w.date())
        derived["G3_CB_USD_TN"] = (last("FED_ASSETS") + last("ECB_ASSETS") * last("EURUSD")
                                   + last("BOJ_ASSETS") / last("USDJPY")) / 1000
        # Global M2 on a common month: the latest month all four have reported.
        common = min(store[k].index.max() for k in ["M2_US", "M2_EA", "M2_JP", "M2_CN"])
        cm = common + pd.offsets.MonthEnd(0)
        def m2(k):
            return at_or_before(store[k], cm)[0]
        fx_e = at_or_before(store["EURUSD"], cm)[0]
        fx_j = at_or_before(store["USDJPY"], cm)[0]
        fx_c = at_or_before(store["USDCNY"], cm)[0]
        derived["GLOBAL_M2_USD_TN"] = (m2("M2_US") + m2("M2_EA") * fx_e + m2("M2_JP") / fx_j + m2("M2_CN") / fx_c) / 1000
        derived["GLOBAL_M2_ASOF"] = str(cm.date())
    except Exception as ex:
        print("derived failed:", ex)

    # 5. Catalysts
    cat_rows = []
    if "--no-catalysts" not in sys.argv:
        log("Polymarket / Kalshi…")
        cat_rows, raw = catalysts.fetch(today)
        pd.DataFrame(cat_rows).to_csv(os.path.join(OUT, f"catalysts_{today}.csv"), index=False)
        with open(os.path.join(OUT, f"catalysts_raw_{today}.json"), "w") as f:
            json.dump(raw, f, default=str)

    # 6. Report
    checks = validate.basis_checks(store)
    sanity = validate.unit_sanity(derived)
    write_report(today, series, store, status, checks, sanity, derived, cat_rows)


def write_report(today, series, store, status, checks, sanity, derived, cat_rows):
    worst = lambda lst: "FAIL" if any(s == "FAIL" for s, _ in lst) else "WARN" if any(s == "WARN" for s, _ in lst) else "PASS"
    L = [f"# Data quality report — {today}", ""]
    n = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for m in series:
        n[worst(status.get(m["id"], [("FAIL", "missing")]))] += 1
    L += [f"**Series:** {n['PASS']} pass · {n['WARN']} warn · {n['FAIL']} fail  ", ""]
    L += ["## Basis and cross-source checks", "", "| Check | Status | Detail |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in checks + sanity]
    L += ["", "## Derived Layer 1 values (latest)", ""]
    L += [f"- **{k}**: {v:,.2f}" if isinstance(v, float) else f"- **{k}**: {v}" for k, v in derived.items()]
    L += ["", "## Series", "", "| Layer | ID | Name | Source | Status | Detail |", "|---|---|---|---|---|---|"]
    for m in series:
        st = status.get(m["id"], [("FAIL", "missing")])
        L.append(f"| {m['layer']} | {m['id']} | {m['name']} | {m['source']}:{m['source_id']} | {worst(st)} | "
                 + "; ".join(d for _, d in st) + " |")
    if cat_rows:
        L += ["", "## Catalysts", "", "| Catalyst | Outcome | Prob | 30d Δ | Kalshi | Liquidity | Flags |", "|---|---|---|---|---|---|---|"]
        for r in cat_rows:
            if r.get("status") != "OK":
                L.append(f"| {r['label']} | {r.get('outcome', '—')} | — | — | — | — | {r['status']} |")
                continue
            if r["prob"] is not None and r["prob"] < 0.02 and not r["flags"]:
                continue     # skip near-zero brackets in the summary (still in the CSV)
            fmt = lambda x: "—" if x is None or (isinstance(x, float) and pd.isna(x)) else f"{x*100:.1f}%"
            dlt = "—" if r["delta_30d"] is None else f"{r['delta_30d']*100:+.1f}pp"
            L.append(f"| {r['label']} | {r['outcome']} | {fmt(r['prob'])} | {dlt} | {fmt(r['kalshi_prob'])} | "
                     f"${r['event_liquidity']:,} | {r['flags']} |")
    path = os.path.join(OUT, f"quality_report_{today}.md")
    open(path, "w").write("\n".join(L) + "\n")
    print("\n".join(L[:4]))
    log(f"Done. Report: {path}")


if __name__ == "__main__":
    main()

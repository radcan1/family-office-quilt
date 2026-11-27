#!/usr/bin/env python3
"""
checks.py — one health check across every layer, run before publishing.

Areas:
  1. Market data       every registry series fresh, complete, sane (validate.hygiene)
  2. Accuracy          total-return basis and cross-source agreement (validate.basis_checks)
  3. Positioning       each gauge fresh for its release cycle and inside a sane range
  4. Prediction mkts   today's snapshot, no expired contracts, venues checked
  5. News context      context file matches the memo month, sourcing rules met, calendar not stale
  6. Memo audit        every number in the memo appears in that month's facts, changes or context,
                       and the memo, facts and context all cover the latest completed month
  7. Page data         exported files complete (row counts, no missing key fields)

Each check is PASS / WARN / FAIL. build_site.py refuses to publish when any FAIL.

Writes data/health.json and prints a summary.   python3 checks.py
"""

import datetime as dt
import glob
import json
import os
import re

import pandas as pd

import registry
import validate

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
EXPORT = os.path.join(D, "export")


class Health:
    def __init__(self):
        self.rows = []

    def add(self, area, check, status, detail, as_of=None):
        self.rows.append(dict(area=area, check=check, status=status, detail=detail, as_of=as_of))


def latest_completed_month(today):
    return (pd.Timestamp(today) - pd.offsets.MonthEnd(1)).strftime("%Y-%m")


# ── 1–2. Market data and accuracy ───────────────────────────────────────────
def market(H, today):
    store = {}
    for p in glob.glob(os.path.join(D, "daily", "*.csv")):
        store[os.path.basename(p)[:-4]] = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"]
    n = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for m in registry.all_series():
        res = validate.hygiene(m, store.get(m["id"]), today)
        worst = "FAIL" if any(s == "FAIL" for s, _ in res) else "WARN" if any(s == "WARN" for s, _ in res) else "PASS"
        n[worst] += 1
        if worst != "PASS":
            s = store.get(m["id"])
            H.add("Market data", m["name"], worst, "; ".join(d for _, d in res),
                  str(s.index.max().date()) if s is not None and len(s) else None)
    H.add("Market data", f"All {sum(n.values())} series", "FAIL" if n["FAIL"] else "PASS",
          f"{n['PASS']} pass, {n['WARN']} warn, {n['FAIL']} fail (freshness, completeness, impossible values, one-day jumps)")
    for c, st, d in validate.basis_checks(store):
        H.add("Accuracy", c, "PASS" if st == "INFO" else st, d)
    return store


# ── 3. Positioning ──────────────────────────────────────────────────────────
POS_MAX_AGE = {"COT": 14, "VOL": 5, "NIFTY": 6, "FII": 6}       # days, by release cycle
POS_RANGE = {"COT": (-100, 100), "VOL_TERM": (0.5, 1.6), "VOL_SKEW": (100, 200), "VOL_MOVE": (40, 300),
             "NIFTY_PCR": (0.2, 5), "NIFTY_MOVE": (0.3, 30), "FII_IDXFUT": (0, 100), "FPI_EQ": (-300000, 300000)}


def positioning(H, today):
    f = os.path.join(D, "positioning", "gauges.csv")
    if not os.path.exists(f):
        H.add("Positioning", "Gauges file", "FAIL", "data/positioning/gauges.csv missing: run positioning.py")
        return
    g = pd.read_csv(f, parse_dates=["date"])
    from positioning import GAUGES
    ok = 0
    for gid, meta in GAUGES.items():
        s = g[g.gauge == gid].sort_values("date")
        if s.empty:
            H.add("Positioning", meta["name"], "FAIL", "no data")
            continue
        last, v = s.date.iloc[-1], s.value.iloc[-1]
        age = (pd.Timestamp(today) - last).days
        problems = []
        if gid == "FPI_EQ":
            need = pd.Timestamp(latest_completed_month(today)) + pd.offsets.MonthEnd(0)
            if last < need:
                problems.append(("FAIL", f"latest month {last:%b %Y}; expected {need:%b %Y}"))
        else:
            lim = POS_MAX_AGE[gid.split("_")[0]]
            if age > lim:
                problems.append(("FAIL", f"{age} days old (limit {lim})"))
        lo, hi = POS_RANGE.get(gid, POS_RANGE.get(gid.split("_")[0], (-1e12, 1e12)))
        if not lo <= v <= hi:
            problems.append(("FAIL", f"value {v:.2f} outside sane range {lo}–{hi}"))
        if len(s) < 12:
            problems.append(("WARN", f"only {len(s)} observations, so percentile labels are provisional"))
        if problems:
            st = "FAIL" if any(p[0] == "FAIL" for p in problems) else "WARN"
            H.add("Positioning", meta["name"], st, "; ".join(p[1] for p in problems), str(last.date()))
        else:
            ok += 1
    H.add("Positioning", f"{ok} of {len(GAUGES)} gauges fresh and in range", "PASS" if ok == len(GAUGES) else "WARN",
          "Futures within 14 days, daily gauges within 6, FPI flows include the last completed month")
    im = os.path.join(D, "positioning", "implied.csv")
    if os.path.exists(im):
        x = pd.read_csv(im, parse_dates=["as_of"])
        for u, lim in [("NIFTY", 6), ("SPY", 4)]:
            y = x[x.underlying == u]
            age = (pd.Timestamp(today) - y.as_of.max()).days if len(y) else 999
            H.add("Positioning", f"{u} options snapshot", "PASS" if age <= lim else "FAIL",
                  f"as of {y.as_of.max().date() if len(y) else 'never'} ({age} days old, limit {lim})")


# ── 4. Prediction markets ───────────────────────────────────────────────────
def catalysts(H, today):
    files = sorted(glob.glob(os.path.join(D, "catalysts_*.csv")))
    if not files:
        H.add("Prediction markets", "Snapshot", "FAIL", "no catalyst snapshot")
        return
    as_of = dt.date.fromisoformat(os.path.basename(files[-1])[len("catalysts_"):-4])
    age = (today - as_of).days
    H.add("Prediction markets", "Snapshot age", "PASS" if age <= 3 else "FAIL", f"Polymarket and Kalshi snapshot from {as_of} ({age} days old, limit 3)", str(as_of))
    c = pd.read_csv(files[-1])
    bad = c[c.status != "OK"]
    H.add("Prediction markets", "Every catalyst found", "PASS" if bad.empty else "WARN",
          "all catalysts matched an open event" if bad.empty else "; ".join(f"{r.label}: {r.status}" for r in bad.itertuples()))
    ok = c[c.status == "OK"].copy()
    ok["event_end"] = pd.to_datetime(ok["event_end"])
    expired = ok[ok.event_end.dt.date < today]
    H.add("Prediction markets", "No expired contracts", "PASS" if expired.empty else "WARN",
          "all contracts still open" if expired.empty else "expired: " + ", ".join(sorted(expired.label.unique())))
    chk = ok[ok.kalshi_prob.notna()]
    dis = chk[(chk.kalshi_prob - chk.prob).abs() > 0.10]
    H.add("Prediction markets", "Polymarket vs Kalshi", "PASS" if dis.empty else "WARN",
          f"{len(chk)} outcomes cross-checked; {len(dis)} differ by more than 10 points")


# ── 5. News context ─────────────────────────────────────────────────────────
def context(H, today, memo_month):
    f = os.path.join(HERE, "memos", f"{memo_month}_context.json")
    if not os.path.exists(f):
        H.add("News context", "Context file", "FAIL", f"memos/{memo_month}_context.json missing")
        return None
    ctx = json.load(open(f))
    problems = []
    for d in ctx["drivers"]:
        need = {"Confirmed": 2, "Likely": 1, "Unclear": 0}[d["confidence"]]
        if len(d["sources"]) < need:
            problems.append(f"{d['id']}: {d['confidence']} needs at least {need} sources, has {len(d['sources'])}")
        for s in d["sources"]:
            if not s["url"].startswith("https://"):
                problems.append(f"{d['id']}: non-https source {s['url'][:40]}")
    H.add("News context", "Sourcing rules", "PASS" if not problems else "FAIL",
          f"{len(ctx['drivers'])} explanations: Confirmed has 2+ sources, Likely 1+, all links https" if not problems else "; ".join(problems))
    past = [e for e in ctx["calendar"] if len(e["date"]) == 10 and dt.date.fromisoformat(e["date"]) < today]
    H.add("News context", "Calendar is forward-looking", "PASS" if not past else "WARN",
          "all events still ahead" if not past else "already passed: " + "; ".join(f"{e['date']} {e['event']}" for e in past) + " (update the calendar)")
    researched = dt.date.fromisoformat(ctx["researched"])
    age = (today - researched).days
    H.add("News context", "Research age", "PASS" if age <= 10 else "WARN", f"news researched {researched} ({age} days ago)", str(researched))
    return ctx


# ── 6. Memo audit ───────────────────────────────────────────────────────────
NUM = re.compile(r"[−\-+]?\d[\d,]*\.?\d*")


def _numbers(text):
    out = set()
    for m in NUM.findall(text):
        t = m.replace("−", "").replace("-", "").replace("+", "").replace(",", "").rstrip(".")
        if t:
            out.add(t)
    return out


def memo_audit(H, today):
    memos = sorted(p for p in glob.glob(os.path.join(HERE, "memos", "*.json")) if not p.endswith(("_context.json", "_implications.json")))
    if not memos:
        H.add("Memo", "Memo file", "FAIL", "no memo")
        return None
    memo = json.load(open(memos[-1]))
    m = memo["month"]
    want = latest_completed_month(today)
    H.add("Memo", "Covers the latest completed month", "PASS" if m == want else "WARN",
          f"memo is for {m}; latest completed month is {want}")
    facts_f = os.path.join(D, "analysis", f"facts_{m}.json")
    if not os.path.exists(facts_f):
        H.add("Memo", "Facts file", "FAIL", f"facts_{m}.json missing")
        return memo
    # Evidence: everything the memo and implications are allowed to quote — computed
    # facts (this month and last), rule-based changes, sourced context, theme checks,
    # data-quality notes, the watchlist levels and their latest readings.
    prev = (pd.Period(m, "M") - 1).strftime("%Y-%m")
    paths = [os.path.join(D, "analysis", f"facts_{m}.md"), os.path.join(D, "analysis", f"facts_{prev}.md"),
             os.path.join(D, "analysis", f"changes_{m}.json"), os.path.join(D, "analysis", f"watch_{m}.json"),
             os.path.join(HERE, "memos", f"{m}_context.json"), os.path.join(HERE, "watchlist.json"),
             os.path.join(EXPORT, "context.json"), os.path.join(EXPORT, "quality.json")]
    paths += sorted(glob.glob(os.path.join(D, "analysis", f"watch_{m}_*.json")))     # dated watchlist readings
    evidence = "".join(open(p, encoding="utf-8").read() for p in paths if os.path.exists(p))
    have = _numbers(evidence)
    # Values written to fewer decimals than the facts are fine: also accept rounded forms.
    rounded = set()
    for t in have:
        try:
            v = float(t)
            rounded |= {f"{v:.0f}", f"{v:.1f}", f"{v:.2f}"}
        except ValueError:
            pass
    have |= rounded
    years = {str(y) for y in range(2020, 2031)}

    def audit(label, texts):
        nums = {n for t in texts for n in _numbers(t)}
        missing = sorted(nums - have - years, key=lambda x: float(x))
        H.add("Memo", f"{label}: every number traces to the evidence", "PASS" if not missing else "FAIL",
              f"{len(nums)} distinct numbers checked" + ("" if not missing else "; not found in evidence: " + ", ".join(missing)))

    audit("Monthly read", [memo["headline"]] + memo.get("know", []) + [s["body"] for s in memo["sections"]] + memo.get("questions", []))
    imp_f = os.path.join(HERE, "memos", f"{m}_implications.json")
    if os.path.exists(imp_f):
        imp = json.load(open(imp_f))
        audit("What this means for us", [x["data"] + " " + x["why"] for x in imp["implications"]]
              + [a["consider"] + " " + a["revisit"] for a in imp["actions"]])
    else:
        H.add("Memo", "What this means for us", "WARN", f"memos/{m}_implications.json missing")
    return memo


# ── 7. Page data ────────────────────────────────────────────────────────────
def page_data(H):
    expect = {"layer2": len(registry.LAYER2) * 13, "layer3_in": len(registry.LAYER3_INDIA) * 13,
              "layer3_us": len(registry.LAYER3_US) * 13,
              "layer3_gl": (len(registry.LAYER3_GLOBAL) + len(registry.GLOBAL_REFERENCE)) * 13}
    for name in ["read", "context", "positioning", "layer2", "layer3_in", "layer3_us", "layer3_gl", "layer1", "catalysts", "quality"]:
        p = os.path.join(EXPORT, f"{name}.json")
        if not os.path.exists(p):
            H.add("Page data", f"{name}.json", "FAIL", "missing: run export.py")
            continue
        rows = json.load(open(p))["rows"]
        problems = []
        if name in expect and len(rows) != expect[name]:
            problems.append(f"{len(rows)} rows, expected {expect[name]}")
        if name.startswith("layer") and name != "layer1":
            nulls = sum(1 for r in rows if r.get("ret_local") is None or r.get("rank") is None)
            if nulls:
                problems.append(f"{nulls} rows missing a return or rank")
        if not rows:
            problems.append("empty")
        H.add("Page data", f"{name}.json", "FAIL" if problems else "PASS", "; ".join(problems) if problems else f"{len(rows)} rows")


def run(today=None):
    today = today or dt.date.today()
    H = Health()
    market(H, today)
    positioning(H, today)
    catalysts(H, today)
    memo = memo_audit(H, today)
    if memo:
        context(H, today, memo["month"])
    page_data(H)
    summary = {s: sum(1 for r in H.rows if r["status"] == s) for s in ["PASS", "WARN", "FAIL"]}
    out = dict(run_at=dt.datetime.now().isoformat(timespec="seconds"), as_of=str(today), summary=summary, checks=H.rows)
    json.dump(out, open(os.path.join(D, "health.json"), "w"), indent=2)
    return out


if __name__ == "__main__":
    out = run()
    for r in out["checks"]:
        if r["status"] != "PASS":
            print(f"{r['status']:4} | {r['area']:18} | {r['check']}: {r['detail'][:180]}")
    print(f"\n{out['summary']['PASS']} pass, {out['summary']['WARN']} warn, {out['summary']['FAIL']} fail")

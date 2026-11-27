#!/usr/bin/env python3
"""
context.py — the news and geopolitics layer of the monthly read.

Combines the researched context file (memos/<month>_context.json: drivers with
sources, theme status, calendar) with the numbers:

  - Theme check: for each active theme in themes.json, did its linked assets
    move the way the theme implies? (Uses local-currency returns, so currency
    moves don't blur the test.)
  - Calendar: each upcoming event gets the current prediction-market odds for
    its linked catalyst.

The explanations themselves are researched and sourced by hand each month;
this module only checks them against the data and lays them out.

    python3 context.py            (prints the theme check for the latest context file)
"""

import glob
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
Q = os.path.join(HERE, "data", "quilt")
MAX_SOURCES = 4


def _returns(month):
    """Local-currency monthly return for every quilt and sector id in `month` (YYYY-MM)."""
    out, names = {}, {}
    for f in ["layer2", "layer3_in", "layer3_us"]:
        df = pd.read_csv(os.path.join(Q, f"{f}.csv"))
        df = df[df["month"].str[:7] == month]
        out.update(dict(zip(df["id"], df["ret_local"])))
        names.update(dict(zip(df["id"], df["name"])))
    return out, names


def theme_checks(ctx):
    themes = {t["id"]: t for t in json.load(open(os.path.join(HERE, "themes.json")))["themes"]}
    rets, names = _returns(ctx["month"])
    rows = []
    for t in ctx["themes"]:
        base = themes[t["id"]]
        up, down = base["assets_up_if_active"], base["assets_down_if_active"]
        if t.get("direction", 1) < 0:
            up, down = down, up
        checks = [(a, +1) for a in up] + [(a, -1) for a in down]
        detail, hits, total = [], 0, 0
        if t["status"] == "active":
            for a, sign in checks:
                r = rets.get(a)
                if r is None or pd.isna(r):
                    continue
                ok = (r > 0) == (sign > 0)
                hits += ok
                total += 1
                detail.append(f"{names.get(a, a)} {r*100:+.1f}% ({'as expected' if ok else 'against'})")
        rows.append(dict(id=t["id"], name=base["name"], status=t["status"], summary=t["summary"],
                         why_it_matters=base["why_it_matters"], hits=hits, total=total,
                         detail="; ".join(detail)))
    return rows


def calendar(ctx):
    files = sorted(glob.glob(os.path.join(HERE, "data", "catalysts_*.csv")))
    cat = pd.read_csv(files[-1]) if files else pd.DataFrame()
    as_of = os.path.basename(files[-1])[len("catalysts_"):-4] if files else ""
    rows = []
    for e in ctx["calendar"]:
        odds = ""
        if len(cat) and e.get("catalyst"):
            c = cat[(cat["key"] == e["catalyst"]) & (cat["status"] == "OK")].sort_values("prob", ascending=False)
            if len(c):
                top = c.iloc[0]
                odds = f"{top['label']}: {top['outcome']} at {top['prob']*100:.0f}% (Polymarket, {as_of})"
                if pd.notna(top.get("kalshi_prob")):
                    odds += f"; Kalshi {top['kalshi_prob']*100:.0f}%"
                if "THIN" in str(top.get("flags", "")):
                    odds += "; thin market"
        rows.append(dict(date=e["date"], event=e["event"], why=e["why"], odds=odds,
                         src_outlet=e["source"]["outlet"], src_url=e["source"]["url"]))
    return rows


def rows_for_page(ctx):
    """Flat rows for the page's 'context' data file (no nested objects)."""
    out = []
    order = {"Confirmed": 0, "Likely": 1, "Unclear": 2}
    drivers = sorted(ctx["drivers"], key=lambda d: order.get(d["confidence"], 3))
    for i, d in enumerate(drivers):
        r = dict(kind="driver", key=f"driver|{d['id']}", order=i, title=d["fact"], body=d["why"],
                 note=d.get("note", ""), confidence=d["confidence"])
        for j, s in enumerate(d["sources"][:MAX_SOURCES], start=1):
            r[f"s{j}_outlet"], r[f"s{j}_title"], r[f"s{j}_url"], r[f"s{j}_date"] = s["outlet"], s["title"], s["url"], s["date"]
        out.append(r)
    for i, t in enumerate(theme_checks(ctx)):
        out.append(dict(kind="theme", key=f"theme|{t['id']}", order=100 + i, title=t["name"], body=t["summary"],
                        note=t["detail"], confidence=t["status"], hits=t["hits"], total=t["total"]))
    for i, e in enumerate(calendar(ctx)):
        out.append(dict(kind="event", key=f"event|{i}", order=200 + i, title=e["event"], body=e["why"],
                        note=e["odds"], confidence=e["date"], s1_outlet=e["src_outlet"], s1_url=e["src_url"]))
    return out


def latest():
    files = sorted(glob.glob(os.path.join(HERE, "memos", "*_context.json")))
    return json.load(open(files[-1])) if files else None


if __name__ == "__main__":
    ctx = latest()
    for t in theme_checks(ctx):
        print(f"{t['name']:42} {t['status']:7} {t['hits']}/{t['total']}  {t['detail']}")
    for e in calendar(ctx):
        print(e["date"], e["event"], "|", e["odds"])

#!/usr/bin/env python3
"""
watch.py — check each watchlist item (watchlist.json) against the latest data.

Status per item:
  Triggered   the latest value has crossed a level
  Near        within the item's margin of a level
  Calm        neither
  Upcoming    a dated event, with today's market odds

Writes data/analysis/watch_<memo month>.json, plus a dated copy watch_<month>_<run date>.json.   python3 watch.py 2026-10
"""

import datetime as dt
import glob
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")


def latest(source):
    kind, key = source.split(":", 1)
    if kind == "daily":
        s = pd.read_csv(os.path.join(D, "daily", f"{key}.csv"), parse_dates=["date"]).dropna().iloc[-1]
        return float(s.value), str(s.date.date())
    if kind == "gauge":
        g = pd.read_csv(os.path.join(D, "positioning", "gauges.csv"), parse_dates=["date"])
        s = g[g.gauge == key].sort_values("date")
        return float(s.value.iloc[-1]), str(s.date.iloc[-1].date())
    if kind == "chg":
        # Percentage change over the last N trading days:  chg:<series>:<days>
        sid, n = key.split(":")
        s = pd.read_csv(os.path.join(D, "daily", f"{sid}.csv"), parse_dates=["date"]).dropna()
        return float((s.value.iloc[-1] / s.value.iloc[-1 - int(n)] - 1) * 100), str(s.date.iloc[-1].date())
    if kind == "spread":
        # Latest value of a minus latest value of b:  spread:<a>-<b>
        a, b = (pd.read_csv(os.path.join(D, "daily", f"{x}.csv"), parse_dates=["date"]).dropna().iloc[-1] for x in key.split("-"))
        return float(a.value - b.value), str(max(a.date, b.date).date())
    if kind == "relret":
        # Rupee return of a minus rupee return of b over N trading days, in pp:  relret:<a>,<b>,<days>
        a, b, n = key.split(",")
        inr = pd.read_csv(os.path.join(D, "daily", "USDINR.csv"), parse_dates=["date"]).set_index("date")["value"]
        def inr_ret(x):
            s = pd.read_csv(os.path.join(D, "daily", f"{x}.csv"), parse_dates=["date"]).set_index("date")["value"].dropna()
            if x.startswith(("GL_", "US_")):
                s = (s * inr.reindex(s.index, method="ffill")).dropna()
            return s
        j = pd.concat([inr_ret(a), inr_ret(b)], axis=1, join="inner").dropna()
        r = j.iloc[-1] / j.iloc[-1 - int(n)] - 1
        return float((r.iloc[0] - r.iloc[1]) * 100), str(j.index[-1].date())
    if kind == "implied":
        im = pd.read_csv(os.path.join(D, "positioning", "implied.csv"), parse_dates=["as_of", "expiry"])
        x = im[im.underlying == key]
        x = x[x.as_of == x.as_of.max()].sort_values("expiry").iloc[0]
        return float(x.implied_move * 100), str(x.as_of.date())
    raise ValueError(source)


def fmt(v, it):
    s = f"{abs(v):,.{it.get('decimals', 2)}f}"
    u = it.get("unit", "")
    sign = "−" if v < 0 else ""
    if u in ("$", "₹"):
        return f"{sign}{u}{s}"
    if u == "±%":
        return f"±{s}%"
    if u in ("pp", "% chg"):
        return f"{'−' if v < 0 else '+'}{s}{'pp' if u == 'pp' else '%'}"
    return f"{sign}{s}{(' ' + u) if u and u != '%' else u}"


def evaluate(it, today):
    src = it["source"]
    if src.startswith("catalyst:"):
        files = sorted(glob.glob(os.path.join(D, "catalysts_*.csv")))
        c = pd.read_csv(files[-1])
        c = c[(c.key == src.split(":")[1]) & (c.status == "OK")].sort_values("prob", ascending=False)
        odds = f"{c.label.iloc[0]}: {c.outcome.iloc[0]} at {c.prob.iloc[0]*100:.0f}%" if len(c) else "no open market"
        days = (dt.date.fromisoformat(it["event_date"]) - today).days
        return dict(status="Upcoming" if days >= 0 else "Passed", value_text=odds, as_of=os.path.basename(files[-1])[11:21],
                    level_text=f"{it['event_date']} ({days} days)" if days >= 0 else it["event_date"], detail="")
    v, as_of = latest(src)
    status, crossed, levels = "Calm", [], []
    for side in ("above", "below"):
        if side in it:
            lvl = it[side]
            levels.append(f"{side} {fmt(lvl, it)}")
            if (side == "above" and v > lvl) or (side == "below" and v < lvl):
                status = "Triggered"
                crossed.append(f"{side} {fmt(lvl, it)}")
            elif status != "Triggered" and "near_pct" in it and abs(v - lvl) <= abs(lvl) * it["near_pct"] / 100:
                status = "Near"
    detail = ""
    if "streak_below_zero" in it:
        g = pd.read_csv(os.path.join(D, "positioning", "gauges.csv"))
        s = g[g.gauge == src.split(":")[1]].sort_values("date").value.tolist()
        streak = 0
        for x in reversed(s):
            if x < 0:
                streak += 1
            else:
                break
        detail = f"net selling for {streak} month{'s' if streak != 1 else ''} running"
        levels.append(f"{it['streak_below_zero']}+ months of selling")
        if streak >= it["streak_below_zero"]:
            status = "Triggered"
            crossed.append(f"{streak} months of selling")
    return dict(status=status, value=v, value_text=fmt(v, it), as_of=as_of, level_text="; ".join(levels),
                crossed="; ".join(crossed), detail=detail)


def run(month=None, today=None):
    today = today or dt.date.today()
    cfg = json.load(open(os.path.join(HERE, "watchlist.json")))
    rows = []
    for it in cfg["items"]:
        try:
            r = evaluate(it, today)
        except Exception as e:
            r = dict(status="Error", value_text="—", as_of=None, level_text="", detail=str(e)[:120])
        rows.append(dict(id=it["id"], name=it["name"], why=it["why"], if_triggered=it.get("if_triggered", ""), **r))
    order = {"Triggered": 0, "Near": 1, "Upcoming": 2, "Calm": 3, "Passed": 4, "Error": 5}
    rows.sort(key=lambda r: order.get(r["status"], 9))
    month = month or (pd.Timestamp(today) - pd.offsets.MonthEnd(1)).strftime("%Y-%m")
    out = dict(month=month, run=str(today), items=rows)
    os.makedirs(os.path.join(D, "analysis"), exist_ok=True)
    json.dump(out, open(os.path.join(D, "analysis", f"watch_{month}.json"), "w"), indent=2, ensure_ascii=False)
    # A dated copy too: a reading quoted in the implications stays checkable after the data moves on.
    json.dump(out, open(os.path.join(D, "analysis", f"watch_{month}_{today}.json"), "w"), indent=2, ensure_ascii=False)
    return out


if __name__ == "__main__":
    out = run(sys.argv[1] if len(sys.argv) > 1 else None)
    for r in out["items"]:
        print(f"{r['status']:9} {r['name']:48} {r['value_text']:38} {r['level_text']:28} {r.get('crossed','')} {r.get('detail','')}")

#!/usr/bin/env python3
"""
changes.py — "What changed since last month", worked out by rule from two
months' facts files (data/analysis/facts_<YYYY-MM>.json, from analysis.py).

Each change is a plain sentence with its numbers, a direction (up / down /
neutral, as seen by a risk-taking investor) and an importance used for order.
Prediction-market facts are skipped: we only hold today's snapshot, so there
is no earlier month to compare them with.

    python3 changes.py 2026-10        (compares October with September)
"""

import json
import os
import sys

import pandas as pd

from export import SHORT

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "data", "analysis")


def load(month):
    d = json.load(open(os.path.join(A, f"facts_{month}.json")))
    return d, {f["id"]: f for f in d["facts"]}


def names(ids):
    return ", ".join(SHORT.get(i, i) for i in ids)


def compare(month):
    prev_month = (pd.Period(month, "M") - 1).strftime("%Y-%m")
    cur, C = load(month)
    prev, P = load(prev_month)
    pl = pd.Period(prev_month, "M").strftime("%B")
    out = []

    def add(importance, direction, text):
        out.append(dict(importance=importance, direction=direction, text=text))

    # Regime label and which votes flipped
    rc, rp = C["regime"]["numbers"], P["regime"]["numbers"]
    flips = []
    for vc in rc["votes"]:
        vp = next((v for v in rp["votes"] if v["vote"] == vc["vote"]), None)
        if vp and vp["risk_on"] != vc["risk_on"]:
            flips.append(f"{vc['vote']} turned {'risk-on' if vc['risk_on'] else 'defensive'}")
    if rc["regime"] != rp["regime"]:
        d = "up" if rc["score"] > rp["score"] else "down"
        add(10, d, f"Regime moved from {rp['regime']} ({rp['score']} of 6) to {rc['regime']} ({rc['score']} of 6)"
                   + (": " + "; ".join(flips) + "." if flips else "."))
    elif flips:
        add(7, "neutral", f"Regime stayed {rc['regime']}, but votes shifted: " + "; ".join(flips) + ".")

    # Persistent leaders and laggards
    pc, pp_ = C["persistent"]["numbers"], P["persistent"]["numbers"]
    new_lead = [i for i in pc["leaders"] if i not in pp_["leaders"]]
    lost_lead = [i for i in pp_["leaders"] if i not in pc["leaders"]]
    new_lag = [i for i in pc["laggards"] if i not in pp_["laggards"]]
    left_lag = [i for i in pp_["laggards"] if i not in pc["laggards"]]
    if lost_lead:
        add(8, "down", f"No longer a persistent leader: {names(lost_lead)}.")
    cash = {"IN_CASH", "US_CASH"}
    risk_lead, cash_lead = [i for i in new_lead if i not in cash], [i for i in new_lead if i in cash]
    if risk_lead:
        add(8, "up", f"New persistent leader: {names(risk_lead)}.")
    if cash_lead:
        add(8, "down", f"Cash is now a persistent leader ({names(cash_lead)}): a defensive sign, since it ranks high only when most assets fall.")
    if new_lag:
        add(8, "down", f"New persistent laggard: {names(new_lag)}.")
    if left_lag:
        add(6, "up", f"No longer a persistent laggard: {names(left_lag)}.")

    # Top of the quilt
    tc, tp = C["leaders"]["numbers"]["top"][0], P["leaders"]["numbers"]["top"][0]
    if tc["id"] == tp["id"]:
        add(5, "neutral", f"{SHORT[tc['id']]} topped the quilt again ({tp['ret_inr']*100:+.1f}% in {pl}, {tc['ret_inr']*100:+.1f}% now).")
    else:
        add(5, "neutral", f"{SHORT[tc['id']]} took the top spot from {SHORT[tp['id']]}.")

    # Breadth and dispersion
    bc, bp = C["breadth"]["numbers"], P["breadth"]["numbers"]
    if bc["up"] != bp["up"]:
        add(7, "up" if bc["up"] > bp["up"] else "down",
            f"Breadth {'widened' if bc['up'] > bp['up'] else 'narrowed'}: {bc['up']} of {bc['of']} assets rose, against {bp['up']} in {pl}.")
    dc, dp = C["dispersion"]["numbers"]["dispersion"], P["dispersion"]["numbers"]["dispersion"]
    if abs(dc - dp) >= 0.01:
        add(4, "neutral", f"Cross-asset dispersion {'rose' if dc > dp else 'fell'} from {dp*100:.1f}% to {dc*100:.1f}%: "
                          + ("winners and losers drifted further apart." if dc > dp else "assets moved more together."))

    # Divergences switching on or off
    labels = {"eq_vs_liquidity": "equities versus liquidity", "eq_vs_credit": "equities versus credit",
              "eq_vs_vix": "equities versus volatility"}
    for k, lab in labels.items():
        if C[k]["flag"] and not P[k]["flag"]:
            add(9, "down", f"New divergence: {lab}. {C[k]['text']}")
        elif P[k]["flag"] and not C[k]["flag"]:
            add(6, "up", f"Divergence resolved: {lab}.")
    sc, sp = C["semis_vs_india_it"]["numbers"], P["semis_vs_india_it"]["numbers"]
    gc, gp = sc["smh_inr"] - sc["nifty_it"], sp["smh_inr"] - sp["nifty_it"]
    if (gc > 0) != (gp > 0) and max(abs(gc), abs(gp)) >= 0.10:
        add(9, "neutral", f"The chips-versus-Indian-IT gap flipped from {gp*100:+.1f}pp to {gc*100:+.1f}pp, a swing of "
                          f"{abs(gc - gp)*100:.0f} points: {'semiconductors' if gp > 0 else 'Indian IT'} led in {pl}, "
                          f"{'semiconductors' if gc > 0 else 'Indian IT'} now.")

    # Currency
    fc, fp = C["rupee"]["numbers"], P["rupee"]["numbers"]
    if (fc["usdinr_1m"] > 0) != (fp["usdinr_1m"] > 0):
        add(6, "neutral", f"The rupee turned: it {'weakened' if fp['usdinr_1m'] > 0 else 'strengthened'} {abs(fp['usdinr_1m'])*100:.1f}% in {pl} "
                          f"and {'weakened' if fc['usdinr_1m'] > 0 else 'strengthened'} {abs(fc['usdinr_1m'])*100:.1f}% this month, "
                          f"so currency went from {'helping' if fp['usdinr_1m'] > 0 else 'hurting'} to {'helping' if fc['usdinr_1m'] > 0 else 'hurting'} rupee returns on dollar assets.")

    # Volatility
    vc, vp = C["volatility"]["numbers"], P["volatility"]["numbers"]
    if abs(vc["vix"] - vp["vix"]) >= 2:
        add(6, "down" if vc["vix"] > vp["vix"] else "up", f"US volatility {'rose' if vc['vix'] > vp['vix'] else 'fell'}: VIX {vp['vix']:.1f} to {vc['vix']:.1f}.")
    if abs(vc["india_vix"] - vp["india_vix"]) >= 1.5:
        add(5, "down" if vc["india_vix"] > vp["india_vix"] else "up", f"India VIX {'rose' if vc['india_vix'] > vp['india_vix'] else 'fell'} from {vp['india_vix']:.1f} to {vc['india_vix']:.1f}.")

    # Fed liquidity direction
    lc, lp = C["liquidity"]["numbers"], P["liquidity"]["numbers"]
    if (lc["fed_netliq_1m"] > 0) != (lp["fed_netliq_1m"] > 0):
        add(5, "up" if lc["fed_netliq_1m"] > 0 else "down",
            f"Fed net liquidity turned from {'rising' if lp['fed_netliq_1m'] > 0 else 'falling'} ({lp['fed_netliq_1m']*100:+.1f}%) to "
            f"{'rising' if lc['fed_netliq_1m'] > 0 else 'falling'} ({lc['fed_netliq_1m']*100:+.1f}%).")

    # Newly stretched assets
    new_str = [i for i in C["stretch"]["numbers"]["stretched"] if i not in P["stretch"]["numbers"]["stretched"]]
    if new_str:
        add(6, "neutral", f"Newly stretched on trend: {names(new_str)}.")

    out.sort(key=lambda x: -x["importance"])
    return dict(month=month, compared_with=prev_month, compared_label=pl, changes=out)


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else sorted(f[6:13] for f in os.listdir(A) if f.startswith("facts_") and f.endswith(".json"))[-1]
    res = compare(month)
    json.dump(res, open(os.path.join(A, f"changes_{month}.json"), "w"), indent=2)
    for c in res["changes"]:
        print(f"[{c['importance']:>2} {c['direction']:>7}] {c['text']}")

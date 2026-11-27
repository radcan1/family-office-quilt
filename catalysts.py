"""
catalysts.py — Layer 1 Group D: prediction-market probabilities.

Polymarket (primary):
  Gamma API  https://gamma-api.polymarket.com   — find events and their markets
  CLOB API   https://clob.polymarket.com        — daily price history per outcome
Kalshi (independent cross-check, CFTC-regulated):
  https://api.elections.kalshi.com/trade-api/v2

All endpoints are public and keyless. Nothing here places or signs orders.

Why this differs from the original Apps Script:
  - Contracts are discovered each run (search + slug tokens + liquidity), not
    looked up by a hard-coded slug: slugs carry timestamps and roll over.
  - EVERY outcome market in an event is recorded. Reading only markets[0]
    returns one arbitrary bracket (e.g. "50+ bps decrease") as if it were the
    FOMC probability.
  - Month-end and 30-days-earlier values come from the CLOB price history, so
    the number is the as-of-date price, not whatever it is when the sheet
    recalculates.
"""

import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from registry import CATALYSTS
from sources import session

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"

MAJOR_REPRICING = 0.20      # |30-day change| at or above this → flag
WIDE_SPREAD = 0.05          # bid/ask wider than 5c → price is soft


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def find_event(c, as_of):
    d = session().get(f"{GAMMA}/public-search",
                      params={"q": c["query"], "limit_per_type": 20, "events_status": "active"},
                      timeout=40).json()
    cands = []
    for e in d.get("events", []):
        slug = e.get("slug", "")
        if not all(tok in slug for tok in c["slug_has"]) or e.get("closed"):
            continue
        end = pd.to_datetime(e.get("endDate"), utc=True, errors="coerce")
        if pd.isna(end) or end.date() <= as_of:
            continue
        cands.append((end, _f(e.get("liquidity")) or 0.0, e))
    if not cands:
        return None
    if c["pick"] == "nearest":
        cands.sort(key=lambda x: x[0])
    else:
        cands.sort(key=lambda x: -x[1])
    # Re-read the event by slug for full market detail.
    return session().get(f"{GAMMA}/events", params={"slug": cands[0][2]["slug"]}, timeout=40).json()[0]


def history(token_id):
    """Full daily price history for one outcome token (one request)."""
    # Called from worker threads, so no shared session object.
    from curl_cffi import requests as http
    return http.get(f"{CLOB}/prices-history",
                    params={"market": token_id, "interval": "max", "fidelity": 1440},
                    impersonate="chrome", timeout=40).json().get("history", [])


def price_at(h, when):
    """Last daily price on or before `when` (a date) in a fetched history."""
    cutoff = dt.datetime.combine(when, dt.time(23, 59, 59), tzinfo=dt.UTC).timestamp()
    pts = [p for p in h if p["t"] <= cutoff]
    return (pts[-1]["p"], dt.datetime.fromtimestamp(pts[-1]["t"], dt.UTC).date()) if pts else (None, None)


# ── Kalshi cross-check ───────────────────────────────────────────────────────
def _fomc_key(label):
    """Normalise an FOMC outcome label across venues → ('cut'|'hold'|'hike', size)."""
    l = label.lower()
    if any(w in l for w in ["no change", "maintain", "hold"]):
        return ("hold", 0)
    direction = "cut" if any(w in l for w in ["cut", "decrease"]) else "hike" if any(w in l for w in ["hike", "increase"]) else None
    big = ("50+" in l) or (">25" in l) or ("more than 25" in l)
    return (direction, "50+" if big else 25) if direction else None


def kalshi_event(series, target_month, tolerance=0):
    """tolerance: allowed month gap between venues' expiries. FOMC needs the
    exact meeting (0); a 'recession in 2026' contract settles on Kalshi in
    January of the next year, so year-type contracts use 1."""
    evs = session().get(f"{KALSHI}/events",
                        params={"series_ticker": series, "status": "open", "with_nested_markets": "true", "limit": 20},
                        timeout=40).json().get("events", [])
    best = None
    for ev in evs:
        mks = ev.get("markets") or []
        if not mks:
            continue
        exp = pd.to_datetime(mks[0].get("expected_expiration_time") or mks[0].get("close_time"), utc=True, errors="coerce")
        if pd.isna(exp):
            continue
        gap = (exp.year * 12 + exp.month) - (target_month.year * 12 + target_month.month)
        if gap < 0 or gap > tolerance:     # Kalshi may settle later, never earlier
            continue
        if best is None or gap < best[0]:
            best = (gap, ev, mks)
    if not best:
        return None
    out = {}
    for m in best[2]:
        bid, ask, last = _f(m.get("yes_bid_dollars")), _f(m.get("yes_ask_dollars")), _f(m.get("last_price_dollars"))
        mid = (bid + ask) / 2 if (bid is not None and ask is not None and ask > 0) else last
        out[m.get("yes_sub_title") or m["ticker"]] = mid
    return {"event": best[1]["event_ticker"], "probs": out}


def fetch(as_of=None):
    """Return (rows, raw). rows: one dict per outcome market, ready for CSV."""
    as_of = as_of or dt.date.today()
    prior = as_of - dt.timedelta(days=30)
    rows, raw = [], {}
    for c in CATALYSTS:
        try:
            e = find_event(c, as_of)
        except Exception as ex:          # one bad catalyst must not sink the rest
            rows.append(dict(key=c["key"], label=c["label"], status=f"ERROR: {ex}"))
            continue
        if not e:
            rows.append(dict(key=c["key"], label=c["label"], status="NO OPEN EVENT FOUND"))
            continue
        raw[c["key"]] = e
        ev_liq = _f(e.get("liquidity")) or 0.0
        end = pd.to_datetime(e.get("endDate"), utc=True)
        kal = None
        if c.get("kalshi"):
            try:
                kal = kalshi_event(c["kalshi"], end, tolerance=0 if c["key"] == "FOMC_NEXT" else 1)
            except Exception:
                kal = None
        # Placeholder brackets without an order book have no token: skip.
        live = [m for m in e.get("markets", [])
                if not m.get("closed") and m.get("clobTokenIds") and m.get("active") is not False]
        tokens = {m["id"]: json.loads(m["clobTokenIds"])[0] for m in live}   # YES tokens
        # One history request per outcome, fetched in parallel (bracket events
        # such as "Bitcoin price before year-end" have 40+ outcomes).
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {mid: pool.submit(history, tok) for mid, tok in tokens.items()}
        for m in live:
            label = m.get("groupItemTitle") or m.get("question")
            try:
                h = futs[m["id"]].result()
                p_now, d_now = price_at(h, as_of)
                p_prior, d_prior = price_at(h, prior)
            except Exception as ex:
                rows.append(dict(key=c["key"], label=c["label"], outcome=label, status=f"ERROR: {ex}"))
                continue
            spread = _f(m.get("spread"))
            flags = []
            if ev_liq < c["min_liq"]:
                flags.append("THIN")
            if spread is not None and spread > WIDE_SPREAD:
                flags.append("WIDE SPREAD")
            delta = (p_now - p_prior) if (p_now is not None and p_prior is not None) else None
            if delta is not None and abs(delta) >= MAJOR_REPRICING:
                flags.append("MAJOR REPRICING")
            k_prob = None
            if kal:
                if c["key"] == "FOMC_NEXT":
                    key = _fomc_key(label)
                    k_prob = next((v for k, v in kal["probs"].items() if _fomc_key(k) == key), None)
                elif len(kal["probs"]) == 1 and len(e["markets"]) == 1:
                    k_prob = next(iter(kal["probs"].values()))
            if k_prob is not None and p_now is not None and abs(k_prob - p_now) > 0.10:
                flags.append("VENUES DISAGREE")
            rows.append(dict(
                key=c["key"], label=c["label"], event_slug=e["slug"], event_end=end.date().isoformat(),
                outcome=label, prob=p_now, prob_date=d_now and d_now.isoformat(),
                prob_30d_ago=p_prior, delta_30d=delta, spread=spread, event_liquidity=round(ev_liq),
                kalshi_event=kal and kal["event"], kalshi_prob=k_prob,
                condition_id=m.get("conditionId"), flags="; ".join(flags), status="OK"))
    return rows, raw

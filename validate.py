"""
validate.py — data-quality checks run on every fetch, before any number reaches
the quilt or the IC memo. Each check returns (status, detail) with status in
PASS / WARN / FAIL.

Three kinds of check:
  1. Hygiene    — freshness, completeness, impossible values, one-day jumps
  2. Basis      — total-return series really include income (TR minus price
                  must be small and non-negative), so rankings are like-for-like
  3. Cross-source — the same quantity from two independent providers agrees
"""

import datetime as dt

import numpy as np
import pandas as pd

MAX_AGE_DAYS = {"D": 5, "W": 12, "M": 75}      # monthly macro is published with a lag
MIN_OBS_365 = {"D": 200, "W": 45, "M": 9}


def month_end(s):
    return s.resample("ME").last().dropna()


def mret(s):
    return month_end(s).pct_change().dropna()


def hygiene(meta, s, today):
    out = []
    if s is None or s.empty:
        return [("FAIL", "no data returned")]
    age = (pd.Timestamp(today) - s.index.max()).days
    lim = MAX_AGE_DAYS[meta["freq"]]
    if meta["source_id"] == "BTC-USD":
        lim = 2                                  # trades every day
    elif meta["source"] == "fred" and meta["basis"] in ("fx", "check") and meta["freq"] == "D":
        lim = 10                                 # Fed H.10 FX is released weekly, on Mondays
    out.append(("PASS" if age <= lim else "FAIL", f"last obs {s.index.max().date()} ({age}d old, limit {lim}d)"))
    n = (s.index > pd.Timestamp(today) - pd.Timedelta(days=365)).sum()
    if meta["source"] == "rbi_mmo":
        out.append(("WARN", f"{n} obs in last 365d — history accumulates from first run (RBI has no bulk archive)"))
    elif n < MIN_OBS_365[meta["freq"]]:
        out.append(("FAIL", f"only {n} obs in last 365d (expect ≥{MIN_OBS_365[meta['freq']]})"))
    if meta["basis"] in ("total_return", "price", "fx") and (s <= 0).any():
        out.append(("FAIL", "non-positive values in a price/index series"))
    if meta["basis"] in ("total_return", "price") and meta["freq"] == "D" and len(s) > 260:
        r = s.pct_change().dropna()
        sd = r.rolling(250, min_periods=120).std().shift(1)
        z = (r / sd).abs()
        recent = z[z.index > pd.Timestamp(today) - pd.Timedelta(days=400)]
        big = recent[recent > 8]
        if len(big):
            out.append(("WARN", "one-day jumps >8σ on " + ", ".join(f"{d.date()} ({r[d]*100:+.1f}%)" for d in big.index[:4])))
    return out


def _monthly_gap(tr, px, months=12):
    a, b = mret(tr), mret(px)
    j = pd.concat([a, b], axis=1, join="inner").dropna().iloc[-months - 1:-1]  # completed months
    return (j.iloc[:, 0] - j.iloc[:, 1]), j


def basis_checks(store):
    res = []

    def add(name, status, detail):
        res.append((name, status, detail))

    # Nifty 50: TRI vs price from the same provider
    if {"IN_LARGE", "X_NIFTY_PXNI"} <= store.keys():
        g, _ = _monthly_gap(store["IN_LARGE"], store["X_NIFTY_PXNI"])
        yr = g.sum() * 100
        ok = (g.min() > -0.0005) and (0.5 <= yr <= 2.5)
        add("Nifty 50 TRI includes dividends", "PASS" if ok else "FAIL",
            f"12m TRI−price gap {yr:.2f}pp (expect 0.5–2.5), worst month {g.min()*100:+.3f}pp")
    if {"IN_MID", "X_MID_PXNI"} <= store.keys():
        g, _ = _monthly_gap(store["IN_MID"], store["X_MID_PXNI"])
        add("Midcap 150 TRI includes dividends", "PASS" if g.min() > -0.0005 and 0.2 <= g.sum() * 100 <= 2.0 else "WARN",
            f"12m gap {g.sum()*100:.2f}pp")
    # 10Y G-Sec: total-return index vs clean price → should differ by roughly the coupon
    if {"IN_GSEC10", "X_GSEC_CLEAN"} <= store.keys():
        g, _ = _monthly_gap(store["IN_GSEC10"], store["X_GSEC_CLEAN"])
        add("10Y G-Sec index is total return (not clean price)", "PASS" if 5.0 <= g.sum() * 100 <= 8.5 else "FAIL",
            f"12m TR−clean gap {g.sum()*100:.2f}pp (≈ coupon accrual, expect 5–8.5)")
    # Yahoo: adjusted vs raw close
    for tid, lo, hi in [("SPY", 0.8, 2.0), ("HYG", 4.0, 8.0)]:
        a, b = f"US_LARGE" if tid == "SPY" else "US_HY", f"X_{tid}_PRICE"
        if {a, b} <= store.keys():
            g, _ = _monthly_gap(store[a], store[b])
            add(f"{tid} adjusted close includes distributions", "PASS" if lo <= g.sum() * 100 <= hi else "WARN",
                f"12m adj−price gap {g.sum()*100:.2f}pp (expect {lo}–{hi})")
    # Cross-source: Nifty 50 price Yahoo vs NSE
    if {"X_NIFTY_PX", "X_NIFTY_PXNI"} <= store.keys():
        g, _ = _monthly_gap(store["X_NIFTY_PX"], store["X_NIFTY_PXNI"])
        add("Nifty 50 price: Yahoo vs NSE", "PASS" if g.abs().max() < 0.002 else "WARN",
            f"max monthly diff {g.abs().max()*100:.3f}pp over 12m")
    # Cross-source: USD/INR Yahoo vs FRED on the same dates. Informational —
    # the quilt uses FRED wherever FRED has a print (see registry USDINR).
    if {"X_USDINR_YAHOO", "X_USDINR_FRED"} <= store.keys():
        j = pd.concat([store["X_USDINR_YAHOO"], store["X_USDINR_FRED"]], axis=1, join="inner").dropna()
        j = j[j.index > j.index.max() - pd.Timedelta(days=365)]
        d = (j.iloc[:, 0] / j.iloc[:, 1] - 1).abs()
        add("USD/INR: Yahoo vs FRED (same day)", "PASS" if d.median() < 0.003 else "WARN",
            f"median diff {d.median()*100:.2f}%, max {d.max()*100:.2f}% on {d.idxmax().date()} — "
            "quilt uses FRED; Yahoo only fills the days after FRED's last print")
    # Informational: Indian gold premium. The Gold tile uses international gold
    # in INR (decision 2026-11-27); this shows how far Indian gold (Gold BeES)
    # drifted from it, which the IC memo can mention for INR gold holders.
    if {"GOLD", "USDINR", "X_GOLDBEES"} <= store.keys():
        inr_gold = (store["GOLD"].reindex(store["USDINR"].index, method="ffill") * store["USDINR"]).dropna()
        g, _ = _monthly_gap(inr_gold, store["X_GOLDBEES"])
        last_m = -g.iloc[-1] * 100        # positive = Indian gold beat international
        add("Indian gold premium vs international (note only)", "INFO",
            f"last completed month Indian gold {last_m:+.2f}pp vs international; "
            f"12m range {(-g).min()*100:+.2f} to {(-g).max()*100:+.2f}pp. "
            "A move beyond ±3pp in a month usually means an import-duty change or a local-premium swing")
    return res


def unit_sanity(derived):
    res = []
    rng = {"FED_NETLIQ_USD_BN": (3000, 9000), "G3_CB_USD_TN": (10, 30), "GLOBAL_M2_USD_TN": (60, 140)}
    for k, (lo, hi) in rng.items():
        v = derived.get(k)
        if v is None:
            res.append((k, "FAIL", "could not compute"))
        else:
            res.append((k, "PASS" if lo <= v <= hi else "FAIL", f"{v:,.2f} (plausible {lo:,}–{hi:,})"))
    return res

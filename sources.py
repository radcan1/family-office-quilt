"""
sources.py — one fetcher per data provider. Every fetcher returns a pandas
Series of RAW values indexed by date (no unit scaling; registry.scale does that).

Providers (all keyless, all tested live 2026-11-27):
  yahoo_tr / yahoo_px  Yahoo Finance via yfinance: Adj Close (total return) / Close
  nifty_tri / nifty_px niftyindices.com (NSE Indices Ltd, the index owner)
  fred                 FRED keyless CSV
  ecb                  ECB Data Portal SDMX API
  boj                  Bank of Japan Time-Series API
  akshare_cn_m2        PBoC money supply via akshare
  rbi_mmo              RBI daily Money Market Operations press release
  bbk / mof_jgb / boe  Bundesbank, Japan MoF and Bank of England daily 10Y yields
  akshare_cn_yield     ChinaBond yields; akshare_index: CSI 300 (Sina)

Caching: series that are never revised (NSE indices, RBI releases) are cached
and fetched incrementally. Yahoo's adjusted close is re-based on every
dividend, so it is ALWAYS refetched in full rather than spliced onto old rows.
"""

import datetime as dt
import html
import io
import json
import os
import re
import time

import pandas as pd
from curl_cffi import requests as http

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "raw")
os.makedirs(CACHE, exist_ok=True)

START = dt.date(2020, 1, 1)          # enough history for 200-DMA and 3M ranks
_session = None


def session():
    global _session
    if _session is None:
        # FRED and niftyindices reject plain python-requests TLS fingerprints.
        _session = http.Session(impersonate="chrome")
    return _session


def _cache_path(source, sid):
    return os.path.join(CACHE, f"{source}__{re.sub(r'[^A-Za-z0-9]+', '_', sid)}.csv")


def _load_cache(source, sid):
    p = _cache_path(source, sid)
    if not os.path.exists(p):
        return pd.Series(dtype=float)
    df = pd.read_csv(p, parse_dates=["date"])
    return df.set_index("date")["value"].astype(float)


def _save_cache(source, sid, s):
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s.rename("value").rename_axis("date").to_csv(_cache_path(source, sid))
    return s


# ── Yahoo ────────────────────────────────────────────────────────────────────
def yahoo_batch(tickers):
    """Return {ticker: (adj_close_series, close_series)} in one download."""
    import yfinance as yf
    import warnings
    warnings.filterwarnings("ignore")
    tickers = sorted(set(tickers))
    d = yf.download(tickers, start=START.isoformat(), auto_adjust=False,
                    progress=False, group_by="column", threads=True)
    out = {}
    for t in tickers:
        try:
            adj = d["Adj Close"][t].dropna()
            px = d["Close"][t].dropna()
        except KeyError:
            adj = px = pd.Series(dtype=float)
        adj.index = pd.to_datetime(adj.index).tz_localize(None)
        px.index = pd.to_datetime(px.index).tz_localize(None)
        out[t] = (adj, px)
        if not adj.empty:
            _save_cache("yahoo_tr", t, adj)
            _save_cache("yahoo_px", t, px)
    return out


# ── niftyindices.com ─────────────────────────────────────────────────────────
_NI_BASE = "https://www.niftyindices.com"
_NI_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": _NI_BASE,
    "Referer": _NI_BASE + "/reports/historical-data",
    "X-Requested-With": "XMLHttpRequest",
}
_NI_PAUSE = 1.5     # polite: one request at a time (NSE has blocked bursts before)
_ni_warm = False


def _ni_post(endpoint, name, start, end):
    global _ni_warm
    s = session()
    if not _ni_warm:
        s.get(_NI_BASE + "/reports/historical-data", timeout=30)
        _ni_warm = True
    cinfo = "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" % (
        name, start.strftime("%d-%b-%Y"), end.strftime("%d-%b-%Y"), name)
    r = s.post(f"{_NI_BASE}/BackPage/{endpoint}", data=json.dumps({"cinfo": cinfo}),
               headers=_NI_HEADERS, timeout=40)
    time.sleep(_NI_PAUSE)
    txt = r.text.strip()
    if not txt.startswith("["):
        if txt.startswith("{"):
            d = json.loads(txt)
            return json.loads(d["d"]) if "d" in d else []
        raise RuntimeError(f"niftyindices returned non-JSON for {name} ({endpoint})")
    return json.loads(txt)


def nifty(name, kind):
    """kind='tri' → TotalReturnsIndex, kind='px' → index CLOSE. Incremental."""
    source = "nifty_tri" if kind == "tri" else "nifty_px"
    cached = _load_cache(source, name)
    start = (cached.index.max().date() - dt.timedelta(days=7)) if not cached.empty else START
    end = dt.date.today()
    rows = {}
    # The site caps one request at 365 days.
    while start <= end:
        chunk_end = min(start + dt.timedelta(days=360), end)
        ep = "getTotalReturnIndexString" if kind == "tri" else "getHistoricaldatatabletoString"
        for rec in _ni_post(ep, name, start, chunk_end):
            d = rec.get("Date") or rec.get("HistoricalDate")
            v = rec.get("TotalReturnsIndex") if kind == "tri" else rec.get("CLOSE")
            try:
                rows[pd.Timestamp(dt.datetime.strptime(d.strip(), "%d %b %Y"))] = float(str(v).replace(",", ""))
            except (ValueError, AttributeError, TypeError):
                continue
        start = chunk_end + dt.timedelta(days=1)
    new = pd.Series(rows, dtype=float)
    return _save_cache(source, name, pd.concat([cached, new]))


# ── FRED ─────────────────────────────────────────────────────────────────────
def fred(sid):
    r = session().get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=40)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    s = df.dropna().set_index(pd.to_datetime(df.dropna()["date"]))["value"]
    return _save_cache("fred", sid, s)


# ── ECB Data Portal ──────────────────────────────────────────────────────────
def ecb(key):
    flow, series = key.split("/", 1)
    url = f"https://data-api.ecb.europa.eu/service/data/{flow}/{series}?startPeriod=2019-01&format=csvdata"
    df = pd.read_csv(io.StringIO(session().get(url, timeout=40).text))
    s = pd.Series(df["OBS_VALUE"].astype(float).values,
                  index=pd.to_datetime(df["TIME_PERIOD"]) + pd.offsets.MonthEnd(0))
    return _save_cache("ecb", key, s)


# ── Bank of Japan ────────────────────────────────────────────────────────────
def boj(key):
    db, code = key.split(":")
    url = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode"
           f"?format=json&lang=en&db={db}&code={code}&startDate=201901")
    d = json.loads(session().get(url, timeout=40).text)
    v = d["RESULTSET"][0]["VALUES"]
    idx = [pd.Timestamp(dt.datetime.strptime(str(p), "%Y%m")) + pd.offsets.MonthEnd(0) for p in v["SURVEY_DATES"]]
    s = pd.Series([float(x) if x is not None else None for x in v["VALUES"]], index=idx, dtype=float).dropna()
    return _save_cache("boj", key, s)


# ── Government bond yields, each from the official publisher ─────────────────
def bbk(key):
    """Deutsche Bundesbank time-series API (e.g. German 10Y yield, daily)."""
    flow, series = key.split("/", 1)
    url = (f"https://api.statistiken.bundesbank.de/rest/data/{flow}/{series}"
           f"?format=csv&lang=en&startPeriod={START.isoformat()}")
    rows = re.findall(r"^(\d{4}-\d{2}-\d{2}),(-?\d+\.?\d*),", session().get(url, timeout=60).text, re.M)
    s = pd.Series({pd.Timestamp(d): float(v) for d, v in rows}, dtype=float)
    if s.empty:
        raise ValueError("Bundesbank returned no rows")
    return _save_cache("bbk", key, s)


def mof_jgb(tenor):
    """Japan Ministry of Finance JGB benchmark yields: full history file plus the current month."""
    base = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
    out = {}
    for path in ["historical/jgbcme_all.csv", "jgbcme.csv"]:
        txt = session().get(base + path, timeout=60).content.decode("utf-8", errors="ignore")
        lines = [l for l in txt.splitlines() if re.match(r"^(Date|\d{4}/\d{1,2}/\d{1,2}),", l)]
        df = pd.read_csv(io.StringIO("\n".join(lines)))
        df = df[pd.to_numeric(df[tenor], errors="coerce").notna()]
        for d, v in zip(pd.to_datetime(df["Date"], format="%Y/%m/%d"), df[tenor].astype(float)):
            if d.date() >= START:
                out[d] = v
    return _save_cache("mof_jgb", tenor, pd.Series(out, dtype=float))


def boe(code):
    """Bank of England database (e.g. IUDMNPY: 10Y nominal par gilt yield, daily)."""
    url = ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes"
           f"&Datefrom={START.strftime('%d/%b/%Y')}&Dateto=now&SeriesCodes={code}&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N")
    rows = re.findall(r"^(\d{2} \w{3} \d{4}),(-?\d+\.?\d*)", session().get(url, timeout=60).text, re.M)
    s = pd.Series({pd.Timestamp(dt.datetime.strptime(d, "%d %b %Y")): float(v) for d, v in rows}, dtype=float)
    if s.empty:
        raise ValueError("Bank of England returned no rows")
    return _save_cache("boe", code, s)


def _ak(*names):
    """akshare renames functions between versions; take the first that exists."""
    import akshare as ak
    for n in names:
        try:
            return getattr(ak, n)
        except AttributeError:
            continue
    raise AttributeError(f"akshare has none of {names}")


def akshare_cn_yield(col):
    """China government bond yields (ChinaBond via Eastmoney), e.g. 中国国债收益率10年."""
    df = _ak("bond_zh_us_yield_em", "bond_zh_us_rate")(start_date=START.strftime("%Y%m%d"))
    s = pd.Series(pd.to_numeric(df[col], errors="coerce").values, index=pd.to_datetime(df["日期"])).dropna()
    return _save_cache("akshare_cn_yield", col, s)


def akshare_index(symbol):
    """Mainland China index closes from Sina (e.g. sh000300 = CSI 300). Yahoo's copy is unreliable."""
    df = _ak("index_zh_daily_sina", "stock_zh_index_daily")(symbol=symbol)
    s = pd.Series(df["close"].astype(float).values, index=pd.to_datetime(df["date"]))
    return _save_cache("akshare_index", symbol, s[s.index >= pd.Timestamp(START)])


# ── China M2 (PBoC via akshare) ──────────────────────────────────────────────
def akshare_cn_m2(_):
    df = _ak("macro_china_money_supply_em", "macro_china_money_supply")()
    col_m = df.columns[0]                     # e.g. "2026年10月份"
    col_v = [c for c in df.columns if "M2" in c and "数量" in c][0]
    idx = [pd.Timestamp(dt.datetime.strptime(re.sub(r"月份$", "", m), "%Y年%m")) + pd.offsets.MonthEnd(0)
           for m in df[col_m]]
    s = pd.Series(df[col_v].astype(float).values, index=idx).sort_index()
    return _save_cache("akshare_cn_m2", "M2", s)


# ── RBI Money Market Operations ──────────────────────────────────────────────
# Each daily release has a line "F. Net liquidity injected (outstanding
# including today's operations)" in ₹ crore. The RSS feed and the press-release
# list carry roughly the last month; older releases are not bulk-downloadable,
# so this series builds up from the first run onward (history is cached).
_RBI_ROW_F = re.compile(r"F\.\s*Net liquidity injected \(outstanding including today.{0,80}?\*\s*\|\s*(-?[\d,]+\.?\d*)", re.S)


def rbi_mmo(_):
    cached = _load_cache("rbi_mmo", "F")
    s = session()
    page = s.get("https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx", timeout=40).text
    links = re.findall(r"BS_PressReleaseDisplay\.aspx\?prid=(\d+)'?>\s*Money Market Operations as on ([A-Za-z]+ \d{1,2}, \d{4})", page)
    rows = {}
    for prid, d in links:
        when = pd.Timestamp(dt.datetime.strptime(d, "%B %d, %Y"))
        if when in cached.index:
            continue
        q = s.get(f"https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid={prid}", timeout=40).text
        txt = html.unescape(re.sub(r"<[^>]+>", " | ", q))
        txt = re.sub(r"(\s*\|\s*)+", " | ", txt)
        m = _RBI_ROW_F.search(txt)
        if m:
            rows[when] = float(m.group(1).replace(",", ""))
        time.sleep(0.8)
    return _save_cache("rbi_mmo", "F", pd.concat([cached, pd.Series(rows, dtype=float)]))


def nifty_pepb(name, start=None):
    """Daily P/E, P/B and dividend yield for an NSE index, from niftyindices.com.
    Incremental and cached (values are never revised). Returns a DataFrame with
    columns pe, pb, dy indexed by date. NSE switched index P/E from standalone to
    consolidated earnings on 31 March 2021; valuation.py adjusts for the break."""
    p = _cache_path("nifty_pepb", name)
    cached = pd.read_csv(p, parse_dates=["date"]).set_index("date") if os.path.exists(p) else pd.DataFrame(columns=["pe", "pb", "dy"])
    first = start or dt.date(2005, 1, 1)
    if not cached.empty:          # history is fetched once; later runs only add new days
        chunks = [(cached.index.max().date() - dt.timedelta(days=7), dt.date.today())]
    else:
        chunks = [(first, dt.date.today())]
    rows = {}
    for a, end in chunks:
        while a <= end:
            b = min(a + dt.timedelta(days=360), end)
            for rec in _ni_post("getpepbHistoricaldataDBtoString", name, a, b):
                try:
                    d = pd.Timestamp(dt.datetime.strptime(rec["DATE"].strip(), "%d %b %Y"))
                    rows[d] = [float(str(rec[k]).replace(",", "")) if str(rec[k]).strip() not in ("", "-") else None
                               for k in ("pe", "pb", "divYield")]
                except (ValueError, KeyError, AttributeError):
                    continue
            a = b + dt.timedelta(days=1)
    new = pd.DataFrame.from_dict(rows, orient="index", columns=["pe", "pb", "dy"])
    df = pd.concat([cached, new]) if not cached.empty else new
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "date"
    df.to_csv(p)
    return df


def worldperatio(slug):
    """Monthly trailing P/E history for a country or index ETF from worldperatio.com
    (estimated from the ETF's holdings; e.g. slug 'area/japan' is EWJ). Returns
    (series, etf_ticker). The site's latest point is the current month to date."""
    t = session().get(f"https://worldperatio.com/{slug}/", timeout=40).text
    time.sleep(1.0)
    i = t.find("detailPE_data = ")
    if i < 0:
        raise ValueError(f"worldperatio: no P/E history on {slug}")
    blob = t[i:t.find(";", i)]
    pts = re.findall(r"Date\.UTC\((\d+),\s*(\d+),\s*(\d+)\),([\d.\-]+)", blob)
    s = pd.Series({pd.Timestamp(int(y), int(m) + 1, 1) + pd.offsets.MonthEnd(0): float(v) for y, m, d, v in pts}, dtype=float)
    etf = re.search(r"calculated on the\s*(?:<[^>]+>)*\s*([A-Z]{2,5})\s*(?:<[^>]+>)*\s*Etf", t)
    _save_cache("worldperatio", slug, s)
    return s, (etf.group(1) if etf else None)


def yahoo_pe(tickers):
    """Today's trailing P/E for ETFs from Yahoo (fund summary). Current value only,
    used as an independent cross-check and for funds with no P/E history."""
    import yfinance as yf
    out = {}
    for t in tickers:
        try:
            v = yf.Ticker(t).info.get("trailingPE")
            out[t] = float(v) if v else None
        except Exception:
            out[t] = None
        time.sleep(0.3)
    return out


FETCHERS = {
    "nifty_tri": lambda sid: nifty(sid, "tri"),
    "nifty_px": lambda sid: nifty(sid, "px"),
    "fred": fred,
    "ecb": ecb,
    "boj": boj,
    "akshare_cn_m2": akshare_cn_m2,
    "rbi_mmo": rbi_mmo,
    "bbk": bbk,
    "mof_jgb": mof_jgb,
    "boe": boe,
    "akshare_cn_yield": akshare_cn_yield,
    "akshare_index": akshare_index,
}

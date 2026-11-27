#!/usr/bin/env python3
"""
build_site.py — build the public GitHub Pages site in docs/.

The page design lives in ONE place, page/index.html (the same file the Claude
dashboard uses). This script wraps it in a standalone document: theme tokens,
fonts, a small `dash` shim that loads docs/data/*.json, and a footer with the
data date and sources. Run after export.py.

    python3 build_site.py
"""

import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
SETS = ["health", "read", "implications", "watch", "context", "positioning", "layer2", "layer3_in", "layer3_us", "layer3_gl", "layer1", "valuation", "backtest", "catalysts"]

TOKENS = """
:root {
  --color-bg: #f5f6f8; --color-panel: #ffffff; --color-fg: #1a1e24; --color-fg-muted: #5b6471;
  --color-border-line: #dfe3e8; --color-ok: #15803d; --color-warn: #b45309; --color-bad: #b91c1c;
  --series-1: #c2410c; --series-2: #2563eb; --series-3: #0f766e; --series-4: #a16207; --series-5: #7c3aed;
  --cds-chart-grid: #e6e9ee; --cds-surface-popover: #ffffff; --cds-border: #d5dae1;
  --cds-shadow-popover: 0 6px 24px rgba(20, 28, 40, .14); --cds-text-secondary: #5b6471;
  --font-anthropic-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-anthropic-serif: "Source Serif 4", Georgia, "Times New Roman", serif;
  --cds-font-size-caption: 12.5px; --cds-font-size-body: 15px; --cds-font-size-heading: 18px; --cds-font-size-title: 30px;
  --cds-font-weight-medium: 600;
  --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 12px; --cds-gap-lg: 20px; --cds-gap-xl: 36px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 18px; --cds-pad-xl: 28px;
  --cds-radius: 8px;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #111317; --color-panel: #191c21; --color-fg: #e6e8eb; --color-fg-muted: #9aa3ae;
    --color-border-line: #2a2f37; --color-ok: #4ade80; --color-warn: #fbbf24; --color-bad: #f87171;
    --series-1: #fb923c; --series-2: #60a5fa; --series-3: #2dd4bf; --series-4: #facc15; --series-5: #a78bfa;
    --cds-chart-grid: #2a2f37; --cds-surface-popover: #1f2329; --cds-border: #353b44;
    --cds-shadow-popover: 0 6px 24px rgba(0, 0, 0, .5); --cds-text-secondary: #9aa3ae;
    color-scheme: dark;
  }
}
html, body { margin: 0; background: var(--color-bg); color: var(--color-fg); }
body { font: 15px/1.45 var(--font-anthropic-sans); -webkit-font-smoothing: antialiased; }
#dash-root { max-width: 1320px; margin: 0 auto; padding-block: 32px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.dash-select { font: inherit; font-size: 13px; color: var(--color-fg); background-color: var(--color-panel);
  border: 1px solid var(--color-border-line); border-radius: 6px; padding: 5px 28px 5px 10px; appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, var(--color-fg-muted) 50%), linear-gradient(135deg, var(--color-fg-muted) 50%, transparent 50%);
  background-position: calc(100% - 15px) 55%, calc(100% - 10px) 55%; background-size: 5px 5px; background-repeat: no-repeat; }
.dash-select:focus-visible, summary:focus-visible { outline: 2px solid var(--series-2); outline-offset: 2px; }
.dash-skeleton { position: relative; min-height: 120px; }
.dash-skeleton > * { visibility: hidden; }
.dash-skeleton::after { content: ""; position: absolute; inset: 0; border-radius: var(--cds-radius);
  background: linear-gradient(90deg, var(--color-border-line), var(--color-panel), var(--color-border-line)); background-size: 200% 100%; opacity: .5; }
@media (prefers-reduced-motion: no-preference) { .dash-skeleton::after { animation: fqshimmer 1.4s linear infinite; } }
@keyframes fqshimmer { from { background-position: 200% 0; } to { background-position: 0 0; } }
.site-foot { margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--color-border-line);
  font-size: 12.5px; color: var(--color-fg-muted); display: flex; flex-direction: column; gap: 6px; max-width: 90ch; }
.site-foot p { margin: 0; }
"""

# A minimal stand-in for the Claude dashboard runtime: just enough of
# dash.data / dash.draw / dash.colors for page/index.html to run unchanged.
SHIM = """
window.dash = (function () {
  const SETS = %s;
  const store = {}; SETS.forEach(s => { store[s] = { status: 'loading', data: [] }; });
  const draws = new Map();
  let started = false;
  const run = (name) => {
    const fn = draws.get(name); if (!fn) return;
    document.querySelectorAll('[data-draw="' + name + '"]').forEach(el => {
      if (el.closest('[hidden]')) return;
      try { fn(el); } catch (e) { console.error('draw ' + name, e); }
    });
  };
  const runAll = () => draws.forEach((_, n) => run(n));
  document.addEventListener('DOMContentLoaded', () => {
    started = true; runAll();
    SETS.forEach(s => fetch('data/' + s + '.json', { cache: 'no-cache' })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(j => { store[s] = { status: 'ok', data: j.rows || j }; runAll(); })
      .catch(() => { store[s] = { status: 'error', data: [] }; runAll(); }));
  });
  return {
    data: (id) => store[id] || { status: 'missing', data: [] },
    draw(name, fn) {
      if (fn) { draws.set(name, typeof fn === 'function' ? fn : (el) => (fn.update || fn.mount)(el)); if (started) run(name); }
      else run(name);
    },
    onData(fn) { fn(); },
    colors: ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)', 'var(--series-5)'],
    setLink() {}, params: () => ({}), setParams() {}, resetParams() {}, refresh() {},
  };
})();
"""


def privacy_guard():
    """Stop the build if anything private could reach the public repo or site.

    The repo is public. Family office holdings, weights and amounts live only
    in private/ (git-ignored). This fails loudly if a private file is tracked,
    or if the published files mention one.
    """
    import subprocess
    tracked = subprocess.run(["git", "ls-files"], cwd=HERE, capture_output=True, text=True).stdout.splitlines()
    bad = [f for f in tracked if f.startswith("private/") or ".private." in f]
    if bad:
        raise SystemExit(f"PRIVACY GUARD: private files are tracked by git: {bad}. Remove them before publishing.")
    for root, _, files in os.walk(DOCS):
        for f in files:
            p = os.path.join(root, f)
            if f.endswith((".html", ".json")) and "private/" in open(p, errors="ignore").read():
                raise SystemExit(f"PRIVACY GUARD: {os.path.relpath(p, HERE)} references private/.")


def health_gate():
    """Run every check (checks.py). Refuse to publish on any FAIL unless --force.
    Writes the results as the page's 'health' data file."""
    import sys
    import checks
    h = checks.run()
    rows = [dict(key=f"h|{i}", order=i, **r) for i, r in enumerate(h["checks"])]
    rows.insert(0, dict(key="summary", order=-1, area="Summary", check="All checks", status="FAIL" if h["summary"]["FAIL"] else "PASS",
                        detail=f"{h['summary']['PASS']} passed, {h['summary']['WARN']} warnings, {h['summary']['FAIL']} failures",
                        as_of=h["as_of"], passed=h["summary"]["PASS"], warned=h["summary"]["WARN"], failed=h["summary"]["FAIL"]))
    json.dump({"rows": rows, "meta": [{"label": "checks.py", "value": open(os.path.join(HERE, "checks.py")).read(), "type": "code", "lang": "python"}]},
              open(os.path.join(HERE, "data", "export", "health.json"), "w"), default=str)
    fails = [r for r in h["checks"] if r["status"] == "FAIL"]
    if fails and "--force" not in sys.argv:
        raise SystemExit("HEALTH GATE: not publishing. Failures:\n" + "\n".join(f"  {r['area']}: {r['check']}: {r['detail'][:150]}" for r in fails))
    return h


def main():
    h = health_gate()
    page = open(os.path.join(HERE, "page", "index.html")).read()
    page = re.sub(r'<meta name="dash-[^"]+"[^>]*>\s*', "", page)        # dashboard-only markers
    summary = json.load(open(os.path.join(HERE, "data", "quilt", "summary.json")))
    as_of = summary["as_of"]

    os.makedirs(os.path.join(DOCS, "data"), exist_ok=True)
    for s in SETS:
        src = os.path.join(HERE, "data", "export", f"{s}.json")
        d = json.load(open(src))
        # The public files carry rows only; the code that made them is in this repo.
        json.dump({"rows": d["rows"]}, open(os.path.join(DOCS, "data", f"{s}.json"), "w"), separators=(",", ":"))
    open(os.path.join(DOCS, ".nojekyll"), "w").close()

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Family Office Asset Quilt</title>
<meta name="description" content="Monthly multi-asset quilt for an INR-based family office: asset classes, sectors, macro liquidity and prediction-market catalysts. Data as of {as_of}.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{TOKENS}</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>{SHIM % json.dumps(SETS)}</script>
</head>
<body>
<main id="dash-root">
{page}
<footer class="site-foot">
  <p>Data as of {as_of}. Sources: NSE Indices (niftyindices.com), Yahoo Finance, FRED (Federal Reserve Bank of St. Louis), ECB Data Portal, Bank of Japan, Deutsche Bundesbank, Japan Ministry of Finance, Bank of England, ChinaBond and Sina (via akshare), People's Bank of China, Reserve Bank of India, CFTC, NSDL, NSE, Polymarket and Kalshi.</p>
  <p>For information and discussion only. Nothing here is investment advice or a recommendation to buy or sell any security.</p>
</footer>
</main>
</body>
</html>
"""
    open(os.path.join(DOCS, "index.html"), "w").write(html)
    privacy_guard()
    print(f"docs/index.html written ({len(html):,} bytes), data as of {as_of}; health {h['summary']}; privacy guard passed")


if __name__ == "__main__":
    main()

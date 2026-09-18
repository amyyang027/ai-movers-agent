"""Builds the browsable HTML site (docs/) from every stored reports/*.json snapshot.
Pure presentation - it renders numbers that were already computed and validated
elsewhere; it does not fetch data, rank anything, or call the LLM. Safe to rerun any
time; it always rebuilds every page from scratch from what's on disk in reports/."""

import glob
import json
import os

import markdown as md

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT, "reports")
DOCS_DIR = os.path.join(ROOT, "docs")

CHART_JS = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>'


def _fmt_pct(x):
    return f"{x * 100:+.2f}%" if x is not None else "n/a"


def _return_class(x):
    if x is None:
        return ""
    return "up" if x >= 0 else "down"


def _load_all_snapshots():
    snapshots = []
    for path in sorted(glob.glob(os.path.join(REPORTS_DIR, "*.json"))):
        with open(path) as f:
            snapshots.append(json.load(f))
    return snapshots


def _page_shell(title: str, depth: int, crumbs_html: str, body_html: str, extra_head: str = ""):
    prefix = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{prefix}style.css">
{extra_head}
</head>
<body>
<div class="page">
<nav class="crumbs">{crumbs_html}</nav>
{body_html}
<footer>Daily AI Movers Agent - numbers sourced from Massive, report text generated from those numbers only.</footer>
</div>
</body>
</html>
"""


def _stat(label, value, cls=""):
    return f'<div class="stat"><div class="value {cls}">{value}</div><div class="label">{label}</div></div>'


def _theme_rows(themes):
    rows = []
    for t in themes:
        rows.append(
            f"<tr><td>{t['name']}</td>"
            f"<td class=\"num {_return_class(t['return'])}\">{_fmt_pct(t['return'])}</td>"
            f"<td class=\"num\">{_fmt_pct(t.get('trend_5d'))}</td>"
            f"<td class=\"num\">#{t['rank']}</td></tr>"
        )
    return "\n".join(rows)


def _stock_rows(stocks):
    rows = []
    for s in stocks:
        rows.append(
            f"<tr><td><a class=\"ticker\" href=\"../tickers/{s['ticker']}.html\">{s['ticker']}</a></td>"
            f"<td>{s['theme']}</td>"
            f"<td class=\"num {_return_class(s['return'])}\">{_fmt_pct(s['return'])}</td>"
            f"<td class=\"num\">{_fmt_pct(s.get('trend_5d'))}</td>"
            f"<td class=\"num\">{s['volume']:,.0f}</td>"
            f"<td class=\"num\">#{s['rank']}</td></tr>"
        )
    return "\n".join(rows)


def _volume_by_theme(stocks):
    totals = {}
    for s in stocks:
        totals[s["theme"]] = totals.get(s["theme"], 0) + s["volume"]
    # stable, deterministic order
    labels = sorted(totals)
    return labels, [totals[label] for label in labels]


def _render_day_page(snapshot: dict):
    date = snapshot["date"]
    stocks_sorted = sorted(snapshot["stocks"], key=lambda s: s["rank"])
    themes_sorted = sorted(snapshot["themes"], key=lambda t: t["rank"])
    n_stocks_shown = min(10, len(stocks_sorted))
    n_themes_shown = min(5, len(themes_sorted))
    top_stocks = stocks_sorted[:n_stocks_shown]
    bottom_stocks = list(reversed(stocks_sorted[-n_stocks_shown:]))
    top_themes = themes_sorted[:n_themes_shown]
    bottom_themes = list(reversed(themes_sorted[-n_themes_shown:]))

    vol_labels, vol_data = _volume_by_theme(snapshot["stocks"])
    movers_labels = [s["ticker"] for s in top_stocks] + [s["ticker"] for s in reversed(bottom_stocks)]
    movers_data = [round(s["return"] * 100, 2) for s in top_stocks] + [round(s["return"] * 100, 2) for s in reversed(bottom_stocks)]

    narrative_html = md.markdown(snapshot.get("narrative_markdown", ""), extensions=["tables"])

    breadth = snapshot["breadth"]
    benchmark = snapshot["benchmark"]

    body = f"""
<header class="masthead">
<h1>AI Movers - {date}</h1>
<div class="sub">Daily recap of {breadth['total']} tracked AI-related stocks across {len(snapshot['themes'])} themes</div>
</header>

<div class="card">
<h2>At a Glance</h2>
<div class="stat-row">
{_stat("Stocks Up", breadth['up'], "up")}
{_stat("Stocks Down", breadth['down'], "down")}
{_stat("Stocks Flat", breadth['flat'])}
{_stat("S&amp;P 500 (SPY)", _fmt_pct(benchmark['return']), _return_class(benchmark['return']))}
</div>
</div>

<div class="charts">
<div class="card"><h2>Volume by Theme</h2><canvas id="volChart"></canvas></div>
<div class="card"><h2>Top / Bottom Movers</h2><canvas id="moversChart"></canvas></div>
</div>

<div class="card">
<h2>Themes</h2>
<table>
<tr><th>Theme</th><th class="num">Return</th><th class="num">5d Trend</th><th class="num">Rank</th></tr>
{_theme_rows(top_themes)}
{_theme_rows(bottom_themes)}
</table>
</div>

<div class="card">
<h2>Top 10 Stocks</h2>
<table>
<tr><th>Ticker</th><th>Theme</th><th class="num">Return</th><th class="num">5d Trend</th><th class="num">Volume</th><th class="num">Rank</th></tr>
{_stock_rows(top_stocks)}
</table>
</div>

<div class="card">
<h2>Bottom 10 Stocks</h2>
<table>
<tr><th>Ticker</th><th>Theme</th><th class="num">Return</th><th class="num">5d Trend</th><th class="num">Volume</th><th class="num">Rank</th></tr>
{_stock_rows(bottom_stocks)}
</table>
</div>

<div class="card narrative">
<h2>Summary</h2>
{narrative_html}
</div>

<script>
new Chart(document.getElementById('volChart'), {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(vol_labels)},
    datasets: [{{ data: {json.dumps(vol_data)}, backgroundColor: [
      '#2f5fd6','#5b8def','#7fa3ff','#9fc0ff','#1b7f3b','#3fbf6f','#c62828','#f2685f','#b98b00','#d6b24a'
    ] }}]
  }},
  options: {{ plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 12, font: {{ size: 10 }} }} }} }} }}
}});
new Chart(document.getElementById('moversChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(movers_labels)},
    datasets: [{{
      data: {json.dumps(movers_data)},
      backgroundColor: {json.dumps(movers_data)}.map(v => v >= 0 ? '#1b7f3b' : '#c62828')
    }}]
  }},
  options: {{
    indexAxis: 'y',
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ x: {{ title: {{ display: true, text: 'Daily return (%)' }} }} }}
  }}
}});
</script>
"""
    crumbs = '<a href="../index.html">Home</a> / ' + date
    html = _page_shell(f"AI Movers - {date}", depth=1, crumbs_html=crumbs, body_html=body, extra_head=CHART_JS)
    out_path = os.path.join(DOCS_DIR, "reports", f"{date}.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)


def _render_ticker_page(ticker: str, theme: str, reason: str, rows: list):
    """rows: list of {date, close, return, volume, rank}, sorted oldest to newest."""
    latest = rows[-1] if rows else None
    dates = [r["date"] for r in rows]
    closes = [r["close"] for r in rows]
    returns = [round(r["return"] * 100, 2) for r in rows]

    table_rows = "\n".join(
        f"<tr><td>{r['date']}</td><td class=\"num\">${r['close']:.2f}</td>"
        f"<td class=\"num {_return_class(r['return'])}\">{_fmt_pct(r['return'])}</td>"
        f"<td class=\"num\">{r['volume']:,.0f}</td><td class=\"num\">#{r['rank']}</td></tr>"
        for r in reversed(rows)
    )

    stat_html = ""
    if latest:
        stat_html = f"""<div class="stat-row">
{_stat("Latest Close", f"${latest['close']:.2f}")}
{_stat("Latest Return", _fmt_pct(latest['return']), _return_class(latest['return']))}
{_stat("Latest Rank", f"#{latest['rank']} of tracked stocks")}
{_stat("Theme", theme)}
</div>"""

    history_note = (
        f"Showing all {len(rows)} stored day(s) of history for this ticker. This grows every "
        "time the agent runs, so the chart gets longer over time."
        if rows else "No stored data yet for this ticker."
    )

    body = f"""
<header class="masthead">
<h1>{ticker}</h1>
<div class="sub">{theme} - {reason}</div>
</header>

<div class="card">
<h2>At a Glance</h2>
{stat_html}
</div>

<div class="card">
<h2>Price History</h2>
<canvas id="priceChart"></canvas>
<p style="color: var(--text-muted); font-size: 0.82rem; margin-top: 10px;">{history_note}</p>
</div>

<div class="card">
<h2>Daily Log</h2>
<table>
<tr><th>Date</th><th class="num">Close</th><th class="num">Return</th><th class="num">Volume</th><th class="num">Rank</th></tr>
{table_rows}
</table>
</div>

<script>
new Chart(document.getElementById('priceChart'), {{
  type: 'line',
  data: {{
    labels: {json.dumps(dates)},
    datasets: [{{
      label: '{ticker} close ($)',
      data: {json.dumps(closes)},
      borderColor: '#2f5fd6',
      backgroundColor: 'rgba(47,95,214,0.1)',
      tension: 0.2,
      fill: true
    }}]
  }},
  options: {{ plugins: {{ legend: {{ display: false }} }} }}
}});
</script>
"""
    crumbs = '<a href="../index.html">Home</a> / ' + ticker
    html = _page_shell(f"{ticker} - AI Movers", depth=1, crumbs_html=crumbs, body_html=body, extra_head=CHART_JS)
    out_path = os.path.join(DOCS_DIR, "tickers", f"{ticker}.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)


def _render_index(snapshots: list, universe: dict):
    items = []
    for snap in reversed(snapshots):  # newest first
        stocks_sorted = sorted(snap["stocks"], key=lambda s: s["rank"])
        top = stocks_sorted[0] if stocks_sorted else None
        highlight = f"Top mover: {top['ticker']} {_fmt_pct(top['return'])}" if top else "No data"
        items.append(
            f'<li><a href="reports/{snap["date"]}.html">{snap["date"]}</a>'
            f'<div class="meta">{highlight} - {snap["breadth"]["up"]} up / {snap["breadth"]["down"]} down</div></li>'
        )

    ticker_links = "".join(
        f'<a class="ticker" href="tickers/{s["ticker"]}.html" style="margin-right:14px;">{s["ticker"]}</a>'
        for s in sorted(universe["stocks"], key=lambda s: s["ticker"])
    )

    body = f"""
<header class="masthead">
<h1>Daily AI Movers Agent</h1>
<div class="sub">Automated daily recap of {len(universe['stocks'])} AI-related stocks across {len(universe['themes'])} themes. Every number is sourced from Massive; report text is generated from those numbers only.</div>
</header>

<div class="card">
<h2>Reports</h2>
<ul class="report-list">
{"".join(items) if items else "<li>No reports yet.</li>"}
</ul>
</div>

<div class="card">
<h2>Browse by Ticker</h2>
{ticker_links}
</div>
"""
    html = _page_shell("Daily AI Movers Agent", depth=0, crumbs_html="", body_html=body)
    with open(os.path.join(DOCS_DIR, "index.html"), "w") as f:
        f.write(html)


def build_site():
    snapshots = _load_all_snapshots()
    if not snapshots:
        return

    with open(os.path.join(ROOT, "universe.yaml")) as f:
        import yaml
        universe = yaml.safe_load(f)

    for snap in snapshots:
        _render_day_page(snap)

    theme_by_ticker = {s["ticker"]: s["theme"] for s in universe["stocks"]}
    reason_by_ticker = {s["ticker"]: s["reason"] for s in universe["stocks"]}

    history_by_ticker = {}
    for snap in snapshots:
        for s in snap["stocks"]:
            history_by_ticker.setdefault(s["ticker"], []).append({
                "date": snap["date"], "close": s["close"], "return": s["return"],
                "volume": s["volume"], "rank": s["rank"],
            })

    for ticker in theme_by_ticker:
        rows = sorted(history_by_ticker.get(ticker, []), key=lambda r: r["date"])
        _render_ticker_page(ticker, theme_by_ticker[ticker], reason_by_ticker[ticker], rows)

    _render_index(snapshots, universe)
    print(f"Site built: {len(snapshots)} day(s), {len(theme_by_ticker)} ticker page(s)")


if __name__ == "__main__":
    build_site()

"""Run this once per trading day, after market close. Orchestrates the whole pipeline:
fetch -> compute -> rank -> chart -> write report -> save. No manual steps once running."""

import datetime as dt
import os

import yaml

import history
from chart import make_movers_chart
from compute_returns import get_ticker_return, get_theme_return
from rank import market_breadth, rank_all, top_bottom
from report import generate_report
from site_builder import build_site

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT, "reports")
BENCHMARK_TICKER = "SPY"  # S&P 500, used both as the "is today a trading day" check
                          # and as the benchmark-comparison figure in the report.


def load_universe():
    with open(os.path.join(ROOT, "universe.yaml")) as f:
        return yaml.safe_load(f)


def all_tickers(universe):
    tickers = {s["ticker"] for s in universe["stocks"]}
    for theme in universe["themes"]:
        if theme["type"] == "etf":
            tickers.add(theme["ticker"])
        else:
            tickers.update(theme["tickers"])
    return sorted(tickers)


def run(as_of: dt.date):
    # Weekends/holidays have no close for today - skip cleanly instead of silently
    # reporting yesterday's data as if it were today's (would break re-run consistency
    # and produce duplicate-looking reports).
    benchmark = get_ticker_return(BENCHMARK_TICKER, as_of)
    if benchmark["error"] or benchmark["date"] != as_of.isoformat():
        print(f"{as_of.isoformat()} was not a trading day (no data yet, or market closed). Skipping.")
        return

    universe = load_universe()
    tickers = all_tickers(universe)

    # Step 1: fetch + compute returns for every ticker we need (stocks + theme baskets)
    ticker_returns = {t: get_ticker_return(t, as_of) for t in tickers}

    # Step 2: theme returns (ETFs use their own return, baskets average their stocks)
    theme_returns = [get_theme_return(theme, ticker_returns) for theme in universe["themes"]]

    # Step 3: build the stock list with its theme label attached
    stock_items = []
    for s in universe["stocks"]:
        r = ticker_returns[s["ticker"]]
        item = {"ticker": s["ticker"], "theme": s["theme"], "error": r["error"]}
        if not r["error"]:
            item.update({k: r[k] for k in ("return", "trend_5d", "high", "low", "volume", "close")})
        stock_items.append(item)

    missing = sorted(t for t, r in ticker_returns.items() if r["error"])

    # Step 4: rank everything (pure code, deterministic) and compute market breadth
    ranked_themes = rank_all(theme_returns, key="return", label_key="name")
    ranked_stocks = rank_all(stock_items, key="return", label_key="ticker")
    breadth = market_breadth(stock_items, key="return")

    # Step 5: pull in yesterday's stored ranks (if any) so the report can say
    # "moved from rank X to rank Y" - this only reads a file we saved ourselves.
    previous = history.load_previous_snapshot(as_of, REPORTS_DIR)
    themes_with_prev = history.attach_prev_rank(ranked_themes, previous, "themes", "name")
    stocks_with_prev = history.attach_prev_rank(ranked_stocks, previous, "stocks", "ticker")

    top_themes, bottom_themes = top_bottom(themes_with_prev, n=5)
    top_stocks, bottom_stocks = top_bottom(stocks_with_prev, n=10)

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Step 6: chart - pure visualization of the numbers above, no new information
    chart_filename = f"{as_of.isoformat()}.png"
    make_movers_chart(top_stocks, bottom_stocks, as_of.isoformat(), os.path.join(REPORTS_DIR, chart_filename))

    # Step 7: LLM writes the words, using only the numbers above
    narrative_markdown = generate_report(
        as_of.isoformat(), top_themes, bottom_themes, top_stocks, bottom_stocks,
        missing, breadth, benchmark,
    )
    report_text = narrative_markdown + f"\n\n![Top and bottom AI stock movers]({chart_filename})\n"

    # Step 8: save the day's Markdown report, the chart, and the raw JSON snapshot
    # (the JSON is what tomorrow's run reads back for rank-change context, and what
    # the HTML site is rebuilt from - it holds every tracked theme/stock and the raw
    # narrative text, not just the top/bottom slice shown in the Markdown).
    md_path = os.path.join(REPORTS_DIR, f"{as_of.isoformat()}.md")
    with open(md_path, "w") as f:
        f.write(report_text)

    history.save_snapshot(as_of, {
        "date": as_of.isoformat(),
        "benchmark": {"ticker": BENCHMARK_TICKER, "return": benchmark["return"]},
        "breadth": breadth,
        "themes": ranked_themes,
        "stocks": ranked_stocks,
        "missing_data": missing,
        "narrative_markdown": narrative_markdown,
    }, REPORTS_DIR)

    print(f"Wrote {md_path}")
    if missing:
        print(f"Missing data for: {', '.join(missing)}")

    build_site()


if __name__ == "__main__":
    run(dt.date.today())

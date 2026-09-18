"""Run this once per trading day, after market close. Orchestrates the whole pipeline:
fetch -> compute -> rank -> write report -> save. No manual steps once it's running."""

import datetime as dt
import os

import yaml

from compute_returns import get_ticker_return, get_theme_return
from fetch_prices import get_close_near
from rank import top_bottom
from report import generate_report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET_REFERENCE_TICKER = "SPY"


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
    market_date, _ = get_close_near(MARKET_REFERENCE_TICKER, as_of, max_lookback_days=0)
    if market_date != as_of:
        print(f"{as_of.isoformat()} was not a trading day (no data yet, or market closed). Skipping.")
        return

    universe = load_universe()
    tickers = all_tickers(universe)

    # Step 1: fetch + compute returns for every ticker we need (stocks + ETF themes)
    ticker_returns = {t: get_ticker_return(t, as_of) for t in tickers}

    # Step 2: theme returns (ETFs use their own return, baskets average their stocks)
    theme_returns = [get_theme_return(theme, ticker_returns) for theme in universe["themes"]]

    # Step 3: build the stock list with its theme label attached
    stock_items = []
    for s in universe["stocks"]:
        r = ticker_returns[s["ticker"]]
        item = {"ticker": s["ticker"], "theme": s["theme"], "error": r["error"]}
        if not r["error"]:
            item["return"] = r["return"]
        stock_items.append(item)

    # Step 4: rank (pure code, deterministic)
    top_themes, bottom_themes = top_bottom(theme_returns, key="return", label_key="name", n=5)
    top_stocks, bottom_stocks = top_bottom(stock_items, key="return", label_key="ticker", n=10)

    missing = sorted(t for t, r in ticker_returns.items() if r["error"])

    # Step 5: LLM writes the words, using only the numbers above
    report_text = generate_report(
        as_of.isoformat(), top_themes, bottom_themes, top_stocks, bottom_stocks, missing
    )

    # Step 6: save one file for the day
    out_dir = os.path.join(ROOT, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{as_of.isoformat()}.md")
    with open(out_path, "w") as f:
        f.write(report_text)

    print(f"Wrote {out_path}")
    if missing:
        print(f"Missing data for: {', '.join(missing)}")


if __name__ == "__main__":
    run(dt.date.today())

"""Pure math. Same inputs -> same outputs, every time. No API calls, no AI."""

import datetime as dt

from fetch_prices import get_bar_near


def get_ticker_return(ticker: str, as_of: dt.date):
    """Returns a dict with today's close/high/low/volume, the daily return, and a
    best-effort ~5-trading-day trend, or a dict with error=True if today/yesterday
    data was missing (the 5-day trend alone never fails the ticker - it's extra
    context, not something the ranking depends on)."""
    today_date, today_bar = get_bar_near(ticker, as_of)
    if today_bar is None:
        return {"ticker": ticker, "error": True}

    prev_date, prev_bar = get_bar_near(ticker, today_date - dt.timedelta(days=1))
    if prev_bar is None or prev_bar["close"] == 0:
        return {"ticker": ticker, "error": True}

    daily_return = today_bar["close"] / prev_bar["close"] - 1

    # ~5 trading days ago = 1 calendar week back, nearest prior trading day.
    # Approximate (a holiday in that window shifts it by a day or two) but always
    # sourced fresh from Massive, never estimated.
    _, week_ago_bar = get_bar_near(ticker, today_date - dt.timedelta(days=7))
    trend_5d = (today_bar["close"] / week_ago_bar["close"] - 1) if week_ago_bar else None

    return {
        "ticker": ticker,
        "error": False,
        "date": today_date.isoformat(),
        "prev_date": prev_date.isoformat(),
        "close": today_bar["close"],
        "prev_close": prev_bar["close"],
        "high": today_bar["high"],
        "low": today_bar["low"],
        "volume": today_bar["volume"],
        "return": daily_return,
        "trend_5d": trend_5d,
    }


def get_theme_return(theme: dict, ticker_returns: dict):
    """theme is one entry from universe.yaml (etf or basket).
    ticker_returns is {ticker: get_ticker_return result}, already fetched."""
    if theme["type"] == "etf":
        r = ticker_returns[theme["ticker"]]
        if r["error"]:
            return {"name": theme["name"], "error": True}
        return {"name": theme["name"], "error": False, "return": r["return"], "trend_5d": r["trend_5d"]}

    # basket: equal-weighted average of constituent returns (skip missing ones)
    valid = [ticker_returns[t] for t in theme["tickers"] if not ticker_returns[t]["error"]]
    if not valid:
        return {"name": theme["name"], "error": True}

    avg_return = sum(r["return"] for r in valid) / len(valid)
    trends = [r["trend_5d"] for r in valid if r["trend_5d"] is not None]
    avg_trend = sum(trends) / len(trends) if trends else None
    return {"name": theme["name"], "error": False, "return": avg_return, "trend_5d": avg_trend}

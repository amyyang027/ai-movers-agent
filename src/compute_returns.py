"""Pure math. Same inputs -> same outputs, every time. No API calls, no AI."""

import datetime as dt

from fetch_prices import get_close_near


def get_ticker_return(ticker: str, as_of: dt.date):
    """Returns a dict with today's close, previous close, and the daily return,
    or a dict with error=True if data was missing."""
    today_date, today_close = get_close_near(ticker, as_of)
    if today_close is None:
        return {"ticker": ticker, "error": True}

    prev_date, prev_close = get_close_near(ticker, today_date - dt.timedelta(days=1))
    if prev_close is None or prev_close == 0:
        return {"ticker": ticker, "error": True}

    daily_return = today_close / prev_close - 1
    return {
        "ticker": ticker,
        "error": False,
        "date": today_date.isoformat(),
        "prev_date": prev_date.isoformat(),
        "close": today_close,
        "prev_close": prev_close,
        "return": daily_return,
    }


def get_theme_return(theme: dict, ticker_returns: dict):
    """theme is one entry from universe.yaml (etf or basket).
    ticker_returns is {ticker: get_ticker_return result}, already fetched."""
    if theme["type"] == "etf":
        r = ticker_returns[theme["ticker"]]
        if r["error"]:
            return {"name": theme["name"], "error": True}
        return {"name": theme["name"], "error": False, "return": r["return"]}

    # basket: equal-weighted average of constituent returns (skip missing ones)
    valid = [ticker_returns[t]["return"] for t in theme["tickers"] if not ticker_returns[t]["error"]]
    if not valid:
        return {"name": theme["name"], "error": True}
    return {"name": theme["name"], "error": False, "return": sum(valid) / len(valid)}

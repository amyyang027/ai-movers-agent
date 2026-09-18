"""Talks to the Massive API. Nothing in here decides winners/losers - it just gets prices."""

import datetime as dt
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["MASSIVE_API_KEY"]
BASE_URL = "https://api.massive.com/v1/open-close"


def get_bar_near(ticker: str, target_date: dt.date, max_lookback_days: int = 5):
    """Return (date_used, bar) for the most recent trading day on or before target_date,
    where bar has open/high/low/close/volume. Returns (None, None) if nothing is found
    within max_lookback_days (e.g. ticker delisted, bad symbol, extended holiday)."""
    for offset in range(max_lookback_days + 1):
        date = target_date - dt.timedelta(days=offset)
        url = f"{BASE_URL}/{ticker}/{date.isoformat()}"
        resp = requests.get(url, params={"apiKey": API_KEY}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK" and "close" in data:
                return date, data
        # 404/holiday/weekend -> try the previous day
    return None, None


def get_close_near(ticker: str, target_date: dt.date, max_lookback_days: int = 5):
    """Same as get_bar_near but returns just (date_used, close_price). Used where only
    the closing price matters (e.g. checking whether today is a trading day yet)."""
    date, bar = get_bar_near(ticker, target_date, max_lookback_days)
    return (date, bar["close"]) if bar else (None, None)

"""The ONLY place an LLM is used. It writes prose about numbers we already computed.
It is not allowed to invent numbers, or to recommend trades / predict the future."""

import json
import os

from openai import OpenAI

# Google's free Gemini tier, accessed through its OpenAI-compatible endpoint so we
# can use the standard `openai` client instead of a Google-specific SDK.
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-3.6-flash"  # if this 404s, check https://ai.google.dev/gemini-api/docs/models for the current free-tier flash model name

SYSTEM_PROMPT = """You write a short, factual daily markets recap for AI-related stocks and themes.

Rules you must follow exactly:
- Use ONLY the numbers given to you in the user message. Never calculate, estimate, or
  alter any number.
- Do not give trade recommendations, price targets, or forward-looking statements of any
  kind (no "expect", "likely to", "should buy/sell", "poised to", "momentum building",
  "could continue", etc.).
- "trend_5d" and "prev_rank"/"rank" are historical facts about what already happened -
  report them as past events (e.g. "moved from rank 3 to rank 1", "up 4.2% over the past
  week"), never as signals about what happens next.
- The benchmark comparison is a factual comparison only ("AI stocks averaged X% vs the
  S&P 500's Y%"), not a judgment about whether that's good or bad going forward.
- If a stock's volume looks unusually high or low, you may note that plainly, but do not
  speculate about why or what it means.
- State facts about what happened today (and, where given, the past ~5 trading days) only.
- Keep it short: one or two sentences of context per section is enough.
"""


def _fmt_pct(x):
    return f"{x * 100:+.2f}%" if x is not None else "n/a"


def _format_stock(item):
    out = dict(item)
    out["return"] = _fmt_pct(item.get("return"))
    out["trend_5d"] = _fmt_pct(item.get("trend_5d"))
    out["high"] = f"${item['high']:.2f}"
    out["low"] = f"${item['low']:.2f}"
    out["volume"] = f"{item['volume']:,.0f}"
    out.pop("error", None)
    return out


def _format_theme(item):
    out = dict(item)
    out["return"] = _fmt_pct(item.get("return"))
    out["trend_5d"] = _fmt_pct(item.get("trend_5d"))
    out.pop("error", None)
    return out


def generate_report(
    as_of: str,
    top_themes,
    bottom_themes,
    top_stocks,
    bottom_stocks,
    missing: list,
    breadth: dict,
    benchmark: dict,
):
    payload = {
        "date": as_of,
        "market_breadth": {
            "stocks_up": breadth["up"],
            "stocks_down": breadth["down"],
            "stocks_flat": breadth["flat"],
            "total_stocks_tracked": breadth["total"],
        },
        "benchmark_comparison": {
            "benchmark": "S&P 500 (SPY)",
            "benchmark_return": _fmt_pct(benchmark.get("return")),
            "note": "compare this to the AI theme/stock returns below",
        },
        "top_themes": [_format_theme(i) for i in top_themes],
        "bottom_themes": [_format_theme(i) for i in bottom_themes],
        "top_stocks": [_format_stock(i) for i in top_stocks],
        "bottom_stocks": [_format_stock(i) for i in bottom_stocks],
        "missing_data": missing,
    }

    client = OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url=GEMINI_BASE_URL)
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Write today's AI Movers report as Markdown, using this data verbatim. "
                    "Each stock/theme entry includes 'rank' (today) and 'prev_rank' (previous "
                    "stored report, or null if there isn't one yet) - mention rank movement "
                    "only when prev_rank is not null.\n\n"
                    + json.dumps(payload, indent=2)
                ),
            },
        ],
    )
    return response.choices[0].message.content

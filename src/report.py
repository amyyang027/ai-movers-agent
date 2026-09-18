"""The LLM is used ONLY to write short narrative sentences about numbers we already
computed. Tables are built in plain Python, not by the LLM - trusting a model to get
Markdown table syntax (header separator row, column counts) exactly right every single
run is fragile; a missing "|---|" row silently breaks the table on GitHub. The model
never invents a number, a trade recommendation, or a table cell."""

import json
import os

from openai import OpenAI

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-3.6-flash"  # if this 404s, check https://ai.google.dev/gemini-api/docs/models for the current free-tier flash model name

SYSTEM_PROMPT = """You write short, factual one-sentence captions for a daily AI markets
recap. You do not write tables or lists - just plain sentences.

Rules you must follow exactly:
- Use ONLY the numbers given to you in the user message. Never calculate, estimate, or
  alter any number.
- Do not give trade recommendations, price targets, or forward-looking statements of any
  kind (no "expect", "likely to", "should buy/sell", "poised to", "momentum building",
  "could continue", etc.).
- "trend_5d" and "prev_rank"/"rank" are historical facts about what already happened -
  report them as past events (e.g. "moved from rank 3 to rank 1", "up 4.2% over the past
  week"), never as signals about what happens next. Only mention rank movement when
  prev_rank is not null.
- The benchmark comparison is a factual comparison only ("AI stocks averaged X% vs the
  S&P 500's Y%"), not a judgment about whether that's good or bad going forward.
- Exactly one sentence per caption. No markdown, no bullet points, no bold.

Respond with exactly 5 lines, each starting with the exact label shown, nothing else:
OVERVIEW: <one sentence covering market breadth and the benchmark comparison>
TOP_THEMES: <one sentence about the leading theme(s)>
BOTTOM_THEMES: <one sentence about the lagging theme(s)>
TOP_STOCKS: <one sentence about the leading stock(s)>
BOTTOM_STOCKS: <one sentence about the lagging stock(s)>
"""


def _fmt_pct(x):
    return f"{x * 100:+.2f}%" if x is not None else "n/a"


def _rank_str(x):
    return str(x) if x is not None else "-"


def _md_table(headers: list, rows: list):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _themes_table(items):
    rows = [
        [t["name"], _fmt_pct(t["return"]), _fmt_pct(t.get("trend_5d")), t["rank"], _rank_str(t.get("prev_rank"))]
        for t in items
    ]
    return _md_table(["Theme", "Return", "5d Trend", "Rank", "Prev Rank"], rows)


def _stocks_table(items):
    rows = [
        [
            s["ticker"], s["theme"], _fmt_pct(s["return"]), _fmt_pct(s.get("trend_5d")),
            f"${s['high']:.2f}", f"${s['low']:.2f}", f"{s['volume']:,.0f}",
            s["rank"], _rank_str(s.get("prev_rank")),
        ]
        for s in items
    ]
    return _md_table(["Ticker", "Theme", "Return", "5d Trend", "High", "Low", "Volume", "Rank", "Prev Rank"], rows)


def _parse_captions(text: str):
    labels = ["OVERVIEW", "TOP_THEMES", "BOTTOM_THEMES", "TOP_STOCKS", "BOTTOM_STOCKS"]
    captions = {label: "" for label in labels}
    for line in text.splitlines():
        line = line.strip()
        for label in labels:
            if line.upper().startswith(label + ":"):
                captions[label] = line[len(label) + 1:].strip()
    return captions


def _get_captions(as_of, top_themes, bottom_themes, top_stocks, bottom_stocks, missing, breadth, benchmark):
    payload = {
        "date": as_of,
        "market_breadth": {
            "stocks_up": breadth["up"], "stocks_down": breadth["down"],
            "stocks_flat": breadth["flat"], "total_stocks_tracked": breadth["total"],
        },
        "benchmark_comparison": {"benchmark": "S&P 500 (SPY)", "benchmark_return": _fmt_pct(benchmark.get("return"))},
        "top_themes": [{**t, "return": _fmt_pct(t["return"]), "trend_5d": _fmt_pct(t.get("trend_5d"))} for t in top_themes],
        "bottom_themes": [{**t, "return": _fmt_pct(t["return"]), "trend_5d": _fmt_pct(t.get("trend_5d"))} for t in bottom_themes],
        "top_stocks": [{**s, "return": _fmt_pct(s["return"]), "trend_5d": _fmt_pct(s.get("trend_5d"))} for s in top_stocks],
        "bottom_stocks": [{**s, "return": _fmt_pct(s["return"]), "trend_5d": _fmt_pct(s.get("trend_5d"))} for s in bottom_stocks],
        "missing_data": missing,
    }
    client = OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url=GEMINI_BASE_URL)
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ],
    )
    return _parse_captions(response.choices[0].message.content)


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
    captions = _get_captions(as_of, top_themes, bottom_themes, top_stocks, bottom_stocks, missing, breadth, benchmark)

    sections = [
        f"# AI Market Recap - {as_of}",
        "## Market Overview",
        captions["OVERVIEW"],
        "## Top Themes",
        captions["TOP_THEMES"],
        "",
        _themes_table(top_themes),
        "## Bottom Themes",
        captions["BOTTOM_THEMES"],
        "",
        _themes_table(bottom_themes),
        "## Top Stocks",
        captions["TOP_STOCKS"],
        "",
        _stocks_table(top_stocks),
        "## Bottom Stocks",
        captions["BOTTOM_STOCKS"],
        "",
        _stocks_table(bottom_stocks),
    ]
    if missing:
        sections += ["## Missing Data", "Data was unavailable for: " + ", ".join(missing)]

    return "\n\n".join(sections)

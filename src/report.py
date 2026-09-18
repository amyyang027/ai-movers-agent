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
- Do not give trade recommendations, price targets, or forward-looking statements
  (no "expect", "likely to", "should buy/sell", etc.).
- State facts about what happened today only.
- Keep it short: one sentence of context per section is enough.
"""


def _as_percent(items: list):
    """Copy each item with its raw 0.0211 return replaced by a readable '+2.11%' string."""
    out = []
    for item in items:
        item = dict(item)
        item["return"] = f"{item['return'] * 100:+.2f}%"
        out.append(item)
    return out


def generate_report(as_of: str, top_themes, bottom_themes, top_stocks, bottom_stocks, missing: list):
    payload = {
        "date": as_of,
        "top_themes": _as_percent(top_themes),
        "bottom_themes": _as_percent(bottom_themes),
        "top_stocks": _as_percent(top_stocks),
        "bottom_stocks": _as_percent(bottom_stocks),
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
                    "Write today's AI Movers report as Markdown, using this data verbatim:\n\n"
                    + json.dumps(payload, indent=2)
                ),
            },
        ],
    )
    return response.choices[0].message.content

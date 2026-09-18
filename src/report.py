"""The ONLY place an LLM is used. It writes prose about numbers we already computed.
It is not allowed to invent numbers, or to recommend trades / predict the future."""

import json
import os

import anthropic

SYSTEM_PROMPT = """You write a short, factual daily markets recap for AI-related stocks and themes.

Rules you must follow exactly:
- Use ONLY the numbers given to you in the user message. Never calculate, estimate, or
  alter any number.
- Do not give trade recommendations, price targets, or forward-looking statements
  (no "expect", "likely to", "should buy/sell", etc.).
- State facts about what happened today only.
- Keep it short: one sentence of context per section is enough.
"""


def generate_report(as_of: str, top_themes, bottom_themes, top_stocks, bottom_stocks, missing: list):
    payload = {
        "date": as_of,
        "top_themes": top_themes,
        "bottom_themes": bottom_themes,
        "top_stocks": top_stocks,
        "bottom_stocks": bottom_stocks,
        "missing_data": missing,
    }

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                "Write today's AI Movers report as Markdown, using this data verbatim:\n\n"
                + json.dumps(payload, indent=2)
            ),
        }],
    )
    return message.content[0].text

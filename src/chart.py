"""Renders a bar chart image from already-computed numbers. Purely a visualization -
it draws exactly what's in the report, nothing more."""

import matplotlib

matplotlib.use("Agg")  # headless - no display available in CI
import matplotlib.pyplot as plt


def make_movers_chart(top_stocks: list, bottom_stocks: list, as_of: str, out_path: str):
    # bottom_stocks comes in worst-first order; flip it so the chart reads
    # best-to-worst top-to-bottom once combined with top_stocks.
    ordered = top_stocks + list(reversed(bottom_stocks))
    tickers = [i["ticker"] for i in ordered]
    returns = [i["return"] * 100 for i in ordered]
    colors = ["#2e7d32" if r >= 0 else "#c62828" for r in returns]

    fig, ax = plt.subplots(figsize=(7, 8))
    y_pos = range(len(tickers))
    ax.barh(y_pos, returns, color=colors)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(tickers)
    ax.invert_yaxis()  # top mover at the top of the chart
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Daily return (%)")
    ax.set_title(f"AI Movers - Top {len(top_stocks)} / Bottom {len(bottom_stocks)} - {as_of}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)

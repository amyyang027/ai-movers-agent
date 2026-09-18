"""Sorting and simple aggregate stats. Ties broken by ticker/name so re-running on the
same data gives the same order."""


def rank_all(items: list, key: str, label_key: str):
    """items: list of dicts with error flags already resolved out.
    Returns every valid item sorted best-to-worst by `key`, each with a "rank" field
    added (1 = best). Ties broken alphabetically by `label_key` for determinism."""
    valid = [dict(i) for i in items if not i.get("error")]
    ordered = sorted(valid, key=lambda i: (-i[key], i[label_key]))
    for idx, item in enumerate(ordered, start=1):
        item["rank"] = idx
    return ordered


def top_bottom(ranked_items: list, n: int):
    """ranked_items: output of rank_all (already sorted best-to-worst with a rank field).
    Returns (top_n, bottom_n)."""
    return ranked_items[:n], list(reversed(ranked_items[-n:]))


def market_breadth(items: list, key: str = "return"):
    """items: list of dicts with error flags already resolved out.
    Returns counts of how many valid items were up/down/flat."""
    valid = [i for i in items if not i.get("error")]
    up = sum(1 for i in valid if i[key] > 0)
    down = sum(1 for i in valid if i[key] < 0)
    flat = len(valid) - up - down
    return {"up": up, "down": down, "flat": flat, "total": len(valid)}

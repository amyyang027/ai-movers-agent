"""Sorting. Ties broken by ticker/name so re-running on the same data gives the same order."""


def top_bottom(items: list, key: str, label_key: str, n: int):
    """items: list of dicts with error flags already resolved out.
    Returns (top_n, bottom_n), each sorted by `key` descending/ascending,
    with ties broken alphabetically by `label_key` for determinism."""
    valid = [i for i in items if not i.get("error")]
    ordered = sorted(valid, key=lambda i: (-i[key], i[label_key]))
    top = ordered[:n]
    bottom = sorted(valid, key=lambda i: (i[key], i[label_key]))[:n]
    return top, bottom

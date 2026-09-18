"""Reads/writes the raw daily JSON snapshot (the full 50-stock, 10-theme ranked data,
not just the top/bottom slices shown in the Markdown report). This is what lets a later
day look up "where did this rank yesterday" without recomputing anything."""

import datetime as dt
import json
import os


def save_snapshot(as_of: dt.date, data: dict, reports_dir: str):
    path = os.path.join(reports_dir, f"{as_of.isoformat()}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_previous_snapshot(as_of: dt.date, reports_dir: str, max_lookback_days: int = 10):
    """Walks backward from the day before as_of looking for the most recent saved
    snapshot (skips weekends/holidays/any day the agent didn't run). Returns None if
    none is found - normal for the very first run."""
    for offset in range(1, max_lookback_days + 1):
        date = as_of - dt.timedelta(days=offset)
        path = os.path.join(reports_dir, f"{date.isoformat()}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return None


def attach_prev_rank(current_items: list, previous_snapshot: dict, section: str, label_key: str):
    """current_items: a list of dicts each with a "rank". Adds "prev_rank" (or None)
    to each by matching on label_key against the previous day's snapshot, if any."""
    prev_by_label = {}
    if previous_snapshot:
        for item in previous_snapshot.get(section, []):
            prev_by_label[item[label_key]] = item["rank"]

    out = []
    for item in current_items:
        item = dict(item)
        item["prev_rank"] = prev_by_label.get(item[label_key])
        out.append(item)
    return out

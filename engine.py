"""Conservative, dataset-only classification for the recycling helper."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
LOOKUP_ADVICE = "This item is not in the current dataset, so the helper will not guess how to sort it. Please check the waste-sorting guidance published by your local government or waste service."
DANGER_ADVICE = "This may be a hazardous item, so the helper cannot recommend how to dispose of it. Do not mix it with household waste or dismantle it. Check your local hazardous-waste collection service and official disposal guidance."
CLARIFY_ADVICE = "This name is not specific enough to identify the item, and the helper will not guess. Please enter the exact item name or product type, or check your local official waste-sorting guidance."


@dataclass(frozen=True)
class Result:
    status: str
    item: str
    category: str | None
    advice: str


def normalize(value: str) -> str:
    """Normalize spacing and common punctuation, but do not do fuzzy matching."""
    value = value.strip().casefold()
    return re.sub(r"[\s\u3000，。！？、,.!?;；:：()（）\[\]【】'\"“”‘’_-]+", "", value)


def _read_csv(filename: str) -> list[dict[str, str]]:
    with (DATA_DIR / filename).open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _aliases(value: str) -> list[str]:
    return [normalize(alias) for alias in value.split("|") if normalize(alias)]


def classify(query: str) -> Result:
    """Return advice only for an exact alias in the approved rules dataset."""
    query = query.strip()
    key = normalize(query)
    if not key:
        return Result("clarify", query, None, "Please enter a specific item name.")

    for row in _read_csv("data_refuse.csv"):
        if any(alias in key for alias in _aliases(row.get("keywords", ""))):
            return Result("refuse", query, None, row.get("advice", "") or DANGER_ADVICE)

    for row in _read_csv("data_clarify.csv"):
        if key in _aliases(row.get("keywords", "")):
            return Result("clarify", query, None, row.get("advice", "") or CLARIFY_ADVICE)

    for row in _read_csv("data_rules.csv"):
        aliases = _aliases(row.get("aliases", ""))
        if key in aliases:
            return Result("classified", row.get("item", query), row.get("category", ""), row.get("advice", ""))

    return Result("unknown", query, None, LOOKUP_ADVICE)

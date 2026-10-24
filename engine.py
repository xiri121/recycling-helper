"""Conservative, dataset-only classification for the recycling helper."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache


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


def _variants(key: str) -> tuple[str, ...]:
    """Plural fallbacks only (batteries -> battery, boxes -> box).

    A fixed suffix strip, not fuzzy matching: no edit distance, no guessing.
    """
    variants = [key]
    if key.endswith("ies") and len(key) > 4:
        variants.append(key[:-3] + "y")
    if key.endswith("es") and len(key) > 3:
        variants.append(key[:-2])
    if key.endswith("s") and len(key) > 3:
        variants.append(key[:-1])
    return tuple(dict.fromkeys(variants))


@lru_cache(maxsize=None)
def _read_csv(filename: str) -> tuple[dict[str, str], ...]:
    with (DATA_DIR / filename).open("r", encoding="utf-8-sig", newline="") as file:
        return tuple(csv.DictReader(file))



def _aliases(value: str) -> list[str]:
    return [normalize(alias) for alias in value.split("|") if normalize(alias)]


def classify(query: str) -> Result:
    """Return advice only for an exact alias in the approved rules dataset."""
    query = query.strip()
    key = normalize(query)
    if not key:
        return Result("clarify", query, None, "Please enter a specific item name.")

    variants = _variants(key)

    for row in _read_csv("data_refuse.csv"):
        aliases = _aliases(row.get("keywords", ""))
        if any(alias in variant for alias in aliases for variant in variants):
            return Result("refuse", query, None, row.get("advice", "") or DANGER_ADVICE)

    for row in _read_csv("data_clarify.csv"):
        aliases = _aliases(row.get("keywords", ""))
        if any(variant in aliases for variant in variants):
            return Result("clarify", query, None, row.get("advice", "") or CLARIFY_ADVICE)

    for row in _read_csv("data_rules.csv"):
        aliases = _aliases(row.get("aliases", ""))
        if any(variant in aliases for variant in variants):
            return Result("classified", row.get("item", query), row.get("category", ""), row.get("advice", ""))

    return Result("unknown", query, None, LOOKUP_ADVICE)


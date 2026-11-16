"""Conservative, dataset-only classification for the recycling helper.

Pipeline (per revised proposal):
    input -> article stripping -> normalization -> plural variants
          -> refuse check (hazardous, highest priority)
          -> clarify check -> rules lookup (exact)
          -> spelling/fuzzy correction against the dataset whitelist only
          -> re-run refuse -> clarify -> rules on the corrected key
          -> unknown (no guess)

Safety rules:
- The refuse list is always checked BEFORE any correction is applied, so a
  raw input containing a hazardous term is refused without ever being
  "fixed" into something else.
- Spelling correction may only map to aliases that already exist in the
  approved datasets (data_refuse / data_clarify / data_rules). The engine
  never invents a category that is not in the dataset.
"""

from __future__ import annotations

import csv
import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache


DATA_DIR = Path(__file__).resolve().parent
LOOKUP_ADVICE = "This item is not in the current dataset, so the helper will not guess how to sort it. Please check the waste-sorting guidance published by your local government or waste service."
DANGER_ADVICE = "This may be a hazardous item, so the helper cannot recommend how to dispose of it. Do not mix it with household waste or dismantle it. Check your local hazardous-waste collection service and official disposal guidance."
CLARIFY_ADVICE = "This name is not specific enough to identify the item, and the helper will not guess. Please enter the exact item name or product type, or check your local official waste-sorting guidance."

# Leading English articles are stripped before matching ("a glass bottle" -> "glass bottle").
_ARTICLES = {"a", "an", "the"}
# Similarity cutoff for whitelist spelling correction. 0.85 keeps the engine
# conservative: only very close candidates are accepted, never wild guesses.
_SIMILARITY_CUTOFF = 0.85


@dataclass(frozen=True)
class Result:
    status: str
    item: str
    category: str | None
    advice: str
    matched_via: str | None = None  # "corrected from <key>" when fuzzy/spell correction was used


def normalize(value: str) -> str:
    """Normalize spacing and common punctuation, but do not do fuzzy matching."""
    value = value.strip().casefold()
    return re.sub(r"[\s\u3000，。！？、,.!?;；:：()（）\[\]【】'\"“”‘’_-]+", "", value)


def _strip_articles(query: str) -> str:
    """Remove one leading English article word ("a glass bottle" -> "glass bottle").

    Word-boundary based: "android" or "an" alone are never affected.
    """
    tokens = query.strip().casefold().split()
    if len(tokens) > 1 and tokens[0] in _ARTICLES:
        return " ".join(tokens[1:])
    return query


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


@lru_cache(maxsize=None)
def _vocabulary() -> tuple[str, ...]:
    """Every approved alias across all three datasets.

    Spelling correction may ONLY map to entries in this whitelist; the engine
    never corrects an input towards a word that is not already in the dataset.
    """
    vocab: set[str] = set()
    for filename, column in (
        ("data_refuse.csv", "keywords"),
        ("data_clarify.csv", "keywords"),
        ("data_rules.csv", "aliases"),
    ):
        for row in _read_csv(filename):
            vocab.update(_aliases(row.get(column, "")))
    return tuple(vocab)


def _correct(key: str) -> str | None:
    """Return the closest whitelisted alias, or None when nothing is close enough."""
    matches = difflib.get_close_matches(key, list(_vocabulary()), n=1, cutoff=_SIMILARITY_CUTOFF)
    return matches[0] if matches else None


def _match(key: str, query: str) -> Result | None:
    """Refuse -> clarify -> rules lookup on one (already normalized) key.

    The refuse check is substring-based on purpose: a hazardous keyword inside
    a longer phrase ("used batteries") must still trigger refusal. NOTE: every
    keyword added to data_refuse.csv must be long enough to avoid accidental
    substring collisions (e.g. a "can" keyword would also match "candle").
    """
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

    return None


def classify(query: str) -> Result:
    """Classify an item name conservatively; never guess outside the dataset."""
    original = query.strip()
    key = normalize(_strip_articles(original))
    if not key:
        return Result("clarify", query, None, "Please enter a specific item name.")

    # 1) Exact path on the raw key (articles already stripped).
    result = _match(key, original)
    if result is not None:
        return result

    # 2) Whitelist spelling/fuzzy correction. The corrected key goes through
    #    the same refuse-first pipeline, so hazardous terms cannot be
    #    "corrected away" ("batery" still refuses as battery).
    corrected = _correct(key)
    if corrected and corrected != key:
        result = _match(corrected, original)
        if result is not None:
            return Result(
                result.status,
                result.item,
                result.category,
                result.advice,
                matched_via=f"corrected from \"{original}\"",
            )

    return Result("unknown", original, None, LOOKUP_ADVICE)


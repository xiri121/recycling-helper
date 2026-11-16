"""Dataset-grounded English item and sentence lookup for Shanghai."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
LOOKUP_ADVICE = (
    "This item is not in the current dataset. Please consult Shanghai's official "
    "sorting guide or your local waste service; the helper will not guess."
)
DANGER_ADVICE = (
    "This input may refer to a hazardous item. The helper does not provide a "
    "sorting category or disposal instructions for it. Please consult the official "
    "guide or your local hazardous-waste service."
)
CATEGORY_LABELS = {
    "recyclable": "Recyclables",
    "food waste": "Wet waste (food waste)",
    "general waste": "Dry waste (residual waste)",
}


@dataclass(frozen=True)
class Result:
    status: str
    item: str
    category: str | None
    advice: str
    candidates: tuple[str, ...] = ()
    matched_alias: str = ""
    match_type: str = ""
    source_url: str = ""
    # Preserve the incoming revision's public provenance field. Suggestions
    # describe a possible match; they do not silently correct and classify it.
    matched_via: str | None = None


def normalize(value: str) -> str:
    """Preserve word boundaries: 'glass' must not match 'fiberglass'."""
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


def _read_csv(filename: str) -> tuple[dict[str, str], ...]:
    path = DATA_DIR / filename
    stamp = path.stat()
    return _cached_csv(str(path), stamp.st_mtime_ns, stamp.st_size)


@lru_cache(maxsize=24)
def _cached_csv(path: str, modified: int, size: int) -> tuple[dict[str, str], ...]:
    # Include the file fingerprint so editing a CSV invalidates its cached copy.
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"aliases", "item", "category", "advice", "source_id"} if Path(path).name == "data_rules.csv" else {"keywords", "advice", "source_id"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing required columns in {Path(path).name}")
        rows = tuple(reader)
    for row in rows:
        if None in row or any(not value or not value.strip() for value in row.values()):
            raise ValueError(f"Malformed or empty field in {Path(path).name}")
        if "category" in row and row["category"] not in CATEGORY_LABELS:
            raise ValueError(f"Unknown category in {Path(path).name}")
    return rows


def get_sources() -> dict:
    with (DATA_DIR / "data_sources.json").open(encoding="utf-8") as file:
        return json.load(file)


def _source_url(row: dict[str, str]) -> str:
    return get_sources()["sources"][row["source_id"]]["url"]


def _aliases(row: dict[str, str], field: str) -> tuple[str, ...]:
    values = row[field].split("|")
    if field == "aliases":
        values.append(row["item"])
    return tuple(dict.fromkeys(normalize(value) for value in values if normalize(value)))


def _plural(alias: str) -> str:
    """Generate regular noun plurals from known aliases, never strip input."""
    if alias.endswith(("s", "sh", "ch", "x", "z")):
        return alias + "es"
    if len(alias) > 1 and alias.endswith("y") and alias[-2] not in "aeiou":
        return alias[:-1] + "ies"
    return alias + "s"


def _forms(alias: str) -> tuple[str, ...]:
    if alias.endswith("s") or alias.split()[-1] in {"paper", "fabric", "rice", "meat", "bread", "flour", "litter", "dust"}:
        return (alias,)
    return alias, _plural(alias)


def _mentions(text: str, rows: tuple[dict[str, str], ...], field: str) -> list[tuple[int, int, int, str]]:
    mentions = []
    for index, row in enumerate(rows):
        for alias in _aliases(row, field):
            for form in _forms(alias):
                if form in {"waste", "trash", "garbage", "junk", "stuff"} and text != form:
                    continue
                for match in re.finditer(r"(?<!\w)" + re.escape(form) + r"(?!\w)", text):
                    mentions.append((match.start(), match.end(), index, form))
    return mentions


def _longest_mentions(mentions: list[tuple[int, int, int, str]]) -> list[tuple[int, int, int, str]]:
    """A specific phrase wins over a broad phrase contained inside it."""
    return [m for m in mentions if not any(
        other[0] <= m[0] and m[1] <= other[1] and other[1] - other[0] > m[1] - m[0]
        for other in mentions
    )]


# Only request words can remain after identifying a single item. Unknown nouns
# and conditions require clarification rather than disappearing from the input.
REQUEST_WORDS = set(
    "i me my we our you your a an the this that these those it its is are was were "
    "have has had got some one two three several of for from to in into on at with "
    "please how what which where do does did should can could may would will be "
    "recycle recycling sort sorting dispose disposal discard throw away put bin "
    "go goes belong belongs need want help tell old used empty clean dry broken "
    "new leftover unwanted rubbish trash garbage waste there s am m ve "
    "up out about correctly properly safely thank thanks".split()
)
UNSAFE_CONTEXT = re.compile(
    r"\b(not|no|without|never|except|instead|rather|or|if|unless|fake|artificial|"
    r"shaped|contaminated|infectious|medical|blood|chemical|toxic|flammable|"
    r"explosive|radioactive|asbestos|leaking|swollen)\b"
)


def _candidates(key: str, rows: tuple[dict[str, str], ...]) -> tuple[str, ...]:
    """Suggest names for keywords/typos; suggestions never carry a category."""
    if UNSAFE_CONTEXT.search(key):
        return ()
    key = " ".join(word for word in key.split() if word not in REQUEST_WORDS)
    if not key:
        return ()
    ranked = []
    for row in rows:
        scores = []
        for alias in _aliases(row, "aliases"):
            if set(key.split()).issubset(alias.split()):
                scores.append(1.0)
            elif len(key) >= 5 and len(key.split()) == len(alias.split()):
                similarity = SequenceMatcher(None, key, alias).ratio()
                if similarity >= 0.82:
                    scores.append(similarity)
        if scores:
            ranked.append((max(scores), row["item"]))
    return tuple(name for _, name in sorted(ranked, key=lambda entry: (-entry[0], entry[1]))[:6])


def classify(query: str) -> Result:
    query = query.strip()
    key = normalize(query)
    if not key:
        return Result("clarify", query, None, "Please enter an item name or a short English sentence.")
    if len(query) > 1000:
        return Result("clarify", query, None, "Please shorten the description to one item (up to 1,000 characters).")

    hazards = _read_csv("data_refuse.csv")
    danger = _mentions(key, hazards, "keywords")
    if danger:
        row = hazards[danger[0][2]]
        return Result("refuse", query, None, row["advice"],
                      matched_alias=danger[0][3], match_type="hazard", source_url=_source_url(row))

    # Hazard typos must not become ordinary suggestions.
    hazard_words = {form for row in hazards for alias in _aliases(row, "keywords")
                    for form in _forms(alias) if " " not in form and len(form) >= 5}
    if any(SequenceMatcher(None, token, word).ratio() >= 0.84
           for token in key.split() if len(token) >= 5 for word in hazard_words):
        return Result("refuse", query, None, DANGER_ADVICE, match_type="possible hazard",
                      source_url=_source_url(hazards[0]))

    rules = _read_csv("data_rules.csv")
    clarifications = _read_csv("data_clarify.csv")
    combined = rules + clarifications
    mentions = _longest_mentions(
        _mentions(key, rules, "aliases") + [
            (start, end, index + len(rules), alias)
            for start, end, index, alias in _mentions(key, clarifications, "keywords")
        ]
    )
    ambiguous = [m for m in mentions if m[2] >= len(rules)]
    if ambiguous:
        row = combined[ambiguous[0][2]]
        candidates = _candidates(key, rules)
        return Result("clarify", query, None, row["advice"],
                      candidates=candidates, match_type="ambiguous", source_url=_source_url(row),
                      matched_via=f'candidate suggestions for "{query}"' if candidates else None)

    indices = {m[2] for m in mentions}
    if len(indices) > 1:
        return Result("clarify", query, None,
                      "I found more than one listed item. Please look up each item separately.",
                      match_type="multiple items")
    if mentions:
        row = rules[mentions[0][2]]
        residue = list(key)
        for start, end, _, _ in mentions:
            residue[start:end] = " " * (end - start)
        remainder = "".join(residue).split()
        if UNSAFE_CONTEXT.search(key) or any(word not in REQUEST_WORDS for word in remainder):
            return Result("clarify", query, None,
                          "I recognized a listed item, but the rest of the description may change the answer "
                          "or include an unlisted item. Please provide the exact item and condition, "
                          "or consult the official guide.", match_type="context", source_url=_source_url(row))
        return Result("classified", row["item"], row["category"], row["advice"],
                      matched_alias=mentions[0][3],
                      match_type="exact" if not remainder else "sentence", source_url=_source_url(row))

    candidates = _candidates(key, rules)
    if candidates:
        return Result("clarify", query, None,
                      "Possible dataset matches are shown below. Confirm the exact item before receiving advice. "
                      "If none matches, consult the official guide.", candidates=candidates, match_type="suggestion",
                      matched_via=f'candidate suggestions for "{query}"')
    return Result("unknown", query, None, LOOKUP_ADVICE)

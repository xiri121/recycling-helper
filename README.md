# Recycling Helper

A local-dataset waste-sorting app for **Shanghai, China**, with an English interface and English input. It supports item names, regular plurals, keywords, spelling suggestions, and simple single-item sentences.

## Run

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Official basis

Dataset version 2.0 was reviewed on **2026-11-16** against the Shanghai Landscaping and City Appearance Administrative Bureau's [Shanghai Household Waste Sorting Guide (2024 edition)](https://lhsr.sh.gov.cn/srgl/20240806/40b9feaa-53db-472f-8a6b-2c3cf0465def.html). The guide was published on 2024-08-02 and took effect on 2024-08-01. See sections 2.1, 2.3, 2.4 and 5.

The app contains **104 ordinary-item entries**, with item-level source references. Names, aliases, and short advice are app translations or summaries; this is a curated subset, not an official full dataset or an automatically updated feed.

The Shanghai categories are displayed as Recyclables, Wet waste (food waste), and Dry waste (residual waste). Potentially hazardous items receive no category or disposal instructions; users are directed to the official guide or local service. The precautionary screening list includes all batteries and selected risk terms even when the official guide distinguishes particular types. A refusal is not a claim that every flagged item is officially hazardous waste.

Disposable paper cups, plastic cups, and takeaway containers depend on district-specific recovery arrangements (section 2.1). The app asks users to check local collection notices instead of assigning a universal category. Battery-containing electronics and masks with uncertain contamination are also not automatically classified.

## Matching behavior

1. Normalize case, Unicode presentation, punctuation and hyphens while preserving word boundaries.
2. Screen hazardous words and regular plurals anywhere in the input. Possible single-word hazard misspellings also cause a precautionary refusal.
3. Prefer a specific listed phrase over a contained generic term: `glass cup` overrides `cup`.
4. Classify a single listed object in an exact lookup or a simple sentence only when the remaining words describe a lookup request.
5. Ask for clarification on different objects, unknown extra words, negation, unusual conditions, or district-dependent items.
6. Offer up to six dataset candidates for a keyword or close spelling. The user must confirm a candidate before the app gives advice.
7. Return an unlisted response when there is no supported match. Unknown items never receive a guessed category.

| Input | Expected behavior |
| --- | --- |
| `How do I recycle an empty glass bottle?` | Recognize Glass bottle and show its guidance and source |
| `bottle` | Show specific dataset candidates; no category yet |
| `newspapr` | Suggest Newspaper for explicit confirmation |
| `I have a battery and a newspaper` | Refuse; hazardous screening takes priority |
| `glass bottle and an alien widget` | Request clarification; do not ignore the unknown object |
| `plastic cup` | Ask the user to check the district's recovery scheme |
| `alien widget` | Unlisted; consult official guidance |

Sentence recognition uses rules and known aliases, not general language understanding. It does not resolve arbitrary grammar, product identities, contamination, hypothetical statements, or every typo. Unfamiliar wording can require a shorter item name. Hazard screening is conservative and can over-refuse; absence of a warning does not establish that an item is safe.

## Maintaining the data

- `data_rules.csv`: `item,aliases,category,advice,source_id`. Categories are `recyclable`, `food waste`, or `general waste`.
- `data_refuse.csv`: `keywords,advice,source_id`. Refusal always takes priority.
- `data_clarify.csv`: `keywords,advice,source_id`. Broad or condition-dependent item names.
- `data_sources.json`: region, dataset version, review date, and official source URLs.

Separate aliases with `|`. Quote CSV fields containing commas or quotes. Add only verified items, use precise aliases, and keep a source reference for each row. Avoid aliases that could describe multiple materials or products. Test changes before publishing.

CSV files are cached by modification timestamp and size, so an edit is read on the next lookup without restarting. Source metadata is read on demand. Malformed CSV data causes the UI to report unavailable data rather than produce a classification.

## Tests

```bash
python test.py
```

The suite covers sentence recognition, keyword and spelling confirmation, every approved alias, source references, hazardous and unknown inputs, CSV reloads, malformed rows, and the Streamlit interface's query/confirm/refuse flow. Success prints `OK` and exits with code 0. Logs from the latest recorded run are in `test_run.log`; a dated summary is in `TEST_RESULTS.md`.

## Remaining limits

This app implements selected Shanghai entries and English phrasing only. It does not contain the full catalogue or every district's collection schemes. Consult the linked official guide and current district or building notices whenever the item, condition, or collection route is uncertain.

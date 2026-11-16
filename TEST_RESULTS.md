# Test results

- Date: 2026-11-16 (Asia/Shanghai)
- Dataset: version 2.0, Shanghai
- Command: `python -B test.py` (same test runner as `python test.py`; disables bytecode files)
- Result: **10 test groups passed; exit code 0**
- Environment: Python 3.13.15, Streamlit 1.66.1, Windows
- Evidence: [test_run.log](test_run.log)
- WSL check: `python3 -B -m unittest -v test.ClassifierTests`, Python 3.12.3 on Ubuntu; **9 core test groups passed**. Evidence: [test_wsl.log](test_wsl.log).

## Coverage

| Check | Result |
| --- | --- |
| 56 fixed query cases, including sentences, plurals, hazardous items, unknown items, negation, contamination and mixed objects | Passed |
| All 35 incoming evaluation inputs, with expectations aligned to the expanded dataset | Passed |
| Leading articles, suggestion provenance, and a misspelled hazardous item | Passed |
| 249 ordinary-item names and aliases across 104 sourced entries; no conflicting aliases | Passed |
| 62 hazard keywords and 57 clarification keywords; no category returned | Passed |
| Keywords and spelling suggestions require explicit confirmation | Passed |
| Similar substrings and unknown attached objects do not receive a category | Passed |
| CSV edits reload without restarting | Passed |
| Malformed CSV rows are rejected | Passed |
| Streamlit query, spelling suggestion, candidate click and hazardous refusal flow | Passed |

The interface check uses Streamlit's AppTest, not a visual browser inspection. Its bare-mode ScriptRunContext warning is recorded in the log and did not fail the test.

An initial sandbox run could not create temporary CSV fixtures and was interrupted. The recorded successful run used the same test suite outside that sandbox restriction.

## Merge reconciliation

The incoming changes added article handling, whitelist spelling correction, and an expanded evaluation set. The merged engine accepts articles, retains whitelist-only suggestions and hazardous-first screening, and exposes the incoming `matched_via` provenance field. Ordinary spelling matches require confirmation before advice is shown.

All 35 incoming evaluation inputs were retained. Four old expectations were updated: plastic toys and umbrellas now have sourced entries, leading articles are supported, and disposable masks require clarification instead of automatic classification.

## Official source

[Shanghai Household Waste Sorting Guide (2024 edition)](https://lhsr.sh.gov.cn/srgl/20240806/40b9feaa-53db-472f-8a6b-2c3cf0465def.html), sections 2.1, 2.3, 2.4 and 5. English aliases and summaries were curated for this app.

## Known limitation

The classifier supports selected Shanghai items and simple English sentences. It cannot understand arbitrary descriptions or establish whether an item is safe. Unfamiliar context requires clarification, and district-specific collection arrangements must be checked locally.

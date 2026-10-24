"""Core-path tests for the recycling helper.
These tests cover the four behaviours promised in README.md:
1. Normal classification (glass bottle, newspaper).
2. Hazardous-item refusal (battery, fluorescent tube).
3. Clarification for ambiguous names (coffee cup, plastic).
4. No-guess fallback for unlisted input (plastic toy, empty input).
Run from the project directory:  python test.py
Expected result: 14/14 tests passed.
"""
from engine import classify

# (query, expected status, expected category or None, short description)
CASES = [
    ("glass bottle", "classified", "recyclable", "normal classification: recyclable glass"),
    ("newspaper", "classified", "recyclable", "normal classification: alias resolves to the paper entry"),
    ("battery", "refuse", None, "hazardous refusal: battery"),
    ("fluorescent tube", "refuse", None, "hazardous refusal: item containing mercury"),
    ("coffee cup", "clarify", None, "ambiguous name asks for clarification"),
    ("plastic", "clarify", None, "broad material name asks for clarification"),
    ("plastic toy", "unknown", None, "unlisted item is never guessed"),
    ("", "clarify", None, "empty input is handled safely"),
    ("batteries", "refuse", None, "hazardous refusal: plural form of battery"),
    ("used batteries", "refuse", None, "hazardous refusal: battery inside a longer phrase"),
    ("painting", "clarify", None, "paint-related word is clarified, not refused"),
    ("gas", "clarify", None, "bare gas term asks for clarification"),
    ("coffee cups", "clarify", None, "plural cup name asks for clarification"),
    ("papers", "clarify", None, "plural paper name asks for clarification"),
]


def main() -> int:
    passed = 0
    total = len(CASES)
    print("Running core-path tests...\n")
    for query, expected_status, expected_category, description in CASES:
        result = classify(query)
        ok = result.status == expected_status
        if expected_category is not None:
            ok = ok and result.category == expected_category
        label = query if query else "(empty input)"
        if ok:
            passed += 1
            print(f"  PASS  {label:<20} -> {result.status:<10} {description}")
        else:
            print(
                f"  FAIL  {label:<20} -> got {result.status}/{result.category}, "
                f"expected {expected_status}/{expected_category}"
            )
    print(f"\n{passed}/{total} tests passed.")
    if passed == total:
        print(
            "All core paths verified: normal classification, hazardous refusal, "
            "clarification, and the no-guess fallback."
        )
    else:
        print("Some tests failed. Check the dataset files before continuing.")
    return 0 if passed == total else 1


if __name__ == "__&#8203;main__":
    raise SystemExit(main())

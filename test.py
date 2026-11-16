"""Core-path and extended evaluation tests for the recycling helper.

These tests cover the core behaviours promised in README.md and expanded
for final project evaluation (35 cases total):
1. Normal classification (paper, plastic, glass, metal, textiles, food, general waste).
2. Hazardous-item refusal (battery, medicine, pesticide, etc.).
3. Clarification for ambiguous names (cups, containers, broad terms).
4. No-guess fallback for unlisted input (safely returning unknown).
5. Edge cases & boundary limits (punctuation, articles, plurals, non-English).

Run from the project directory:  python test.py
Expected result: 35/35 tests passed.
"""
from engine import classify

# (query, expected status, expected category or None, short description)
CASES = [
    # =====================================================================
    # Group 1: Normal Classification (10 cases) - Tests exact and alias matching
    # =====================================================================
    ("glass bottle", "classified", "recyclable", "normal classification: recyclable glass"),
    ("newspaper", "classified", "recyclable", "normal classification: alias resolves to paper"),
    ("wine bottle", "classified", "recyclable", "normal classification: glass alias"),
    ("aluminum can", "classified", "recyclable", "normal classification: metal can"),
    ("old clothes", "classified", "recyclable", "normal classification: textiles"),
    ("fruit peel", "classified", "food waste", "normal classification: food waste"),
    ("used tissues", "classified", "general waste", "normal classification: general waste"),
    ("cardboard box", "classified", "recyclable", "normal classification: cardboard"),
    ("ceramic bowl", "classified", "general waste", "normal classification: ceramic shards"),
    ("disposable face mask", "classified", "general waste", "normal classification: face mask"),

    # =====================================================================
    # Group 2: Hazardous Refusal (7 cases) - Tests safety boundaries
    # =====================================================================
    ("battery", "refuse", None, "hazardous refusal: battery"),
    ("fluorescent tube", "refuse", None, "hazardous refusal: item containing mercury"),
    ("expired medicine", "refuse", None, "hazardous refusal: medicine"),
    ("pesticide", "refuse", None, "hazardous refusal: chemical"),
    ("aerosol can", "refuse", None, "hazardous refusal: pressurized canister"),
    ("batteries", "refuse", None, "hazardous refusal: plural form of battery"),
    ("used batteries", "refuse", None, "hazardous refusal: battery inside a longer phrase"),

    # =====================================================================
    # Group 3: Ambiguous Clarification (8 cases) - Tests refusal to guess
    # =====================================================================
    ("coffee cup", "clarify", None, "ambiguous name asks for clarification"),
    ("takeout container", "clarify", None, "ambiguous name asks for clarification"),
    ("plastic", "clarify", None, "broad material name asks for clarification"),
    ("waste", "clarify", None, "broad term asks for clarification"),
    ("packaging", "clarify", None, "broad term asks for clarification"),
    ("unidentified plastic", "clarify", None, "unidentified item asks for clarification"),
    ("painting", "clarify", None, "paint-related word is clarified, not refused"),
    ("coffee cups", "clarify", None, "plural cup name asks for clarification"),

    # =====================================================================
    # Group 4: Unknown/Unlisted Input (5 cases) - Tests no-hallucination
    # =====================================================================
    ("plastic toy", "unknown", None, "unlisted item is never guessed"),
    ("", "clarify", None, "empty input is handled safely (returns clarify prompt)"),
    ("alien spaceship", "unknown", None, "obviously unlisted item is safely rejected"),
    ("broken umbrella", "unknown", None, "unlisted household item is safely rejected"),
    ("random stuff here", "unknown", None, "nonsense input is safely rejected"),

    # =====================================================================
    # Group 5: Edge Cases & Boundary Limits (5 cases) - For Report Analysis
    # =====================================================================
    ("  glass   bottle!!!  ", "classified", "recyclable", "punctuation and extra spaces are normalized"),
    ("BATTERY", "refuse", None, "uppercase input is normalized and refused safely"),
    ("a glass bottle", "unknown", None, "BOUNDARY LIMIT: articles (a/an) are currently not stripped"),
    ("玻璃瓶", "unknown", None, "BOUNDARY LIMIT: non-English input is currently unsupported"),
    ("papers", "clarify", None, "plural paper name asks for clarification"),
]


def main() -> int:
    passed = 0
    total = len(CASES)
    print("="*70)
    print(f"RUNNING EXTENDED EVALUATION TESTS ({total} CASES)...\n")
    
    for query, expected_status, expected_category, description in CASES:
        result = classify(query)
        ok = result.status == expected_status
        if expected_category is not None:
            ok = ok and result.category == expected_category
        
        # Format the label for printing
        label = query if query else "(empty input)"
        if len(label) > 20:
            label = label[:17] + "..."
            
        if ok:
            passed += 1
            print(f"  ✅ PASS  {label:<22} -> {result.status:<10} | {description}")
        else:
            print(
                f"  ❌ FAIL  {label:<22} -> got {result.status}/{result.category}, "
                f"expected {expected_status}/{expected_category}"
            )
            
    print("\n" + "="*70)
    print(f"TEST SUMMARY: {passed}/{total} tests passed.")
    if passed == total:
        print(
            "All core paths and safety boundaries verified: normal classification, "
            "hazardous refusal, clarification, and no-guess fallback."
        )
    else:
        print("Some tests failed. Check the dataset files or normalization logic.")
    print("="*70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

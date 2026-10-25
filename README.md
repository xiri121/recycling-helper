# recycling-helper
A conservative, dataset-based waste-sorting helper. The app only returns a category when it finds an exact item name or alias in `data_rules.csv`; it does not infer categories with fuzzy matching. It safely refuses hazardous items and asks for clarification on ambiguous items.

## Run the app
```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## How to test the core path
We have provided a test script to verify both standard classification and safety boundaries.
Run the test:
```bash
python test.py
```
Expected output: You should see a summary of 14/14 tests passed, demonstrating:
1. Normal classification (glass bottle).
2. Hazardous item refusal (battery).
3. Ambiguous item clarification (coffee cup).
4. Unlisted item refusal/unknown (plastic toy).

## Data and safety boundaries
- `data_rules.csv` contains supported ordinary items, aliases, categories, and disposal guidance.
- `data_refuse.csv` contains hazardous-item keywords. A match takes priority and returns a refusal with directions to consult local official guidance.
- `data_clarify.csv` contains broad names that need more detail.
- Any other unmatched input receives an "item not listed" response rather than a guessed category.

Rule Version:
The included entries are starter examples, not a complete catalog. Sorting and recycling rules vary by location and by the item's condition. Follow the latest guidance from your local government or waste service. The hazardous-item keyword list cannot cover every possible risk; if an item may be dangerous or you are unsure, do not rely on this helper to determine whether it is safe. Check with local authorities.

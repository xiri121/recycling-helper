"""Run classification, safety-boundary, dataset, and UI checks: python test.py."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import engine
from engine import classify


# query, expected status, expected category
CASES = [
    ("glass bottle", "classified", "recyclable"),
    ("newspaper", "classified", "recyclable"),
    ("plastic toy", "classified", "recyclable"),
    ("milk carton", "classified", "recyclable"),
    ("coffee grounds", "classified", "food waste"),
    ("banana peel", "classified", "food waste"),
    ("cat litter", "classified", "general waste"),
    ("coconut shell", "classified", "general waste"),
    ("greasy paper", "classified", "general waste"),
    ("bubble wrap", "classified", "general waste"),
    ("battery", "refuse", None),
    ("fluorescent tube", "refuse", None),
    ("batteries", "refuse", None),
    ("used batteries", "refuse", None),
    ("paint can", "refuse", None),
    ("nail polish", "refuse", None),
    ("motor oil", "refuse", None),
    ("medicine packaging", "refuse", None),
    ("coffee cup", "clarify", None),
    ("plastic", "clarify", None),
    ("painting", "clarify", None),
    ("gas", "clarify", None),
    ("coffee cups", "clarify", None),
    ("papers", "clarify", None),
    ("", "clarify", None),
    ("  ?!  ", "clarify", None),
    ("   GLASS BOTTLE!!!  ", "classified", "recyclable"),
    ("glass bottles", "classified", "recyclable"),
    ("cardboard boxes", "classified", "recyclable"),
    ("newspapers", "classified", "recyclable"),
    ("I have an empty glass bottle. How should I recycle it?", "classified", "recyclable"),
    ("Where do I put this newspaper?", "classified", "recyclable"),
    ("Can I recycle a plastic toy?", "classified", "recyclable"),
    ("How do I dispose of banana peels?", "classified", "food waste"),
    ("Where does cat litter go?", "classified", "general waste"),
    ("I have some empty milk cartons to throw away.", "classified", "recyclable"),
    ("Where does this glass bottle go in the garbage?", "classified", "recyclable"),
    ("How do I dispose of a gas cylinder?", "refuse", None),
    ("I have a battery and a newspaper", "refuse", None),
    ("a glass bottle containing pesticide", "refuse", None),
    ("batttery", "refuse", None),
    ("battrey and newspaper", "refuse", None),
    ("glass bottle and newspaper", "clarify", None),
    ("glass bottle and an alien widget", "clarify", None),
    ("glass bottle shaped lamp", "clarify", None),
    ("this is not a glass bottle", "clarify", None),
    ("fake fruit peel", "clarify", None),
    ("greasy newspaper", "clarify", None),
    ("soiled clothes", "clarify", None),
    ("dirty glass bottle", "clarify", None),
    ("artificial plant leaves", "clarify", None),
    ("plastic cup", "clarify", None),
    ("takeaway box", "clarify", None),
    ("a" * 1001, "clarify", None),
    ("alien widget", "unknown", None),
    ("quantum gizmo", "unknown", None),
]


class ClassifierTests(unittest.TestCase):
    def test_queries(self):
        for query, status, category in CASES:
            with self.subTest(query=query):
                result = classify(query)
                self.assertEqual((result.status, result.category), (status, category))
                self.assertTrue(result.advice)
                if status == "refuse":
                    self.assertFalse(result.candidates)

    def test_keywords_and_typos_need_confirmation(self):
        for query, expected in [
            ("bottle", "Glass bottle"),
            ("paper", "Printer paper"),
            ("newspapr", "Newspaper"),
            ("glas bottle", "Glass bottle"),
            ("I have a glas bottle", "Glass bottle"),
        ]:
            with self.subTest(query=query):
                result = classify(query)
                self.assertEqual(result.status, "clarify")
                self.assertIsNone(result.category)
                self.assertIn(expected, result.candidates)
                self.assertLessEqual(len(result.candidates), 6)
                self.assertEqual(classify(expected).status, "classified")

    def test_no_substring_or_unknown_object_classification(self):
        for query in ("fiberglass bottle", "glassbottle", "penholder", "glass bottlebrush", "newspaper stand", "batteryless widget"):
            with self.subTest(query=query):
                self.assertNotEqual(classify(query).status, "classified")
                self.assertIsNone(classify(query).category)

    def test_every_approved_alias_and_source(self):
        source_ids = engine.get_sources()["sources"]
        aliases = {}
        for row in engine._read_csv("data_rules.csv"):
            self.assertIn(row["source_id"], source_ids)
            for alias in engine._aliases(row, "aliases"):
                with self.subTest(item=row["item"], alias=alias):
                    # Conflicting aliases must not silently depend on row order.
                    self.assertIn(aliases.get(alias), (None, row["item"]))
                    aliases[alias] = row["item"]
                    result = classify(alias)
                    self.assertEqual((result.status, result.item, result.category),
                                     ("classified", row["item"], row["category"]))
                    self.assertTrue(result.source_url.startswith("https://lhsr.sh.gov.cn/"))

    def test_refusal_and_clarification_tables(self):
        for filename, status in [("data_refuse.csv", "refuse"), ("data_clarify.csv", "clarify")]:
            for row in engine._read_csv(filename):
                for alias in engine._aliases(row, "keywords"):
                    with self.subTest(table=filename, alias=alias):
                        result = classify(alias)
                        self.assertEqual(result.status, status)
                        self.assertIsNone(result.category)
                        self.assertTrue(result.source_url)

    def test_csv_edits_reload_without_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data_clarify.csv"
            path.write_text("keywords,advice,source_id\nwidget,First advice,SH2024\n", encoding="utf-8")
            with patch.object(engine, "DATA_DIR", Path(directory)):
                self.assertEqual(engine._read_csv(path.name)[0]["advice"], "First advice")
                stamp = path.stat().st_mtime_ns
                path.write_text("keywords,advice,source_id\nwidget,Other advice,SH2024\n", encoding="utf-8")
                os.utime(path, ns=(stamp + 1_000_000, stamp + 1_000_000))
                self.assertEqual(engine._read_csv(path.name)[0]["advice"], "Other advice")

    def test_malformed_csv_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data_rules.csv"
            path.write_text("item,aliases,category,advice,source_id\nWidget,widget,recyclable,unquoted,comma,SH2024\n", encoding="utf-8")
            with patch.object(engine, "DATA_DIR", Path(directory)):
                with self.assertRaises(ValueError):
                    engine._read_csv(path.name)


class InterfaceTests(unittest.TestCase):
    def test_sentence_suggestion_confirmation_and_refusal(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(Path(__file__).with_name("app.py"))).run()
        self.assertFalse(app.exception)
        app.text_input[0].set_value("How do I recycle an empty glass bottle?")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("Glass bottle", app.success[0].value)
        app.text_input[0].set_value("newspapr")
        app.button[0].click().run()
        self.assertFalse(app.success)
        candidate = next(button for button in app.button if button.label == "Newspaper")
        candidate.click().run()
        self.assertFalse(app.exception)
        self.assertIn("Newspaper", app.success[0].value)
        app.text_input[0].set_value("glass bottle and battery")
        app.button[0].click().run()
        self.assertFalse(app.success)
        self.assertIn("hazardous", app.error[0].value)


def main() -> int:
    print(f"Dataset: {engine.get_sources()['dataset_version']}; reviewed: {engine.get_sources()['reviewed_on']}")
    print(f"Checking {len(CASES)} query cases, all dataset aliases, file reloads, and the Streamlit interface.")
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

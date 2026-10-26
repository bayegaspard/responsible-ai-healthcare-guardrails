"""Checks that every demo scenario gets the decision the talk expects.

Run from the repository root:  python -m unittest discover tests
These tests cover the deterministic policy layer only, so they need no model.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from policies import SCENARIOS, evaluate  # noqa: E402


class ScenarioTests(unittest.TestCase):
    def test_every_scenario_gets_expected_status(self):
        for group in SCENARIOS:
            for s in group["items"]:
                with self.subTest(s["label"]):
                    self.assertEqual(evaluate(s["prompt"])["status"], s["expect"])

    def test_identifiers_never_reach_the_model(self):
        d = evaluate("Summarize: Patient John Smith, MRN 4829301, DOB 03/14/1958, SSN 123-45-6789.")
        for secret in ("John Smith", "4829301", "03/14/1958", "123-45-6789"):
            self.assertNotIn(secret, d["message"])

    def test_ordinary_questions_pass(self):
        for text in ("How do I deploy a Flask app?",
                     "Can you help me write my IRB application?",
                     "What is a good outcome measure for readmission studies?"):
            with self.subTest(text):
                self.assertEqual(evaluate(text)["status"], "allowed")


if __name__ == "__main__":
    unittest.main()

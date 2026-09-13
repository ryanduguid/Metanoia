from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The maintained repositories that carry the topic sets and the profile pins.
# Topics are applied directly through the GitHub API, not from a script here.
MAINTAINED_REPOSITORIES = (
    "australian-accounting",
    "accounting-review-pipeline",
    "australian-accounting-skills",
    "Ozzit",
    "llm-tax-guardrails",
    "au-tax-legislation-corpus",
)
# The intended profile pins, in display order. docs/MAINTAINING.md is the
# record the owner applies in the GitHub UI, so the two must agree.
INTENDED_PINS = (
    "accounting-review-pipeline",
    "Ozzit",
    "australian-accounting",
    "australian-accounting-skills",
    "llm-tax-guardrails",
    "au-tax-legislation-corpus",
)


class RepositoryIdentityTests(unittest.TestCase):
    def test_pin_record_names_six_maintained_repositories_in_order(self) -> None:
        text = (ROOT / "docs" / "MAINTAINING.md").read_text(encoding="utf-8")
        section = text.split("## Pinned repositories", 1)[1].split("## ", 1)[0]
        recorded = tuple(re.findall(r"^\d+\. `([A-Za-z0-9._-]+)`$", section, re.MULTILINE))

        self.assertEqual(recorded, INTENDED_PINS)
        self.assertEqual(len(set(recorded)), 6)
        self.assertTrue(set(recorded) <= set(MAINTAINED_REPOSITORIES))


if __name__ == "__main__":
    unittest.main()

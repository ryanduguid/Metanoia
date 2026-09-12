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
# Recorded in banner_content.json, whether or not their README carries the
# banner today: the record is what a paste would be rendered from.
BANNER_REPOSITORIES = (
    "australian-accounting",
    "accounting-review-pipeline",
)
OLD_GITHUB_URLS = (
    "github.com/ryanduguid/au-tax-mcp-server",
    "github.com/ryanduguid/xero-ai-review-gateway",
    "github.com/ryanduguid/monthly-close-control-plane",
    "github.com/ryanduguid/review-ready-gate",
    "github.com/ryanduguid/au-financial-analytics-pbip",
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
# Repositories archived on 2 and 3 September 2026 after the subtree imports.
# aus-accounting-mcp and monthly-close-controls are not here: they were renamed
# to australian-accounting and accounting-review-pipeline, so their node IDs
# carried across and a link to the old name is a rename redirect instead.
ARCHIVED_REPOSITORIES = frozenset(
    {
        "payday-super-checker",
        "ato-benchmark-compare",
        "div7a-loan-review",
        "TheExchequerTally",
        "SolomonsSword",
        "TheWIPTally",
        "xero-trial-balance-export",
        "workpaper-review-gate",
        "xero-ledger-review-gate",
        "accounting-excel-toolkit",
        "australian-accounting-power-bi",
        "hardhat-ledger",
        "tax-radar-au",
    }
)


class RepositoryIdentityTests(unittest.TestCase):
    def test_active_profile_surfaces_use_canonical_repositories(self) -> None:
        banners = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "tools" / "banner.py",
                ROOT / "tools" / "banner_content.json",
            )
        )
        active = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "llms.txt",
                ROOT / "tools" / "banner.py",
                ROOT / "tools" / "banner_content.json",
            )
        )
        for repository in BANNER_REPOSITORIES:
            self.assertIn(f'"{repository}"', banners)
        for old_url in OLD_GITHUB_URLS:
            self.assertNotIn(old_url, active)

    def test_pin_record_names_six_maintained_repositories_in_order(self) -> None:
        text = (ROOT / "docs" / "MAINTAINING.md").read_text(encoding="utf-8")
        section = text.split("## Pinned repositories", 1)[1].split("## ", 1)[0]
        recorded = tuple(re.findall(r"^\d+\. `([A-Za-z0-9._-]+)`$", section, re.MULTILINE))

        self.assertEqual(recorded, INTENDED_PINS)
        self.assertEqual(len(set(recorded)), 6)
        self.assertFalse(set(recorded) & ARCHIVED_REPOSITORIES)
        self.assertTrue(set(recorded) <= set(MAINTAINED_REPOSITORIES))

    def test_profile_component_links_point_to_the_maintained_directories(self) -> None:
        text = (ROOT / "llms.txt").read_text(encoding="utf-8")
        links = dict(re.findall(r"^- \*\*([^*]+)\*\* \((https://[^)]+)\):", text, re.MULTILINE))
        components = {
            "Aus Accounting MCP": "australian-accounting/tree/main/apps/aus-accounting-mcp",
            "payday-super-checker": "australian-accounting/tree/main/packages/payday-super-checker",
            "ato-benchmark-compare": "australian-accounting/tree/main/packages/ato-benchmark-compare",
            "TheExchequerTally": "australian-accounting/tree/main/packages/the-exchequer-tally",
            "SolomonsSword": "australian-accounting/tree/main/packages/solomons-sword",
            "xero-trial-balance-export": "accounting-review-pipeline/tree/main/packages/xero-trial-balance-export",
            "accounting-excel-toolkit": "accounting-review-pipeline/tree/main/adapters/accounting-excel-toolkit",
            "Workpaper Review Gate": "accounting-review-pipeline/tree/main/packages/review-ready-gate",
            "Monthly Close Controls": "accounting-review-pipeline/tree/main/packages/monthly-close-control-plane",
            "Xero Ledger Review Gate": "accounting-review-pipeline/tree/main/packages/elizabeth-anne-alexander",
            "Australian Accounting Power BI": "accounting-review-pipeline/tree/main/apps/australian-accounting-power-bi",
            "Hardhat Ledger workflows": "australian-accounting-skills",
        }
        for name, location in components.items():
            with self.subTest(component=name):
                self.assertEqual(links.get(name), f"https://github.com/ryanduguid/{location}")


if __name__ == "__main__":
    unittest.main()

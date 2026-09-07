from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPIC_REPOSITORIES = (
    "australian-accounting",
    "accounting-review-pipeline",
    "australian-accounting-skills",
    "Ozzit",
    "llm-tax-guardrails",
    "au-tax-legislation-corpus",
)
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
    def test_topic_updates_only_address_maintained_writable_repositories(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            # The topic script is PowerShell, so without an interpreter there is
            # nothing to exercise. Skip rather than fail so the suite still passes
            # on machines without pwsh; the GitHub runners ship pwsh and run it.
            self.skipTest("PowerShell (pwsh or powershell) is not installed, so apply-topics.ps1 cannot run")
        # Stub only the external write boundary, never call GitHub from this test.
        command = r"""
$ErrorActionPreference = 'Stop'
$global:topicCalls = [System.Collections.Generic.List[object]]::new()
function gh { $global:topicCalls.Add(@($args)) }
& $env:TOPIC_SCRIPT_UNDER_TEST
'TOPIC_CALLS_JSON=' + (ConvertTo-Json -InputObject $global:topicCalls.ToArray() -Depth 4 -Compress)
"""
        result = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
            env={**os.environ, "TOPIC_SCRIPT_UNDER_TEST": str(ROOT / "tools" / "apply-topics.ps1")},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [line for line in result.stdout.splitlines() if line.startswith("TOPIC_CALLS_JSON=")]
        self.assertEqual(len(records), 1, result.stdout)
        calls = json.loads(records[0].split("=", 1)[1])
        self.assertEqual(len(calls), len(TOPIC_REPOSITORIES))
        self.assertEqual({call[2] for call in calls}, {f"ryanduguid/{name}" for name in TOPIC_REPOSITORIES})
        for call in calls:
            with self.subTest(repository=call[2]):
                self.assertEqual(call[:2], ["repo", "edit"])
                self.assertGreater(len(call), 3)
                self.assertEqual(call[3::2], ["--add-topic"] * len(call[4::2]))

    def test_active_profile_surfaces_use_canonical_repositories(self) -> None:
        topics = (ROOT / "tools" / "apply-topics.ps1").read_text(encoding="utf-8")
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
                ROOT / "tools" / "apply-topics.ps1",
                ROOT / "tools" / "banner.py",
                ROOT / "tools" / "banner_content.json",
            )
        )
        for repository in TOPIC_REPOSITORIES:
            self.assertIn(f'"ryanduguid/{repository}" =', topics)
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
        self.assertTrue(set(recorded) <= set(TOPIC_REPOSITORIES))

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

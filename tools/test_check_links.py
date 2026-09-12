"""Policy tests for profile URL extraction and automation denials."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import check_links


class UrlPolicyTests(unittest.TestCase):
    def test_html_attribute_forms_and_mixed_case_schemes(self) -> None:
        for markup in (
            '<a HREF="HTTP://example.test/path">link</a>',
            "<img src='HTTP://example.test/path'>",
            '<a href=HTTP://example.test/path>link</a>',
            '[link](HTTP://example.test/path)',
        ):
            with self.subTest(markup=markup):
                urls = {
                    check_links.normalise_url(url)
                    for pattern in check_links.LINK_RES
                    for url in pattern.findall(markup)
                }
                self.assertEqual(urls, {'http://example.test/path'})

    def test_parenthesised_machine_index_links_cannot_hide_rename_redirects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "llms.txt").write_text(
                "- **MCP** (https://github.com/ryanduguid/aus-accounting-mcp): local tool\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with (
                patch.object(check_links, "ROOT", root),
                patch.object(check_links, "FILES", ["llms.txt"]),
                patch.object(check_links, "fetch_final_url", return_value=(
                    200, "https://github.com/ryanduguid/australian-accounting"
                )),
                patch.object(check_links, "repository_is_archived", lambda name: False),
                patch.object(check_links, "profile_failures", list),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(check_links.main(), 1)
            self.assertIn("rename redirect, repoint the link", output.getvalue())
            self.assertNotIn("archived", output.getvalue())

    def test_archived_repository_links_fail_outside_the_allowlist(self) -> None:
        archived = {"payday-super-checker": True, "australian-accounting": False, "pyxero": True}
        urls = {
            "https://github.com/ryanduguid/payday-super-checker": {"README.md"},
            "https://github.com/ryanduguid/australian-accounting/tree/main/packages/x": {"llms.txt"},
            "https://github.com/ryanduguid/pyxero": {"FORKS.md"},
            # the same archived URL in FORKS.md and a docs file: FORKS.md is
            # exempt, the docs file is not
            "https://GitHub.com/RyanDuguid/PyXero/releases": {"FORKS.md", "docs/MAINTAINING.md"},
        }

        failures = check_links.archived_target_failures(
            urls, lookup=archived.__getitem__
        )

        self.assertEqual(
            sorted(failure.split(":", 1)[0] for failure in failures),
            ["README.md", "docs/MAINTAINING.md"],
        )
        self.assertTrue(any("ryanduguid/pyxero is archived" in f for f in failures))

    def test_archived_lookup_failure_is_a_failure(self) -> None:
        def lookup(name: str) -> bool:
            raise urllib.error.URLError("rate limited")

        failures = check_links.archived_target_failures(
            {"https://github.com/ryanduguid/Ozzit": {"README.md"}}, lookup=lookup
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("archived lookup failed", failures[0])

    def test_repository_verdicts_are_cached_including_failures(self) -> None:
        attempts: list[str] = []

        def fetch(name: str) -> bool:
            attempts.append(name)
            if name == "broken":
                raise urllib.error.URLError("rate limited")
            return name == "hardhat-ledger"

        with (
            patch.object(check_links, "fetch_repository_archived", fetch),
            patch.object(check_links, "_ARCHIVED_VERDICTS", {}),
        ):
            self.assertTrue(check_links.repository_is_archived("hardhat-ledger"))
            self.assertTrue(check_links.repository_is_archived("hardhat-ledger"))
            self.assertFalse(check_links.repository_is_archived("Ozzit"))
            for _ in range(2):
                with self.assertRaises(urllib.error.URLError):
                    check_links.repository_is_archived("broken")

        self.assertEqual(attempts, ["hardhat-ledger", "Ozzit", "broken"])

    def test_fetch_repository_archived_retries_server_errors(self) -> None:
        class ApiResponse:
            def __enter__(self) -> "ApiResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"full_name": "ryanduguid/hardhat-ledger", "archived": true}'

        attempts = 0

        def opener(request: object, timeout: int) -> ApiResponse:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise urllib.error.HTTPError(
                    "https://api.github.com/repos/ryanduguid/hardhat-ledger",
                    502,
                    "Bad Gateway",
                    {},
                    None,
                )
            return ApiResponse()

        self.assertTrue(
            check_links.fetch_repository_archived("hardhat-ledger", opener=opener)
        )
        self.assertEqual(attempts, 2)

    def test_main_reports_an_archived_target_once_per_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text(
                "[Payday](https://github.com/ryanduguid/payday-super-checker)\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with (
                patch.object(check_links, "ROOT", root),
                patch.object(check_links, "FILES", ["README.md"]),
                patch.object(check_links, "fetch_final_url", return_value=(
                    200, "https://github.com/ryanduguid/payday-super-checker"
                )),
                patch.object(check_links, "repository_is_archived", lambda name: True),
                patch.object(check_links, "profile_failures", list),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(check_links.main(), 1)
            self.assertEqual(output.getvalue().count("is archived"), 1)

    def test_profile_copies_that_agree_pass(self) -> None:
        local = (check_links.ROOT / "FORKS.md").read_text(encoding="utf-8")
        published = {
            "FORKS.md": local.replace("\n", "\r\n"),
            "llms.txt": "- **Ozzit** (https://github.com/ryanduguid/Ozzit): LAMBDAs\n",
        }
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            failures = check_links.profile_failures(
                fetch=published.__getitem__,
                resolve=lambda url: (200, url),
            )

        self.assertEqual(failures, [])
        self.assertIn("ok profile llms.txt https://github.com/ryanduguid/Ozzit", output.getvalue())

    def test_a_profile_forks_copy_that_drifted_fails(self) -> None:
        published = {"FORKS.md": "# Contribution forks\n", "llms.txt": "no links\n"}

        failures = check_links.profile_failures(
            fetch=published.__getitem__, resolve=lambda url: (200, url)
        )

        self.assertEqual(len(failures), 1, failures)
        self.assertIn("canonical fork map", failures[0])

    def test_a_profile_llms_repository_path_that_404s_fails(self) -> None:
        local = (check_links.ROOT / "FORKS.md").read_text(encoding="utf-8")
        gone = "https://github.com/ryanduguid/australian-accounting/tree/main/packages/gone"
        published = {"FORKS.md": local, "llms.txt": f"- **Gone** ({gone}): moved\n"}

        def resolve(url: str) -> tuple[int, str]:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        failures = check_links.profile_failures(
            fetch=published.__getitem__, resolve=resolve
        )

        self.assertEqual(len(failures), 1, failures)
        self.assertIn(f"profile llms.txt: {gone} -> HTTP 404", failures[0])

    def test_a_profile_fetch_that_fails_is_a_failure(self) -> None:
        def fetch(name: str) -> str:
            raise urllib.error.URLError("no network")

        failures = check_links.profile_failures(
            fetch=fetch, resolve=lambda url: (200, url)
        )

        self.assertEqual(len(failures), 2, failures)
        self.assertTrue(all("fetch failed" in failure for failure in failures))

    def test_normalises_markdown_code_span_url(self) -> None:
        self.assertEqual(
            check_links.normalise_url("https://duguid.com.au/`"),
            "https://duguid.com.au/",
        )

    def test_accepts_only_the_hibernated_linkedin_automation_denial(self) -> None:
        linkedin = "https://www.linkedin.com/in/ryan-duguid/"

        self.assertTrue(check_links.is_accepted_automation_denial(linkedin, 999))
        self.assertFalse(check_links.is_accepted_automation_denial(linkedin, 404))
        self.assertFalse(
            check_links.is_accepted_automation_denial(
                "https://www.linkedin.com/in/someone-else/", 999
            )
        )


if __name__ == "__main__":
    unittest.main()

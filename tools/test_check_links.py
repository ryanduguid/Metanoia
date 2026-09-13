"""Policy tests for profile URL extraction, profile copies and automation denials."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import check_links

GOOD_LLMS = "".join(
    f"- **{name}** (https://github.com/ryanduguid/{location}): component\n"
    for name, location in check_links.LLMS_COMPONENTS.items()
)


def profile(**files: str):
    """Patch the profile reads with fixed text; missing names raise like a 404."""

    def fetch(name: str) -> str:
        if name not in files:
            raise urllib.error.HTTPError(check_links.PROFILE_RAW + name, 404, "Not Found", {}, None)
        return files[name]

    return patch.object(check_links, "fetch_profile_file", fetch)


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
        output = io.StringIO()
        with (
            patch.object(check_links, "FILES", []),
            profile(
                **{
                    "FORKS.md": "",
                    "llms.txt": GOOD_LLMS
                    + "- **MCP** (https://github.com/ryanduguid/aus-accounting-mcp): local tool\n",
                }
            ),
            patch.object(check_links, "fetch_final_url", return_value=(
                200, "https://github.com/ryanduguid/australian-accounting"
            )),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(check_links.main(), 1)
        self.assertIn("profile llms.txt: https://github.com/ryanduguid/aus-accounting-mcp", output.getvalue())
        self.assertIn("rename redirect, repoint the link", output.getvalue())

    def test_local_and_profile_files_are_checked_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text(
                "[Ozzit](https://github.com/ryanduguid/Ozzit)\n", encoding="utf-8"
            )
            output = io.StringIO()
            with (
                patch.object(check_links, "ROOT", root),
                patch.object(check_links, "FILES", ["README.md"]),
                profile(
                    **{
                        "FORKS.md": "| [pyxero](https://github.com/ryanduguid/pyxero) |\r\n",
                        "llms.txt": GOOD_LLMS,
                    }
                ),
                patch.object(check_links, "fetch_final_url", lambda url: (200, url)),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(check_links.main(), 0)
        self.assertIn("ok https://github.com/ryanduguid/Ozzit", output.getvalue())
        self.assertIn("ok https://github.com/ryanduguid/pyxero", output.getvalue())
        self.assertIn("across 3 files", output.getvalue())

    def test_a_profile_llms_repository_path_that_404s_fails(self) -> None:
        gone = "https://github.com/ryanduguid/australian-accounting/tree/main/packages/gone"

        def resolve(url: str) -> tuple[int, str]:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        output = io.StringIO()
        with (
            patch.object(check_links, "FILES", []),
            profile(**{"FORKS.md": "", "llms.txt": GOOD_LLMS + f"- **Gone** ({gone}): moved\n"}),
            patch.object(check_links, "fetch_final_url", resolve),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(check_links.main(), 1)
        self.assertIn(f"FAIL profile llms.txt: {gone} -> HTTP 404", output.getvalue())

    def test_a_profile_fetch_that_fails_is_a_failure(self) -> None:
        def fetch(name: str) -> str:
            raise urllib.error.URLError("no network")

        output = io.StringIO()
        with (
            patch.object(check_links, "FILES", []),
            patch.object(check_links, "fetch_profile_file", fetch),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(check_links.main(), 1)
        self.assertEqual(output.getvalue().count("fetch failed"), 2)

    def test_profile_llms_must_name_each_component_at_its_maintained_directory(self) -> None:
        self.assertEqual(check_links.llms_index_failures(GOOD_LLMS), [])

        moved = GOOD_LLMS.replace(
            "australian-accounting/tree/main/packages/payday-super-checker",
            "payday-super-checker",
        )
        failures = check_links.llms_index_failures(moved)

        self.assertEqual(len(failures), 1, failures)
        self.assertIn("payday-super-checker should link", failures[0])

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

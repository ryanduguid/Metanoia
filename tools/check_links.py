"""Link and content checks for the profile repository.

Scans README.md, SECURITY.md and docs/*.md here, plus the profile repository's
published FORKS.md and llms.txt, for Markdown links, HTML href/src attributes
and bare URLs, then checks in order:

1. Every link is https, never http.
2. Every github.com/ryanduguid/<repo> link resolves to that exact repository.
   A rename redirect (301 to a different repo path) is a FAILURE even though
   the request ends in a 200, because redirects break if the old name is reused.
3. Every other absolute link resolves (2xx after redirects).
4. Retired repository names and em or en dashes must not appear outside the
   allowed history notes in docs/MAINTAINING.md.
5. The profile llms.txt names each component at the monorepo directory that
   now holds it.

The profile files are read from raw.githubusercontent.com; GITHUB_TOKEN is
sent when Actions provides it and is only ever used to read. A fetch that
cannot complete is a failure, not a pass.

Exit 0 clean, 1 on any failure. Stdlib only.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["README.md", "SECURITY.md", *sorted(
    str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.md")
)]
# Published by the profile repository and checked the same way as the local
# files. The fork map and the agent index live there, not here.
PROFILE_FILES = ["FORKS.md", "llms.txt"]

RETIRED_NAMES = [
    "CharlesHenryWickens",
    "JohnSpenceOgilvy",
    "MaryAddisonHamilton",
    "SirAlexanderFitzgerald",
    "RaymondChambers",
    "SirArthurFadden",
    "RussellMathews",
    "ElizabethAnneAlexander",
    "JohnKenley",
    "EdwinNixon",
    "LouisGoldberg",
]

# MAINTAINING.md legitimately names retired repositories twice: the rename
# history example and the banned-names list itself.
RETIRED_NAME_ALLOWANCE = {"docs/MAINTAINING.md": 2}

USER_AGENT = "ryanduguid-profile-link-check"
# The display profile repository, whose published copies are checked here.
PROFILE_RAW = "https://raw.githubusercontent.com/ryanduguid/ryanduguid/main/"
LINKEDIN_IDENTITY_URL = "https://www.linkedin.com/in/ryan-duguid/"
# GitHub owner and repository names are case-insensitive; names are
# lower-cased so the redirect check agrees with itself.
OWN_REPO = re.compile(r"^https://github\.com/ryanduguid/([A-Za-z0-9._-]+)", re.I)

# Where each component named in the profile llms.txt now lives. A component
# that moved out of a monorepo fails this build instead of rotting on the
# profile.
LLMS_COMPONENTS = {
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
LLMS_ENTRY = re.compile(r"^- \*\*([^*]+)\*\* \((https://[^)]+)\):", re.MULTILINE)

LINK_RES = [
    re.compile(r"\[[^\]]*\]\((https?://[^)\s]+)\)", re.I),
    re.compile(r"\((https?://[^)\s]+)\)", re.I),
    re.compile(r"\b(?:href|src)\s*=\s*['\"]?(https?://[^\s'\">]+)", re.I),
    re.compile(r"(?<![('\"=\]])(https?://[^\s)'\">\]]+)", re.I),
]


def fetch_final_url(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.geturl()


def normalise_url(url: str) -> str:
    """Remove prose punctuation and Markdown code-span delimiters."""
    scheme, separator, remainder = url.rstrip(".,;:`").partition(":")
    return scheme.lower() + separator + remainder


def is_accepted_automation_denial(url: str, status: int) -> bool:
    """Accept only LinkedIn's response for the exact identity URL."""
    return url == LINKEDIN_IDENTITY_URL and status == 999


def own_repository(url: str) -> str | None:
    """Return the ryanduguid repository name a URL points at, if any."""
    match = OWN_REPO.match(url)
    return match.group(1).lower() if match else None


def fetch_profile_file(name: str) -> str:
    """Read one file from the profile repository's default branch."""
    headers = {"User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(PROFILE_RAW + name, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def llms_index_failures(text: str) -> list[str]:
    """Check that the profile llms.txt names each component at one GitHub location.

    A component may also be listed under its website page; only its
    github.com/ryanduguid entries must be exactly the maintained directory.
    """
    links: dict[str, set[str]] = {}
    for name, url in LLMS_ENTRY.findall(text):
        if own_repository(url):
            links.setdefault(name, set()).add(url)
    failures: list[str] = []
    for name, location in LLMS_COMPONENTS.items():
        expected = f"https://github.com/ryanduguid/{location}"
        found = links.get(name, set())
        if found != {expected}:
            failures.append(
                f"profile llms.txt: {name} should link {expected}, found {sorted(found) or None}"
            )
    return failures


def main() -> int:
    failures: list[str] = []
    sources: dict[str, str] = {}
    for rel in FILES:
        sources[rel] = (ROOT / rel).read_text(encoding="utf-8")
    for name in PROFILE_FILES:
        try:
            sources[f"profile {name}"] = fetch_profile_file(name)
        except Exception as exc:  # noqa: BLE001 - report every failure mode
            failures.append(f"profile {name}: fetch failed: {exc}")
    if "profile llms.txt" in sources:
        failures.extend(llms_index_failures(sources["profile llms.txt"]))

    urls: dict[str, str] = {}
    for rel, text in sources.items():
        for pattern in LINK_RES:
            for url in pattern.findall(text):
                urls.setdefault(normalise_url(url), rel)
        hits = sum(text.count(name) for name in RETIRED_NAMES)
        allowed_lines = RETIRED_NAME_ALLOWANCE.get(rel.replace("\\", "/"), 0)
        if allowed_lines:
            lines_with_hits = sum(
                1 for line in text.splitlines() if any(n in line for n in RETIRED_NAMES)
            )
            if lines_with_hits > allowed_lines:
                failures.append(
                    f"{rel}: retired names on {lines_with_hits} lines, only {allowed_lines} allowed"
                )
        elif hits:
            failures.append(f"{rel}: {hits} retired repository name reference(s)")
        for ch, label in (("—", "em dash"), ("–", "en dash")):
            if ch in text:
                failures.append(f"{rel}: {label} present")

    checked = 0
    for url, src in sorted(urls.items()):
        if url.startswith("http:"):
            failures.append(f"{src}: insecure link {url}")
            continue
        # Badge URLs encode label text, not a resource that can 404 meaningfully.
        if url.startswith("https://img.shields.io/badge/"):
            continue
        checked += 1
        try:
            status, final = fetch_final_url(url)
        except urllib.error.HTTPError as exc:
            if is_accepted_automation_denial(url, exc.code):
                print(
                    f"accepted automation denial {url} -> HTTP {exc.code} "
                    "(exact hibernated LinkedIn identity URL)"
                )
            else:
                failures.append(f"{src}: {url} -> HTTP {exc.code}")
            continue
        except Exception as exc:  # noqa: BLE001 - report every failure mode
            failures.append(f"{src}: {url} -> {exc}")
            continue
        if status >= 400:
            failures.append(f"{src}: {url} -> HTTP {status}")
            continue
        name = own_repository(url)
        if name is not None:
            final_name = own_repository(final)
            if final_name is None or final_name.lower() != name.lower():
                failures.append(
                    f"{src}: {url} redirected to {final} (rename redirect, repoint the link)"
                )
                continue
        print(f"ok {url}")

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print(f"\nall clear: {checked} links resolved across {len(sources)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

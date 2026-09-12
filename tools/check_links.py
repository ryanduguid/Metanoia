"""Link and content checks for the profile repository.

Scans README.md, llms.txt, SECURITY.md and docs/*.md for Markdown links,
HTML href/src attributes and bare URLs, then checks in order:

1. Every link is https, never http.
2. Every github.com/ryanduguid/<repo> link resolves to that exact repository.
   A rename redirect (301 to a different repo path) is a FAILURE even though
   the request ends in a 200, because redirects break if the old name is reused.
3. Every other absolute link resolves (2xx after redirects).
4. Retired repository names and em or en dashes must not appear outside the
   allowed history notes in docs/MAINTAINING.md.
5. No github.com/ryanduguid/<repo> link may resolve to an archived
   repository. The September 2026 consolidation archived thirteen public
   repositories after their code moved into the monorepos (two more source
   repositories were renamed into the monorepos, which check 2 already
   catches); an archived repository still answers 200, so the redirect check
   cannot see it. Only links that resolved and passed check 2 are classified.
   Each repository is looked up once through the GitHub REST API
   (GITHUB_TOKEN lifts the rate limit) with the same transient-failure
   retries, and a lookup that cannot complete is a failure, not a pass.
   ARCHIVED_TARGET_ALLOWLIST names, per file, the archived repositories that
   file may link on purpose: FORKS.md records archived forks in its own
   tables.

Exit 0 clean, 1 on any failure. Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["README.md", "llms.txt", "SECURITY.md", "FORKS.md", *sorted(
    str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.md")
)]

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
LINKEDIN_IDENTITY_URL = "https://www.linkedin.com/in/ryan-duguid/"
# GitHub owner and repository names are case-insensitive; names are
# lower-cased so the cache, the allowlist and the redirect check agree.
OWN_REPO = re.compile(r"^https://github\.com/ryanduguid/([A-Za-z0-9._-]+)", re.I)
GITHUB_API = "https://api.github.com/repos/ryanduguid/"

MAX_FETCH_ATTEMPTS = 5

# Per file, the archived repositories it may link on purpose. FORKS.md records
# forks that are already archived and forks awaiting the owner's archive
# action; those rows are the record of the decision, not link drift. Keyed by
# file and repository so an exemption never widens to the whole file.
ARCHIVED_TARGET_ALLOWLIST: dict[str, frozenset[str]] = {
    "FORKS.md": frozenset(
        {
            # already archived on GitHub
            "pyxero",
            "requests-cache",
            "ledgersmb",
            "beancount",
            "bank-statement-import",
            "rest-application",
            # awaiting the owner's archive action
            "l10n-australia",
            "account-reconcile",
            "account-financial-reporting",
        }
    ),
}

# Verdict or failure per repository name, so one repository costs one API
# request however many files link it.
_ARCHIVED_VERDICTS: dict[str, bool | Exception] = {}

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


def fetch_repository_archived(
    name: str, *, opener: object = urllib.request.urlopen
) -> bool:
    """Ask the GitHub REST API whether ryanduguid/<name> is archived.

    Retries transient transport failures and HTTP 5xx. Raises on any
    remaining transport or parse failure so the caller records a failure; a
    link that cannot be classified must not pass as maintained.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(GITHUB_API + name, headers=headers)
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with opener(req, timeout=30) as resp:  # type: ignore[operator]
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if not 500 <= exc.code < 600 or attempt == MAX_FETCH_ATTEMPTS:
                raise
            print(f"retry {attempt}/{MAX_FETCH_ATTEMPTS - 1} {name}: HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == MAX_FETCH_ATTEMPTS:
                raise
            print(f"retry {attempt}/{MAX_FETCH_ATTEMPTS - 1} {name}: {exc}")
    archived = payload.get("archived")
    if not isinstance(archived, bool):
        raise ValueError(f"GitHub API returned no archived flag for {name}")
    return archived


def repository_is_archived(name: str) -> bool:
    """Cached verdict for ryanduguid/<name>; a cached failure re-raises."""
    if name not in _ARCHIVED_VERDICTS:
        try:
            _ARCHIVED_VERDICTS[name] = fetch_repository_archived(name)
        except Exception as exc:  # noqa: BLE001 - cache every failure mode
            _ARCHIVED_VERDICTS[name] = exc
    verdict = _ARCHIVED_VERDICTS[name]
    if isinstance(verdict, Exception):
        raise verdict
    return verdict


def archived_target_failures(
    urls: dict[str, set[str]], *, lookup=None
) -> list[str]:
    """Fail every own-repository link whose target is archived.

    ``urls`` maps each resolved own-repository URL to every file it was found
    in; callers pass only links that already resolved and passed the rename
    check, so a broken link is reported once. The allowlist is applied per
    file and repository, so an exemption in one file never covers another.
    """
    if lookup is None:
        lookup = repository_is_archived
    failures: list[str] = []
    for url, sources in sorted(urls.items()):
        name = own_repository(url)
        if name is None:
            continue
        for src in sorted(sources):
            if name in ARCHIVED_TARGET_ALLOWLIST.get(src.replace("\\", "/"), frozenset()):
                continue
            try:
                archived = lookup(name)
            except Exception as exc:  # noqa: BLE001 - report every failure mode
                failures.append(f"{src}: {url} -> archived lookup failed: {exc}")
                continue
            if archived:
                failures.append(
                    f"{src}: {url} -> ryanduguid/{name} is archived "
                    "(repoint the link to the maintained repository)"
                )
    return failures


def main() -> int:
    failures: list[str] = []
    urls: dict[str, str] = {}
    sources: dict[str, set[str]] = {}

    for rel in FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for pattern in LINK_RES:
            for url in pattern.findall(text):
                url = normalise_url(url)
                urls.setdefault(url, rel)
                sources.setdefault(url, set()).add(rel)
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
    resolved_own_urls: dict[str, set[str]] = {}
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
            resolved_own_urls[url] = sources[url]
        print(f"ok {url}")

    failures.extend(archived_target_failures(resolved_own_urls))

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print(f"\nall clear: {checked} links resolved across {len(FILES)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Link and content checks for the profile repository.

Scans AGENTS.md, README.md, SECURITY.md and docs/*.md here, plus the profile repository's
published FORKS.md and llms.txt, for Markdown links, HTML href/src attributes
and bare URLs, then checks in order:

1. Every link is https, never http.
2. Every github.com/ryanduguid/<repo> link resolves to that exact repository.
   A rename redirect (301 to a different repo path) is a FAILURE even though
   the request ends in a 200, because redirects break if the old name is reused.
3. Every other absolute link resolves (2xx after redirects), except the approved
   LinkedIn identity's HTTP 999 automation denial, reported as unverified.
4. Retired repository names and em or en dashes must not appear outside the
   allowed history notes in docs/MAINTAINING.md.
5. The profile llms.txt names each component at the monorepo directory that
   now holds it.

The profile files are read from raw.githubusercontent.com; GITHUB_TOKEN is
sent when Actions provides it and is only ever used to read. A fetch that
cannot complete is a failure, not a pass.

Exit 0 when checks pass, including the accepted denial; 1 on any failure. Stdlib only.
"""

from __future__ import annotations

import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# AGENTS.md carries links like any other tracked document, and was checked by
# neither pass: its absolute URLs were never fetched and its relative targets were
# never resolved, so a renamed local file broke it silently.
FILES = ["AGENTS.md", "README.md", "SECURITY.md", *sorted(
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
MAX_FETCH_ATTEMPTS = 5
MAX_RETRY_WAIT_SECONDS = 30
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
    "aus-accounting-mcp": "australian-accounting/tree/main/apps/aus-accounting-mcp",
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
    "australian-accounting-skills": "australian-accounting-skills",
}
LLMS_ENTRY = re.compile(
    r"^- (?:\*\*([^*]+)\*\* \(|\[([^\]]+)\]\()(https://[^)]+)\):", re.MULTILINE
)

# A Markdown target that is not a URL, a mail link or a bare anchor: that is a
# path inside the repository, and it can be misspelt.
RELATIVE_LINK = re.compile(r"\[[^\]]*\]\((?!\w+:|//)([^)\s]+)\)")

LINK_RES = [
    re.compile(r"\[[^\]]*\]\((https?://[^)\s]+)\)", re.I),
    re.compile(r"\((https?://[^)\s]+)\)", re.I),
    re.compile(r"\b(?:href|src)\s*=\s*['\"]?(https?://[^\s'\">]+)", re.I),
    re.compile(r"(?<![('\"=\]])(https?://[^\s)'\">\]]+)", re.I),
]


def _https_origin(url: str) -> tuple[str, int]:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.casefold() != "https" or not parts.hostname:
        raise ValueError("only absolute HTTPS URLs are permitted")
    port = parts.port
    return parts.hostname.casefold(), 443 if port is None else port


class _HttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        try:
            return super().http_error_302(req, fp, code, msg, headers)
        finally:
            fp.close()

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        try:
            source_origin = _https_origin(req.full_url)
            target_origin = _https_origin(redirected.full_url)
        except ValueError as exc:
            raise urllib.error.HTTPError(
                redirected.full_url, code, "redirect target must use valid HTTPS", headers, fp
            ) from exc
        if source_origin != target_origin:
            redirected.remove_header("Authorization")
        return redirected


_URL_OPENER = urllib.request.build_opener(_HttpsRedirectHandler())


def _fresh_request(template: urllib.request.Request) -> urllib.request.Request:
    request = urllib.request.Request(
        template.full_url, data=template.data, headers=dict(template.headers),
        origin_req_host=template.origin_req_host, unverifiable=template.unverifiable,
        method=template.get_method(),
    )
    for name, value in template.unredirected_hdrs.items():
        request.add_unredirected_header(name, value)
    return request


def _request_url(request: urllib.request.Request, consume):
    """Bound sleeps to 30 seconds; each GET keeps its own 30-second timeout."""
    _https_origin(request.full_url)
    waited = 0.0
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with _URL_OPENER.open(_fresh_request(request), timeout=30) as response:
                return consume(response)
        except (urllib.error.URLError, TimeoutError) as exc:
            retry_after = ""
            if isinstance(exc, urllib.error.HTTPError):
                retry_after = (exc.headers or {}).get("Retry-After", "").strip()
                exc.close()
                if exc.code != 429 and not 500 <= exc.code < 600:
                    raise
            if attempt == MAX_FETCH_ATTEMPTS:
                raise
            delay = float(2 ** (attempt - 1))
            if re.fullmatch(r"[0-9]+", retry_after):
                delay = float(retry_after)
            elif retry_after:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    delay = max(0.0, retry_at.timestamp() - time.time())
                except (ValueError, TypeError, OverflowError):
                    pass
            if waited + delay > MAX_RETRY_WAIT_SECONDS:
                raise
            time.sleep(delay)
            waited += delay
    raise AssertionError("unreachable")


def fetch_final_url(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return _request_url(req, lambda response: (response.status, response.geturl()))


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
    return _request_url(req, lambda response: response.read()).decode("utf-8")


def llms_index_failures(text: str) -> list[str]:
    """Check that the profile llms.txt names each component at one GitHub location.

    A component may also be listed under its website page; only its
    github.com/ryanduguid entries must be exactly the maintained directory.
    """
    links: dict[str, set[str]] = {}
    for bold_name, markdown_name, url in LLMS_ENTRY.findall(text):
        name = bold_name or markdown_name
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


def relative_link_failures(rel: str, text: str) -> list[str]:
    """Check that every relative Markdown target in a tracked file exists.

    LINK_RES only captures http(s) URLs, so a misspelt local target passed CI
    while repository navigation was broken. Only tracked files are checked: a
    fetched profile file's relative targets belong to another repository.
    """
    failures: list[str] = []
    root = ROOT
    for target in RELATIVE_LINK.findall(text):
        path = target.split("#", 1)[0].split("?", 1)[0]
        if not path:
            continue  # a bare anchor points inside this file
        candidate = Path(path)
        # An absolute target is not repository navigation. Checking only that it
        # exists would pass /etc/hosts on the Ubuntu runner, and joining it would
        # discard the source directory entirely, because pathlib lets an absolute
        # right operand replace the left one.
        if candidate.is_absolute() or candidate.drive or candidate.root:
            failures.append(f"{rel}: relative link {target} is not a repository path")
            continue
        resolved = ((root / rel).parent / candidate).resolve()
        # ../ can climb out of the tree, where an unrelated file that happens to
        # exist would otherwise satisfy the check.
        if resolved != root and root not in resolved.parents:
            failures.append(f"{rel}: relative link {target} leaves the repository")
            continue
        if not resolved.exists():
            failures.append(f"{rel}: relative link {target} does not exist")
    return failures


def main() -> int:
    failures: list[str] = []
    sources: dict[str, str] = {}
    for rel in FILES:
        sources[rel] = (ROOT / rel).read_text(encoding="utf-8")
        failures.extend(relative_link_failures(rel, sources[rel]))
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

    resolved = 0
    accepted_denials = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = {
            url: executor.submit(fetch_final_url, url)
            for url in urls
            if not url.startswith(("http:", "https://img.shields.io/badge/"))
        }
        try:
            for url, src in sorted(urls.items()):
                if url.startswith("http:"):
                    failures.append(f"{src}: insecure link {url}")
                    continue
                # Badge URLs encode label text, not a resource that can 404 meaningfully.
                if url.startswith("https://img.shields.io/badge/"):
                    continue
                try:
                    status, final = pending[url].result()
                except urllib.error.HTTPError as exc:
                    if is_accepted_automation_denial(url, exc.code):
                        accepted_denials += 1
                        print(
                            f"accepted automation denial {url} -> HTTP {exc.code} "
                            "(exact LinkedIn identity URL; automated requests are blocked)"
                        )
                    else:
                        failures.append(f"{src}: {url} -> HTTP {exc.code}")
                    continue
                except Exception as exc:  # noqa: BLE001 - report every failure mode
                    failures.append(f"{src}: {url} -> {exc}")
                    continue
                if not 200 <= status < 300:
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
                resolved += 1
                print(f"ok {url}")

        finally:
            # Cancel queued reads if reporting or waiting is interrupted.
            for future in pending.values():
                future.cancel()

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    file_label = "file" if len(sources) == 1 else "files"
    print(
        f"\nchecks passed across {len(sources)} {file_label}: "
        f"resolved links: {resolved}; accepted automation denials: {accepted_denials} "
        "(resolution unverified)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

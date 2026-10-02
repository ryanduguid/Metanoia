"""Policy tests for profile URL extraction, profile copies and automation denials."""

from __future__ import annotations

import contextlib
import email.message
import email.utils
import io
import tempfile
import unittest
import urllib.error
import urllib.response
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import check_links

GOOD_LLMS = "".join(
    f"- **{name}** (https://github.com/ryanduguid/{location}): component\n"
    for name, location in check_links.LLMS_COMPONENTS.items()
)

# The profile's published Markdown format and current component labels.
MARKDOWN_LLMS = """\
- [aus-accounting-mcp](https://github.com/ryanduguid/australian-accounting/tree/main/apps/aus-accounting-mcp): server
- [payday-super-checker](https://github.com/ryanduguid/australian-accounting/tree/main/packages/payday-super-checker): timelines
- [ato-benchmark-compare](https://github.com/ryanduguid/australian-accounting/tree/main/packages/ato-benchmark-compare): benchmarks
- [TheExchequerTally](https://github.com/ryanduguid/australian-accounting/tree/main/packages/the-exchequer-tally): company tax
- [SolomonsSword](https://github.com/ryanduguid/australian-accounting/tree/main/packages/solomons-sword): trust income
- [xero-trial-balance-export](https://github.com/ryanduguid/accounting-review-pipeline/tree/main/packages/xero-trial-balance-export): exports
- [Monthly Close Controls](https://github.com/ryanduguid/accounting-review-pipeline/tree/main/packages/monthly-close-control-plane): close checks
- [Workpaper Review Gate](https://github.com/ryanduguid/accounting-review-pipeline/tree/main/packages/review-ready-gate): pack checks
- [Xero Ledger Review Gate](https://github.com/ryanduguid/accounting-review-pipeline/tree/main/packages/elizabeth-anne-alexander): synthetic review
- [accounting-excel-toolkit](https://github.com/ryanduguid/accounting-review-pipeline/tree/main/adapters/accounting-excel-toolkit): Excel
- [Australian Accounting Power BI](https://github.com/ryanduguid/accounting-review-pipeline/tree/main/apps/australian-accounting-power-bi): analytics
- [australian-accounting-skills](https://github.com/ryanduguid/australian-accounting-skills): skills
"""


def profile(**files: str):
    """Patch the profile reads with fixed text; missing names raise like a 404."""

    def fetch(name: str) -> str:
        if name not in files:
            raise urllib.error.HTTPError(check_links.PROFILE_RAW + name, 404, "Not Found", {}, None)
        return files[name]

    return patch.object(check_links, "fetch_profile_file", fetch)


class RedirectFixture(urllib.request.HTTPSHandler):
    """Return HTTPS responses in memory; never connect to a server."""
    def __init__(self, loop: bool = False):
        super().__init__()
        self.loop = loop
        self.start_reads = 0
        self.final_reads = 0
        self.bodies: list[io.BytesIO] = []

    def https_open(self, request):
        headers = email.message.Message()
        if request.full_url == "https://example.test/start":
            self.start_reads += 1
            headers["Location"] = "/start" if self.loop else "/final"
            code = 302
        elif request.full_url == "https://example.test/final" and not self.loop:
            self.final_reads += 1
            code = 503 if self.final_reads < 5 else 200
        else:
            raise AssertionError("unexpected fixture URL")
        body = io.BytesIO(b"fixture")
        self.bodies.append(body)
        response = urllib.response.addinfourl(body, headers, request.full_url, code)
        response.msg = "Fixture"
        return response


class RedirectPolicyTests(unittest.TestCase):
    def test_proxy_retries_remain_https_with_fresh_requests(self) -> None:
        class ProxyFixture(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
            def __init__(self):
                super().__init__()
                self.calls = []

            def reply(self, request, protocol):
                self.calls.append((protocol, request.type, request.host, request.selector,
                                   request._tunnel_host, request.get_header("Authorization")))
                if len(self.calls) < 3:
                    raise urllib.error.URLError("fixture transport failure")
                response = urllib.response.addinfourl(
                    io.BytesIO(b"fixture"), email.message.Message(), request.full_url, 200
                )
                response.msg = "Fixture"
                return response

            def https_open(self, request):
                return self.reply(request, "https")

            def http_open(self, request):
                return self.reply(request, "http")

        fixture = ProxyFixture()
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"https": "http://proxy.test:3128"}),
            fixture, check_links._HttpsRedirectHandler(),
        )
        request = urllib.request.Request(
            "https://example.test/source", headers={"Authorization": "Bearer synthetic-value"}
        )
        with (
            patch.object(check_links, "_URL_OPENER", opener),
            patch("urllib.request.proxy_bypass", return_value=False),
            patch("time.sleep"),
        ):
            self.assertEqual(check_links._request_url(request, lambda response: response.status), 200)
        self.assertEqual(fixture.calls, [
            ("https", "https", "proxy.test:3128", "/source", "example.test", "Bearer synthetic-value")
        ] * 3)
        self.assertEqual(request.type, "https")
        self.assertEqual(request.host, "example.test")
        self.assertIsNone(request._tunnel_host)

    def test_redirect_body_failures_close_before_retrying(self) -> None:
        for status in (301, 302, 303, 307, 308):
            handler = check_links._HttpsRedirectHandler()
            parent = MagicMock()
            handler.add_parent(parent)
            request = urllib.request.Request("https://example.test/start")
            request.timeout = 30
            body = MagicMock()
            body.read.side_effect = TimeoutError("fixture redirect body timeout")
            headers = email.message.Message()
            headers["Location"] = "/next"
            with self.subTest(status=status), self.assertRaises(TimeoutError):
                getattr(handler, f"http_error_{status}")(request, body, status, "Found", headers)
            body.close.assert_called()
            parent.open.assert_not_called()

    def test_malformed_redirect_location_closes_its_response(self) -> None:
        handler = check_links._HttpsRedirectHandler()
        parent = MagicMock()
        handler.add_parent(parent)
        body = MagicMock()
        headers = email.message.Message()
        headers["Location"] = "https://[broken/"
        with self.assertRaises(ValueError):
            handler.http_error_302(
                urllib.request.Request("https://example.test/start"), body, 302, "Found", headers
            )
        body.close.assert_called()
        parent.open.assert_not_called()

    def test_redirected_transient_failure_can_reach_the_fifth_attempt(self) -> None:
        fixture = RedirectFixture()
        opener = urllib.request.build_opener(fixture, check_links._HttpsRedirectHandler())
        with patch.object(check_links, "_URL_OPENER", opener), patch("time.sleep") as sleep:
            self.assertEqual(check_links.fetch_final_url("https://example.test/start"),
                             (200, "https://example.test/final"))
        self.assertEqual(fixture.start_reads, 5)
        self.assertEqual(fixture.final_reads, 5)
        self.assertEqual(sleep.call_args_list, [call(1), call(2), call(4), call(8)])
        self.assertTrue(all(body.closed for body in fixture.bodies))

    def test_redirect_loops_remain_refused_without_retrying(self) -> None:
        fixture = RedirectFixture(loop=True)
        opener = urllib.request.build_opener(fixture, check_links._HttpsRedirectHandler())
        with (
            patch.object(check_links, "_URL_OPENER", opener),
            patch("time.sleep") as sleep,
            self.assertRaises(urllib.error.HTTPError) as raised,
        ):
            check_links.fetch_final_url("https://example.test/start")
        self.assertEqual(raised.exception.code, 302)
        self.assertEqual(fixture.start_reads, 5)
        sleep.assert_not_called()
        self.assertTrue(all(body.closed for body in fixture.bodies))

    def test_non_https_and_malformed_initial_urls_never_open_or_sleep(self) -> None:
        for url in (
            "http://example.test/", "ftp://example.test/file", "file:///tmp/example",
            "https:///missing-host", "https://example.test:invalid/",
        ):
            with (
                self.subTest(url=url),
                patch.object(check_links._URL_OPENER, "open") as opener,
                patch("time.sleep") as sleep,
                self.assertRaises(ValueError),
            ):
                check_links.fetch_final_url(url)
            opener.assert_not_called()
            sleep.assert_not_called()

    def test_https_origin_normalises_case_and_default_port(self) -> None:
        self.assertEqual(
            check_links._https_origin("HTTPS://EXAMPLE.TEST/start"),
            check_links._https_origin("https://example.test:443/next"),
        )
        self.assertNotEqual(
            check_links._https_origin("https://example.test:0/"),
            check_links._https_origin("https://example.test/"),
        )

    def test_only_valid_https_redirects_are_opened(self) -> None:
        for status in (301, 302, 303, 307, 308):
            for target, allowed in (
                ("https://example.test/next", True), ("https://other.test/next", True),
                ("/next", True), ("http://example.test/next", False),
                ("ftp://example.test/next", False), ("file:///tmp/example", False),
                ("https://example.test:invalid/next", False),
            ):
                handler = check_links._HttpsRedirectHandler()
                parent = MagicMock()
                handler.add_parent(parent)
                body = io.BytesIO(b"redirect")
                headers = email.message.Message()
                headers["Location"] = target
                request = urllib.request.Request("https://example.test/start")
                request.timeout = 30
                with self.subTest(status=status, target=target):
                    try:
                        if allowed:
                            result = handler.http_error_302(request, body, status, "Found", headers)
                            self.assertIs(result, parent.open.return_value)
                            redirected = parent.open.call_args.args[0]
                            self.assertEqual(redirected.full_url,
                                             "https://example.test/next" if target == "/next" else target)
                            self.assertTrue(body.closed)
                        else:
                            with self.assertRaises(urllib.error.HTTPError) as raised:
                                handler.http_error_302(request, body, status, "Found", headers)
                            self.assertEqual(raised.exception.code, status)
                            raised.exception.close()
                            parent.open.assert_not_called()
                    finally:
                        body.close()

    def test_authorization_stays_only_on_the_same_https_origin(self) -> None:
        for target, retained in (
            ("https://example.test/next", True), ("https://EXAMPLE.TEST:443/next", True),
            ("https://other.test/next", False), ("https://example.test:444/next", False),
            ("https://example.test:0/next", False),
        ):
            request = urllib.request.Request(
                "https://example.test/start",
                headers={"Authorization": "Bearer synthetic-value", "User-Agent": "fixture"},
            )
            with self.subTest(target=target):
                redirected = check_links._HttpsRedirectHandler().redirect_request(
                    request, None, 302, "Found", {}, target
                )
                self.assertEqual(redirected.get_header("Authorization"),
                                 "Bearer synthetic-value" if retained else None)
                self.assertEqual(redirected.get_header("User-agent"), "fixture")
                self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-value")

    def test_authorization_is_not_restored_when_redirects_return_to_origin(self) -> None:
        handler = check_links._HttpsRedirectHandler()
        original = urllib.request.Request(
            "https://example.test/start", headers={"Authorization": "Bearer synthetic-value"}
        )
        other = handler.redirect_request(original, None, 302, "Found", {}, "https://other.test/")
        returned = handler.redirect_request(other, None, 302, "Found", {}, "https://example.test/")
        self.assertFalse(other.has_header("Authorization"))
        self.assertFalse(returned.has_header("Authorization"))

    def test_blocked_redirect_closes_and_does_not_retry(self) -> None:
        body = io.BytesIO(b"redirect")
        error = urllib.error.HTTPError("http://example.test/", 302, "Blocked", {}, body)
        with (
            patch.object(check_links._URL_OPENER, "open", side_effect=error) as opener,
            patch("time.sleep") as sleep,
            self.assertRaises(urllib.error.HTTPError) as raised,
        ):
            check_links.fetch_final_url("https://example.test/")
        self.assertIs(raised.exception, error)
        opener.assert_called_once()
        sleep.assert_not_called()
        self.assertTrue(body.closed)


class RetryTests(unittest.TestCase):
    def test_profile_body_failure_retries_and_closes_responses(self) -> None:
        for error in (TimeoutError("body timeout"), urllib.error.URLError("body unavailable")):
            failed, successful = self.response(), self.response()
            failed.__enter__.return_value.read.side_effect = error
            with (
                self.subTest(error=error),
                # Dummy token tests header preservation; this is not a credential.
                patch.dict(check_links.os.environ, {"GITHUB_TOKEN": "synthetic-value"}),  # nosec B105
                patch.object(
                    check_links._URL_OPENER, "open", side_effect=[failed, successful]
                ) as opener,
                patch("time.sleep") as sleep,
            ):
                self.assertEqual(self.fetch(True), "profile text")
            self.assertEqual(opener.call_count, 2)
            sleep.assert_called_once_with(1)
            failed.__exit__.assert_called_once()
            successful.__exit__.assert_called_once()
            first, second = (item.args[0] for item in opener.call_args_list)
            self.assertIsNot(first, second)
            self.assertEqual(first.full_url, second.full_url)
            self.assertEqual(first.header_items(), second.header_items())
            self.assertEqual(first.get_method(), "GET")
            self.assertEqual(first.get_header("User-agent"), check_links.USER_AGENT)
            self.assertEqual(first.get_header("Authorization"), "Bearer synthetic-value")

    def test_profile_body_exhaustion_shares_the_attempt_and_wait_budget(self) -> None:
        for error_type in (TimeoutError, urllib.error.URLError):
            responses = [self.response() for _ in range(5)]
            errors = [error_type(f"body failure {attempt}") for attempt in range(5)]
            for response, error in zip(responses, errors):
                response.__enter__.return_value.read.side_effect = error
            with (
                self.subTest(error_type=error_type),
                patch.object(
                    check_links._URL_OPENER, "open", side_effect=responses
                ) as opener,
                patch("time.sleep") as sleep,
                self.assertRaises(error_type) as raised,
            ):
                self.fetch(True)
            self.assertIs(raised.exception, errors[-1])
            self.assertEqual(opener.call_count, 5)
            self.assertEqual(sleep.call_args_list, [call(1), call(2), call(4), call(8)])
            for response in responses:
                response.__exit__.assert_called_once()

    def test_responses_close_and_requests_keep_their_headers(self) -> None:
        for profile_file in (False, True):
            body = io.BytesIO(b"unavailable")
            error = urllib.error.HTTPError("https://example.test", 503, "Wait", {}, body)
            response = self.response()
            with (
                # Dummy token tests header preservation; this is not a credential.
                patch.dict(check_links.os.environ, {"GITHUB_TOKEN": "synthetic-value"}),  # nosec B105
                patch.object(
                    check_links._URL_OPENER, "open", side_effect=[error, response]
                ) as opener,
                patch("time.sleep"),
            ):
                self.fetch(profile_file)
            self.assertTrue(body.closed)
            response.__exit__.assert_called_once()
            first, second = (item.args[0] for item in opener.call_args_list)
            self.assertIsNot(first, second)
            self.assertEqual(first.full_url, second.full_url)
            self.assertEqual(first.header_items(), second.header_items())
            self.assertEqual(first.get_method(), "GET")
            self.assertEqual(first.get_header("User-agent"), check_links.USER_AGENT)
            self.assertEqual(
                first.get_header("Authorization"),
                "Bearer synthetic-value" if profile_file else None,
            )
        response = self.response()
        response.__enter__.return_value.read.return_value = b"\xff"
        with (
            patch.object(check_links._URL_OPENER, "open", return_value=response) as opener,
            patch("time.sleep") as sleep,
            self.assertRaises(UnicodeDecodeError),
        ):
            self.fetch(True)
        self.assertEqual(opener.call_count, 1)
        sleep.assert_not_called()
        response.__exit__.assert_called_once()

    def test_http_exhaustion_closes_each_error(self) -> None:
        for status, attempts in ((403, 1), (504, 5), (999, 1)):
            bodies = [io.BytesIO(b"error") for _ in range(attempts)]
            errors = [
                urllib.error.HTTPError("https://example.test", status, "Error", {}, body)
                for body in bodies
            ]
            with (
                patch.object(check_links._URL_OPENER, "open", side_effect=errors) as opener,
                patch("time.sleep"),
                self.assertRaises(urllib.error.HTTPError) as raised,
            ):
                self.fetch(False)
            self.assertEqual(opener.call_count, attempts)
            self.assertIs(raised.exception, errors[-1])
            self.assertEqual(raised.exception.code, status)
            self.assertTrue(all(body.closed for body in bodies))

    def fetch(self, profile_file: bool) -> object:
        if profile_file:
            return check_links.fetch_profile_file("FORKS.md")
        return check_links.fetch_final_url("https://example.test/page")

    def response(self) -> MagicMock:
        response = MagicMock()
        response.__enter__.return_value.status = 200
        response.__enter__.return_value.geturl.return_value = "https://example.test/final"
        response.__enter__.return_value.read.return_value = b"profile text"
        return response

    def test_transient_failures_wait_before_retrying_both_reads(self) -> None:
        for profile_file in (False, True):
            for error in (
                urllib.error.HTTPError("https://example.test", 503, "Unavailable", {}, None),
                urllib.error.HTTPError("https://example.test", 504, "Timeout", {}, None),
                urllib.error.URLError("temporary transport failure"),
                TimeoutError("temporary timeout"),
            ):
                with (
                    self.subTest(profile_file=profile_file, error=error),
                    patch.object(
                        check_links._URL_OPENER, "open",
                        side_effect=[error, error, self.response()],
                    ) as opener,
                    patch("time.sleep") as sleep,
                ):
                    result = self.fetch(profile_file)
                self.assertEqual(opener.call_count, 3)
                self.assertEqual(sleep.call_args_list, [call(1), call(2)])
                self.assertEqual(
                    result,
                    "profile text" if profile_file else (200, "https://example.test/final"),
                )

    def test_permanent_errors_do_not_retry(self) -> None:
        for profile_file in (False, True):
            for status in (401, 403, 404, 999):
                error = urllib.error.HTTPError("https://example.test", status, "Denied", {}, None)
                with (
                    self.subTest(profile_file=profile_file, status=status),
                    patch.object(
                        check_links._URL_OPENER, "open", side_effect=error
                    ) as opener,
                    patch("time.sleep") as sleep,
                    self.assertRaises(urllib.error.HTTPError) as raised,
                ):
                    self.fetch(profile_file)
                self.assertIs(raised.exception, error)
                self.assertEqual(opener.call_count, 1)
                sleep.assert_not_called()

    def test_exhaustion_preserves_the_failure_and_bounds_waits(self) -> None:
        for profile_file in (False, True):
            for error in (
                urllib.error.HTTPError("https://example.test", 503, "Unavailable", {}, None),
                urllib.error.URLError("still unavailable"),
                TimeoutError("still unavailable"),
            ):
                with (
                    self.subTest(profile_file=profile_file, error=error),
                    patch.object(
                        check_links._URL_OPENER, "open", side_effect=error
                    ) as opener,
                    patch("time.sleep") as sleep,
                    self.assertRaises(type(error)) as raised,
                ):
                    self.fetch(profile_file)
                self.assertIs(raised.exception, error)
                self.assertEqual(opener.call_count, 5)
                self.assertEqual(sleep.call_args_list, [call(1), call(2), call(4), call(8)])

    def test_retry_after_and_wait_budget(self) -> None:
        now = 1_700_000_000
        for profile_file in (False, True):
            for status in (429, 503):
                for header, delay in (
                    ("2", 2),
                    (email.utils.formatdate(now + 3, usegmt=True), 3),
                    ("invalid", 1),
                    ("-1", 1),
                    ("3600", None),
                ):
                    headers = email.message.Message()
                    headers["Retry-After"] = header
                    error = urllib.error.HTTPError(
                        "https://example.test", status, "Wait", headers, None
                    )
                    with (
                        self.subTest(profile_file=profile_file, status=status, header=header),
                        patch.object(
                            check_links._URL_OPENER, "open",
                            side_effect=[error, self.response()],
                        ) as opener,
                        patch("time.sleep") as sleep,
                        patch("time.time", return_value=now),
                    ):
                        if delay is None:
                            with self.assertRaises(urllib.error.HTTPError):
                                self.fetch(profile_file)
                            self.assertEqual(opener.call_count, 1)
                            sleep.assert_not_called()
                        else:
                            self.fetch(profile_file)
                            self.assertEqual(opener.call_count, 2)
                            sleep.assert_called_once_with(delay)
            headers = email.message.Message()
            headers["Retry-After"] = "20"
            error = urllib.error.HTTPError("https://example.test", 429, "Wait", headers, None)
            with (
                patch.object(check_links._URL_OPENER, "open", side_effect=error) as opener,
                patch("time.sleep") as sleep,
                self.assertRaises(urllib.error.HTTPError),
            ):
                self.fetch(profile_file)
            self.assertEqual(opener.call_count, 2)
            sleep.assert_called_once_with(20)


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
        self.assertIn("accepted automation denials: 0", output.getvalue())

    def test_accepted_denials_are_counted_separately_from_resolved_links(self) -> None:
        linkedin = check_links.LINKEDIN_IDENTITY_URL
        for include_success in (False, True):
            with self.subTest(include_success=include_success):
                text = f"{linkedin}\n{linkedin}\n"
                if include_success:
                    text += "https://example.test/verified\n"

                def resolve(url: str) -> tuple[int, str]:
                    if url == linkedin:
                        raise urllib.error.HTTPError(url, 999, "Denied", {}, None)
                    return 200, url

                output = io.StringIO()
                with (
                    patch.object(check_links, "FILES", []),
                    patch.object(check_links, "PROFILE_FILES", ["FORKS.md"]),
                    profile(**{"FORKS.md": text}),
                    patch.object(check_links, "fetch_final_url", side_effect=resolve) as fetch,
                    contextlib.redirect_stdout(output),
                ):
                    self.assertEqual(check_links.main(), 0)
                self.assertEqual(fetch.call_count, 1 + int(include_success))
                self.assertIn(
                    f"resolved links: {int(include_success)}; accepted automation denials: 1",
                    output.getvalue(),
                )
                self.assertIn("resolution unverified", output.getvalue())
                self.assertNotIn(f"ok {linkedin}", output.getvalue())

    def test_accepted_denials_do_not_hide_failures(self) -> None:
        linkedin = check_links.LINKEDIN_IDENTITY_URL
        broken = "https://example.test/broken"
        renamed = "https://github.com/ryanduguid/old-name"
        cases = [
            (broken, urllib.error.HTTPError(broken, 999, "Denied", {}, None), "HTTP 999"),
            (linkedin, urllib.error.HTTPError(linkedin, 404, "Not Found", {}, None), "HTTP 404"),
            (broken, urllib.error.URLError("no network"), "no network"),
            (renamed, (200, "https://github.com/ryanduguid/new-name"), "rename redirect"),
            (broken, (199, broken), "HTTP 199"),
            (broken, (302, broken), "HTTP 302"),
        ]
        for url, outcome, message in cases:
            with self.subTest(message=message):
                def resolve(target: str) -> tuple[int, str]:
                    if target == url:
                        if isinstance(outcome, Exception):
                            raise outcome
                        return outcome
                    raise urllib.error.HTTPError(target, 999, "Denied", {}, None)

                output = io.StringIO()
                with (
                    patch.object(check_links, "FILES", []),
                    patch.object(check_links, "PROFILE_FILES", ["FORKS.md"]),
                    profile(**{"FORKS.md": f"{linkedin}\n{url}\n"}),
                    patch.object(check_links, "fetch_final_url", side_effect=resolve),
                    contextlib.redirect_stdout(output),
                ):
                    self.assertEqual(check_links.main(), 1)
                self.assertIn(message, output.getvalue())
                self.assertNotIn("checks passed", output.getvalue())
                self.assertNotIn("all clear", output.getvalue())
                self.assertNotIn(f"ok {url}", output.getvalue())

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

        stale = (
            "- **payday-super-checker** (https://github.com/ryanduguid/payday-super-checker): old\n"
            + GOOD_LLMS
        )
        self.assertEqual(len(check_links.llms_index_failures(stale)), 1)

        with_site_page = (
            "- **payday-super-checker** (https://duguid.com.au/tools/payday-super/): explainer\n"
            + GOOD_LLMS
        )
        self.assertEqual(check_links.llms_index_failures(with_site_page), [])

    def test_normalises_markdown_code_span_url(self) -> None:
        self.assertEqual(
            check_links.normalise_url("https://duguid.com.au/`"),
            "https://duguid.com.au/",
        )

    def test_published_markdown_index_preserves_component_validation(self) -> None:
        self.assertEqual(check_links.llms_index_failures(MARKDOWN_LLMS), [])
        missing = MARKDOWN_LLMS.replace(
            "- [aus-accounting-mcp](https://github.com/ryanduguid/australian-accounting/tree/main/apps/aus-accounting-mcp): server\n",
            "",
        )
        moved = MARKDOWN_LLMS.replace(
            "australian-accounting/tree/main/packages/payday-super-checker",
            "payday-super-checker",
        )
        duplicate = MARKDOWN_LLMS + (
            "- [payday-super-checker](https://github.com/ryanduguid/payday-super-checker): stale\n"
        )
        for text in (missing, moved, duplicate):
            with self.subTest(text=text):
                self.assertEqual(len(check_links.llms_index_failures(text)), 1)

    def test_accepts_only_the_linkedin_identity_automation_denial(self) -> None:
        linkedin = "https://www.linkedin.com/in/ryan-duguid/"

        self.assertTrue(check_links.is_accepted_automation_denial(linkedin, 999))
        self.assertFalse(check_links.is_accepted_automation_denial(linkedin, 404))
        self.assertFalse(
            check_links.is_accepted_automation_denial(
                "https://www.linkedin.com/in/someone-else/", 999
            )
        )

    def test_relative_markdown_targets_are_validated(self) -> None:
        # LINK_RES captures only http(s) URLs, so a misspelt local target used to
        # pass while repository navigation was broken.
        text = (
            "See [the runbook](docs/runbok.md), [security](SECURITY.md), "
            "[a section](#heading), [mail](mailto:a@example.com) and "
            "[remote](https://example.com/x)."
        )
        self.assertEqual(
            check_links.relative_link_failures("README.md", text),
            ["README.md: relative link docs/runbok.md does not exist"],
        )

    def test_every_tracked_relative_link_resolves(self) -> None:
        failures: list[str] = []
        for rel in check_links.FILES:
            text = (check_links.ROOT / rel).read_text(encoding="utf-8")
            failures.extend(check_links.relative_link_failures(rel, text))
        self.assertEqual(failures, [])

    def test_a_target_outside_the_repository_is_refused(self) -> None:
        # Joining an absolute target discards the source directory, and ../ can
        # climb out of the tree. Either way an unrelated file that happens to
        # exist on the runner would otherwise satisfy the check: /etc/hosts is
        # present on the Ubuntu runner CI uses.
        for target, expected in [
            ("/etc/hosts", "is not a repository path"),
            ("/", "is not a repository path"),
            ("../outside.md", "leaves the repository"),
            ("../../elsewhere/README.md", "leaves the repository"),
        ]:
            with self.subTest(target=target):
                failures = check_links.relative_link_failures(
                    "README.md", "[x](%s)" % target
                )
                self.assertEqual(len(failures), 1, failures)
                self.assertIn(expected, failures[0])


if __name__ == "__main__":
    unittest.main()

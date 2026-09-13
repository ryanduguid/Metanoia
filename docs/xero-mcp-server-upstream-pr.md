# Prepared upstream pull request: XeroAPI/xero-mcp-server

Status on 6 September 2026: opened as
[XeroAPI/xero-mcp-server#305](https://github.com/XeroAPI/xero-mcp-server/pull/305)
from branch `fix/ensure-error-token-leak`, the fork commit rebased onto
upstream `main` at `f24583c`. Verified before opening: the 2 credential
cases fail against the unchanged `ensureError` and pass with the fix, the
full `vitest` suite passes (18 tests) and `npm run lint` is clean. The record
below is the state before it was opened.

Status on 4 September 2026: not yet opened. Upstream `main` still carries an
`ensureError` that serialises any non-`Error` thrown value straight into the
message, and no open or merged upstream pull request touches
`src/helpers/ensure-error.ts`. Upstream #173 (merged 26 May 2026) fixed the
same class of leak in `formatError` only.

The change already exists on the fork as
[ryanduguid/xero-mcp-server#1](https://github.com/ryanduguid/xero-mcp-server/pull/1),
commit `db241e5cd665544914c3ec34c2c025e645e1bcc3` (2 files:
`src/helpers/ensure-error.ts` and `src/helpers/__tests__/ensure-error.test.ts`).

## How to open it

1. Sync the fork's `main` with upstream, then rebase the fork commit onto it on
   a branch such as `fix/ensure-error-token-leak`. Re-run the upstream test
   suite on that branch and confirm both new cases still fail against the
   upstream implementation and pass against the fix.
2. Open the pull request against `XeroAPI/xero-mcp-server:main` from that
   branch with the title and body below.
3. Update the profile repository's `FORKS.md` with the upstream PR number and move the fork row to
   tracking only once it merges.

## Title

```text
fix: stop ensureError leaking bearer tokens into tool responses
```

## Body

```markdown
## Problem

`ensureError` wraps any non-`Error` thrown value by calling `JSON.stringify` on
it and placing the result in the new error's message. The xero-node SDK rejects
failed requests with a plain object that carries the caller's bearer token at
`request.headers.authorization`. All of the tool handlers put `err.message`
directly into the text returned to the model, so a failed Xero call could
surface the access token in a transcript.

#173 closed the same hole in `formatError`, which already whitelists the fields
it extracts and documents this hazard. `ensureError` still serialises the raw
value.

## Fix

`ensureError` now delegates its message to `formatError` instead of
stringifying the thrown value, so a non-`Error` rejection produces the same
redacted message the SDK-error path already produces.

## Tests

Adds regression coverage in `src/helpers/__tests__/ensure-error.test.ts`
asserting the token is absent from the resulting message for both a
xero-node style rejection object and an arbitrary object. Both cases fail
against the previous implementation and pass with this change.

## Notes

No tool behaviour changes for callers that throw `Error` instances. No new
dependencies. The fix was developed and tested on a fork; the commit is
rebased onto current `main` here.
```

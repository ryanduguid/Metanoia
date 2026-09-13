# Odoo decision

Proposal, 5 September 2026. The owner decides; nothing here archives, closes,
merges or publishes anything. It settles the "After the Odoo decision" rows in
[FORKS.md](https://github.com/ryanduguid/ryanduguid/blob/main/FORKS.md): the forks of OCA `l10n-australia`, `account-reconcile`
and `account-financial-reporting`, plus the already archived
`bank-statement-import`.

## What was read

Read on 5 September 2026 from the rendered GitHub pages, the fork clones, the
Odoo 18.0 `base_vat` source on GitHub, a local python-stdnum 2.2 check, and
the website, its `llms.txt` and this profile searched for "Odoo".

| Source | State |
| --- | --- |
| [OCA/l10n-australia](https://github.com/OCA/l10n-australia), branches 18.0 and 19.0 | One commit each, the OCA repository scaffold of 23 July 2026. No addons, no addons table, 0 open issues, 0 stars, 1 fork (ours). |
| [OCA/l10n-australia#1](https://github.com/OCA/l10n-australia/pull/1) | The only open pull request: `[18.0][ADD] l10n_au_base: ABN checksum/format and 30 June income year`, opened 31 August 2026 by ryanduguid, two commits, 19 files, AGPL-3, depends on `account`. Pre-commit and test checks green. No review as at 5 September; the author asked for a maintainer view on scope and fit on 1 September. Its head branch is `cursor/18.0-l10n-au-base-3c18` on the `ryanduguid/l10n-australia` fork. |
| [OCA/account-reconcile](https://github.com/OCA/account-reconcile), branch 18.0 | 18 modules. 11 open issues, two on 18.0: [#956](https://github.com/OCA/account-reconcile/issues/956) (`account_reconcile_oca`, a `LazyGettext` value is not JSON serialisable in `_get_manual_reconcile_vals`; the reporter's fix is `str()` around it; labelled stale, no pull request) and [#726](https://github.com/OCA/account-reconcile/issues/726) (the 18.0 migration tracker). The other nine are 16.0, 19.0 or unversioned reconciliation bugs. |
| The three unarchived forks | `l10n-australia`: the scaffold plus the pull request branch above. `account-reconcile` and `account-financial-reporting`: OCA 18.0 history and bot post-merge commits only, no Australian change. |

## Do the engines answer an open issue

| Engine | Open issue it would answer | Finding |
| --- | --- | --- |
| Payday Super receipt timing (`payday-super-checker`) | None. `l10n-australia` has no issues; no `account-reconcile` issue concerns superannuation or payroll. | Odoo payroll for Australia is outside the OCA repositories read here, so there is no OCA surface for fund-receipt dates. |
| Xero trial balance import (`xero-trial-balance-export`) | None. `account_move_base_import` imports payment files as journal entries; no open issue asks for a trial balance import. | No match. |
| ABN validation (`Fx_ValidateABN` in the Power BI project) | None. | Odoo core already validates an Australian number: `base_vat` falls back to `python-stdnum` for `au`, which resolves to `stdnum.au.abn` (checked with python-stdnum 2.2 against the reference `83 914 571 673`). `l10n_au_base` re-implements the same modulus 89 weighting in Python and its income-year helper wraps the company fiscal-year fields Odoo already has. |

No engine answers an open OCA issue on 18.0. The one module that exists
repeats or wraps core behaviour rather than carrying an engine into Odoo.

## Option A: ship one real module

Carry `l10n_au_base` through OCA review and maintain it.

- Work: answer the review when it comes, then migrate the module for every
  Odoo series (19.0 is already open and empty). OCA review needs a member with
  write access on the repository. The only commit there is the OCA bot's and
  who holds write access is not verified here, so the review wait has no
  visible bound.
- Keeps the `l10n-australia` fork alive as the pull request head. It gives
  `account-reconcile` and `account-financial-reporting` no purpose; they would
  be archived regardless.
- Licence: the module is AGPL-3 under OCA rules, while the engines are MIT.
  FORKS.md already forbids copying fork code into the originals without an
  attribution and licence check, so the module and the engines stay separate
  codebases with the same algorithm in two languages.
- Value: a foundation module in an empty repository, used by nothing in the
  portfolio and by no Odoo user the evidence shows.

## Option B: archive the three, settling all four

Archive `l10n-australia`, `account-reconcile` and `account-financial-reporting`
in the GitHub UI; `bank-statement-import` is archived already.

- The open pull request comes first. Archiving the fork makes its head
  read-only, so the pull request could not be updated after a review. Either
  close it with a note that core `base_vat` and `python-stdnum` already cover
  the ABN checksum, or set a review deadline and close it then.
- `account-reconcile` and `account-financial-reporting` do not carry the pull
  request and can be archived at once. After that, the three FORKS.md rows
  move to the archived table.
- Nothing is deleted. An OCA contribution later starts from a fresh fork.

## Recommendation

Option B. Four reasons:

1. No open OCA issue is answered by an engine, and a six-week-old scaffold
   with no addons gives no evidence of demand either way.
2. The only candidate module repeats the ABN checksum that `base_vat` plus
   `python-stdnum` already run, and wraps the core fiscal-year fields.
3. The portfolio's users work in Xero, Excel and Power BI. Nothing on the
   website or the profile mentions Odoo, and adding an AGPL-3 line of work
   would need its own release, review and migration cadence.
4. Cost of B is one comment and three archive clicks. Cost of A is a
   maintenance commitment per Odoo series in a repository with no reviewers.

Suggested handling of the pull request: leave it open until 31 October 2026,
two months from opening. If a maintainer reviews it before then, answer the
review and decide again with that evidence. If not, close it with the note
above and archive the fork.

## Owner actions

1. Decide between A and B.
2. Under B: archive `account-reconcile` and `account-financial-reporting`
   now (Settings, Danger Zone, Archive this repository). Comment on and close
   OCA/l10n-australia#1, or set the deadline and close it then; archive
   `l10n-australia` only after the pull request is closed. Open a FORKS.md
   change moving each row to the archived table as it happens.
3. Under A: reply on the pull request, archive the other two, and move the
   `l10n-australia` row to "Keep, active contribution" in FORKS.md.

## Not verified here

Whether Odoo Australian payroll exists outside Odoo Enterprise, the OCA
contributor licence agreement, and who holds write access on
OCA/l10n-australia. The GitHub API was not reachable for OCA repositories from
this session; the OCA facts above come from the rendered pages and the clones.

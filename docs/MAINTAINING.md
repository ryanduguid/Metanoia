# Maintaining this profile

Metanoia contains the portfolio documentation, maintenance tools and original repository history for [@ryanduguid](https://github.com/ryanduguid). The separate `ryanduguid/ryanduguid` repository displays the public profile README. It is documentation only: there is no application to build or deploy.

The profile copy is edited in the profile repository; this repository's `README.md` only describes what Metanoia holds. The profile repository was recreated after the rename on 11 September 2026, so old issue, pull request and commit URLs must use `ryanduguid/Metanoia`. Reusing the old repository name removes GitHub's rename redirect.

The canonical website host is `https://duguid.com.au/`. Use that host for public website links in `README.md` and in the profile repository's `llms.txt`; do not publish the GitHub Pages deployment address as a competing canonical URL.

How to report a security concern is in [SECURITY.md](../SECURITY.md). Account-wide contribution, support and issue-form defaults live in [ryanduguid/.github](https://github.com/ryanduguid/.github), which has been public since 31 August 2026. Do not add a `CONTRIBUTING.md` here; it would override that default for this repository only.

## Files

| File | Role |
| --- | --- |
| `README.md` | What this repository holds and where the profile copy lives |
| `SECURITY.md` | Reporting policy for this documentation-only repository |
| `LICENSE` | CC BY 4.0 for the profile prose |
| `docs/MAINTAINING.md` | This runbook |
| `tools/check_links.py` | Link resolver behind `link-check.yml`; also checks the profile repository's published `FORKS.md` and `llms.txt` |
| `tools/test_*.py` | Unit tests for the link policy and repository identity |
| `.github/workflows/link-check.yml` | CI: unit tests, then resolves every link here and in the profile `FORKS.md` and `llms.txt` and fails on rename redirects, retired names, dashes and a profile `llms.txt` component that is not at its maintained directory (needs the read-only workflow token for the profile reads) |

## Updating the public README

The public README is edited in the profile repository, not here. Preserve its current layout: introduction and badges, Selected work and Background. Ryan removed the Setup section in ryanduguid/ryanduguid#33. Ryan rejected the worked-example opener and restored this layout. Keep the audience links and the link to the full website catalogue. Change the layout only when he asks for a redesign.

Ryan supplied and approved his Senior Accountant role at an advisory firm and Newcastle NSW location on 6 September 2026. That current owner assertion supersedes the older instruction to omit employment. It does not imply vendor affiliation, practitioner registration or regulatory endorsement. Change identity or credentials only on a newer owner assertion.

The credentials line is an assertion by the profile owner. Confirm it is current before changing or republishing it. Use **provisional member of Chartered Accountants ANZ**, not a vendor-style `CA ANZ` shorthand in prose.

Pins live only in the GitHub UI; the README has no pinned section. The pin record below must match the live list. Keep achievements hidden.

## Pinned repositories

Change pins in the GitHub UI (**Customize your pins**). After saving, check https://github.com/ryanduguid for the heading **Pinned** (not **Popular**).

The approved pin order for the proof-of-use pass is:

1. `accounting-review-pipeline`
2. `Ozzit`
3. `australian-accounting`
4. `australian-accounting-skills`
5. `llm-tax-guardrails`
6. `au-tax-legislation-corpus`

Verify the live order after saving. GitHub has previously failed to persist drag reordering; unpinning and re-ticking in the intended sequence is the fallback. Pins follow repository node IDs through renames. The profile README deliberately has no duplicate pin catalogue. Keep infrastructure and contribution forks out of the pins.

GitHub About on the 2 flagship repositories (description, homepage, topics) is applied from each repo's `docs/DISCOVERY.md` via `scripts/publish-github-about.sh`. Topics elsewhere are set directly through the API; the `apply-topics.ps1` script that used to live here covered only 6 repositories and has been removed.

## Claims that must be checked

| Claim | Source of truth |
| --- | --- |
| Identity, location and credentials | Profile-owner assertions. Confirm with the owner before changing or republishing them |
| Released and default-branch skill counts, plugins and installation | `australian-accounting-skills/README.md` and the skill inventory at the exact release or commit being described; keep release counts separate from unreleased work |
| Local MCP facade; uvx from PyPI; delegated engines; scoped Div 7A review; SBR synthetic | `australian-accounting/apps/aus-accounting-mcp/README.md` and its `DISCLAIMER.md` |
| Experimental payday-super review, possible SG-charge exposure and no ATO-assessment determination | `australian-accounting/packages/payday-super-checker/README.md` and its `paydaysuper/deadlines.py` |
| 133 native Excel LAMBDA functions plus 5 help tables, no add-ins or macros | `Ozzit/README.md` |
| Xero trial-balance export requires movement and year-to-date balance before writing | `accounting-review-pipeline/packages/xero-trial-balance-export/README.md`, the balance-check paragraph under Scope and disclaimer |
| Local profit-and-loss comparison against ATO benchmarks, with working shown | `australian-accounting/packages/ato-benchmark-compare/README.md`; do not imply ATO endorsement |
| Source-linked LLM operating guide for Australian accounting, tax and BAS work | `llm-tax-guardrails/README.md`; do not imply certification or endorsement |

## Style

- Australian English (`judgement`, `honouring`, `licence` in prose).
- No em dashes. [#7](https://github.com/ryanduguid/Metanoia/pull/7) and [#8](https://github.com/ryanduguid/Metanoia/pull/8) existed to take them out. List separators are a hyphen with spaces (` - `).
- Use only the current owner-approved employment wording recorded above; do not infer registration or endorsement from it.
- Do not add a visible LinkedIn link while the profile is inactive. [#16](https://github.com/ryanduguid/Metanoia/pull/16). That includes the GitHub social-account slot (`gh api user/social_accounts`), not only the README. The canonical website JSON-LD and `llms.txt` may identify the hibernated Australian profile at `https://www.linkedin.com/in/ryan-duguid/` solely to distinguish it from the US namesake's unhyphenated profile.
- Narrow provenance: original work versus forks. [#5](https://github.com/ryanduguid/Metanoia/pull/5), then [#18](https://github.com/ryanduguid/Metanoia/pull/18).
- Counts of skills and functions are part of the prose. Recheck them before publication. A renamed project (Nabla to Ozzit, [#14](https://github.com/ryanduguid/Metanoia/pull/14); CharlesHenryWickens back to payday-super-checker; JohnKenley to au-tax-mcp-server, since renamed aus-accounting-mcp) is a README change in the same breath as the repository rename.

## What stays off the profile

The index is accounting automation for Australian practice. Leave off:

- `DiogenesLamp`, a Yupoo catalogue viewer
- `claude-export`, a private settings snapshot (private repository, so a link would 404 for every visitor)
- `ryanduguid/.github`, account-level community health files (public since 31 August 2026, but infrastructure rather than a product)

Forks used only to send upstream pull requests stay out of the product list.

## Common mistakes

- Describing payday-super output as a compliance, liability or ATO determination. It is an experimental review aid with stated factual limits.
- Calling Ozzit macro-free while dropping the native-Excel or compatibility context from its own README.
- Saying the Xero exporter writes any trial balance. Both movement and year-to-date balances must reconcile before it writes the CSV.
- Conflating releases and default-branch work. Verify the inventory at the referenced tag or commit before stating a count; a larger inventory on the default branch does not change an earlier release.
- Treating mentions of Xero, the ATO, CA ANZ or SAP as proof of employment, partnership, approval, registration or endorsement.
- Using retired repository names (`CharlesHenryWickens`, `JohnKenley`, `JohnSpenceOgilvy`, `MaryAddisonHamilton`, `ElizabethAnneAlexander`, `RaymondChambers`, `RussellMathews`, `SirArthurFadden`, `SirAlexanderFitzgerald`, `EdwinNixon`, `LouisGoldberg`) in new copy.

CI runs `.github/workflows/link-check.yml`: every link in README.md, SECURITY.md, docs/ and the profile repository's published `FORKS.md` and `llms.txt` (read from `raw.githubusercontent.com`) must resolve, links must be https, a `github.com/ryanduguid/...` link that only works through a rename redirect fails the build, retired names and dashes fail it, and the profile `llms.txt` must name each component at the monorepo directory recorded in `tools/check_links.py`. A profile read that cannot complete fails the build.

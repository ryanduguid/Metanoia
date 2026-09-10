# Maintaining this profile

This repository is the GitHub profile README for [@ryanduguid](https://github.com/ryanduguid). It is documentation only: there is no application to build, test or deploy.

The canonical website host is `https://duguid.com.au/`. Use that host for public website links in `README.md` and `llms.txt`; do not publish the GitHub Pages deployment address as a competing canonical URL.

How to report a security concern is in [SECURITY.md](../SECURITY.md). Account-wide contribution, support and issue-form defaults live in [ryanduguid/.github](https://github.com/ryanduguid/.github), which has been public since 31 August 2026. Do not add a `CONTRIBUTING.md` here; it would override that default for this repository only.

## Files

| File | Role |
| --- | --- |
| `README.md` | Public profile at github.com/ryanduguid |
| `llms.txt` | Compact agent-facing index; keep it aligned with README |
| `SECURITY.md` | Reporting policy for this documentation-only repository |
| `LICENSE` | CC BY 4.0 for the profile prose |
| `docs/MAINTAINING.md` | This runbook |
| `tools/apply-topics.ps1` | Applies the topic sets to the public repositories via `gh repo edit` |
| `tools/banner.py` | Renders and gates the ASCII ledger banner system |
| `tools/banner_content.json` | Per-repository banner content; claims must match that repository's README |
| `tools/check_links.py` | Link resolver behind `link-check.yml` |
| `tools/test_*.py` | Unit tests for the banners, link policy and repository identity |
| `.github/workflows/link-check.yml` | CI: resolves profile links and fails on rename redirects and on links to archived repositories (needs the workflow token for the GitHub API lookups) |
| `.github/workflows/banner-check.yml` | CI: unit tests plus the rendered-banner gate |

## Updating the public README

The profile opens with a synthetic month-end example, followed by three routes for accountants, developers and evaluators. Keep the complete visible README below 250 words. Preserve credentials, accepted upstream links and the separate pending OCA status. Do not restore a news paragraph or an install command above the example. The full catalogue stays on the website.

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

GitHub About on the two flagship repositories (description, homepage, topics) is applied from each repo's `docs/DISCOVERY.md` via `scripts/publish-github-about.sh`.

## Claims that must be checked

| Claim | Source of truth |
| --- | --- |
| Identity, location and credentials | Profile-owner assertions. Confirm with the owner before changing or republishing them |
| Nineteen released workflows (v0.2.0), plugin and `npx skills` install | `australian-accounting-skills/README.md` and the 19 `.claude/skills/*/SKILL.md` folders at tag `v0.2.0`: nine public-practice and ten subcontractor workflows |
| Local MCP facade; uvx from PyPI; delegated engines; scoped Div 7A review; SBR synthetic | `australian-accounting/apps/aus-accounting-mcp/README.md` and its `DISCLAIMER.md` |
| Experimental payday-super review, possible SG-charge exposure and no ATO-assessment determination | `australian-accounting/packages/payday-super-checker/README.md` and its `paydaysuper/deadlines.py` |
| 133 native Excel LAMBDA functions plus five help tables, no add-ins or macros | `Ozzit/README.md` |
| Xero trial-balance export requires movement and year-to-date balance before writing | `accounting-review-pipeline/packages/xero-trial-balance-export/README.md`, the balance-check paragraph under Scope and disclaimer |
| Local profit-and-loss comparison against ATO benchmarks, with working shown | `australian-accounting/packages/ato-benchmark-compare/README.md`; do not imply ATO endorsement |
| Source-linked LLM operating guide for Australian accounting, tax and BAS work | `llm-tax-guardrails/README.md`; do not imply certification or endorsement |

## Style

- Australian English (`judgement`, `honouring`, `licence` in prose).
- No em dashes. [#7](https://github.com/ryanduguid/ryanduguid/pull/7) and [#8](https://github.com/ryanduguid/ryanduguid/pull/8) existed to take them out. List separators are a hyphen with spaces (` - `).
- Use only the current owner-approved employment wording recorded above; do not infer registration or endorsement from it.
- Do not add a visible LinkedIn link while the profile is inactive. [#16](https://github.com/ryanduguid/ryanduguid/pull/16). That includes the GitHub social-account slot (`gh api user/social_accounts`), not only the README. The canonical website JSON-LD and `llms.txt` may identify the hibernated Australian profile at `https://www.linkedin.com/in/ryan-duguid/` solely to distinguish it from the US namesake's unhyphenated profile.
- Narrow provenance: original work vs forks. [#5](https://github.com/ryanduguid/ryanduguid/pull/5), then [#18](https://github.com/ryanduguid/ryanduguid/pull/18).
- Counts of skills and functions are part of the prose. Recheck them before publication. A renamed project (Nabla to Ozzit, [#14](https://github.com/ryanduguid/ryanduguid/pull/14); CharlesHenryWickens back to payday-super-checker; JohnKenley to au-tax-mcp-server, since renamed aus-accounting-mcp) is a README change in the same breath as the repository rename.

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
- Conflating releases. Historical v0.1.5 shipped nine public-practice skills. The unified v0.2.0 release ships those nine plus ten construction and mining workflows. Use the released nineteen-skill count for adoption; retain the nine-skill count only when describing v0.1.5.
- Treating mentions of Xero, the ATO, CA ANZ or SAP as proof of employment, partnership, approval, registration or endorsement.
- Using retired repository names (`CharlesHenryWickens`, `JohnKenley`, `JohnSpenceOgilvy`, `MaryAddisonHamilton`, `ElizabethAnneAlexander`, `RaymondChambers`, `RussellMathews`, `SirArthurFadden`, `SirAlexanderFitzgerald`, `EdwinNixon`, `LouisGoldberg`) in new copy.

CI runs `.github/workflows/link-check.yml`: every link in README.md, llms.txt, SECURITY.md and docs/ must resolve, links must be https, a `github.com/ryanduguid/...` link that only works through a rename redirect fails the build, and a `github.com/ryanduguid/...` link whose repository is archived fails the build (one GitHub REST API lookup per repository, fail-closed when the lookup cannot complete). `FORKS.md` is also checked; its archived forks are allow-listed by name in `tools/check_links.py`, because its tables record them on purpose.

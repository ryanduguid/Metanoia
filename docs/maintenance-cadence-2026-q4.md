# Maintenance cadence: 7 September to 29 November 2026

The README cuts, native release example and static Payday page were brought forward at the owner's request on 6 September. The first six weeks below are therefore verification and feedback checkpoints for those changes, not instructions to open duplicate documentation PRs.

At most one new PR per week across the estate, with zero on investigation-only or maintainer-waiting weeks. One accounting or evaluator problem per PR, normally 1 to 3 edited files and roughly 20 to 150 authored lines; documentation moves may be larger. Do not split a coherent change or combine unrelated repositories to hit a count. Updates to an existing upstream PR are not a reason to open another one.

Dependabot pull requests sit outside that count: they are not authored work. Fifteen repositories run weekly dependency checks, so they arrive in batches. Merge the ones whose checks pass in a single pass on the first Monday after they open, close a bump that would move a pin the tests hold (the release-policy commit pins are already excluded in each Dependabot configuration), and record a week in which only Dependabot merges happened as a zero-PR week. A dependency bump that needs an authored change to pass, such as a test that pins a version string, counts as that week's one PR.

CI hygiene sits outside the count in the same way. A workflow-only change qualifies when it adds or aligns a gate that an equivalent package in the estate already runs (a coverage flag, a dependency-audit job, a Python version leg, a linter or action pin, a check script) and changes no job id, no required check name and nothing that ships. Batch such changes per repository rather than trickling them, run the repository's own suite and actionlint before opening, and merge them in the same Monday pass as Dependabot. A workflow change that alters what ships, renames a required check or touches source counts as that week's one PR. The 7 September pair (accounting-review-pipeline 117 and australian-accounting 113, each adding coverage and a dependency audit to a component that lacked them) is the first use of this carve-out; this wording change is week 1's authored PR.

- Week 1, 7 to 13 September: check that Ozzit's published image, v3.2.0 hash and capture recipe remain consistent. Record any actual reproduction failure and retain the distinction from native verification of main.
- Week 2, 14 to 20 September: check the Payday page against its pinned reproduction record and any actual reader question about remittance versus receipt.
- Week 3, 21 to 27 September: check whether the Harbour Light example makes the positive 13-week cash balance and negative year-end cash balance understandable. Record the specific assumption or explanation a reader questions.
- Week 4, 28 September to 4 October: review any observed installation or BAS tie-out problem in australian-accounting-skills. Keep the tested-runtime and human-sign-off boundaries visible.
- Week 5, 5 to 11 October: check the corpus example and moved source limitations. Review the first month's actual evaluator observations on 6 October, recording no response where none was received.
- Week 6, 12 to 18 October: check release-policy's recorded canary evidence against its documented consumer pin. Record drift without cutting a release merely to refresh evidence.
- Week 7, 19 to 25 October: accounting-review-pipeline, one observed obstacle to finding or explaining the $250 exception. If none is observed, reproduce the case and open no PR.
- Week 8, 26 October to 1 November: australian-accounting, one reproduced Payday or Division 7A defect or explanation gap. No invented edge case merely to create activity.
- Week 9, 2 to 8 November: au-fpa-pack, one observed Harbour Light assumption or output-reading problem; retain the source trace.
- Week 10, 9 to 15 November: respond to requested changes on an existing OCA, Xero or OpenAccountants contribution. No fresh batch of unsolicited PRs.
- Week 11, 16 to 22 November: retest changed examples with willing readers. Publish only consented factual observations on the website; no response is recorded as no response.
- Week 12, 23 to 29 November: one evidence-summary PR if there are new findings, otherwise a private review. Record what remains unresolved and the exact tested revisions.

Five-hour weekly budget: two hours reproducing the problem and checking sources, 90 minutes making the scoped change, one hour checking/reviewing it, and 30 minutes recording the result or arranging the next evaluation. A difficult investigation can consume the whole week without a commit. Preserve existing attribution and accurate future AI trailers.

A suitable commit message:

```text
docs(payday): explain why timely remittance remains AT_RISK

Show the fixed $120 fixture and 17 August deadline before installation.
Keep missing fund receipt as an unresolved reviewer question.

Verified with the 0.1.3 wheel and pinned fixture; verdict AT_RISK.
```

On 1 December, an outside reviewer should be able to say: I can follow a small set of Australian accounting examples from observed problem through review and verification, and see which conclusions still lack evidence. The original burst and AI attribution remain visible; the subsequent work supplies context through traceable changes, not a cosmetically smooth graph.

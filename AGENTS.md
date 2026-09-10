# Profile repository instructions

Before editing profile copy, read [docs/MAINTAINING.md](docs/MAINTAINING.md).
Keep `README.md` and `llms.txt` consistent, preserve the current owner-approved
layout and credential wording, and verify project claims against their source
repositories. Distinguish released capabilities from default-branch work.

For banner changes, use the source and verification process in that runbook.
For contribution planning, read [docs/development-practice.md](docs/development-practice.md).

Before handoff, run the checks defined in
[banner-check.yml](.github/workflows/banner-check.yml) and
[link-check.yml](.github/workflows/link-check.yml). Report any unresolved live
links separately from local test results. Account metadata, pins and publication
require explicit user authorisation; running a check does not grant it.

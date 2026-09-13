# Metanoia

Portfolio documentation and maintenance tooling for [@ryanduguid](https://github.com/ryanduguid). It holds the original history of the profile repository, which was renamed on 11 September 2026. There is nothing here to build or deploy.

The public profile README, the fork map `FORKS.md` and the profile `llms.txt` live in the separate `ryanduguid/ryanduguid` repository. The project catalogue, the worked examples and the canonical `llms.txt` live on the website, [duguid.com.au](https://duguid.com.au/).

## What is here

- `tools/check_links.py` resolves every link in this repository and in the profile repository's published `FORKS.md` and `llms.txt`, fails on rename redirects, retired names and dashes, and checks that the profile `llms.txt` names each component at its maintained directory. It runs in `.github/workflows/link-check.yml`.
- `tools/test_*.py` are the unit tests for the link policy and the repository identity records.

## Documentation

- [docs/MAINTAINING.md](docs/MAINTAINING.md): the runbook for the profile copy, the pin record and the claims that must be checked against their source repositories.
- [docs/development-practice.md](docs/development-practice.md): how this work is developed and what the contribution graph does and does not show.
- [docs/odoo-decision.md](docs/odoo-decision.md): the proposal for the OCA Odoo forks recorded in `FORKS.md`.
- [docs/xero-mcp-server-upstream-pr.md](docs/xero-mcp-server-upstream-pr.md): the record of the prepared upstream pull request to `XeroAPI/xero-mcp-server`.
- [SECURITY.md](SECURITY.md): how to report a security concern about this documentation.

The prose is licensed CC BY 4.0; see [LICENSE](LICENSE).

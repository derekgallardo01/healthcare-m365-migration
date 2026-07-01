# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-07-01

### Added
- Mock healthcare tenant (50 users, 3 departments, 3 license SKUs, PHI + non-PHI documents, unhardened baseline config)
- 8-check HIPAA config gate with CFR citations and remediation steps (DLP, sensitivity labels, retention, Copilot residency, audit log, external sharing, MFA, unlabeled PHI docs)
- 4-wave phased migration planner (pilot, wave 1, wave 2, cleanup) with MFA-gap blocker detection
- Post-cutover audit (stuck users, MFA gaps, former-still-licensed, unlabeled PHI, license waste $)
- CLI (`healthcare-m365 hipaa-gate / plan-migration / post-cutover-audit / demo`) with `--json` output on every subcommand
- End-to-end sample app: `examples/end_to_end_migration.py` writes a full markdown report
- 33 unit tests + 5 golden eval cases + GitHub Actions CI + Pages live demo + auto-captured screenshots
- Documented Graph swap point (msgraph-sdk + msal sketch in `docs/customization.md`)

[1.0.0]: https://github.com/derekgallardo01/healthcare-m365-migration/releases/tag/v1.0.0

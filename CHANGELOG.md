# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-07-01

### Added
- **Wave rollback planner** (`wave_rollback.py`) — per-user + per-step rollback plan for a failed wave, with Purview 14-day retention window awareness, per-user recovery estimates that scale with mailbox size, owner-assigned action list (delivery_lead / partner_engineer / client_admin / microsoft_support), and escalation flag when users are past retention. `rollback_plan_to_markdown()` renders for pasting to Slack during a live incident.
- **Copilot-for-healthcare PHI leakage evaluator** (`copilot_phi_eval.py`) — 15+ adversarial prompts across 7 PHI categories, 6 regex-based leakage detectors (SSN / MRN / DOB / medication / ICD-10 / patient-named), with `MockCopilot(unsafe=True)` for pre-hardening simulation. This is the QA gate the compliance officer signs off on before enabling Copilot licenses tenant-wide.
- Two new CLI subcommands: `wave-rollback` and `copilot-phi-eval` (both with `--json`)
- 22 new tests (11 rollback + 12 PHI eval) - now 55 total
- 4 new golden eval cases - now 9 total
- Extended `docs/architecture.md`, `docs/customization.md`, `docs/diagrams.md`, `docs/evaluation.md`, `docs/faq.md`, and `docs/getting-started.md` to cover both new modules
- Extended live Pages demo to show both new module summaries

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

[1.1.0]: https://github.com/derekgallardo01/healthcare-m365-migration/releases/tag/v1.1.0
[1.0.0]: https://github.com/derekgallardo01/healthcare-m365-migration/releases/tag/v1.0.0

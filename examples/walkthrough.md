# Walkthrough: end_to_end_migration.py

## What it does

Runs the four phases of a healthcare M365 pilot migration against the
bundled mock tenant, then writes a single markdown report suitable for
handing to a practice manager on the day of cutover.

## Phases

1. **Discovery** — enumerate users, departments, licenses, mailbox
   sizes. Feeds the wave plan.
2. **HIPAA gate** — 8 tenant-config checks (DLP, sensitivity labels,
   Purview retention, Copilot residency, audit log, external sharing,
   MFA, unlabeled PHI documents). Each check cites a specific HIPAA rule
   (45 CFR §164.xxx) and provides remediation steps.
3. **Wave plan** — pilot (≤10 users, MFA-ready, mixed departments),
   wave 1 (largest single department), wave 2 (remainder), cleanup
   (former staff to offboard, not migrate). MFA gaps are flagged as
   blockers per wave.
4. **Post-cutover audit** — stuck users, MFA gaps, former staff still
   licensed (with $/mo waste), unlabeled PHI documents.

## Run

```bash
pip install -e .
python examples/end_to_end_migration.py
```

Output: `pilot-migration-report.md` in the current directory + a
first-40-lines preview in the terminal.

## Wire to a real tenant

The kit ships MockBackend. To run against a live M365 tenant, implement
`GraphBackend` per the sketch in `docs/customization.md` (msgraph-sdk +
msal, ~150 lines), then export `GRAPH_BACKEND=graph`. The rest of the
pipeline (HIPAA gate, wave planner, audit, report generator) is
unchanged.

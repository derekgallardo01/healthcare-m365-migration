# Evaluation

## Two suites

1. **Unit tests** (`tests/`) — 33 pytest tests covering the backend
   invariants, the HIPAA gate (per check + overall gate), the wave
   planner (per invariant), and the post-cutover audit.
2. **Golden evals** (`evals/golden.json`) — 5 end-to-end assertions
   against the mock tenant. Run via `python evals/run.py`.

## What the tests cover

**Backend:**

- 50 users; 3 departments (Clinical, Billing, Admin); 3 SKUs (E5, E3, F3)
- MFA gaps exist but are a minority (5-12 users)
- Former staff (>= 2) exist and have `account_enabled=False`
- Every user has a source mailbox
- Billing mailboxes are larger than clinical on average (matches reality)
- Documents include both PHI and non-PHI; both labeled and unlabeled PHI
- Tenant config baseline is intentionally *pre-hardening* so the gate has
  real work to do

**HIPAA gate:**

- Baseline tenant is `blocked` (>= 5 failures)
- Fully-hardened tenant clears (0 failures)
- Every failed check has a `remediation` string
- Every check has a CFR citation starting with `164.`
- Summary line format is stable

**Wave planner:**

- 4 waves; correct ordering; pilot capped at 10
- Every pilot user is MFA-registered
- Every active user placed in wave 1/2/3 (not cleanup)
- Cleanup wave contains only former staff
- MFA gaps become per-wave blockers
- Warning includes MFA reminder when gaps exist

**Post-cutover audit:**

- Finds `former_still_licensed` users
- Computes correct dollar waste (E5=$57, E3=$36, F3=$8)
- Finds MFA gaps
- Threshold days changes stuck-user count monotonically
- Unlabeled PHI documents are surfaced with full path

## What the golden evals cover

5 end-to-end cases:

1. `hipaa_gate_blocks_baseline_tenant` — blocked=true, failures>=5, 8 checks total
2. `hipaa_gate_all_fails_have_remediation` — every fail has a remediation
3. `wave_plan_has_four_waves_pilot_capped` — 4 waves, pilot <= 10, cleanup wave named correctly
4. `post_cutover_audit_finds_gaps` — >=2 former licensed, >=1 MFA gap, >=2 unlabeled PHI, >=$50/mo waste
5. `post_cutover_audit_summary_readable` — summary contains 'stuck', 'MFA gaps', '$'

## Adding a new eval

Edit `evals/golden.json`. The assertion syntax supports:

- `eq` — equals
- `gte` / `lte` — >= / <=
- `contains` — substring match on string values

Paths are dot-separated. Synthetic paths (e.g. `checks.length`,
`checks.every_fail_has_remediation`) are computed in `evals/run.py`.

## CI

`.github/workflows/ci.yml` runs the tests + evals on every push
across Python 3.10, 3.11, 3.12. It also smoke-tests the CLI
(`healthcare-m365 demo`).

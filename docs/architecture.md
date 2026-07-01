# Architecture

## Layers

```
CLI  ->  healthcare_m365.cli
              |
              v
         Analyses  ->  hipaa_gate.py     (8 config checks)
                       migration_planner.py  (4-wave planner)
                       post_cutover_audit.py (post-cutover audit)
              |
              v
         Backend  ->  backend.py (Protocol + MockBackend + GraphBackend sketch)
```

Every analysis takes a Backend and returns a dataclass. The CLI + sample
app + eval harness all consume the same dataclasses, so behavior is
identical regardless of the backend.

## The Backend seam

The Backend protocol has 4 methods:

```python
class Backend(Protocol):
    def list_users(self) -> list[User]: ...
    def list_source_mailboxes(self) -> list[MailboxSource]: ...
    def list_documents(self) -> list[Document]: ...
    def get_tenant_config(self) -> TenantConfig: ...
```

`MockBackend` implements all 4 against an in-memory dataset (50 users,
3 departments, 3 SKUs, ~10 PHI/non-PHI documents, unhardened baseline
tenant config).

`GraphBackend` is a sketch — see [customization.md](customization.md)
for the msgraph-sdk + msal wiring.

## The HIPAA gate

`run_hipaa_gate(backend)` iterates a list of check functions. Each check:

- Reads a specific field from `TenantConfig` (or `list_documents()`)
- Returns a `HipaaCheck` with a `pass` / `warn` / `fail` status,
  the specific CFR citation (e.g. `164.312(a)(1)`), a detail line,
  and a remediation string when applicable

Adding a check = writing one more function + appending it to `CHECKS`.

## The wave planner

`plan_migration(backend)` produces a `MigrationPlan` with 4 waves:

- **Pilot** — <= 10 users, at least 1 per department, all MFA-registered
- **Wave 1** — the largest single department (usually Clinical), less pilot users
- **Wave 2** — all remaining active users
- **Cleanup** — former staff (offboard, do NOT migrate to new tenant)

MFA gaps become per-wave `blockers` so the delivery lead can chase
resolution before that wave's cutover date.

## The post-cutover audit

`run_post_cutover_audit(backend)` runs after each wave completes and
reports:

- **Stuck users** — enabled accounts with no signin since threshold days
- **MFA gaps** — enabled accounts without MFA registered
- **Former still licensed** — disabled accounts still holding a paid SKU
- **Unlabeled PHI docs** — documents flagged PHI without a sensitivity label
- **License waste $/mo** — dollar cost of the former-still-licensed set

The summary line is designed to paste straight into a wave-completion
status email.

## The sample app

`examples/end_to_end_migration.py` runs all four phases and stitches
the output into a single markdown report — the primary deliverable of
a real engagement.

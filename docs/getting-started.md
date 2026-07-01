# Getting started

## Install

```bash
pip install -e .
```

That's all you need for the mock-backend path (default). To swap to a
real Graph tenant, install the optional extras:

```bash
pip install -e ".[graph]"
```

## Run the demo

```bash
healthcare-m365 demo
```

This walks all four phases against the bundled 50-user mock healthcare
tenant:

1. **Discovery** — enumerate users, departments, licenses, mailbox sizes
2. **HIPAA gate** — 8 tenant-config checks with CFR citations + remediation
3. **Wave plan** — 4 waves (pilot / wave 1 / wave 2 / cleanup)
4. **Post-cutover audit** — stuck users, MFA gaps, license waste, unlabeled PHI

## Run each phase individually

```bash
healthcare-m365 hipaa-gate                        # HIPAA gate only
healthcare-m365 plan-migration                    # wave plan only
healthcare-m365 post-cutover-audit                # audit only
healthcare-m365 wave-rollback --days-since-cutover 5   # unwind a failed wave
healthcare-m365 copilot-phi-eval                  # Copilot PHI leakage eval
```

Every subcommand supports `--json` for machine-readable output:

```bash
healthcare-m365 hipaa-gate --json | jq '.checks[] | select(.status=="fail")'
healthcare-m365 copilot-phi-eval --unsafe --json   # simulate broken tenant
```

## Run the end-to-end sample app

```bash
python examples/end_to_end_migration.py
```

Writes `pilot-migration-report.md` in the current directory — a full
markdown report suitable for handing to a practice manager on cutover
day. See [examples/walkthrough.md](../examples/walkthrough.md) for the
detailed breakdown.

## Run tests + evals

```bash
python -m pytest -q     # 55 unit tests
python evals/run.py     # 9 golden eval cases
```

## Next

- [Architecture](architecture.md) — how the pieces fit together
- [Customization](customization.md) — swap the mock backend for real Graph
- [Evaluation](evaluation.md) — how the eval harness works
- [Diagrams](diagrams.md) — one flowchart, one wave-plan diagram
- [FAQ](faq.md) — common questions

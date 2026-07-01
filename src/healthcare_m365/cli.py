"""CLI entrypoint: `healthcare-m365 <subcommand>`."""
from __future__ import annotations

import argparse
import json
import sys

from healthcare_m365.backend import get_backend
from healthcare_m365.hipaa_gate import run_hipaa_gate
from healthcare_m365.migration_planner import plan_migration
from healthcare_m365.post_cutover_audit import run_post_cutover_audit


def _print_hipaa(as_json: bool = False) -> None:
    result = run_hipaa_gate()
    if as_json:
        print(json.dumps({
            "summary": result.summary(),
            "blocked": result.blocked,
            "checks": [c.__dict__ for c in result.checks],
        }, indent=2))
        return

    print(result.summary())
    print()
    for c in result.checks:
        marker = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[c.status]
        print(f"  [{marker}] {c.name}   ({c.hipaa_citation})")
        print(f"         {c.detail}")
        if c.remediation:
            print(f"         Fix: {c.remediation}")
        print()


def _print_plan(as_json: bool = False) -> None:
    plan = plan_migration()
    if as_json:
        print(json.dumps({
            "summary": plan.summary(),
            "waves": [
                {
                    "name": w.name,
                    "order": w.order,
                    "user_count": w.user_count(),
                    "est_hours": w.est_hours,
                    "blockers": w.blockers,
                }
                for w in plan.waves
            ],
            "warnings": plan.warnings,
        }, indent=2))
        return

    print(plan.summary())
    print()
    for wave in plan.waves:
        print(f"  Wave {wave.order}: {wave.name}   {wave.user_count()} users   {wave.est_hours:.1f}h est")
        for u in wave.users[:5]:
            print(f"    - {u.display_name:24s} {u.department:10s} {u.license_sku}")
        if wave.user_count() > 5:
            print(f"    ... plus {wave.user_count() - 5} more")
        if wave.blockers:
            for b in wave.blockers:
                print(f"    BLOCKER: {b}")
        print()

    for w in plan.warnings:
        print(f"  WARNING: {w}")


def _print_audit(as_json: bool = False) -> None:
    report = run_post_cutover_audit()
    if as_json:
        print(json.dumps({
            "summary": report.summary(),
            "stuck_users":            [u.display_name for u in report.stuck_users],
            "mfa_gaps":                [u.display_name for u in report.mfa_gaps],
            "former_still_licensed":  [u.display_name for u in report.former_still_licensed],
            "unlabeled_phi_docs":      report.unlabeled_phi_docs,
            "licenses_at_risk_usd":    report.licenses_at_risk_usd,
        }, indent=2))
        return

    print(report.summary())
    print()
    if report.stuck_users:
        print("  Stuck users (no signin since cutover):")
        for u in report.stuck_users[:8]:
            print(f"    - {u.display_name:24s} {u.department:10s} last_signin={u.last_signin.date()}")
        if len(report.stuck_users) > 8:
            print(f"    ... plus {len(report.stuck_users) - 8} more")
        print()
    if report.mfa_gaps:
        print("  MFA gaps:")
        for u in report.mfa_gaps:
            print(f"    - {u.display_name:24s} {u.department:10s} {u.job_title}")
        print()
    if report.former_still_licensed:
        print(f"  Former staff still holding a license (${report.licenses_at_risk_usd:.2f}/mo waste):")
        for u in report.former_still_licensed:
            print(f"    - {u.display_name:24s} {u.license_sku}")
        print()
    if report.unlabeled_phi_docs:
        print("  PHI documents without a sensitivity label:")
        for path in report.unlabeled_phi_docs[:5]:
            print(f"    - {path}")
        if len(report.unlabeled_phi_docs) > 5:
            print(f"    ... plus {len(report.unlabeled_phi_docs) - 5} more")


def _demo() -> None:
    print("=" * 68)
    print("HEALTHCARE M365 MIGRATION - end-to-end demo (mock tenant)")
    print("=" * 68)
    print()
    print("Step 1 - Discovery: what do we have?")
    print("-" * 68)
    backend = get_backend()
    users = backend.list_users()
    print(f"  Users: {len(users)}")
    print(f"  Departments: {sorted({u.department for u in users})}")
    print(f"  Licenses: {sorted({u.license_sku for u in users})}")
    print()

    print("Step 2 - HIPAA gate: is the tenant safe to migrate into?")
    print("-" * 68)
    _print_hipaa()

    print("Step 3 - Plan the phased migration")
    print("-" * 68)
    _print_plan()

    print("Step 4 - Post-cutover audit (simulated: wave 1 completed)")
    print("-" * 68)
    _print_audit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="healthcare-m365")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_h = sub.add_parser("hipaa-gate", help="Run the HIPAA-specific config gate.")
    p_h.add_argument("--json", action="store_true")

    p_p = sub.add_parser("plan-migration", help="Plan phased cohort migration.")
    p_p.add_argument("--json", action="store_true")

    p_a = sub.add_parser("post-cutover-audit", help="Run the post-cutover audit.")
    p_a.add_argument("--json", action="store_true")

    sub.add_parser("demo", help="Walk through all four steps end-to-end.")

    args = parser.parse_args(argv)

    if args.cmd == "hipaa-gate":
        _print_hipaa(as_json=args.json)
    elif args.cmd == "plan-migration":
        _print_plan(as_json=args.json)
    elif args.cmd == "post-cutover-audit":
        _print_audit(as_json=args.json)
    elif args.cmd == "demo":
        _demo()
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

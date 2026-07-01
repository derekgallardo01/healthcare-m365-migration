"""Eval harness with path-based assertions.

Runs golden.json against the mock tenant. Fails CI if any assertion
regresses. Path syntax: dot-separated indexing into the result dict
(also supports `.length`, `.every_fail_has_remediation` synthetic paths).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from datetime import timedelta

from healthcare_m365.backend import NOW, get_backend
from healthcare_m365.copilot_phi_eval import MockCopilot, run_copilot_phi_eval
from healthcare_m365.hipaa_gate import run_hipaa_gate
from healthcare_m365.migration_planner import plan_migration
from healthcare_m365.post_cutover_audit import run_post_cutover_audit
from healthcare_m365.wave_rollback import plan_wave_rollback


HERE = Path(__file__).parent


def _hipaa_result_as_dict() -> dict:
    r = run_hipaa_gate()
    return {
        "blocked": r.blocked,
        "failures": r.failures,
        "warnings": r.warnings,
        "passed": r.passed,
        "checks": {
            "length": len(r.checks),
            "every_fail_has_remediation": all(
                c.remediation for c in r.checks if c.status == "fail"
            ),
        },
    }


def _plan_result_as_dict() -> dict:
    p = plan_migration()
    return {
        "total_users": p.total_users,
        "total_active": p.total_active,
        "waves": {
            "length": len(p.waves),
            "0": {"name": p.waves[0].name, "user_count": p.waves[0].user_count()},
            "3": {"name": p.waves[3].name, "user_count": p.waves[3].user_count()},
        },
    }


def _audit_result_as_dict() -> dict:
    a = run_post_cutover_audit()
    return {
        "former_still_licensed": {"length": len(a.former_still_licensed)},
        "mfa_gaps": {"length": len(a.mfa_gaps)},
        "unlabeled_phi_docs": {"length": len(a.unlabeled_phi_docs)},
        "stuck_users": {"length": len(a.stuck_users)},
        "licenses_at_risk_usd": a.licenses_at_risk_usd,
        "summary": a.summary(),
    }


def _rollback_recent() -> dict:
    b = get_backend()
    plan = plan_migration(b)
    users = plan.waves[0].users
    rp = plan_wave_rollback(users, b, "PilotDemo", NOW - timedelta(days=3))
    return {
        "escalation_required": rp.escalation_required,
        "within_retention": rp.within_retention,
        "past_retention": rp.past_retention,
        "action_count": len(rp.actions),
        "summary": rp.summary(),
    }


def _rollback_stale() -> dict:
    b = get_backend()
    plan = plan_migration(b)
    users = plan.waves[0].users
    rp = plan_wave_rollback(users, b, "PilotDemo", NOW - timedelta(days=60))
    return {
        "escalation_required": rp.escalation_required,
        "within_retention": rp.within_retention,
        "past_retention": rp.past_retention,
        "action_count": len(rp.actions),
        "summary": rp.summary(),
    }


def _copilot_safe() -> dict:
    report = run_copilot_phi_eval(copilot=MockCopilot(unsafe=False))
    return {
        "gate_passed": report.gate_passed(),
        "leaked_count": report.leaked_count,
        "total_prompts": report.total_prompts,
    }


def _copilot_unsafe() -> dict:
    report = run_copilot_phi_eval(copilot=MockCopilot(unsafe=True))
    return {
        "gate_passed": report.gate_passed(),
        "leaked_count": report.leaked_count,
        "total_prompts": report.total_prompts,
    }


OPS = {
    "hipaa_gate": _hipaa_result_as_dict,
    "plan_migration": _plan_result_as_dict,
    "post_cutover_audit": _audit_result_as_dict,
    "post_cutover_audit_summary": _audit_result_as_dict,
    "wave_rollback_recent": _rollback_recent,
    "wave_rollback_stale": _rollback_stale,
    "copilot_phi_safe": _copilot_safe,
    "copilot_phi_unsafe": _copilot_unsafe,
}


def _path_lookup(obj, path: str):
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list):
            obj = obj[int(part)]
        else:
            return None
        if obj is None:
            return None
    return obj


def _check_assertion(result: dict, a: dict) -> tuple[bool, str]:
    value = _path_lookup(result, a["path"])
    if "eq" in a:
        expected = a["eq"]
        ok = value == expected
        return ok, f"{a['path']} = {value} (expected {expected})"
    if "gte" in a:
        expected = a["gte"]
        ok = value is not None and value >= expected
        return ok, f"{a['path']} = {value} (expected >= {expected})"
    if "lte" in a:
        expected = a["lte"]
        ok = value is not None and value <= expected
        return ok, f"{a['path']} = {value} (expected <= {expected})"
    if "contains" in a:
        expected = a["contains"]
        ok = value is not None and expected in str(value)
        return ok, f"{a['path']} = {value!r} (expected to contain {expected!r})"
    return False, f"unknown assertion op in {a}"


def main() -> int:
    golden = json.loads((HERE / "golden.json").read_text())
    passed = 0
    failed = 0

    print(f"Running {len(golden['cases'])} eval cases against mock tenant...")
    print()

    for case in golden["cases"]:
        op = case["op"]
        result = OPS[op]()
        case_ok = True
        for a in case["assertions"]:
            ok, msg = _check_assertion(result, a)
            marker = "PASS" if ok else "FAIL"
            print(f"  [{marker}] {case['name']} :: {msg}")
            case_ok = case_ok and ok

        if case_ok:
            passed += 1
        else:
            failed += 1
        print()

    print(f"Result: {passed}/{passed + failed} cases passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

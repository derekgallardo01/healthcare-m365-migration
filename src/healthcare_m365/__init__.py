"""HIPAA-aware M365 migration kit for healthcare orgs."""
from healthcare_m365.backend import Backend, MockBackend, get_backend
from healthcare_m365.copilot_phi_eval import (
    EvalReport,
    EvalResult,
    MockCopilot,
    PhiPromptCase,
    detect_leakage,
    run_copilot_phi_eval,
)
from healthcare_m365.hipaa_gate import HipaaCheck, HipaaGateResult, run_hipaa_gate
from healthcare_m365.migration_planner import (
    MigrationPlan,
    MigrationWave,
    plan_migration,
)
from healthcare_m365.post_cutover_audit import PostCutoverReport, run_post_cutover_audit
from healthcare_m365.wave_rollback import (
    RollbackAction,
    RollbackPlan,
    UserRollbackRow,
    plan_wave_rollback,
    rollback_plan_to_markdown,
)

__all__ = [
    "Backend",
    "MockBackend",
    "get_backend",
    "HipaaCheck",
    "HipaaGateResult",
    "run_hipaa_gate",
    "MigrationPlan",
    "MigrationWave",
    "plan_migration",
    "PostCutoverReport",
    "run_post_cutover_audit",
    "RollbackAction",
    "RollbackPlan",
    "UserRollbackRow",
    "plan_wave_rollback",
    "rollback_plan_to_markdown",
    "EvalReport",
    "EvalResult",
    "MockCopilot",
    "PhiPromptCase",
    "detect_leakage",
    "run_copilot_phi_eval",
]

from healthcare_m365.backend import MockBackend, TenantConfig
from healthcare_m365.hipaa_gate import run_hipaa_gate


def test_baseline_tenant_gets_blocked():
    result = run_hipaa_gate(MockBackend())
    assert result.blocked is True
    assert result.failures > 0


def test_hardened_tenant_clears():
    b = MockBackend()
    b._tenant_config = TenantConfig(
        dlp_phi_policy_enabled=True,
        sensitivity_labels_published=["Public", "Internal", "Confidential", "PHI - Highly Confidential"],
        purview_retention_years=6,
        copilot_data_residency_us=True,
        audit_log_retention_days=365,
        external_sharing_restricted=True,
        mfa_required_all_users=True,
    )
    # Also fix the doc-labeling gap
    for d in b._documents:
        if d.contains_phi and not d.sensitivity_label:
            d.sensitivity_label = "PHI - Highly Confidential"

    result = run_hipaa_gate(b)
    assert result.blocked is False
    assert result.failures == 0


def test_every_check_has_citation():
    result = run_hipaa_gate(MockBackend())
    for c in result.checks:
        assert c.hipaa_citation.startswith("164.")


def test_failed_checks_include_remediation():
    result = run_hipaa_gate(MockBackend())
    fails = [c for c in result.checks if c.status == "fail"]
    assert fails
    for c in fails:
        assert c.remediation  # every fail must tell you how to fix it


def test_check_count_stable():
    result = run_hipaa_gate(MockBackend())
    assert len(result.checks) == 8


def test_summary_line_format():
    result = run_hipaa_gate(MockBackend())
    s = result.summary()
    assert "pass" in s and "warn" in s and "fail" in s
    assert "BLOCKED" in s or "CLEARED" in s

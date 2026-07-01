from healthcare_m365.backend import MockBackend
from healthcare_m365.post_cutover_audit import run_post_cutover_audit


def test_audit_finds_former_still_licensed():
    report = run_post_cutover_audit(MockBackend())
    assert len(report.former_still_licensed) >= 2


def test_audit_computes_license_waste_from_former_users():
    report = run_post_cutover_audit(MockBackend())
    assert report.licenses_at_risk_usd > 0
    # E5 is $57/mo, E3 is $36/mo. Two former users on E5 + E3 = 93.00 minimum
    assert report.licenses_at_risk_usd >= 50.00


def test_audit_finds_mfa_gaps():
    report = run_post_cutover_audit(MockBackend())
    assert len(report.mfa_gaps) >= 1
    for u in report.mfa_gaps:
        assert not u.mfa_registered
        assert u.account_enabled
        assert not u.is_former


def test_audit_finds_stuck_users_below_threshold_days():
    # 7-day threshold: users with last_signin 140 days ago should count as stuck
    report = run_post_cutover_audit(MockBackend(), stuck_threshold_days=7)
    assert len(report.stuck_users) >= 1
    # Long-threshold: at 200 days, only the *very* stale users count
    long_report = run_post_cutover_audit(MockBackend(), stuck_threshold_days=200)
    assert len(long_report.stuck_users) < len(report.stuck_users)


def test_audit_flags_unlabeled_phi_documents():
    report = run_post_cutover_audit(MockBackend())
    assert len(report.unlabeled_phi_docs) >= 2
    # Every reported doc should be a "site/library/path" string
    for d in report.unlabeled_phi_docs:
        assert "/" in d


def test_audit_summary_readable():
    report = run_post_cutover_audit(MockBackend())
    s = report.summary()
    assert "stuck" in s
    assert "MFA gaps" in s
    assert "$" in s


def test_total_users_matches():
    b = MockBackend()
    report = run_post_cutover_audit(b)
    assert report.total_users == len(b.list_users())

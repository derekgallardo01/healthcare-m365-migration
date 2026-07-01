from healthcare_m365.copilot_phi_eval import (
    DEFAULT_PROMPTS,
    LEAKAGE_PATTERNS,
    MockCopilot,
    detect_leakage,
    run_copilot_phi_eval,
)


def test_safe_response_has_no_leakage():
    leaked, matched = detect_leakage(
        "I can't surface individual patient identifiers or clinical data."
    )
    assert not leaked
    assert not matched


def test_ssn_pattern_detected():
    leaked, matched = detect_leakage("SSN 123-45-6789 on file for John Smith.")
    assert leaked
    assert "ssn" in matched


def test_mrn_pattern_detected():
    leaked, matched = detect_leakage("Patient MRN 12345 last note.")
    assert leaked
    assert "mrn" in matched


def test_dob_pattern_detected():
    leaked, matched = detect_leakage("Patient DOB was 04/12/1975.")
    assert leaked
    assert "dob" in matched


def test_medication_pattern_detected():
    leaked, matched = detect_leakage("40 units Lantus qhs + 15 units Humalog per meal.")
    assert leaked
    assert "rx_dose" in matched


def test_icd10_pattern_detected():
    leaked, matched = detect_leakage("Diagnosis code E11.9 with complications.")
    assert leaked
    assert "icd10" in matched


def test_patient_named_pattern_detected():
    leaked, matched = detect_leakage("The patient John Smith has been discharged.")
    assert leaked
    assert "patient_named" in matched


def test_gate_passes_with_safe_copilot():
    report = run_copilot_phi_eval(copilot=MockCopilot(unsafe=False))
    assert report.gate_passed()
    assert report.leaked_count == 0
    assert report.safe_count == report.total_prompts


def test_gate_fails_with_unsafe_copilot():
    report = run_copilot_phi_eval(copilot=MockCopilot(unsafe=True))
    assert not report.gate_passed()
    assert report.leaked_count >= 3  # multiple prompts leak in unsafe mode
    assert "FAIL" in report.summary()


def test_unsafe_leakage_categories_reported():
    report = run_copilot_phi_eval(copilot=MockCopilot(unsafe=True))
    # per_category dict has entries per leaking category
    assert report.per_category  # non-empty
    for cat, count in report.per_category.items():
        assert count > 0
        assert cat in {"ssn", "mrn", "dob_name", "medication", "icd10",
                       "combined", "patient_named"}


def test_all_prompts_have_category():
    for p in DEFAULT_PROMPTS:
        assert p.phi_category
        assert p.phi_category in {"ssn", "mrn", "dob_name", "medication",
                                   "icd10", "combined", "patient_named"}


def test_default_prompt_set_has_at_least_15():
    assert len(DEFAULT_PROMPTS) >= 15


def test_every_leakage_pattern_has_a_test_prompt():
    """Every named leakage pattern should be exercised by at least one prompt."""
    all_pattern_names = set(LEAKAGE_PATTERNS.keys())
    referenced_patterns = {p for case in DEFAULT_PROMPTS for p in case.leakage_patterns}
    # Every pattern in LEAKAGE_PATTERNS should be referenced by at least one case
    for name in all_pattern_names:
        assert name in referenced_patterns, f"Pattern {name!r} has no prompt exercising it"


def test_summary_line_shows_gate_status():
    report = run_copilot_phi_eval(copilot=MockCopilot(unsafe=False))
    assert "PASS" in report.summary()
    assert "leaked" in report.summary()

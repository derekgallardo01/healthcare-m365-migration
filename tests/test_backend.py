from healthcare_m365.backend import MockBackend


def test_mock_backend_ships_50_users():
    b = MockBackend()
    users = b.list_users()
    assert len(users) == 50


def test_departments_are_realistic():
    b = MockBackend()
    depts = {u.department for u in b.list_users()}
    assert depts == {"Clinical", "Billing", "Admin"}


def test_licenses_span_all_three_skus():
    b = MockBackend()
    skus = {u.license_sku for u in b.list_users()}
    assert skus == {"SPE_E5", "SPE_E3", "SPE_F3"}


def test_mfa_gaps_exist_but_are_minority():
    b = MockBackend()
    users = b.list_users()
    gaps = [u for u in users if not u.mfa_registered]
    assert 5 <= len(gaps) <= 12  # meaningful sample, not majority
    assert len(gaps) < len(users) / 2


def test_former_staff_flagged():
    b = MockBackend()
    former = [u for u in b.list_users() if u.is_former]
    assert len(former) >= 2
    assert all(not u.account_enabled for u in former)


def test_source_mailboxes_exist_for_every_user():
    b = MockBackend()
    users = b.list_users()
    mailboxes = b.list_source_mailboxes()
    upns_u = {u.upn for u in users}
    upns_m = {m.upn for m in mailboxes}
    assert upns_u == upns_m


def test_billing_mailboxes_are_larger():
    b = MockBackend()
    users = {u.upn: u for u in b.list_users()}
    boxes = b.list_source_mailboxes()
    billing_avg = sum(m.size_gb for m in boxes if users[m.upn].department == "Billing") / \
                  sum(1 for m in boxes if users[m.upn].department == "Billing")
    clinical_avg = sum(m.size_gb for m in boxes if users[m.upn].department == "Clinical") / \
                   sum(1 for m in boxes if users[m.upn].department == "Clinical")
    assert billing_avg > clinical_avg


def test_documents_include_phi_and_non_phi():
    b = MockBackend()
    docs = b.list_documents()
    assert any(d.contains_phi for d in docs)
    assert any(not d.contains_phi for d in docs)


def test_documents_include_labeled_and_unlabeled_phi():
    b = MockBackend()
    docs = b.list_documents()
    labeled_phi = [d for d in docs if d.contains_phi and d.sensitivity_label]
    unlabeled_phi = [d for d in docs if d.contains_phi and not d.sensitivity_label]
    assert labeled_phi and unlabeled_phi  # both sides of the gap


def test_tenant_config_baseline_is_pre_hardening():
    b = MockBackend()
    c = b.get_tenant_config()
    # We ship a realistically-broken baseline so the gate has real work to do
    assert c.dlp_phi_policy_enabled is False
    assert c.purview_retention_years < 6
    assert c.mfa_required_all_users is False

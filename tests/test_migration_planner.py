from healthcare_m365.backend import MockBackend
from healthcare_m365.migration_planner import plan_migration


def test_plan_has_four_waves():
    plan = plan_migration(MockBackend())
    assert len(plan.waves) == 4
    assert [w.order for w in plan.waves] == [1, 2, 3, 4]


def test_pilot_is_capped_at_10():
    plan = plan_migration(MockBackend())
    pilot = plan.waves[0]
    assert pilot.name == "Pilot"
    assert pilot.user_count() <= 10


def test_pilot_users_are_all_mfa_registered():
    plan = plan_migration(MockBackend())
    pilot = plan.waves[0]
    assert all(u.mfa_registered for u in pilot.users)


def test_cleanup_wave_has_former_staff():
    plan = plan_migration(MockBackend())
    cleanup = plan.waves[3]
    assert "Cleanup" in cleanup.name
    assert cleanup.user_count() >= 2
    assert all(u.is_former or not u.account_enabled for u in cleanup.users)


def test_total_active_matches_backend():
    b = MockBackend()
    plan = plan_migration(b)
    active_from_backend = [u for u in b.list_users() if not u.is_former and u.account_enabled]
    assert plan.total_active == len(active_from_backend)


def test_every_active_user_placed():
    b = MockBackend()
    plan = plan_migration(b)
    # Every active user should end up in wave 1, 2, or 3 (not the cleanup wave)
    placed_ids = {u.id for w in plan.waves[:3] for u in w.users}
    active_ids = {u.id for u in b.list_users() if not u.is_former and u.account_enabled}
    assert placed_ids == active_ids


def test_mfa_gaps_are_flagged_as_blockers():
    plan = plan_migration(MockBackend())
    blockers = [b for w in plan.waves for b in w.blockers]
    assert blockers  # we ship MFA gaps, so blockers must be reported
    assert any("no MFA" in b for b in blockers)


def test_warning_includes_mfa_reminder_when_gaps_exist():
    plan = plan_migration(MockBackend())
    assert any("MFA" in w for w in plan.warnings)


def test_summary_reports_totals():
    plan = plan_migration(MockBackend())
    s = plan.summary()
    assert "active users" in s
    assert "waves" in s
    assert "GB" in s


def test_wave_1_named_after_largest_department():
    plan = plan_migration(MockBackend())
    wave1 = plan.waves[1]
    assert "Wave 1" in wave1.name
    # In the mock, Clinical is the largest department by construction
    assert "Clinical" in wave1.name

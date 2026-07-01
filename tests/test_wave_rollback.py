from datetime import timedelta

from healthcare_m365.backend import MockBackend, NOW
from healthcare_m365.wave_rollback import (
    PURVIEW_RETENTION_DAYS,
    plan_wave_rollback,
    rollback_plan_to_markdown,
)


def test_within_retention_can_rollback():
    b = MockBackend()
    users = b.list_users()[:8]
    cutover = NOW - timedelta(days=3)
    plan = plan_wave_rollback(users, b, "TestWave", cutover)
    assert plan.days_since_cutover == 3
    assert plan.within_retention == 8
    assert plan.past_retention == 0
    assert not plan.escalation_required


def test_past_retention_flags_escalation():
    b = MockBackend()
    users = b.list_users()[:5]
    cutover = NOW - timedelta(days=PURVIEW_RETENTION_DAYS + 5)
    plan = plan_wave_rollback(users, b, "OldWave", cutover)
    assert plan.past_retention == 5
    assert plan.within_retention == 0
    assert plan.escalation_required


def test_actions_are_ordered_and_owned():
    b = MockBackend()
    users = b.list_users()[:4]
    plan = plan_wave_rollback(users, b, "W", NOW - timedelta(days=2))
    steps = [a.step for a in plan.actions]
    assert steps == list(range(1, len(steps) + 1))
    owners = {a.owner for a in plan.actions}
    assert "delivery_lead" in owners
    assert "partner_engineer" in owners
    assert "client_admin" in owners


def test_mailbox_restore_action_per_user():
    b = MockBackend()
    users = b.list_users()[:3]
    plan = plan_wave_rollback(users, b, "W", NOW - timedelta(days=2))
    restore_actions = [a for a in plan.actions if "Restore" in a.action and "mailbox" in a.action]
    assert len(restore_actions) == 3


def test_no_restore_actions_when_all_past_retention():
    b = MockBackend()
    users = b.list_users()[:3]
    plan = plan_wave_rollback(users, b, "W", NOW - timedelta(days=100))
    restore_actions = [a for a in plan.actions if "Restore" in a.action and "mailbox" in a.action]
    assert len(restore_actions) == 0
    escalation = [a for a in plan.actions if "Premier" in a.action]
    assert escalation


def test_summary_line_reports_risk():
    b = MockBackend()
    users = b.list_users()[:5]
    ok_plan = plan_wave_rollback(users, b, "W", NOW - timedelta(days=3))
    assert "RECOVERABLE" in ok_plan.summary()
    bad_plan = plan_wave_rollback(users, b, "W", NOW - timedelta(days=100))
    assert "ESCALATION" in bad_plan.summary()


def test_markdown_report_includes_all_users_and_actions():
    b = MockBackend()
    users = b.list_users()[:5]
    plan = plan_wave_rollback(users, b, "MarkdownWave", NOW - timedelta(days=2))
    md = rollback_plan_to_markdown(plan)
    assert "# Rollback plan: MarkdownWave" in md
    for u in users:
        assert u.display_name in md
    for a in plan.actions:
        assert a.action[:30] in md
    assert "Estimated total effort" in md


def test_est_minutes_scales_with_mailbox_size():
    """Bigger mailboxes take longer to restore."""
    b = MockBackend()
    users = b.list_users()
    plan = plan_wave_rollback(users, b, "W", NOW - timedelta(days=2))
    restore_actions = [a for a in plan.actions if "Restore" in a.action and "mailbox" in a.action]
    minutes = [a.est_minutes for a in restore_actions]
    assert max(minutes) > min(minutes)  # varies by mailbox size

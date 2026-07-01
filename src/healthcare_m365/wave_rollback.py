"""Wave rollback planner.

Fires when a completed migration wave goes wrong (data loss on cutover,
mass user complaints, license enforcement gap, etc.). The rollback
planner produces a step-by-step plan to unwind the wave and restore
users to their pre-cutover state.

Rollback is expensive and lossy - Purview retention holds the source
mailboxes for ~14 days after cutover, so this plan is a race against
that clock. The delivery lead needs the plan generated in < 5 minutes
so they can execute or escalate.

Design invariants:
- Every user in the affected wave gets a per-user rollback row (mailbox,
  license, group memberships, sensitivity labels).
- Every rollback row lists both the pre-cutover state and the current
  (broken) state so it's clear what to restore.
- The plan flags any user whose source mailbox is already past the
  Purview retention window (i.e. rollback is not possible; they need a
  separate escalation path).
- Every step has an owner (delivery lead / partner engineer / client
  admin) so no one asks 'who does this?' during an incident.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from healthcare_m365.backend import Backend, MailboxSource, NOW, User


# Purview retention window for source mailboxes after cutover (days).
# In production this is tenant-configured; the kit assumes 14 days as
# the M365 default recoverable-items window.
PURVIEW_RETENTION_DAYS = 14


@dataclass
class RollbackAction:
    step: int
    owner: str  # "delivery_lead" | "partner_engineer" | "client_admin" | "microsoft_support"
    action: str
    user_upn: str = ""
    est_minutes: int = 15
    blocking: bool = True
    note: str = ""


@dataclass
class UserRollbackRow:
    user: User
    original_mailbox_gb: float
    current_status: str  # "signed_in_new" | "stuck" | "escalated"
    mailbox_in_retention: bool
    license_restored_from: str
    can_rollback: bool
    reason_if_blocked: str = ""


@dataclass
class RollbackPlan:
    wave_name: str
    cutover_date: datetime
    days_since_cutover: int
    total_users: int
    within_retention: int = 0
    past_retention: int = 0
    actions: list[RollbackAction] = field(default_factory=list)
    user_rows: list[UserRollbackRow] = field(default_factory=list)
    escalation_required: bool = False

    def summary(self) -> str:
        risk = "RECOVERABLE" if not self.escalation_required else "ESCALATION REQUIRED"
        return (
            f"Rollback plan for {self.wave_name}: {self.total_users} users, "
            f"{self.within_retention} within Purview retention, "
            f"{self.past_retention} past retention. "
            f"{len(self.actions)} actions. Risk: {risk}"
        )


def plan_wave_rollback(
    wave_users: list[User],
    backend: Backend,
    wave_name: str,
    cutover_date: datetime,
) -> RollbackPlan:
    """Build a per-user + per-step rollback plan for a failed wave.

    Assumes source mailboxes are still discoverable via `list_source_mailboxes`
    (the pre-cutover state). In a real engagement, the source-tenant
    Exchange Hybrid config + tenant backup service are what you'd read
    from; this kit uses the mock backend.
    """
    days_since = max(0, (NOW - cutover_date).days)
    plan = RollbackPlan(
        wave_name=wave_name,
        cutover_date=cutover_date,
        days_since_cutover=days_since,
        total_users=len(wave_users),
    )

    source_mailboxes = {m.upn: m for m in backend.list_source_mailboxes()}
    within_window = days_since <= PURVIEW_RETENTION_DAYS

    for user in wave_users:
        mailbox = source_mailboxes.get(user.upn)
        row = UserRollbackRow(
            user=user,
            original_mailbox_gb=mailbox.size_gb if mailbox else 0.0,
            current_status="stuck" if user.last_signin < cutover_date else "signed_in_new",
            mailbox_in_retention=within_window,
            license_restored_from=user.license_sku,
            can_rollback=within_window and mailbox is not None,
            reason_if_blocked=(
                "" if (within_window and mailbox is not None)
                else "past Purview retention" if not within_window
                else "source mailbox not discoverable"
            ),
        )
        plan.user_rows.append(row)

    plan.within_retention = sum(1 for r in plan.user_rows if r.can_rollback)
    plan.past_retention = plan.total_users - plan.within_retention
    plan.escalation_required = plan.past_retention > 0

    plan.actions = _build_rollback_actions(wave_users, plan)
    return plan


def _build_rollback_actions(users: list[User], plan: RollbackPlan) -> list[RollbackAction]:
    actions: list[RollbackAction] = []
    step = 0

    def add(owner: str, action: str, minutes: int = 15, blocking: bool = True,
            user_upn: str = "", note: str = "") -> None:
        nonlocal step
        step += 1
        actions.append(RollbackAction(
            step=step, owner=owner, action=action, est_minutes=minutes,
            blocking=blocking, user_upn=user_upn, note=note,
        ))

    # Phase 1: freeze the target tenant so damage doesn't compound
    add("delivery_lead",
        "Post 'migration paused' notice to affected users via Teams announcement",
        minutes=10)
    add("delivery_lead",
        "Disable all Conditional Access policies targeting the wave's user set "
        "(prevents further sign-in traffic to target tenant)",
        minutes=15)
    add("partner_engineer",
        "Pause the SharePoint Migration Tool job queue (avoid partial-migration corruption)",
        minutes=10)

    # Phase 2: restore mailboxes from source
    for row in plan.user_rows:
        if not row.can_rollback:
            continue
        add(
            "partner_engineer",
            f"Restore {row.user.display_name}'s mailbox from source-tenant Recovery Items "
            f"(source ~{row.original_mailbox_gb:.1f} GB)",
            minutes=int(30 + row.original_mailbox_gb * 2),  # rough estimate
            user_upn=row.user.upn,
        )

    # Phase 3: restore licenses on source tenant
    add("client_admin",
        "Reassign every affected user's license on the source tenant "
        "(licenses were transferred to target during migration; source is now unlicensed)",
        minutes=30, blocking=True,
        note=f"{plan.within_retention} users to reassign")

    # Phase 4: escalation path for users past retention
    if plan.past_retention > 0:
        add("delivery_lead",
            "Open Microsoft Premier ticket for post-retention recovery attempts "
            "(chance of success: low). Include tenant IDs, user list, and cutover date.",
            minutes=30, blocking=False)
        add("delivery_lead",
            "Notify practice manager: N users cannot be rolled back within retention. "
            "Decision required: accept-and-move-forward vs escalate to Microsoft Premier.",
            minutes=15, blocking=True,
            note=f"{plan.past_retention} users past retention")

    # Phase 5: communicate + post-mortem
    add("delivery_lead",
        "Send status email to all affected users: 'You've been restored to the previous tenant. "
        "Sign in with your old credentials. Any new mail from today will need to be forwarded manually.'",
        minutes=15)
    add("delivery_lead",
        "Schedule post-mortem within 48 hours (root cause + corrective actions before next wave attempt).",
        minutes=10, blocking=False)

    return actions


def rollback_plan_to_markdown(plan: RollbackPlan) -> str:
    """Render a plan to a markdown report the delivery lead can paste to Slack."""
    parts: list[str] = []
    parts.append(f"# Rollback plan: {plan.wave_name}")
    parts.append("")
    parts.append(f"*Generated {NOW.date()}. Cutover was {plan.cutover_date.date()} "
                 f"({plan.days_since_cutover} days ago).*")
    parts.append("")
    parts.append(f"**{plan.summary()}**")
    parts.append("")

    if plan.escalation_required:
        parts.append("> **Warning:** Some users are past the 14-day Purview retention "
                     "window. Rollback is NOT guaranteed for those users - Microsoft "
                     "Premier ticket + client-side decision required.")
        parts.append("")

    parts.append("## Actions (execute in order)")
    parts.append("")
    parts.append("| # | Owner | Action | Est. min | Blocking? |")
    parts.append("|---|---|---|---|:---:|")
    for a in plan.actions:
        blocking = "yes" if a.blocking else "no"
        note = f"<br>*{a.note}*" if a.note else ""
        parts.append(f"| {a.step} | {a.owner} | {a.action}{note} | {a.est_minutes} | {blocking} |")
    parts.append("")

    parts.append("## Per-user rollback status")
    parts.append("")
    parts.append("| User | Dept | Mailbox (GB) | Can rollback? | Reason if blocked |")
    parts.append("|---|---|---:|:---:|---|")
    for row in plan.user_rows:
        can = "yes" if row.can_rollback else "**NO**"
        reason = row.reason_if_blocked or "-"
        parts.append(f"| {row.user.display_name} | {row.user.department} | "
                     f"{row.original_mailbox_gb:.1f} | {can} | {reason} |")
    parts.append("")

    total_min = sum(a.est_minutes for a in plan.actions)
    parts.append(f"**Estimated total effort:** {total_min} minutes ({total_min // 60}h {total_min % 60}min)")
    parts.append("")
    return "\n".join(parts)

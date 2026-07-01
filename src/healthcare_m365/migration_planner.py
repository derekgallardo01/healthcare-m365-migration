"""Phased-cohort migration planner.

Groups users into pilot / wave-1 / wave-2 / cleanup cohorts based on
department, license, MFA readiness, and mailbox size. Emits a plan the
delivery team can hand to a project manager.

Design rules baked in:
- Pilot cohort <= 10 users, mixed departments, all MFA-ready.
- Wave 1 = the largest single department (usually Clinical) less pilot users.
- Wave 2 = remaining active users.
- Cleanup wave = former staff (offboard, do not migrate).
- Any user without MFA is flagged as blocking - resolve before that user's wave.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from healthcare_m365.backend import Backend, MailboxSource, User


@dataclass
class MigrationWave:
    name: str
    order: int
    users: list[User] = field(default_factory=list)
    est_hours: float = 0.0
    blockers: list[str] = field(default_factory=list)

    def user_count(self) -> int:
        return len(self.users)

    def total_mailbox_gb(self, source_by_upn: dict[str, MailboxSource]) -> float:
        return sum(source_by_upn[u.upn].size_gb for u in self.users if u.upn in source_by_upn)


@dataclass
class MigrationPlan:
    waves: list[MigrationWave] = field(default_factory=list)
    total_users: int = 0
    total_active: int = 0
    total_former: int = 0
    total_mailbox_gb: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [
            f"{self.total_active} active users across {len(self.waves)} waves",
            f"{self.total_mailbox_gb:.1f} GB mailbox data to migrate",
            f"{self.total_former} former accounts to offboard",
        ]
        if self.warnings:
            parts.append(f"{len(self.warnings)} planning warning(s)")
        return " | ".join(parts)


PILOT_CAP = 10
HOURS_PER_USER_PILOT = 1.2
HOURS_PER_USER_STANDARD = 0.6
HOURS_PER_USER_CLEANUP = 0.2


def plan_migration(backend: Backend | None = None,
                   pilot_cap: int = PILOT_CAP) -> MigrationPlan:
    from healthcare_m365.backend import get_backend

    b = backend if backend is not None else get_backend()
    users = b.list_users()
    source_mailboxes = {m.upn: m for m in b.list_source_mailboxes()}

    active = [u for u in users if not u.is_former and u.account_enabled]
    former = [u for u in users if u.is_former or not u.account_enabled]

    plan = MigrationPlan(
        total_users=len(users),
        total_active=len(active),
        total_former=len(former),
    )

    # Pilot: <= pilot_cap users, MFA-ready, one per department if possible.
    pilot: list[User] = []
    remaining: list[User] = []
    for dept in sorted({u.department for u in active}):
        dept_active_mfa = [u for u in active if u.department == dept and u.mfa_registered]
        # take 3-4 per department to fill pilot proportionally
        take = min(len(dept_active_mfa), max(1, pilot_cap // 3))
        pilot.extend(dept_active_mfa[:take])
    pilot = pilot[:pilot_cap]

    pilot_ids = {u.id for u in pilot}
    for u in active:
        if u.id not in pilot_ids:
            remaining.append(u)

    # Wave 1: largest department (from remaining)
    by_dept: dict[str, list[User]] = {}
    for u in remaining:
        by_dept.setdefault(u.department, []).append(u)
    largest_dept = max(by_dept.keys(), key=lambda d: len(by_dept[d])) if by_dept else None

    wave1_users = by_dept.pop(largest_dept, []) if largest_dept else []
    wave2_users = [u for group in by_dept.values() for u in group]

    plan.waves = [
        MigrationWave(name="Pilot", order=1, users=pilot,
                      est_hours=len(pilot) * HOURS_PER_USER_PILOT),
        MigrationWave(name=f"Wave 1 - {largest_dept or 'none'}", order=2,
                      users=wave1_users,
                      est_hours=len(wave1_users) * HOURS_PER_USER_STANDARD),
        MigrationWave(name="Wave 2 - remaining active", order=3,
                      users=wave2_users,
                      est_hours=len(wave2_users) * HOURS_PER_USER_STANDARD),
        MigrationWave(name="Cleanup - former staff (offboard, do not migrate)",
                      order=4, users=former,
                      est_hours=len(former) * HOURS_PER_USER_CLEANUP),
    ]

    for wave in plan.waves:
        gap = [u for u in wave.users if not u.mfa_registered and not u.is_former]
        for u in gap:
            wave.blockers.append(f"{u.display_name} - no MFA registered")

    plan.total_mailbox_gb = sum(m.size_gb for m in source_mailboxes.values())

    if any(wave.blockers for wave in plan.waves):
        plan.warnings.append(
            "MFA gaps found; users listed as blockers in each wave must register "
            "MFA before their wave's cutover date."
        )

    return plan

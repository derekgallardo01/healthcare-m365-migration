"""Post-cutover audit.

Runs after each wave completes. Answers the questions every stakeholder asks
the day after a wave migrates:

- Which licenses are we now paying for that we're not using?
- Who's on the new tenant but hasn't signed in yet (stuck user)?
- Who's still missing MFA (safety gap)?
- Are our PHI documents in the new tenant carrying the sensitivity label?
- Are any former staff still holding an active license?

Emits a structured `PostCutoverReport` and a summary line the delivery
lead can paste straight into the wave-completion status email.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from healthcare_m365.backend import Backend, NOW, User


LICENSE_MONTHLY_USD = {
    "SPE_E5": 57.00,
    "SPE_E3": 36.00,
    "SPE_F3": 8.00,
    "COPILOT_M365": 30.00,
}


@dataclass
class PostCutoverReport:
    stuck_users: list[User] = field(default_factory=list)
    mfa_gaps: list[User] = field(default_factory=list)
    former_still_licensed: list[User] = field(default_factory=list)
    unlabeled_phi_docs: list[str] = field(default_factory=list)
    licenses_at_risk_usd: float = 0.0
    total_users: int = 0

    def summary(self) -> str:
        return (
            f"Post-cutover: {len(self.stuck_users)} stuck "
            f"({100 * len(self.stuck_users) / max(1, self.total_users):.0f}%), "
            f"{len(self.mfa_gaps)} MFA gaps, "
            f"{len(self.former_still_licensed)} former staff still licensed, "
            f"{len(self.unlabeled_phi_docs)} PHI docs unlabeled, "
            f"${self.licenses_at_risk_usd:.2f}/mo license waste at risk"
        )


def run_post_cutover_audit(backend: Backend | None = None,
                           stuck_threshold_days: int = 7) -> PostCutoverReport:
    from healthcare_m365.backend import get_backend

    b = backend if backend is not None else get_backend()
    users = b.list_users()
    documents = b.list_documents()

    stuck_cutoff = NOW - timedelta(days=stuck_threshold_days)
    stuck = [u for u in users if u.account_enabled and u.last_signin < stuck_cutoff and not u.is_former]

    mfa_gaps = [u for u in users if u.account_enabled and not u.mfa_registered and not u.is_former]

    former_still = [u for u in users if u.is_former and u.license_sku in LICENSE_MONTHLY_USD]

    waste_usd = sum(LICENSE_MONTHLY_USD.get(u.license_sku, 0.0) for u in former_still)

    unlabeled = [f"{d.site}/{d.library}{d.path}"
                 for d in documents if d.contains_phi and not d.sensitivity_label]

    return PostCutoverReport(
        stuck_users=stuck,
        mfa_gaps=mfa_gaps,
        former_still_licensed=former_still,
        unlabeled_phi_docs=unlabeled,
        licenses_at_risk_usd=waste_usd,
        total_users=len(users),
    )

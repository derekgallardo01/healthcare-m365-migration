"""HIPAA-specific configuration gate.

Reads the tenant config from the backend and checks the 8 items that most
often block a healthcare M365 pilot from going live. Each check returns a
pass / fail / warn + a citation to the applicable HIPAA rule so the finding
can be dropped straight into a compliance report.

This is the piece that differentiates a healthcare-specific migration from
a generic M365 migration. Every other kit in the portfolio audits users,
licenses, and mailboxes. This one audits the *configuration surface* that
HIPAA requires.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from healthcare_m365.backend import Backend, Document, TenantConfig


@dataclass
class HipaaCheck:
    name: str
    hipaa_citation: str
    status: str  # "pass" | "warn" | "fail"
    detail: str
    remediation: str = ""


@dataclass
class HipaaGateResult:
    checks: list[HipaaCheck] = field(default_factory=list)
    blocked: bool = False
    warnings: int = 0
    failures: int = 0
    passed: int = 0

    def summary(self) -> str:
        return (
            f"HIPAA gate: {self.passed} pass, {self.warnings} warn, "
            f"{self.failures} fail  [{'BLOCKED' if self.blocked else 'CLEARED'}]"
        )


def _check_dlp(config: TenantConfig) -> HipaaCheck:
    if config.dlp_phi_policy_enabled:
        return HipaaCheck(
            name="PHI DLP policy enabled",
            hipaa_citation="164.312(a)(1) - access control",
            status="pass",
            detail="A DLP policy targeting PHI-classified content is active.",
        )
    return HipaaCheck(
        name="PHI DLP policy enabled",
        hipaa_citation="164.312(a)(1) - access control",
        status="fail",
        detail="No DLP policy is scanning for PHI patterns (SSN, MRN, DOB combinations).",
        remediation=(
            "In Purview -> Data loss prevention -> Policies, create a policy scoped "
            "to Exchange + SharePoint + OneDrive using the built-in 'U.S. Health "
            "Insurance Act (HIPAA)' template. Set enforcement mode to 'Test with "
            "notifications' for 7 days, then flip to 'Turn on'."
        ),
    )


def _check_sensitivity_labels(config: TenantConfig) -> HipaaCheck:
    has_phi = any("PHI" in label.upper() for label in config.sensitivity_labels_published)
    if has_phi:
        return HipaaCheck(
            name="PHI sensitivity label published",
            hipaa_citation="164.312(c)(1) - integrity",
            status="pass",
            detail="A PHI-marked sensitivity label is available to end users.",
        )
    return HipaaCheck(
        name="PHI sensitivity label published",
        hipaa_citation="164.312(c)(1) - integrity",
        status="fail",
        detail=(
            f"Published labels are {config.sensitivity_labels_published}. "
            "There is no PHI-specific label, so clinical staff cannot mark PHI "
            "consistently and DLP has no signal to key off."
        ),
        remediation=(
            "In Purview -> Information protection -> Labels, publish 'PHI - Highly "
            "Confidential' with encryption + do-not-forward + a watermark. Assign to "
            "all clinical + billing users via a label policy."
        ),
    )


def _check_retention(config: TenantConfig) -> HipaaCheck:
    if config.purview_retention_years >= 6:
        return HipaaCheck(
            name="Purview retention >= 6 years",
            hipaa_citation="164.316(b)(2)(i) - retention",
            status="pass",
            detail=f"Retention is set to {config.purview_retention_years} years.",
        )
    return HipaaCheck(
        name="Purview retention >= 6 years",
        hipaa_citation="164.316(b)(2)(i) - retention",
        status="fail",
        detail=(
            f"Retention is {config.purview_retention_years} years. HIPAA requires "
            "documentation retention for at least 6 years from the date of creation "
            "or last effective date, whichever is later."
        ),
        remediation=(
            "In Purview -> Data lifecycle management -> Retention policies, create "
            "or extend the retention policy applied to SharePoint sites containing "
            "PHI to 6 years (7 recommended for buffer)."
        ),
    )


def _check_copilot_residency(config: TenantConfig) -> HipaaCheck:
    if config.copilot_data_residency_us:
        return HipaaCheck(
            name="Copilot data residency in US",
            hipaa_citation="164.308(b)(1) - business associate",
            status="pass",
            detail="Copilot data-at-rest is pinned to the US geography.",
        )
    return HipaaCheck(
        name="Copilot data residency in US",
        hipaa_citation="164.308(b)(1) - business associate",
        status="warn",
        detail=(
            "Copilot data residency is not pinned to US. This is not a hard HIPAA "
            "violation but many healthcare BAAs require it explicitly."
        ),
        remediation=(
            "In M365 admin center -> Settings -> Org settings -> Data location, "
            "confirm the primary geography is 'United States' and that no Copilot "
            "add-ons are provisioned in EU / APAC data centers."
        ),
    )


def _check_audit_log(config: TenantConfig) -> HipaaCheck:
    if config.audit_log_retention_days >= 365:
        return HipaaCheck(
            name="Unified audit log >= 365 days",
            hipaa_citation="164.312(b) - audit controls",
            status="pass",
            detail=f"Audit log retention is {config.audit_log_retention_days} days.",
        )
    return HipaaCheck(
        name="Unified audit log >= 365 days",
        hipaa_citation="164.312(b) - audit controls",
        status="fail",
        detail=(
            f"Audit log retention is {config.audit_log_retention_days} days. "
            "HIPAA breach investigations often need 12+ months of history."
        ),
        remediation=(
            "In Purview -> Audit -> Audit retention policies, create a policy "
            "setting retention to 1 year for Exchange + SharePoint + OneDrive + "
            "AzureActiveDirectory record types. E5 tenants can go to 10 years."
        ),
    )


def _check_external_sharing(config: TenantConfig) -> HipaaCheck:
    if config.external_sharing_restricted:
        return HipaaCheck(
            name="External sharing restricted",
            hipaa_citation="164.312(a)(1) - access control",
            status="pass",
            detail="External sharing is restricted at the tenant level.",
        )
    return HipaaCheck(
        name="External sharing restricted",
        hipaa_citation="164.312(a)(1) - access control",
        status="fail",
        detail=(
            "External sharing is unrestricted. A user could accidentally share a "
            "PHI-containing OneDrive file with anyone with a link."
        ),
        remediation=(
            "In SharePoint admin -> Policies -> Sharing, set the SharePoint slider "
            "to 'New and existing guests' and the OneDrive slider to 'Only people "
            "in your organization'. Configure per-site exceptions if needed."
        ),
    )


def _check_mfa(config: TenantConfig) -> HipaaCheck:
    if config.mfa_required_all_users:
        return HipaaCheck(
            name="MFA required tenant-wide",
            hipaa_citation="164.312(d) - person or entity authentication",
            status="pass",
            detail="MFA is required for all users via a Conditional Access policy.",
        )
    return HipaaCheck(
        name="MFA required tenant-wide",
        hipaa_citation="164.312(d) - person or entity authentication",
        status="fail",
        detail=(
            "MFA is not tenant-wide. HIPAA does not name MFA specifically but the "
            "Security Rule's 'reasonable and appropriate' standard treats MFA as "
            "table stakes in 2026."
        ),
        remediation=(
            "In Entra -> Protection -> Conditional Access, deploy 'Require MFA "
            "for all users' with a break-glass account exclusion. Roll out via "
            "'Report-only' mode for 3 days first."
        ),
    )


def _check_unlabeled_phi(documents: list[Document]) -> HipaaCheck:
    unlabeled = [d for d in documents if d.contains_phi and not d.sensitivity_label]
    if not unlabeled:
        return HipaaCheck(
            name="All PHI documents carry a sensitivity label",
            hipaa_citation="164.312(c)(1) - integrity",
            status="pass",
            detail="Every document flagged as PHI has an appropriate sensitivity label.",
        )
    detail = (
        f"{len(unlabeled)} PHI-containing document(s) have no sensitivity label. "
        f"Examples: {', '.join(d.path for d in unlabeled[:3])}"
    )
    return HipaaCheck(
        name="All PHI documents carry a sensitivity label",
        hipaa_citation="164.312(c)(1) - integrity",
        status="fail",
        detail=detail,
        remediation=(
            "Run Purview auto-labeling with a policy that trains on the pattern "
            "'MRN + DOB + patient-name proximity'. Auto-label as 'PHI - Highly "
            "Confidential' in simulation mode first."
        ),
    )


CHECKS: list[Callable[..., HipaaCheck]] = [
    _check_dlp,
    _check_sensitivity_labels,
    _check_retention,
    _check_copilot_residency,
    _check_audit_log,
    _check_external_sharing,
    _check_mfa,
]


def run_hipaa_gate(backend: Backend | None = None) -> HipaaGateResult:
    """Run every HIPAA check against the tenant. Blocks migration if any fail."""
    from healthcare_m365.backend import get_backend

    b = backend if backend is not None else get_backend()
    config = b.get_tenant_config()
    documents = b.list_documents()

    result = HipaaGateResult()
    for check_fn in CHECKS:
        result.checks.append(check_fn(config))
    result.checks.append(_check_unlabeled_phi(documents))

    for c in result.checks:
        if c.status == "pass":
            result.passed += 1
        elif c.status == "warn":
            result.warnings += 1
        elif c.status == "fail":
            result.failures += 1

    result.blocked = result.failures > 0
    return result

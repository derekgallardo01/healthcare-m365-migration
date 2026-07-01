"""Mock healthcare tenant + Backend seam for the Microsoft Graph swap.

The mock is a small but realistic 50-user healthcare org:
- 3 departments (Clinical, Billing, Admin)
- Mix of MFA-registered and gap users
- A few inactive accounts (former staff / rotated interns)
- E5 + E3 + F3 license mix (E5 for clinicians, F3 for kiosk / rotating staff)
- PHI-labeled documents in SharePoint (some with correct sensitivity label,
  some without - the gap we look for)
- Legacy Exchange source tenant to migrate FROM

Set GRAPH_BACKEND=graph and provide AZURE_TENANT_ID / AZURE_CLIENT_ID /
AZURE_CLIENT_SECRET to swap to a real Graph backend. The GraphBackend class
is a documented sketch; the mock is what ships.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol


NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)


@dataclass
class User:
    id: str
    display_name: str
    upn: str
    mail: str
    department: str
    job_title: str
    license_sku: str
    mfa_registered: bool
    last_signin: datetime
    account_enabled: bool = True
    is_former: bool = False


@dataclass
class MailboxSource:
    """Legacy source (on-prem Exchange OR another cloud tenant) - the FROM side."""

    upn: str
    size_gb: float
    item_count: int
    last_logon: datetime


@dataclass
class Document:
    id: str
    site: str
    library: str
    path: str
    contains_phi: bool
    sensitivity_label: str  # "" = unlabeled
    owner_upn: str


@dataclass
class TenantConfig:
    """The M365 tenant-level configuration we care about for HIPAA."""

    dlp_phi_policy_enabled: bool
    sensitivity_labels_published: list[str] = field(default_factory=list)
    purview_retention_years: int = 0
    copilot_data_residency_us: bool = False
    audit_log_retention_days: int = 0
    external_sharing_restricted: bool = False
    mfa_required_all_users: bool = False


class Backend(Protocol):
    def list_users(self) -> list[User]: ...
    def list_source_mailboxes(self) -> list[MailboxSource]: ...
    def list_documents(self) -> list[Document]: ...
    def get_tenant_config(self) -> TenantConfig: ...


class MockBackend:
    """Deterministic in-memory healthcare tenant used by tests + demos."""

    def __init__(self) -> None:
        self._users = self._build_users()
        self._source_mailboxes = self._build_source_mailboxes()
        self._documents = self._build_documents()
        self._tenant_config = self._build_tenant_config()

    def list_users(self) -> list[User]:
        return list(self._users)

    def list_source_mailboxes(self) -> list[MailboxSource]:
        return list(self._source_mailboxes)

    def list_documents(self) -> list[Document]:
        return list(self._documents)

    def get_tenant_config(self) -> TenantConfig:
        return self._tenant_config

    def _build_users(self) -> list[User]:
        recent = NOW - timedelta(days=2)
        stale = NOW - timedelta(days=140)
        gone = NOW - timedelta(days=300)

        rows: list[tuple[str, str, str, str, bool, datetime, bool]] = [
            # (name, dept, title, sku, mfa, last_signin, is_former)
            ("Dr. Alice Reyes",     "Clinical",   "Physician",              "SPE_E5", True,  recent, False),
            ("Dr. Ben Cho",         "Clinical",   "Physician",              "SPE_E5", True,  recent, False),
            ("Dr. Carla Fox",       "Clinical",   "Physician",              "SPE_E5", True,  recent, False),
            ("Dr. Diane Hall",      "Clinical",   "Physician",              "SPE_E5", False, recent, False),
            ("Dr. Ethan Ku",        "Clinical",   "Physician",              "SPE_E5", True,  recent, False),
            ("Nurse Faye Long",     "Clinical",   "RN",                     "SPE_E3", True,  recent, False),
            ("Nurse Grace Park",    "Clinical",   "RN",                     "SPE_E3", True,  recent, False),
            ("Nurse Henry Ito",     "Clinical",   "RN",                     "SPE_E3", False, recent, False),
            ("Nurse Ivy Kim",       "Clinical",   "LPN",                    "SPE_E3", True,  recent, False),
            ("Nurse Jack Lin",      "Clinical",   "LPN",                    "SPE_E3", True,  recent, False),
            ("Kayla Moss",          "Clinical",   "Medical Assistant",      "SPE_F3", True,  recent, False),
            ("Leo Nguyen",          "Clinical",   "Medical Assistant",      "SPE_F3", True,  recent, False),
            ("Mia Olsen",           "Clinical",   "Medical Assistant",      "SPE_F3", False, recent, False),
            ("Noah Park",           "Clinical",   "Medical Assistant",      "SPE_F3", True,  recent, False),
            ("Olivia Qi",           "Clinical",   "Phlebotomist",           "SPE_F3", True,  recent, False),
            ("Pete Rho",            "Clinical",   "Phlebotomist",           "SPE_F3", True,  recent, False),
            ("Quinn Suh",           "Clinical",   "Phlebotomist",           "SPE_F3", False, recent, False),
            ("Rita Tan",            "Clinical",   "Phlebotomist",           "SPE_F3", True,  recent, False),
            ("Sam Underwood",       "Clinical",   "Front Desk",             "SPE_F3", True,  recent, False),
            ("Tara Vega",           "Clinical",   "Front Desk",             "SPE_F3", True,  recent, False),
            ("Uma Wong",            "Clinical",   "Front Desk",             "SPE_F3", True,  recent, False),
            ("Vic Xu",              "Clinical",   "Care Coordinator",       "SPE_E3", True,  recent, False),
            ("Wren Yates",          "Clinical",   "Care Coordinator",       "SPE_E3", True,  recent, False),
            ("Xu Zhang",            "Clinical",   "Care Coordinator",       "SPE_E3", False, recent, False),
            ("Yara Abbas",          "Clinical",   "Care Coordinator",       "SPE_E3", True,  recent, False),

            ("Zara Bell",           "Billing",    "Billing Manager",        "SPE_E5", True,  recent, False),
            ("Ana Chen",            "Billing",    "Billing Specialist",     "SPE_E3", True,  recent, False),
            ("Ben Diaz",            "Billing",    "Billing Specialist",     "SPE_E3", True,  recent, False),
            ("Cora Ellis",          "Billing",    "Coder",                  "SPE_E3", False, recent, False),
            ("Dan Feld",            "Billing",    "Coder",                  "SPE_E3", True,  recent, False),
            ("Erin Gao",            "Billing",    "AR Specialist",          "SPE_E3", True,  recent, False),
            ("Finn Ho",             "Billing",    "AR Specialist",          "SPE_E3", True,  recent, False),
            ("Gina Iyer",           "Billing",    "AR Specialist",          "SPE_E3", True,  recent, False),
            ("Hank Jung",           "Billing",    "Denial Analyst",         "SPE_E3", False, recent, False),
            ("Iris Kaur",           "Billing",    "Denial Analyst",         "SPE_E3", True,  recent, False),

            ("Jake Li",             "Admin",      "Practice Manager",       "SPE_E5", True,  recent, False),
            ("Kim Ma",              "Admin",      "HR Manager",             "SPE_E5", True,  recent, False),
            ("Lee Novak",           "Admin",      "HR Coordinator",         "SPE_E3", True,  recent, False),
            ("Mona Ortiz",          "Admin",      "Payroll",                "SPE_E3", True,  recent, False),
            ("Nate Perez",          "Admin",      "Front Office Lead",      "SPE_E3", True,  recent, False),
            ("Opal Qadir",          "Admin",      "Scheduler",              "SPE_F3", True,  recent, False),
            ("Pat Rios",            "Admin",      "Scheduler",              "SPE_F3", True,  recent, False),
            ("Quin Salt",           "Admin",      "Scheduler",              "SPE_F3", False, recent, False),
            ("Ray Tam",             "Admin",      "Reception",              "SPE_F3", True,  recent, False),
            ("Sam Ur",              "Admin",      "Reception",              "SPE_F3", True,  recent, False),

            # Gaps + former staff that the audit should catch
            ("Ivy Villanueva",      "Clinical",   "RN (on leave)",          "SPE_E5", True,  stale,  False),
            ("Kai Wu",              "Billing",    "Coder (rotated)",        "SPE_E3", True,  stale,  False),
            ("Lila Xu",             "Admin",      "Reception (per-diem)",   "SPE_F3", False, stale,  False),
            ("Mona Yun",            "Clinical",   "Former MA",              "SPE_E5", True,  gone,   True),
            ("Nolan Zhang",         "Billing",    "Former Coder",           "SPE_E3", True,  gone,   True),
        ]

        return [
            User(
                id=f"u-{i+1:03d}",
                display_name=name,
                upn=f"{name.split()[0].lower()}.{name.split()[-1].lower()}@clinic.onmicrosoft.com",
                mail=f"{name.split()[0].lower()}.{name.split()[-1].lower()}@clinic.com",
                department=dept,
                job_title=title,
                license_sku=sku,
                mfa_registered=mfa,
                last_signin=signin,
                account_enabled=not former,
                is_former=former,
            )
            for i, (name, dept, title, sku, mfa, signin, former) in enumerate(rows)
        ]

    def _build_source_mailboxes(self) -> list[MailboxSource]:
        """Legacy on-prem mailboxes to migrate from."""
        return [
            MailboxSource(upn=u.upn, size_gb=self._mailbox_size_for(u), item_count=int(self._mailbox_size_for(u) * 1800),
                          last_logon=u.last_signin)
            for u in self._users
        ]

    @staticmethod
    def _mailbox_size_for(u: User) -> float:
        if u.is_former:
            return 12.4
        if u.department == "Clinical":
            return 4.8
        if u.department == "Billing":
            return 7.2  # billing keeps a lot of email
        return 3.1

    def _build_documents(self) -> list[Document]:
        # A few PHI-labeled + a few PHI-unlabeled (the gap the HIPAA gate catches)
        return [
            Document("d-01", "Clinical",  "Patient Records", "/2026/patient-a-chart.docx", True,  "PHI - Highly Confidential", "alice.reyes@clinic.onmicrosoft.com"),
            Document("d-02", "Clinical",  "Patient Records", "/2026/patient-b-chart.docx", True,  "PHI - Highly Confidential", "ben.cho@clinic.onmicrosoft.com"),
            Document("d-03", "Clinical",  "Patient Records", "/2025-archive/patient-c.docx", True, "", "carla.fox@clinic.onmicrosoft.com"),
            Document("d-04", "Clinical",  "Patient Records", "/2025-archive/patient-d.docx", True, "", "diane.hall@clinic.onmicrosoft.com"),
            Document("d-05", "Billing",   "Claims",          "/june/claim-batch.xlsx",     True,  "", "zara.bell@clinic.onmicrosoft.com"),
            Document("d-06", "Billing",   "Claims",          "/june/eob-log.xlsx",         True,  "PHI - Highly Confidential", "zara.bell@clinic.onmicrosoft.com"),
            Document("d-07", "Admin",     "HR",              "/policies/handbook.pdf",     False, "Internal", "kim.ma@clinic.onmicrosoft.com"),
            Document("d-08", "Admin",     "HR",              "/onboarding/checklist.docx", False, "Internal", "lee.novak@clinic.onmicrosoft.com"),
            Document("d-09", "Clinical",  "Shared",          "/misc/lab-worksheet.xlsx",   True,  "", "faye.long@clinic.onmicrosoft.com"),
            Document("d-10", "Billing",   "Denials",         "/q2/denials-list.csv",       True,  "Confidential", "hank.jung@clinic.onmicrosoft.com"),
        ]

    def _build_tenant_config(self) -> TenantConfig:
        # A realistic pre-hardening baseline - the gate should FAIL several items.
        return TenantConfig(
            dlp_phi_policy_enabled=False,
            sensitivity_labels_published=["Public", "Internal", "Confidential"],  # missing PHI label
            purview_retention_years=3,  # too short for HIPAA 6-year rule
            copilot_data_residency_us=True,
            audit_log_retention_days=90,  # too short for HIPAA
            external_sharing_restricted=False,
            mfa_required_all_users=False,
        )


class GraphBackend:
    """Sketch of the production Graph backend. Fill in with msgraph-sdk + msal.

    Not exported from `get_backend` unless GRAPH_BACKEND=graph. Ship the mock;
    swap this in during a real engagement.
    """

    def __init__(self) -> None:  # pragma: no cover - documentation only
        raise NotImplementedError(
            "GraphBackend is a sketch. See docs/customization.md for the "
            "msgraph-sdk + msal wiring, or run with the default MockBackend."
        )


def get_backend() -> Backend:
    if os.environ.get("GRAPH_BACKEND", "mock").lower() == "graph":
        return GraphBackend()  # type: ignore[return-value]
    return MockBackend()

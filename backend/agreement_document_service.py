"""
Agreement document rendering helpers for worker-side contract and handbook access.

This module keeps agreement document generation in one place so worker views,
downloads, and signature/acknowledgement flows all reference the same persisted
rendered artifact and template version.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.document import Document as DocumentObject
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph as PdfParagraph, SimpleDocTemplate, Spacer, Table as PdfTable, TableStyle
from xml.sax.saxutils import escape

from services.pdf_service import get_logo_image
from supabase_storage import download_file_from_storage, upload_file_to_storage


BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "agreement_assets"
CONTRACT_TEMPLATE_DOCX_PATH = ASSET_DIR / "zero_hour_contract_template_canonical.docx"
CONTRACT_TEMPLATE_PDF_PATH = ASSET_DIR / "zero_hour_contract_template.pdf"
HANDBOOK_TEMPLATE_PATH = ASSET_DIR / "employee_handbook_template.docx"

CONTRACT_TEMPLATE_ID = "ZERO_HOUR_CONTRACT_V1"
HANDBOOK_TEMPLATE_ID = "EMPLOYEE_HANDBOOK_FULL_V1"

CONTRACT_AGREEMENT_TYPE = "contract_acceptance"
HANDBOOK_AGREEMENT_TYPE = "handbook_acknowledgement"
CANONICAL_CONTRACT_TEMPLATE_PREFIX = f"{CONTRACT_AGREEMENT_TYPE}_v_"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _employee_name(employee: Dict[str, Any]) -> str:
    full_name = (employee.get("name") or "").strip()
    if full_name:
        return full_name
    return f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() or "Employee"


def _format_date(value: Any, default_text: str = "TBC") -> str:
    if not value:
        return default_text
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
            try:
                if "%z" in fmt:
                    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                else:
                    dt = datetime.strptime(text, fmt)
                break
            except Exception:
                dt = None
        if dt is None:
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except Exception:
                return text
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%d %B %Y")


def _format_money(value: Any, default_text: str = "TBC") -> str:
    if value in (None, "", "null"):
        return default_text
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _format_job_title(value: Any, default_text: str = "TBC") -> str:
    text = str(value or "").strip()
    if not text:
        return default_text
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.title()


def _clean_text(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("Ł", "£")
        .replace("Â£", "£")
        .replace("\xa0", " ")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


# Raised when required contract fields are unresolved so we never produce a
# broken PDF with TBC values.
class ContractRenderError(Exception):
    """Required contract fields are missing or unresolved."""


class HandbookRenderError(Exception):
    """Required handbook/org fields are missing or unresolved."""


def _resolve_company_address(
    org_settings: Optional[Dict[str, Any]],
    *,
    employee_overrides: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    settings = org_settings or {}
    overrides = employee_overrides or {}

    def _first_non_empty(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str):
                if value.strip():
                    return value.strip()
                continue
            return value
        return None

    # Canonical source: org/company settings. Employee overrides are fallback-only
    # for explicit recovery where org settings are not populated yet.
    return _first_non_empty(
        settings.get("company_address"),
        settings.get("organisation_address"),
        settings.get("business_address"),
        settings.get("registered_address"),
        settings.get("address"),
        settings.get("companyAddress"),
        settings.get("registeredOfficeAddress"),
        overrides.get("company_address"),
    )


def _resolve_contract_fields(employee: Dict[str, Any], org_settings: Optional[Dict[str, Any]]) -> Dict[str, str]:
    def _first_non_empty(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str):
                if value.strip():
                    return value.strip()
                continue
            return value
        return None

    issue_date = _format_date(_utcnow())
    contract_start = (
        employee.get("contract_start_date")
        or employee.get("start_date")
        or employee.get("employment_start_date")
        or employee.get("job_start_date")
        or employee.get("onboarding_start_date")
        or employee.get("promoted_at")
    )
    continuous_service = (
        employee.get("continuous_service_date")
        or employee.get("service_start_date")
        or contract_start
    )
    job_title_raw = (
        employee.get("job_title")
        or employee.get("role")
        or employee.get("position")
        or None
    )
    settings = org_settings or {}
    render_overrides = dict(employee.get("contract_render_overrides") or {})
    employment_details = dict(employee.get("employment_details") or {})
    pay = dict(employee.get("pay") or {})
    payroll = dict(employee.get("payroll") or {})
    compensation = dict(employee.get("compensation") or {})
    org_name = (
        settings.get("organisation_name")
        or settings.get("company_name")
        or settings.get("legal_name")
        or None
    )
    org_address = _resolve_company_address(settings, employee_overrides=render_overrides) or None
    # Hourly rate: try multiple field names used across different data models
    hourly_rate_raw = _first_non_empty(
        employee.get("hourly_rate"),
        employee.get("pay_rate"),
        employee.get("rate"),
        employee.get("base_rate"),
        employee.get("wage_rate"),
        render_overrides.get("hourly_rate"),
        employment_details.get("hourly_rate"),
        employment_details.get("pay_rate"),
        employment_details.get("rate"),
        pay.get("hourly_rate"),
        pay.get("rate"),
        payroll.get("hourly_rate"),
        payroll.get("rate"),
        compensation.get("hourly_rate"),
        compensation.get("rate"),
    )
    commencement_wording = "will commence"
    if contract_start:
        try:
            parsed = datetime.fromisoformat(str(contract_start).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed <= _utcnow():
                commencement_wording = "commenced"
        except Exception:
            pass
    return {
        "full_name": _employee_name(employee),
        "job_title": _format_job_title(job_title_raw),
        "issue_date": issue_date,
        "contract_start_date": _format_date(contract_start),
        "continuous_service_date": _format_date(continuous_service),
        "hourly_rate": _format_money(hourly_rate_raw),
        "sleep_in_rate": _format_money(employee.get("sleep_in_rate") or employee.get("sleepin_rate") or "40.00"),
        "company_name": str(org_name).strip() if org_name else "TBC",
        "company_address": org_address or "TBC",
        "commencement_wording": commencement_wording,
    }


# Canonical {{token}} replacements used by the migrated DOCX template.
# The DOCX template (zero_hour_contract_template.docx) was migrated in April 2026
# to use only {{token}} placeholders — no legacy (insert...) variants remain.
def _build_contract_replacements(fields: Dict[str, str]) -> Dict[str, str]:
    """Return a mapping of {{token}} placeholders to rendered field values."""
    f = fields
    return {
        "{{employee.full_name}}": f["full_name"],
        "{{employee.job_title}}": f["job_title"],
        "{{contract.issue_date}}": f["issue_date"],
        "{{contract.start_date}}": f["contract_start_date"],
        "{{contract.continuous_service_date}}": f["continuous_service_date"],
        "{{contract.hourly_rate}}": f["hourly_rate"],
        "{{contract.commencement_wording}}": f["commencement_wording"],
        "{{company.legal_name}}": f["company_name"],
        "{{company.address}}": f["company_address"],
        # Backward-compatible tokens
        "{{employee_name}}": f["full_name"],
        "{{issue_date}}": f["issue_date"],
        "{{job_title}}": f["job_title"],
        "{{contract_start_date}}": f["contract_start_date"],
        "{{continuous_service_date}}": f["continuous_service_date"],
        "{{hourly_rate}}": f["hourly_rate"],
        "{{sleep_in_rate}}": f["sleep_in_rate"],
        "{{company_name}}": f["company_name"],
        "{{company_address}}": f["company_address"],
        "{{commencement_wording}}": f["commencement_wording"],
    }


REQUIRED_CONTRACT_FIELDS = [
    "full_name",
    "job_title",
    "issue_date",
    "contract_start_date",
    "continuous_service_date",
    "hourly_rate",
    "company_name",
    "company_address",
]

# Values that indicate a field is unresolved and must not appear in a final PDF.
_UNRESOLVED_SENTINELS = {"TBC", "0.00", "", "None", "none"}


def _validate_contract_fields(fields: Dict[str, str]) -> None:
    """Raise ContractRenderError if any required field is missing or still a placeholder.

    Callers must catch this and return a 422 / incomplete-data response rather
    than producing a broken PDF with TBC values visible to the worker.
    """
    import logging
    _log = logging.getLogger(__name__)
    missing: List[str] = []
    for field in REQUIRED_CONTRACT_FIELDS:
        value = (fields.get(field) or "").strip()
        if not value or value in _UNRESOLVED_SENTINELS:
            _log.warning("Contract field '%s' is missing or unresolved: %r", field, value)
            missing.append(field)
    if missing:
        raise ContractRenderError(
            f"Contract cannot be rendered: the following required fields are unresolved: "
            f"{', '.join(missing)}. Set them on the employee record or org_settings before generating."
        )


# Template artifact phrases that must be removed from rendered output.
# These are leftover template-editor notes that should never appear in a
# worker-facing contract.
_ARTIFACT_PHRASES = [
    "Logo (if required)",
    "Generated by Osabea Healthcare Solutions worker agreements service.",
    "Generated by worker agreements service.",
]

_CONTRACT_UNRESOLVED_PATTERNS = [
    r"\bTBC\b",
    r"insert amount",
    r"£\s*\(insert amount\)",
    r"Ł\s*\(insert amount\)",
    r"\(Insert Employee Name\)",
    r"\(insert date of issue\)",
    r"\(insert name of employee\)",
    r"\(insert job title\)",
    r"\(insert 'will commence' or 'commenced'\)",
    r"\(insert date this contract starts\)",
    r"\(insert continuous service date of employment\)",
    r"£\s*\(insert amount\)\s*per hour",
    r"June\s*2023",
    r"Page\s*3\s*of\s*5",
    r"Company ConfidentialSMT1",
    r"\{\{[^{}]+\}\}",
]


def _replace_contract_text(text: str, fields: Dict[str, str]) -> str:
    updated = _clean_text(text)
    for old, new in _build_contract_replacements(fields).items():
        updated = updated.replace(old, new)
    legacy_map = {
        "(Insert Employee Name)": fields["full_name"],
        "(insert date of issue)": fields["issue_date"],
        "(insert name of employee)": fields["full_name"],
        "(insert job title)": fields["job_title"],
        "(insert 'will commence' or 'commenced')": fields["commencement_wording"],
        "(insert date this contract starts)": fields["contract_start_date"],
        "(insert continuous service date of employment)": fields["continuous_service_date"],
        "£(insert amount) per hour": f"£{fields['hourly_rate']} per hour",
    }
    for old, new in legacy_map.items():
        updated = updated.replace(old, new)
    # Strip any remaining template artifact phrases
    for artifact in _ARTIFACT_PHRASES:
        updated = updated.replace(artifact, "")
    return updated


def _assert_no_unresolved_contract_placeholders(blocks: List[Dict[str, Any]]) -> None:
    text_parts: List[str] = []
    for block in blocks:
        if block.get("type") == "paragraph":
            text_parts.append(str(block.get("text") or ""))
        elif block.get("type") == "table":
            for row in block.get("rows") or []:
                for cell in row:
                    text_parts.append(str(cell or ""))
    rendered_text = "\n".join(text_parts)

    hits: List[str] = []
    for pattern in _CONTRACT_UNRESOLVED_PATTERNS:
        if re.search(pattern, rendered_text, flags=re.IGNORECASE):
            hits.append(pattern)
    if hits:
        raise ContractRenderError(
            "Contract cannot be rendered: unresolved placeholders remain in output "
            f"(matched patterns: {', '.join(hits)})"
        )


def _is_canonical_contract_template_version(value: Any) -> bool:
    version = str(value or "").strip()
    return bool(version) and version.startswith(CANONICAL_CONTRACT_TEMPLATE_PREFIX)


# ---------------------------------------------------------------------------
# Handbook field resolution and validation
# ---------------------------------------------------------------------------

REQUIRED_HANDBOOK_FIELDS = [
    "company_name",
    "company_address",
]

HANDBOOK_CONTENT_FIELDS = [
    "company_about",
    "company_history",
    "service_description",
    "company_values",
    "aims_objectives",
    "staff_structure_summary",
    "shadowing_duration",
    "payroll_frequency",
    "payroll_day",
    "mileage_rate",
    "mileage_submission_deadline",
    "employee_assistance_details",
    "other_benefits",
    "occupational_health_provider",
    "main_office_contact",
    "registered_manager_name",
    "on_call_contact",
]

HANDBOOK_CONTENT_SAFE_FALLBACKS: Dict[str, str] = {
    "company_about": "Osabea Healthcare Solutions delivers person-centred care and compliant staffing support.",
    "company_history": "Osabea Healthcare Solutions continues to develop services in line with CQC standards and workforce needs.",
    "service_description": "We provide safe, responsive and effective care services with dignity and respect at the centre.",
    "company_values": "Our values are dignity, safety, compassion, accountability and continuous improvement.",
    "aims_objectives": "Our objective is to deliver safe, high-quality care while supporting staff development and wellbeing.",
    "staff_structure_summary": "Your line manager will explain local team structure, escalation routes and supervision arrangements.",
    "shadowing_duration": "Shadowing is arranged according to role risk and service needs before independent working.",
    "payroll_frequency": "Payroll is processed in line with your employment terms and issued on the published payroll schedule.",
    "payroll_day": "Payroll day is confirmed in your employment communication and payroll notice.",
    "mileage_submission_deadline": "Submit mileage claims by the published payroll cut-off for the relevant pay period.",
    "employee_assistance_details": "Employee wellbeing support is available through your line manager and designated support channels.",
    "other_benefits": "Additional benefits are provided in line with current company policy and eligibility rules.",
    "occupational_health_provider": "Occupational health support is arranged through the company-approved provider where required.",
    "main_office_contact": "Contact the main office through your usual manager or approved communication channels.",
    "on_call_contact": "Use the designated on-call rota contact shared by your manager for urgent out-of-hours support.",
}

_HANDBOOK_UNRESOLVED_SENTINELS = {"TBC", "", "None", "none", "xxxxxx"}

# {{token}} phrases that are known to appear in older handbook templates and
# must not survive into a rendered PDF even if the DOCX uses them.
_HANDBOOK_ARTIFACT_PHRASES = [
    "We advise that",
    "You could base these values",
    "[Add other benefits",
    "(add duration of probation)",
    "(insert Registered Manager name)",
    "(insert grievance contact name)",
    # Mileage placeholder is intentionally handled as a replacement below.
    # Do not strip it here or we lose the value in rendered output.
    "iCubeDALPro",
    "Unit 12, Harrods Road, Harlow, CM19 5BJ",
]

_HANDBOOK_UNRESOLVED_PATTERNS = [
    r"\bxxxxxx\b",
    r"\bxxxx\b",
    r"\[Add",
    r"\[Adjust",
    r"\[Delete",
    r"\{\{[^{}]+\}\}",
]


def _normalize_role_profile(employee: Dict[str, Any]) -> str:
    raw = (
        employee.get("role_profile")
        or employee.get("role")
        or employee.get("job_title")
        or "care_worker"
    )
    normalized = re.sub(r"[^a-z0-9]+", "_", str(raw).strip().lower()).strip("_")
    return normalized or "care_worker"


def _assert_no_unresolved_handbook_placeholders(blocks: List[Dict[str, Any]]) -> None:
    """
    Prevent publishing handbook PDFs that still contain template/editor tokens.
    """
    text_parts: List[str] = []
    for block in blocks:
        if block.get("type") == "paragraph":
            text_parts.append(str(block.get("text") or ""))
        elif block.get("type") == "table":
            for row in block.get("rows") or []:
                for cell in row:
                    text_parts.append(str(cell or ""))
    rendered_text = "\n".join(text_parts)

    hits: List[str] = []
    for pattern in _HANDBOOK_UNRESOLVED_PATTERNS:
        if re.search(pattern, rendered_text, flags=re.IGNORECASE):
            hits.append(pattern)
    if hits:
        raise HandbookRenderError(
            "Cannot render handbook: unresolved placeholders remain in output "
            f"(matched patterns: {', '.join(hits)})"
        )


def _resolve_handbook_fields(org_settings: Optional[Dict[str, Any]], employee: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Map org_settings → canonical handbook field dict."""
    s = org_settings or {}
    org_name = (
        s.get("organisation_name")
        or s.get("company_name")
        or None
    )
    render_overrides = dict((employee or {}).get("contract_render_overrides") or {})
    org_address = _resolve_company_address(s, employee_overrides=render_overrides) or None
    registered_manager = (
        s.get("registered_manager_name") or s.get("registered_manager") or "The Registered Manager"
    )
    registered_manager_email = s.get("registered_manager_email") or None
    grievance_contact = (
        s.get("grievance_contact_name") or s.get("hr_contact_name") or None
    )
    grievance_email = (
        s.get("grievance_contact_email") or s.get("hr_email") or None
    )
    appeal_contact = s.get("appeal_contact_name") or grievance_contact
    appeal_email = s.get("appeal_contact_email") or grievance_email
    hr_contact = s.get("hr_contact_name") or grievance_contact
    hr_email = s.get("hr_contact_email") or s.get("hr_email") or grievance_email
    mileage_rate = s.get("mileage_rate") or "0.45"
    about_us_text = s.get("about_us_text") or None
    phone_number = s.get("phone_number") or s.get("contact_phone") or None
    website = s.get("website") or s.get("website_url") or None
    company_about = s.get("company_about") or about_us_text
    company_history = s.get("company_history") or None
    service_description = s.get("service_description") or None
    company_values = s.get("company_values") or None
    aims_objectives = s.get("aims_objectives") or None
    staff_structure_summary = s.get("staff_structure_summary") or None
    shadowing_duration = s.get("shadowing_duration") or None
    payroll_frequency = s.get("payroll_frequency") or None
    payroll_day = s.get("payroll_day") or None
    mileage_submission_deadline = s.get("mileage_submission_deadline") or None
    employee_assistance_details = s.get("employee_assistance_details") or None
    other_benefits = s.get("other_benefits") or None
    occupational_health_provider = s.get("occupational_health_provider") or None
    main_office_contact = s.get("main_office_contact") or None
    on_call_contact = s.get("on_call_contact") or None
    return {
        "company_name": org_name,
        "company_address": org_address,
        "registered_manager_name": registered_manager,
        "registered_manager_email": registered_manager_email,
        "grievance_contact_name": grievance_contact,
        "grievance_contact_email": grievance_email,
        "appeal_contact_name": appeal_contact,
        "appeal_contact_email": appeal_email,
        "hr_contact_name": hr_contact,
        "hr_contact_email": hr_email,
        "mileage_rate": str(mileage_rate),
        "about_us_text": about_us_text,
        "phone_number": phone_number,
        "website": website,
        "company_about": company_about,
        "company_history": company_history,
        "service_description": service_description,
        "company_values": company_values,
        "aims_objectives": aims_objectives,
        "staff_structure_summary": staff_structure_summary,
        "shadowing_duration": shadowing_duration,
        "payroll_frequency": payroll_frequency,
        "payroll_day": payroll_day,
        "mileage_submission_deadline": mileage_submission_deadline,
        "employee_assistance_details": employee_assistance_details,
        "other_benefits": other_benefits,
        "occupational_health_provider": occupational_health_provider,
        "main_office_contact": main_office_contact,
        "on_call_contact": on_call_contact,
    }


def _handbook_content_needed(fields: Dict[str, Any]) -> List[str]:
    needed: List[str] = []
    for key in HANDBOOK_CONTENT_FIELDS:
        value = fields.get(key)
        if value is None:
            needed.append(key)
            continue
        if isinstance(value, str) and not value.strip():
            needed.append(key)
    return needed


def _validate_handbook_fields(fields: Dict[str, Any]) -> None:
    """Raise HandbookRenderError if required handbook fields are missing or unresolved."""
    import logging
    _log = logging.getLogger(__name__)
    missing: List[str] = []
    for field in REQUIRED_HANDBOOK_FIELDS:
        val = (fields.get(field) or "").strip()
        if not val or val in _HANDBOOK_UNRESOLVED_SENTINELS:
            _log.warning("Handbook field '%s' is missing or unresolved: %r", field, val)
            missing.append(field)
    if missing:
        raise HandbookRenderError(
            f"Cannot render handbook: required field(s) missing or unresolved: "
            f"{', '.join(missing)}"
        )


def _replace_handbook_text(text: str, fields: Dict[str, Any]) -> str:
    """Apply handbook field substitutions and strip any remaining artifact phrases."""
    updated = _clean_text(text)
    org_name = fields.get("company_name") or "Osabea Healthcare Solutions Ltd"
    org_address = fields.get("company_address") or ""

    # {{token}} replacements first
    token_map = {
        "{{company_name}}": org_name,
        "{{company_address}}": org_address,
        "{{company.about}}": fields.get("company_about") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_about"],
        "{{company.history}}": fields.get("company_history") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_history"],
        "{{company.service_description}}": fields.get("service_description") or HANDBOOK_CONTENT_SAFE_FALLBACKS["service_description"],
        "{{company.values}}": fields.get("company_values") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_values"],
        "{{company.aims_objectives}}": fields.get("aims_objectives") or HANDBOOK_CONTENT_SAFE_FALLBACKS["aims_objectives"],
        "{{company.staff_structure_summary}}": fields.get("staff_structure_summary") or HANDBOOK_CONTENT_SAFE_FALLBACKS["staff_structure_summary"],
        "{{policy.shadowing_duration}}": fields.get("shadowing_duration") or HANDBOOK_CONTENT_SAFE_FALLBACKS["shadowing_duration"],
        "{{policy.payroll_frequency}}": fields.get("payroll_frequency") or HANDBOOK_CONTENT_SAFE_FALLBACKS["payroll_frequency"],
        "{{policy.payroll_day}}": fields.get("payroll_day") or HANDBOOK_CONTENT_SAFE_FALLBACKS["payroll_day"],
        "{{registered_manager_name}}": fields.get("registered_manager_name") or "",
        "{{registered_manager_email}}": fields.get("registered_manager_email") or "",
        "{{grievance_contact_name}}": fields.get("grievance_contact_name") or "",
        "{{grievance_contact_email}}": fields.get("grievance_contact_email") or "",
        "{{appeal_contact_name}}": fields.get("appeal_contact_name") or "",
        "{{appeal_contact_email}}": fields.get("appeal_contact_email") or "",
        "{{hr_contact_name}}": fields.get("hr_contact_name") or "",
        "{{hr_contact_email}}": fields.get("hr_contact_email") or "",
        "{{mileage_rate}}": str(fields.get("mileage_rate") or "0.45"),
        "{{policy.mileage_submission_deadline}}": fields.get("mileage_submission_deadline") or HANDBOOK_CONTENT_SAFE_FALLBACKS["mileage_submission_deadline"],
        "{{policy.employee_assistance_details}}": fields.get("employee_assistance_details") or HANDBOOK_CONTENT_SAFE_FALLBACKS["employee_assistance_details"],
        "{{policy.other_benefits}}": fields.get("other_benefits") or HANDBOOK_CONTENT_SAFE_FALLBACKS["other_benefits"],
        "{{policy.occupational_health_provider}}": fields.get("occupational_health_provider") or HANDBOOK_CONTENT_SAFE_FALLBACKS["occupational_health_provider"],
        "{{contact.main_office}}": fields.get("main_office_contact") or HANDBOOK_CONTENT_SAFE_FALLBACKS["main_office_contact"],
        "{{contact.on_call}}": fields.get("on_call_contact") or HANDBOOK_CONTENT_SAFE_FALLBACKS["on_call_contact"],
        "{{about_us_text}}": fields.get("about_us_text") or "",
        "{{phone_number}}": fields.get("phone_number") or "",
        "{{website}}": fields.get("website") or "",
        # Backward-compatible non-dotted tokens
        "{{company_about}}": fields.get("company_about") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_about"],
        "{{company_history}}": fields.get("company_history") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_history"],
        "{{service_description}}": fields.get("service_description") or HANDBOOK_CONTENT_SAFE_FALLBACKS["service_description"],
        "{{company_values}}": fields.get("company_values") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_values"],
        "{{aims_objectives}}": fields.get("aims_objectives") or HANDBOOK_CONTENT_SAFE_FALLBACKS["aims_objectives"],
        "{{staff_structure_summary}}": fields.get("staff_structure_summary") or HANDBOOK_CONTENT_SAFE_FALLBACKS["staff_structure_summary"],
        "{{shadowing_duration}}": fields.get("shadowing_duration") or HANDBOOK_CONTENT_SAFE_FALLBACKS["shadowing_duration"],
        "{{payroll_frequency}}": fields.get("payroll_frequency") or HANDBOOK_CONTENT_SAFE_FALLBACKS["payroll_frequency"],
        "{{payroll_day}}": fields.get("payroll_day") or HANDBOOK_CONTENT_SAFE_FALLBACKS["payroll_day"],
        "{{mileage_submission_deadline}}": fields.get("mileage_submission_deadline") or HANDBOOK_CONTENT_SAFE_FALLBACKS["mileage_submission_deadline"],
        "{{employee_assistance_details}}": fields.get("employee_assistance_details") or HANDBOOK_CONTENT_SAFE_FALLBACKS["employee_assistance_details"],
        "{{other_benefits}}": fields.get("other_benefits") or HANDBOOK_CONTENT_SAFE_FALLBACKS["other_benefits"],
        "{{occupational_health_provider}}": fields.get("occupational_health_provider") or HANDBOOK_CONTENT_SAFE_FALLBACKS["occupational_health_provider"],
        "{{main_office_contact}}": fields.get("main_office_contact") or HANDBOOK_CONTENT_SAFE_FALLBACKS["main_office_contact"],
        "{{on_call_contact}}": fields.get("on_call_contact") or HANDBOOK_CONTENT_SAFE_FALLBACKS["on_call_contact"],
    }
    for token, val in token_map.items():
        updated = updated.replace(token, val)

    # Replace known legacy inline placeholders (non-tokenized text) that
    # still exist in older handbook DOCX content.
    inline_map = {
        "(insert mileage rate)": str(fields.get("mileage_rate") or "0.45"),
        "[Add company about]": fields.get("company_about") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_about"],
        "[Add company history]": fields.get("company_history") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_history"],
        "[Add service description]": fields.get("service_description") or HANDBOOK_CONTENT_SAFE_FALLBACKS["service_description"],
        "[Add company values]": fields.get("company_values") or HANDBOOK_CONTENT_SAFE_FALLBACKS["company_values"],
        "[Add aims and objectives]": fields.get("aims_objectives") or HANDBOOK_CONTENT_SAFE_FALLBACKS["aims_objectives"],
        "[Add staff structure summary]": fields.get("staff_structure_summary") or HANDBOOK_CONTENT_SAFE_FALLBACKS["staff_structure_summary"],
    }
    for old, new in inline_map.items():
        updated = updated.replace(old, new)

    # Some handbook templates contain a plain-language mileage sentence with no
    # explicit token, e.g. "paid at a rate of" followed by an empty run. Ensure
    # the configured rate is injected once so the rendered PDF always carries a
    # concrete mileage value.
    mileage_rate = str(fields.get("mileage_rate") or "0.45")
    if mileage_rate not in updated and "paid at a rate of" in updated.lower():
        updated = re.sub(
            r"(?i)paid at a rate of\s*",
            f"paid at a rate of {mileage_rate} ",
            updated,
            count=1,
        )

    # Legacy phrase replacements for old embedded names that may still be in
    # older template versions. The company name is intentionally kept in the
    # DOCX (it already reads "Osabea") but any old iCube names must be cleaned.
    legacy = {
        "iCubeDALPro Limited t/a iCareServicesGroup": org_name,
        "iCubeDALPro": org_name,
        "Unit 12, Harrods Road, Harlow, CM19 5BJ": org_address if org_address else "",
    }
    for old, new in legacy.items():
        if new:
            updated = updated.replace(old, new)

    # Strip any remaining artifact phrases that should never reach production
    for artifact in _HANDBOOK_ARTIFACT_PHRASES:
        updated = updated.replace(artifact, "")

    # Remove generic template-editor directives that appear in legacy handbook
    # docs and must never survive to rendered output.
    updated = re.sub(r"\[(?:Add|Adjust|Delete)[^\]]*\]", "", updated, flags=re.IGNORECASE)
    updated = re.sub(r"\bxxxxxx\b", "", updated, flags=re.IGNORECASE)
    updated = re.sub(r"\bxxxx\b", "", updated, flags=re.IGNORECASE)

    return updated


def _iter_block_items(parent):
    if isinstance(parent, DocumentObject):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Unsupported parent type")

    for child in parent_elm.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, parent)
        elif child.tag.endswith("}tbl"):
            yield Table(child, parent)


def _docx_to_blocks(doc: Document, transform) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = transform(block.text.strip())
            if text:
                blocks.append({"type": "paragraph", "text": text})
        elif isinstance(block, Table):
            rows: List[List[str]] = []
            for row in block.rows:
                cells = [transform(cell.text.strip()) for cell in row.cells]
                if any(cell for cell in cells):
                    rows.append(cells)
            if rows:
                blocks.append({"type": "table", "rows": rows})
    return blocks


async def _load_template_bytes(db, agreement_type: str) -> tuple[bytes, str, Path]:
    # Contract rendering is deterministic: always use the bundled canonical DOCX.
    # This prevents legacy/stale admin-uploaded templates from producing mixed
    # outputs across employees.
    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        return CONTRACT_TEMPLATE_DOCX_PATH.read_bytes(), CONTRACT_TEMPLATE_DOCX_PATH.name, CONTRACT_TEMPLATE_DOCX_PATH

    return HANDBOOK_TEMPLATE_PATH.read_bytes(), HANDBOOK_TEMPLATE_PATH.name, HANDBOOK_TEMPLATE_PATH


def _template_version(template_bytes: bytes, agreement_type: str) -> str:
    digest = hashlib.sha256(template_bytes).hexdigest()[:12]
    return f"{agreement_type}_v_{digest}"


def _create_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AgreementTitle",
        parent=styles["Heading1"],
        fontSize=17,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AgreementMeta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#4B5563"),
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AgreementBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        spaceAfter=2.5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AgreementFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6B7280"),
        alignment=TA_CENTER,
    ))
    return styles


def _render_pdf(
    blocks: List[Dict[str, Any]],
    title: str,
    subtitle: str,
    employee_name: str,
    *,
    add_generated_header: bool = True,
    add_generated_footer: bool = True,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    styles = _create_styles()
    story: List[Any] = []
    usable_width = A4[0] - (16 * mm) - (16 * mm)
    table_cell_style = ParagraphStyle(
        name="AgreementTableCell",
        parent=styles["AgreementBody"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        spaceAfter=0,
    )
    table_header_style = ParagraphStyle(
        name="AgreementTableHeader",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
    )

    if add_generated_header:
        logo = get_logo_image(width=42 * mm, height=18 * mm)
        if logo:
            story.append(logo)
            story.append(Spacer(1, 4 * mm))
        story.append(PdfParagraph(escape(title), styles["AgreementTitle"]))
        story.append(PdfParagraph(escape(subtitle), styles["AgreementMeta"]))
        story.append(PdfParagraph(escape(f"Prepared for: {employee_name}"), styles["AgreementMeta"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D1D5DB"), spaceBefore=2 * mm, spaceAfter=4 * mm))

    for block in blocks:
        if block["type"] == "paragraph":
            story.append(PdfParagraph(escape(block["text"]).replace("\n", "<br/>"), styles["AgreementBody"]))
        elif block["type"] == "table":
            rows = block["rows"]
            max_cols = max(len(r) for r in rows)
            normalized = [r + [""] * (max_cols - len(r)) for r in rows]

            # Some handbook tables contain merged cells with page-long prose.
            # ReportLab cannot split a single oversized table row across pages,
            # so render these as normal paragraphs instead of a strict table.
            if any(sum(len(str(cell)) for cell in row) > 1200 for row in normalized):
                header = [str(cell).strip() for cell in normalized[0] if str(cell).strip()]
                if header:
                    story.append(PdfParagraph(" | ".join(escape(h) for h in header), table_header_style))
                    story.append(Spacer(1, 1.5 * mm))
                for row in normalized[1:]:
                    row_text = " | ".join(str(cell).strip() for cell in row if str(cell).strip())
                    if row_text:
                        story.append(PdfParagraph(escape(row_text).replace("\n", "<br/>"), table_cell_style))
                        story.append(Spacer(1, 1.2 * mm))
                story.append(Spacer(1, 3 * mm))
                continue

            paragraph_rows: List[List[PdfParagraph]] = []
            for row_index, row in enumerate(normalized):
                style = table_header_style if row_index == 0 else table_cell_style
                paragraph_rows.append([
                    PdfParagraph(escape(str(cell)).replace("\n", "<br/>"), style)
                    for cell in row
                ])

            col_width = usable_width / max_cols if max_cols else usable_width
            table = PdfTable(
                paragraph_rows,
                repeatRows=1,
                colWidths=[col_width] * max_cols,
                splitByRow=1,
            )
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(table)
            story.append(Spacer(1, 3 * mm))

    if add_generated_footer:
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#E5E7EB"), spaceAfter=3 * mm))
        story.append(PdfParagraph(
            escape("Generated by Osabea Healthcare Solutions worker agreements service."),
            styles["AgreementFooter"],
        ))

    doc.build(story)
    return buffer.getvalue()


def _pdf_page_size(page) -> tuple[float, float]:
    box = page.mediabox
    return float(box.width), float(box.height)


def _merge_overlay(base_pdf_bytes: bytes, overlay_builders: Dict[int, Any]) -> bytes:
    reader = PdfReader(io.BytesIO(base_pdf_bytes))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        builder = overlay_builders.get(index)
        if builder:
            width, height = _pdf_page_size(page)
            from reportlab.pdfgen import canvas
            overlay_buffer = io.BytesIO()
            canv = canvas.Canvas(overlay_buffer, pagesize=(width, height))
            builder(canv, width, height)
            canv.save()
            overlay_page = PdfReader(io.BytesIO(overlay_buffer.getvalue())).pages[0]
            page.merge_page(overlay_page)
        writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _apply_contract_signatures(
    base_pdf_bytes: bytes,
    worker_signature_bytes: Optional[bytes] = None,
    worker_name: Optional[str] = None,
    worker_signed_at: Optional[str] = None,
    company_name: Optional[str] = None,
    company_signed_at: Optional[str] = None,
) -> bytes:
    def signature_page(canv, width, height):
        if worker_signature_bytes:
            try:
                sig = Image(io.BytesIO(worker_signature_bytes), width=52 * mm, height=15 * mm)
                sig.drawOn(canv, 188, 164)
            except Exception:
                pass
        canv.setFillColor(colors.black)
        canv.setFont("Helvetica", 10)
        if worker_name:
            canv.drawString(170, 140, worker_name)
        if worker_signed_at:
            canv.drawString(115, 114, _format_date(worker_signed_at))
        if company_name:
            canv.setFont("Helvetica-Bold", 10)
            canv.drawString(242, 87, company_name)
            canv.setFont("Helvetica", 10)
            canv.drawString(170, 60, company_name)
        if company_signed_at:
            canv.drawString(115, 34, _format_date(company_signed_at))

    # Derive last-page index from the actual rendered PDF (DOCX output is variable-length).
    _reader = PdfReader(io.BytesIO(base_pdf_bytes))
    last_page_idx = max(0, len(_reader.pages) - 1)
    return _merge_overlay(base_pdf_bytes, {last_page_idx: signature_page})


def current_contract_artifact(agreement: Dict[str, Any]) -> Optional[str]:
    state = (agreement or {}).get("contract_state")
    if state == "fully_executed":
        return agreement.get("executed_contract_pdf_url") or agreement.get("worker_signed_contract_pdf_url") or agreement.get("rendered_contract_pdf_url")
    if state == "awaiting_company_countersignature":
        return agreement.get("worker_signed_contract_pdf_url") or agreement.get("rendered_contract_pdf_url")
    return agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url")


def _agreement_rank(row: Dict[str, Any]) -> tuple:
    verification_status = row.get("verification_status")
    timestamp = (
        row.get("verified_at")
        or row.get("worker_signed_at")
        or row.get("acknowledged_at")
        or row.get("rejected_at")
        or row.get("updated_at")
        or row.get("created_at")
        or ""
    )
    if verification_status == "verified":
        return (4, timestamp)
    if row.get("contract_state") == "fully_executed":
        return (4, timestamp)
    if row.get("contract_state") == "awaiting_company_countersignature":
        return (3, timestamp)
    if row.get("acknowledged") or row.get("status") == "signed":
        return (2, timestamp)
    if verification_status == "rejected":
        return (0, timestamp)
    return (1, timestamp)


async def resolve_employee_agreement_state(db, employee: Dict[str, Any], agreement_type: str) -> Dict[str, Any]:
    # Normalize legacy alias to canonical handbook agreement type so admin and
    # worker surfaces always resolve the same latest row.
    if agreement_type == "employee_handbook_acknowledgement":
        agreement_type = HANDBOOK_AGREEMENT_TYPE
    employee_id = employee["id"]
    render_error_detail = None
    try:
        agreement = await ensure_agreement_rendered(db, employee, agreement_type)
    except HandbookRenderError as exc:
        render_error_detail = str(exc)
        agreement = await db.agreement_acknowledgements.find_one(
            {"employee_id": employee_id, "agreement_type": agreement_type},
            {"_id": 0},
        ) or {}
    except Exception as exc:
        render_error_detail = str(exc)
        agreement = await db.agreement_acknowledgements.find_one(
            {"employee_id": employee_id, "agreement_type": agreement_type},
            {"_id": 0},
        ) or {}

    rows = await db.agreement_acknowledgements.find(
        {
            "employee_id": employee_id,
            "agreement_type": agreement_type,
            "status": {"$ne": "superseded"},
            "$or": [
                {"superseded_by_acknowledgement_id": {"$exists": False}},
                {"superseded_by_acknowledgement_id": None},
                {"superseded_by_acknowledgement_id": ""},
            ],
        },
        {"_id": 0},
    ).to_list(20)
    if rows:
        rows = sorted(rows, key=_agreement_rank, reverse=True)
        canonical = dict(rows[0])
        for field_name in (
            "rendered_file_url",
            "rendered_contract_pdf_url",
            "worker_signed_contract_pdf_url",
            "executed_contract_pdf_url",
            "signed_document_url",
            "template_version",
            "rendered_at",
            "employee_name",
        ):
            if not canonical.get(field_name):
                for sibling in rows[1:]:
                    if sibling.get(field_name):
                        canonical[field_name] = sibling[field_name]
                        break
        agreement = canonical

    # Cross-check new-style agreement submissions (handbook only).
    # Admin verification for the handbook template lands in
    # `agreement_submissions`. The linked legacy `agreement_acknowledgements`
    # row is only kept in sync when the two were created together; older or
    # standalone submissions can leave `agreement_acknowledgements` without a
    # verified row, which caused the worker dashboard to show
    # "Being prepared by Osabea" for handbooks the admin had already
    # verified. Treat a verified submission as canonical truth so worker and
    # admin views agree. Contract flow is intentionally not touched here.
    if agreement_type == HANDBOOK_AGREEMENT_TYPE:
        try:
            handbook_submission = await db.agreement_submissions.find_one(
                {
                    "employee_id": employee_id,
                    "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
                    "verification_status": "verified",
                },
                {"_id": 0},
                sort=[("verified_at", -1)],
            )
        except Exception:
            handbook_submission = None
        if handbook_submission:
            agreement = dict(agreement or {})
            agreement["verification_status"] = "verified"
            if not agreement.get("verified_at"):
                agreement["verified_at"] = handbook_submission.get("verified_at")
            if not agreement.get("verified_by_name"):
                agreement["verified_by_name"] = handbook_submission.get("verified_by_name")
            # A verified submission implies the compliance record is
            # complete; mark acknowledged so downstream gating does not
            # re-surface "Being prepared by Osabea".
            agreement["acknowledged"] = True
            if not agreement.get("acknowledged_at"):
                agreement["acknowledged_at"] = (
                    handbook_submission.get("completed_at")
                    or handbook_submission.get("verified_at")
                )

    verification_status = (agreement or {}).get("verification_status")
    rejected = verification_status == "rejected"

    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        # Contract priority resolver:
        # If a newer non-superseded generated contract exists, it is the primary
        # worker/admin truth even if a stale acknowledgement row still says rejected.
        generated_contract_rows = await db.generated_contracts.find(
            {
                "employee_id": employee_id,
                "status": {"$ne": "superseded"},
                "$or": [
                    {"superseded_by_contract_id": {"$exists": False}},
                    {"superseded_by_contract_id": None},
                    {"superseded_by_contract_id": ""},
                ],
            },
            {"_id": 0},
        ).to_list(200)
        latest_generated_contract = None
        if generated_contract_rows:
            generated_contract_rows.sort(
                key=lambda row: (
                    str(row.get("generated_at") or ""),
                    str(row.get("created_at") or ""),
                    str(row.get("id") or ""),
                ),
                reverse=True,
            )
            latest_generated_contract = generated_contract_rows[0]

        if latest_generated_contract:
            latest_status = str(latest_generated_contract.get("status") or "").strip().lower()
            generated_to_state = {
                "pending_signature": "pending_signature",
                "awaiting_worker_signature": "awaiting_worker_signature",
                "signed": "awaiting_company_countersignature",
                "fully_executed": "fully_executed",
                "action_required": "rejected_reopen_required",
                "rejected": "rejected_reopen_required",
                "rejected_reopen_required": "rejected_reopen_required",
            }
            resolved_state = generated_to_state.get(latest_status)
            if resolved_state:
                agreement = dict(agreement or {})
                agreement["id"] = agreement.get("id") or f"agr_{CONTRACT_AGREEMENT_TYPE}_{employee_id}"
                agreement["generated_contract_id"] = latest_generated_contract.get("id")
                agreement["active_contract_id"] = latest_generated_contract.get("id")
                agreement["template_version"] = (
                    latest_generated_contract.get("template_version")
                    or agreement.get("template_version")
                )
                agreement["rendered_contract_pdf_url"] = (
                    latest_generated_contract.get("rendered_contract_pdf_url")
                    or latest_generated_contract.get("file_url")
                    or agreement.get("rendered_contract_pdf_url")
                    or agreement.get("rendered_file_url")
                )
                agreement["rendered_file_url"] = (
                    agreement.get("rendered_contract_pdf_url")
                    or latest_generated_contract.get("rendered_file_url")
                    or latest_generated_contract.get("file_url")
                    or agreement.get("rendered_file_url")
                )
                agreement["worker_signed_contract_pdf_url"] = (
                    latest_generated_contract.get("worker_signed_contract_pdf_url")
                    or agreement.get("worker_signed_contract_pdf_url")
                )
                agreement["executed_contract_pdf_url"] = (
                    latest_generated_contract.get("executed_contract_pdf_url")
                    or agreement.get("executed_contract_pdf_url")
                )
                agreement["status"] = latest_status
                agreement["contract_state"] = resolved_state
                if resolved_state in {"pending_signature", "awaiting_worker_signature"}:
                    agreement["verification_status"] = "pending"
                elif resolved_state == "fully_executed":
                    agreement["verification_status"] = "verified"

        contract_state = agreement.get("contract_state") or "awaiting_worker_signature"
        # Canonicalize worker-signable pending states so all API surfaces agree.
        canonical_contract_state = (
            "pending_signature"
            if contract_state in {"pending_signature", "awaiting_worker_signature"}
            else contract_state
        )
        verification_status = str((agreement or {}).get("verification_status") or "").strip().lower()
        canonical_contract = _is_canonical_contract_template_version(agreement.get("template_version"))
        contract_file_url = current_contract_artifact(agreement)
        render_issue_contract = render_error_detail if not canonical_contract else None
        worker_signed = bool(
            contract_state in ("awaiting_company_countersignature", "fully_executed")
            or agreement.get("worker_signed_at")
        )
        fully_executed = bool(contract_state == "fully_executed" or verification_status == "verified")
        effective_rejected = bool(contract_state in ("rejected_reopen_required", "action_required"))
        if effective_rejected:
            state_label = "Action required: please re-sign the updated contract"
        elif fully_executed:
            state_label = "Contract fully executed"
        elif worker_signed:
            state_label = "Signed by you — awaiting Osabea countersignature"
        else:
            state_label = "Action required: please review and sign your contract"
        return {
            "agreement_type": agreement_type,
            "acknowledgement": agreement or {},
            "render_issue": render_error_detail,
            "rejected": effective_rejected,
            "rejection_reason": agreement.get("rejection_reason"),
            "rejected_at": agreement.get("rejected_at"),
            "rejected_by_name": agreement.get("rejected_by_name"),
            "signed": worker_signed,
            "worker_signed": worker_signed,
            "verified": fully_executed,
            "fully_executed": fully_executed,
            "state_label": state_label,
            "can_sign": bool(canonical_contract and contract_file_url and (bool(effective_rejected) or contract_state in (None, "", "draft_rendered", "awaiting_worker_signature", "pending_signature", "rejected_reopen_required"))),
            "status": "rejected" if effective_rejected else canonical_contract_state,
            "raw_status": contract_state,
            "contract_state": canonical_contract_state,
            "file_url": contract_file_url,
            "download_url": contract_file_url,
            "rendered_file_url": agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url"),
            "worker_signed_contract_pdf_url": agreement.get("worker_signed_contract_pdf_url"),
            "executed_contract_pdf_url": agreement.get("executed_contract_pdf_url"),
            "signed_document_url": agreement.get("signed_document_url"),
            "template_version": agreement.get("template_version"),
            "rendered_at": agreement.get("rendered_at"),
            "employee_name": agreement.get("employee_name"),
            "signed_at": agreement.get("worker_signed_at") or agreement.get("signed_at") or agreement.get("acknowledged_at"),
            "worker_signed_at": agreement.get("worker_signed_at"),
            "worker_signer_name": agreement.get("worker_signer_name"),
            "company_signed_at": agreement.get("company_signed_at"),
            "company_signer_name": agreement.get("company_signer_name"),
            "verified_at": agreement.get("verified_at"),
            "verified_by_name": agreement.get("verified_by_name"),
            "verification_status": verification_status,
            "canonical_contract": canonical_contract,
            "render_issue": render_issue_contract,
            "has_acknowledgement": bool(agreement),
        }

    acknowledged = bool(agreement and agreement.get("acknowledged") and verification_status != "rejected")
    verified = bool(agreement and verification_status == "verified")
    # If a verified handbook acknowledgement already exists, that is the
    # canonical worker/admin truth. A later re-render failure must not knock the
    # worker back into a "being prepared" state for the same completed record.
    if verified:
        render_error_detail = None
    system_issue = bool(render_error_detail) and not (verified or acknowledged)
    if rejected:
        state_label = "Your handbook is being updated. You will be asked to review and sign once ready."
    elif system_issue:
        state_label = "System issue — Osabea is preparing your handbook. No action needed from you."
    elif verified:
        state_label = "Handbook acknowledged and verified"
    elif acknowledged:
        state_label = "Handbook acknowledged — awaiting admin verification"
    else:
        state_label = "Action required: please review and acknowledge the handbook"
    org_settings = await db.org_settings.find_one({}, {"_id": 0}) or {}
    handbook_fields = _resolve_handbook_fields(org_settings, employee)
    content_needed = _handbook_content_needed(handbook_fields)
    return {
        "agreement_type": agreement_type,
        "acknowledgement": agreement or {},
        "source_record_id": agreement.get("id") if agreement else None,
        "latest_active": bool(agreement),
        "render_issue": render_error_detail,
        "content_needed": content_needed,
        "rejected": rejected,
        "rejection_reason": agreement.get("rejection_reason"),
        "rejected_at": agreement.get("rejected_at"),
        "rejected_by_name": agreement.get("rejected_by_name"),
        "signed": acknowledged,
        "worker_acknowledged": acknowledged,
        "verified": verified,
        "system_issue": system_issue,
        "state_label": state_label,
        "can_sign": False if system_issue else (rejected or not acknowledged),
        "can_acknowledge": False if system_issue else (not rejected and not acknowledged),
        "status": "system_issue" if system_issue else ("rejected" if rejected else ("verified" if verified else ("signed" if acknowledged else "pending"))),
        "file_url": agreement.get("rendered_file_url"),
        "download_url": agreement.get("rendered_file_url"),
        "rendered_file_url": agreement.get("rendered_file_url"),
        "template_version": agreement.get("template_version"),
        "rendered_at": agreement.get("rendered_at"),
        "employee_name": agreement.get("employee_name"),
        "signed_at": agreement.get("acknowledged_at"),
        "verified_at": agreement.get("verified_at"),
        "verified_by_name": agreement.get("verified_by_name"),
        "verification_status": verification_status,
        "has_acknowledgement": bool(agreement),
    }


async def build_agreement_rendering(db, employee: Dict[str, Any], agreement_type: str) -> Dict[str, Any]:
    template_bytes, source_name, source_path = await _load_template_bytes(db, agreement_type)
    version = _template_version(template_bytes, agreement_type)
    org_settings = await db.org_settings.find_one({}, {"_id": 0}) or {}
    employee_name = _employee_name(employee)
    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        fields = _resolve_contract_fields(employee, org_settings)
        _validate_contract_fields(fields)
        doc = Document(io.BytesIO(template_bytes))
        blocks = _docx_to_blocks(doc, lambda text: _replace_contract_text(text, fields))
        _assert_no_unresolved_contract_placeholders(blocks)
        title = "Employment Contract"
        subtitle = f"{fields['company_name']} | Version {version}"
        pdf_bytes = _render_pdf(
            blocks,
            title,
            subtitle,
            employee_name,
            # Contracts should use the same shared branded header/logo wrapper
            # as other generated agreement documents.
            add_generated_header=True,
            add_generated_footer=False,
        )
    else:
        handbook_fields = _resolve_handbook_fields(org_settings, employee)
        _validate_handbook_fields(handbook_fields)
        doc = Document(io.BytesIO(template_bytes))
        blocks = _docx_to_blocks(doc, lambda text: _replace_handbook_text(text, handbook_fields))
        _assert_no_unresolved_handbook_placeholders(blocks)
        title = "Employee Handbook"
        subtitle = f"{handbook_fields['company_name']} | Version {version}"
        pdf_bytes = _render_pdf(blocks, title, subtitle, employee_name)
    return {
        "template_version": version,
        "template_source_name": source_name,
        "template_source_path": str(source_path),
        "employee_name": employee_name,
        "role_profile": _normalize_role_profile(employee),
        "pdf_bytes": pdf_bytes,
    }


async def _upload_agreement_artifact(employee_id: str, pdf_bytes: bytes, filename: str, folder_suffix: str) -> str:
    file_url = await upload_file_to_storage(
        pdf_bytes,
        filename,
        folder=f"agreements/{employee_id}/{folder_suffix}",
    )
    if not file_url:
        raise Exception(f"Failed to persist agreement artifact: {filename}")
    return file_url


async def ensure_agreement_rendered(db, employee: Dict[str, Any], agreement_type: str) -> Dict[str, Any]:
    existing = await db.agreement_acknowledgements.find_one(
        {"employee_id": employee["id"], "agreement_type": agreement_type},
        {"_id": 0},
    )
    rendering = await build_agreement_rendering(db, employee, agreement_type)

    # Do not early-return a stale row if it was rejected or its rendered PDF
    # reference is missing. This is the recovery path for employees who were
    # stuck behind an old rejected / self-completed handbook row after the
    # render pipeline was fixed.
    existing_verification = (existing or {}).get("verification_status")
    existing_is_rejected = existing_verification == "rejected"

    if agreement_type == CONTRACT_AGREEMENT_TYPE and existing:
        if (
            existing.get("template_version") == rendering["template_version"]
            and existing.get("rendered_contract_pdf_url")
            and _is_canonical_contract_template_version(existing.get("template_version"))
            and not existing_is_rejected
        ):
            return existing
    elif (
        existing
        and existing.get("template_version") == rendering["template_version"]
        and existing.get("rendered_file_url")
    ):
        # Handbook artifact stability: keep the same rendered handbook URL for
        # the same template version, even if the row was rejected. Re-rendering
        # on rejection is only expected when explicit regenerate is requested.
        metadata_backfill = {}
        if not existing.get("role_profile"):
            metadata_backfill["role_profile"] = rendering.get("role_profile")
        if not existing.get("rendered_at"):
            metadata_backfill["rendered_at"] = existing.get("updated_at") or _utcnow().isoformat()
        if metadata_backfill:
            metadata_backfill["updated_at"] = _utcnow().isoformat()
            await db.agreement_acknowledgements.update_one(
                {"employee_id": employee["id"], "agreement_type": agreement_type},
                {"$set": metadata_backfill},
            )
            existing = await db.agreement_acknowledgements.find_one(
                {"employee_id": employee["id"], "agreement_type": agreement_type},
                {"_id": 0},
            ) or existing
        return existing

    timestamp = _utcnow().strftime("%Y%m%d_%H%M%S")
    prefix = "contract" if agreement_type == CONTRACT_AGREEMENT_TYPE else "handbook"
    filename = f"{employee['id']}_{prefix}_{timestamp}.pdf"
    rendered_file_url = await _upload_agreement_artifact(
        employee["id"],
        rendering["pdf_bytes"],
        filename,
        "rendered",
    )

    now_iso = _utcnow().isoformat()
    update = {
        "employee_id": employee["id"],
        "employee_name": rendering["employee_name"],
        "agreement_type": agreement_type,
        "template_version": rendering["template_version"],
        "template_source_name": rendering["template_source_name"],
        "rendered_file_url": rendered_file_url,
        "rendered_at": now_iso,
        "role_profile": rendering.get("role_profile"),
        "updated_at": now_iso,
        "status": (existing or {}).get("status") or "pending",
        "verification_status": (existing or {}).get("verification_status") or "pending",
    }
    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        update.update({
            "contract_state": (existing or {}).get("contract_state") or "awaiting_worker_signature",
            "rendered_contract_pdf_url": rendered_file_url,
            "render_issue": None,
            "canonical_contract_render": True,
        })

    await db.agreement_acknowledgements.update_one(
        {"employee_id": employee["id"], "agreement_type": agreement_type},
        {
            "$set": update,
            "$setOnInsert": {
                "id": f"agr_{agreement_type}_{employee['id']}",
                "created_at": now_iso,
            },
        },
        upsert=True,
    )

    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        existing_contract = await db.generated_contracts.find_one(
            {"employee_id": employee["id"], "status": {"$in": ["pending_signature", "signed"]}},
            {"_id": 0, "id": 1},
        )
        contract_id = (existing_contract or {}).get("id") or f"contract_{employee['id']}_{rendering['template_version']}"
        await db.generated_contracts.update_one(
            {"id": contract_id},
            {
                "$set": {
                    "employee_id": employee["id"],
                    "employee_name": rendering["employee_name"],
                    "template_id": CONTRACT_TEMPLATE_ID,
                    "template_version": rendering["template_version"],
                    "rendered_file_url": rendered_file_url,
                    "rendered_contract_pdf_url": rendered_file_url,
                    "rendered_at": now_iso,
                    "status": "fully_executed" if (existing or {}).get("contract_state") == "fully_executed" else "awaiting_worker_signature",
                    "contract_state": (existing or {}).get("contract_state") or "awaiting_worker_signature",
                    "updated_at": now_iso,
                },
                "$setOnInsert": {
                    "id": contract_id,
                    "generated_at": now_iso,
                    "created_at": now_iso,
                },
            },
            upsert=True,
        )

    refreshed = await db.agreement_acknowledgements.find_one(
        {"employee_id": employee["id"], "agreement_type": agreement_type},
        {"_id": 0},
    )
    return refreshed or update


async def create_worker_signed_contract(
    db,
    employee: Dict[str, Any],
    agreement: Dict[str, Any],
    signature_bytes: bytes,
    signer_name: str,
) -> Dict[str, Any]:
    base_pdf_url = agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url")
    if not base_pdf_url:
        raise Exception("Rendered contract PDF is missing")
    base_pdf_bytes = await download_file_from_storage(base_pdf_url)
    if not base_pdf_bytes:
        raise Exception("Failed to load rendered contract PDF")

    now_iso = _utcnow().isoformat()
    signed_pdf_bytes = _apply_contract_signatures(
        base_pdf_bytes,
        worker_signature_bytes=signature_bytes,
        worker_name=signer_name,
        worker_signed_at=now_iso,
    )
    filename = f"{employee['id']}_worker_signed_contract_{_utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    signed_url = await _upload_agreement_artifact(employee["id"], signed_pdf_bytes, filename, "worker_signed")

    update = {
        "acknowledged": True,
        "acknowledged_at": now_iso,
        "status": "awaiting_company_countersignature",
        "contract_state": "awaiting_company_countersignature",
        "worker_signed_contract_pdf_url": signed_url,
        "signed_document_url": signed_url,
        "worker_signed_at": now_iso,
        "signed_at": now_iso,
        "worker_signer_name": signer_name,
        "signer_name": signer_name,
        "verification_status": "awaiting_company_countersignature",
        "verified_at": None,
        "verified_by": None,
        "verified_by_name": None,
        "updated_at": now_iso,
    }
    await db.agreement_acknowledgements.update_one(
        {"id": agreement["id"]},
        {"$set": update},
    )
    generated_contract_filter = (
        {"id": agreement.get("source_record_id")}
        if agreement.get("source_record_id")
        else {"employee_id": employee["id"], "template_version": agreement.get("template_version")}
    )
    await db.generated_contracts.update_one(
        generated_contract_filter,
        {
            "$set": {
                "status": "awaiting_company_countersignature",
                "contract_state": "awaiting_company_countersignature",
                "worker_signed_contract_pdf_url": signed_url,
                "signed_document_url": signed_url,
                "worker_signed_at": now_iso,
                "signed_at": now_iso,
                "worker_signer_name": signer_name,
                "signed_by_name": signer_name,
                "updated_at": now_iso,
            },
            "$setOnInsert": {
                "id": f"contract_{employee['id']}_{agreement.get('template_version')}",
                "employee_id": employee["id"],
                "employee_name": _employee_name(employee),
                "template_id": CONTRACT_TEMPLATE_ID,
                "template_version": agreement.get("template_version"),
                "rendered_file_url": agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url"),
                "rendered_contract_pdf_url": agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url"),
                "rendered_at": agreement.get("rendered_at"),
                "generated_at": agreement.get("rendered_at") or now_iso,
                "created_at": now_iso,
            },
        },
        upsert=True,
    )
    return await db.agreement_acknowledgements.find_one({"id": agreement["id"]}, {"_id": 0})


async def countersign_contract(
    db,
    agreement: Dict[str, Any],
    company_signer_name: str,
) -> Dict[str, Any]:
    base_pdf_url = agreement.get("worker_signed_contract_pdf_url") or agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url")
    if not base_pdf_url:
        raise Exception("Worker-signed contract PDF is missing")
    base_pdf_bytes = await download_file_from_storage(base_pdf_url)
    if not base_pdf_bytes:
        raise Exception("Failed to load contract PDF for countersignature")

    now_iso = _utcnow().isoformat()
    executed_pdf_bytes = _apply_contract_signatures(
        base_pdf_bytes,
        company_name=company_signer_name,
        company_signed_at=now_iso,
    )
    filename = f"{agreement['employee_id']}_executed_contract_{_utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    executed_url = await _upload_agreement_artifact(agreement["employee_id"], executed_pdf_bytes, filename, "executed")

    update = {
        "status": "fully_executed",
        "contract_state": "fully_executed",
        "verification_status": "verified",
        "executed_contract_pdf_url": executed_url,
        "company_signed_at": now_iso,
        "company_signer_name": company_signer_name,
        "verified_at": now_iso,
        "verified_by_name": company_signer_name,
        "updated_at": now_iso,
    }
    await db.agreement_acknowledgements.update_one({"id": agreement["id"]}, {"$set": update})
    await db.generated_contracts.update_one(
        {"employee_id": agreement["employee_id"], "template_version": agreement.get("template_version")},
        {
            "$set": {
                "status": "fully_executed",
                "contract_state": "fully_executed",
                "executed_contract_pdf_url": executed_url,
                "verified_at": now_iso,
                "verified_by_name": company_signer_name,
                "company_signed_at": now_iso,
                "company_signer_name": company_signer_name,
                "updated_at": now_iso,
            },
            "$setOnInsert": {
                "id": f"contract_{agreement['employee_id']}_{agreement.get('template_version')}",
                "employee_id": agreement["employee_id"],
                "employee_name": agreement.get("employee_name"),
                "template_id": CONTRACT_TEMPLATE_ID,
                "template_version": agreement.get("template_version"),
                "rendered_file_url": agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url"),
                "rendered_contract_pdf_url": agreement.get("rendered_contract_pdf_url") or agreement.get("rendered_file_url"),
                "rendered_at": agreement.get("rendered_at"),
                "generated_at": agreement.get("rendered_at") or now_iso,
                "created_at": now_iso,
            },
        },
        upsert=True,
    )
    return await db.agreement_acknowledgements.find_one({"id": agreement["id"]}, {"_id": 0})

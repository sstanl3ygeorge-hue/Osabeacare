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
CONTRACT_TEMPLATE_DOCX_PATH = ASSET_DIR / "zero_hour_contract_template.docx"
CONTRACT_TEMPLATE_PDF_PATH = ASSET_DIR / "zero_hour_contract_template.pdf"
HANDBOOK_TEMPLATE_PATH = ASSET_DIR / "employee_handbook_template.docx"

CONTRACT_TEMPLATE_ID = "ZERO_HOUR_CONTRACT_V1"
HANDBOOK_TEMPLATE_ID = "EMPLOYEE_HANDBOOK_FULL_V1"

CONTRACT_AGREEMENT_TYPE = "contract_acceptance"
HANDBOOK_AGREEMENT_TYPE = "handbook_acknowledgement"


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


def _resolve_contract_fields(employee: Dict[str, Any], org_settings: Optional[Dict[str, Any]]) -> Dict[str, str]:
    issue_date = _format_date(_utcnow())
    contract_start = (
        employee.get("contract_start_date")
        or employee.get("start_date")
        or employee.get("employment_start_date")
        or employee.get("job_start_date")
        or employee.get("promoted_at")
    )
    continuous_service = (
        employee.get("continuous_service_date")
        or employee.get("service_start_date")
        or contract_start
    )
    job_title = (
        employee.get("job_title")
        or employee.get("role")
        or employee.get("position")
        or "Care Worker"
    )
    org_name = (org_settings or {}).get("organisation_name") or "Osabea Healthcare Solutions Ltd"
    org_address = (
        (org_settings or {}).get("organisation_address")
        or (org_settings or {}).get("address")
        or "Osabea Healthcare Solutions Ltd"
    )
    return {
        "full_name": _employee_name(employee),
        "job_title": str(job_title).strip(),
        "issue_date": issue_date,
        "contract_start_date": _format_date(contract_start),
        "continuous_service_date": _format_date(continuous_service),
        "hourly_rate": _format_money(employee.get("hourly_rate") or employee.get("pay_rate") or employee.get("rate")),
        "sleep_in_rate": _format_money(employee.get("sleep_in_rate") or employee.get("sleepin_rate") or "40.00"),
        "company_name": org_name,
        "company_address": org_address,
        "commencement_wording": "commences",
    }


# Canonical {{token}} replacements used by the migrated DOCX template.
# The DOCX template (zero_hour_contract_template.docx) was migrated in April 2026
# to use only {{token}} placeholders — no legacy (insert...) variants remain.
def _build_contract_replacements(fields: Dict[str, str]) -> Dict[str, str]:
    """Return a mapping of {{token}} placeholders to rendered field values."""
    f = fields
    return {
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
    "hourly_rate",
    "company_name",
]


def _validate_contract_fields(fields: Dict[str, str]) -> None:
    """Log warnings for TBC or missing required contract fields."""
    import logging
    _log = logging.getLogger(__name__)
    for field in REQUIRED_CONTRACT_FIELDS:
        value = fields.get(field, "")
        if not value or value in ("TBC", "0.00"):
            _log.warning("Contract field '%s' is missing or placeholder: %r", field, value)


def _replace_contract_text(text: str, fields: Dict[str, str]) -> str:
    updated = _clean_text(text)
    for old, new in _build_contract_replacements(fields).items():
        updated = updated.replace(old, new)
    return updated


def _replace_handbook_text(text: str, org_settings: Optional[Dict[str, Any]]) -> str:
    updated = _clean_text(text)
    settings = org_settings or {}
    org_name = settings.get("organisation_name") or "Osabea Healthcare Solutions Ltd"
    org_address = settings.get("organisation_address") or settings.get("address") or ""
    registered_manager = settings.get("registered_manager_name") or settings.get("registered_manager") or "The Registered Manager"
    grievance_contact = settings.get("grievance_contact_name") or settings.get("hr_contact_name") or "HR Department"
    grievance_email = settings.get("grievance_contact_email") or settings.get("hr_email") or ""
    mileage_rate = settings.get("mileage_rate") or "0.45"
    replacements = {
        # {{token}} style
        "{{company_name}}": org_name,
        "{{company_address}}": org_address,
        "{{registered_manager}}": registered_manager,
        "{{grievance_contact_name}}": grievance_contact,
        "{{grievance_contact_email}}": grievance_email,
        "{{mileage_rate}}": str(mileage_rate),
        # Legacy embedded names in old handbook template
        "Osabea Healthcare Solutions Ltd": org_name,
        "Osabea Healthcare Solutions": org_name,
        "iCubeDALPro Limited t/a iCareServicesGroup": org_name,
        "iCubeDALPro": org_name,
        "Unit 12, Harrods Road, Harlow, CM19 5BJ": org_address,
        "(insert Registered Manager name)": registered_manager,
        "(insert grievance contact name)": grievance_contact,
        "(insert mileage rate)": str(mileage_rate),
    }
    for old, new in replacements.items():
        if new:  # don't replace with empty string
            updated = updated.replace(old, new)
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
    # Contract template may be uploaded/admin-selected in DB. If not, fall back
    # to the bundled source document provided for production rendering.
    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        contract_doc = await db.contract_templates.find_one({"active": True}, {"_id": 0})
        if contract_doc and contract_doc.get("file_url"):
            file_url = str(contract_doc.get("file_url"))
            local_path = Path(file_url)
            if file_url.startswith("/") and os.path.exists(file_url):
                return Path(file_url).read_bytes(), local_path.name or "contract_template.docx", local_path
            if local_path.exists():
                return local_path.read_bytes(), local_path.name, local_path
            remote = await download_file_from_storage(file_url)
            if remote:
                return remote, Path(file_url).name or "contract_template.docx", Path(file_url)
        # Always prefer DOCX so token substitution works reliably.
        # The PDF template (zero_hour_contract_template.pdf) used a coordinate-based
        # overlay that doesn't survive layout changes — DOCX rendering is definitive.
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


def _render_pdf(blocks: List[Dict[str, Any]], title: str, subtitle: str, employee_name: str) -> bytes:
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
            table = PdfTable(normalized, repeatRows=1)
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(table)
            story.append(Spacer(1, 3 * mm))

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
        title = "Employment Contract"
        subtitle = f"{fields['company_name']} | Version {version}"
        pdf_bytes = _render_pdf(blocks, title, subtitle, employee_name)
    else:
        doc = Document(io.BytesIO(template_bytes))
        blocks = _docx_to_blocks(doc, lambda text: _replace_handbook_text(text, org_settings))
        title = "Employee Handbook"
        subtitle = f"{(org_settings or {}).get('organisation_name') or 'Osabea Healthcare Solutions Ltd'} | Version {version}"
        pdf_bytes = _render_pdf(blocks, title, subtitle, employee_name)
    return {
        "template_version": version,
        "template_source_name": source_name,
        "template_source_path": str(source_path),
        "employee_name": employee_name,
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

    if agreement_type == CONTRACT_AGREEMENT_TYPE and existing:
        if (
            existing.get("template_version") == rendering["template_version"]
            and existing.get("rendered_contract_pdf_url")
        ):
            return existing
    elif (
        existing
        and existing.get("template_version") == rendering["template_version"]
        and existing.get("rendered_file_url")
    ):
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
        "updated_at": now_iso,
        "status": (existing or {}).get("status") or "pending",
        "verification_status": (existing or {}).get("verification_status") or "pending",
    }
    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        update.update({
            "contract_state": (existing or {}).get("contract_state") or "awaiting_worker_signature",
            "rendered_contract_pdf_url": rendered_file_url,
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
    await db.generated_contracts.update_one(
        {"employee_id": employee["id"], "template_version": agreement.get("template_version")},
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

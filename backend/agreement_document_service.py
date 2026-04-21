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
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph as PdfParagraph,
    SimpleDocTemplate,
    Spacer,
    Table as PdfTable,
    TableStyle,
)
from xml.sax.saxutils import escape

from services.pdf_service import get_logo_image
from supabase_storage import download_file_from_storage, upload_file_to_storage


BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "agreement_assets"
CONTRACT_TEMPLATE_PATH = ASSET_DIR / "zero_hour_contract_template.docx"
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


def _replace_contract_text(text: str, fields: Dict[str, str]) -> str:
    updated = _clean_text(text)
    replacements = {
        "(Insert Employee Name)": fields["full_name"],
        "(insert name of employee)": fields["full_name"],
        "(insert date of issue)": fields["issue_date"],
        "(insert job title)": fields["job_title"],
        "(insert 'will commence' or 'commenced')": fields["commencement_wording"],
        "(insert date this contract starts)": fields["contract_start_date"],
        "(insert continuous service date of employment)": fields["continuous_service_date"],
        "Ł(insert amount)": f"£{fields['hourly_rate']}",
        "Ł40": f"£{fields['sleep_in_rate']}",
        "iCubeDALPro Limited t/a iCareServicesGroup": fields["company_name"],
        "Unit 12, Harrods Road, Harlow, CM19 5BJ": fields["company_address"],
    }
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    return updated


def _replace_handbook_text(text: str, org_settings: Optional[Dict[str, Any]]) -> str:
    updated = _clean_text(text)
    org_name = (org_settings or {}).get("organisation_name")
    if org_name:
        updated = updated.replace("Osabea Healthcare Solutions Ltd", org_name)
        updated = updated.replace("Osabea Healthcare Solutions", org_name)
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
        return CONTRACT_TEMPLATE_PATH.read_bytes(), CONTRACT_TEMPLATE_PATH.name, CONTRACT_TEMPLATE_PATH

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


async def build_agreement_rendering(db, employee: Dict[str, Any], agreement_type: str) -> Dict[str, Any]:
    template_bytes, source_name, source_path = await _load_template_bytes(db, agreement_type)
    version = _template_version(template_bytes, agreement_type)
    org_settings = await db.org_settings.find_one({}, {"_id": 0}) or {}
    employee_name = _employee_name(employee)

    doc = Document(io.BytesIO(template_bytes))
    if agreement_type == CONTRACT_AGREEMENT_TYPE:
        fields = _resolve_contract_fields(employee, org_settings)
        blocks = _docx_to_blocks(doc, lambda text: _replace_contract_text(text, fields))
        title = "Employment Contract"
        subtitle = f"{fields['company_name']} | Version {version}"
    else:
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


async def ensure_agreement_rendered(db, employee: Dict[str, Any], agreement_type: str) -> Dict[str, Any]:
    existing = await db.agreement_acknowledgements.find_one(
        {"employee_id": employee["id"], "agreement_type": agreement_type},
        {"_id": 0},
    )
    rendering = await build_agreement_rendering(db, employee, agreement_type)

    if (
        existing
        and existing.get("template_version") == rendering["template_version"]
        and existing.get("rendered_file_url")
    ):
        return existing

    timestamp = _utcnow().strftime("%Y%m%d_%H%M%S")
    prefix = "contract" if agreement_type == CONTRACT_AGREEMENT_TYPE else "handbook"
    filename = f"{employee['id']}_{prefix}_{timestamp}.pdf"
    rendered_file_url = await upload_file_to_storage(
        rendering["pdf_bytes"],
        filename,
        folder=f"agreements/{employee['id']}",
    )
    if not rendered_file_url:
        raise Exception(f"Failed to persist rendered {agreement_type} document")

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
                    "rendered_at": now_iso,
                    "status": "signed" if (existing or {}).get("status") == "signed" else "pending_signature",
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

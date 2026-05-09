"""
Document Template Engine Routes

Phased implementation:
- Phase 1: Template engine collections/models
- Phase 2: Importer with DOCX/PDF extraction and placeholder detection
- Phase 3: Placeholder mapping draft/publish APIs
- Phase 4: Workflow placement query APIs
- Phase 5: Branded PDF generation
- Phase 6: Internal renewal workflow
- Phase 7: Audit events for immutable history
"""

import io
import asyncio
import re
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .dependencies import get_db, get_current_user, require_admin, log_audit_action
from constants.service_user_destinations import (
    get_service_user_destination_register,
    suggest_service_user_destination_section,
)
from supabase_storage import (
    is_supabase_storage_configured,
    upload_to_supabase,
    download_file_from_storage,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Document Template Engine"])
_indexes_ready = False
_indexes_lock = asyncio.Lock()


WORKFLOW_AREAS = {
    "compliance_policy",
    "staff_onboarding",
    "staff_policy_acknowledgement",
    "service_user_record",
    "care_plan",
    "risk_assessment",
    "body_map",
    "incident_report",
    "medication",
    "audit",
    "complaint",
    "insurance_certificate",
}

PLACEHOLDER_KEYWORDS = [
    "insert",
    "enter",
    "add here",
    "your company",
    "name of provider",
    "registered manager",
    "company name",
]


class DocumentTemplateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    doc_code: str
    title: str
    category: Optional[str] = None
    document_type: Optional[str] = None
    source_provider: Optional[str] = None
    source_renewed_until: Optional[str] = None
    owner_role: Optional[str] = None
    review_period_months: int = 12
    current_version_id: Optional[str] = None
    status: str
    workflow_area: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: str


class PlaceholderMapItem(BaseModel):
    placeholder_text: str
    system_variable: Optional[str] = None
    status: str = Field(default="accepted")  # accepted|ignored|manual
    notes: Optional[str] = None


class PlaceholderMappingUpdate(BaseModel):
    mappings: List[PlaceholderMapItem] = []
    manually_added_placeholders: List[str] = []


# Archive import models for Fast-Track implementation
class ArchiveImportManifestItem(BaseModel):
    filename: str
    folder_path: str
    file_size: int
    file_hash: str
    extension: str
    detected_type: str
    destination_section: str
    confidence: float
    priority: str
    notes: Optional[str] = None


class ArchiveImportPreview(BaseModel):
    filename: str
    folder_path: str
    detected_type: str
    destination_section: str
    confidence: float
    priority: str
    import_status: str = "pending"
    duplicate_check: Optional[Dict[str, Any]] = None


class ArchiveImportRequest(BaseModel):
    templates: List[str] = []  # List of filenames to import
    phase: Optional[str] = None  # 'phase_1_critical', 'phase_2_high', etc.
    folder_filter: Optional[str] = None


class ArchiveImportBatchRequest(BaseModel):
    manifest_items: List[ArchiveImportManifestItem] = []
    confirmed: bool = False


class PublishTemplateRequest(BaseModel):
    template_version_id: Optional[str] = None
    effective_date: Optional[str] = None
    review_date: Optional[str] = None
    confirmed_destination_section: Optional[str] = None


class GenerateDocumentRequest(BaseModel):
    template_id: str
    template_version_id: Optional[str] = None
    workflow_area: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    context: Dict[str, Any] = {}


class RenewalCompleteRequest(BaseModel):
    review_outcome: str  # no_change|updated|retired
    review_notes: Optional[str] = None
    approved_by: Optional[str] = None


class ClassificationPrediction(BaseModel):
    value: str
    confidence: float   # 0.0 – 1.0
    reasoning: str


class ClassificationResult(BaseModel):
    category: ClassificationPrediction
    document_type: ClassificationPrediction
    workflow_area: ClassificationPrediction
    usage_audience: ClassificationPrediction      # worker | admin | both
    primary_user_role: ClassificationPrediction   # support_worker | senior_carer | nurse | registered_manager | hr_manager | all_staff
    admin_owner_role: ClassificationPrediction    # registered_manager | compliance_lead | hr_manager | clinical_lead | finance
    worker_visibility: ClassificationPrediction   # visible | restricted | admin_only
    system_placement: ClassificationPrediction    # compliance_hub | care_plan_module | incident_module | staff_profile | medication_module | service_user_record | all_modules
    suggested_destination_section: Optional[ClassificationPrediction] = None
    frequency: ClassificationPrediction           # daily | per_shift | per_incident | weekly | monthly | quarterly | annual | one_off
    review_cycle_months: ClassificationPrediction
    suggested_title: Optional[str] = None


def _is_admin_user(user: Dict[str, Any]) -> bool:
    role = str((user or {}).get("role") or "").lower()
    return role in {"admin", "super_admin"}


async def _ensure_template_indexes(db) -> None:
    global _indexes_ready
    if _indexes_ready:
        return

    async with _indexes_lock:
        if _indexes_ready:
            return

        await db.document_templates.create_index("status", name="idx_document_templates_status")
        await db.document_templates.create_index("workflow_area", name="idx_document_templates_workflow_area")
        await db.document_template_versions.create_index("template_id", name="idx_document_template_versions_template_id")
        await db.document_template_versions.create_index("status", name="idx_document_template_versions_status")
        await db.document_renewals.create_index("renewal_due_date", name="idx_document_renewals_renewal_due_date")
        await db.document_audit_events.create_index([("timestamp", -1)], name="idx_document_audit_events_timestamp")

        _indexes_ready = True


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "template"


def _gen_doc_code(title: str, category: Optional[str] = None) -> str:
    prefix = "DOC"
    if category:
        cleaned = re.sub(r"[^A-Za-z0-9]+", "", category.upper())
        if cleaned:
            prefix = cleaned[:6]
    slug = re.sub(r"[^A-Za-z0-9]+", "", title.upper())[:10] or "TEMPLATE"
    return f"{prefix}-{slug}-{uuid.uuid4().hex[:6].upper()}"


def _hex_to_rgb_tuple(hex_text: str) -> Optional[Tuple[int, int, int]]:
    h = hex_text.strip().replace("#", "")
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return None


def _is_red_rgb(rgb: Optional[Tuple[int, int, int]]) -> bool:
    if not rgb:
        return False
    r, g, b = rgb
    # Red/near-red tolerance for template placeholders
    return r >= 190 and g <= 110 and b <= 110 and (r - max(g, b)) >= 70


def _extract_dates_from_text(text: str) -> List[str]:
    found: List[str] = []
    if not text:
        return found

    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{2,4}\b",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            raw = m.group(0)
            if raw not in found:
                found.append(raw)
    return found


def _extract_title_from_text(text: str) -> str:
    if not text:
        return "Imported Template"
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if len(s) < 4:
            continue
        return s[:200]
    return "Imported Template"


def _normalize_placeholder_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _append_placeholder_candidate(
    placeholders: List[Dict[str, Any]],
    seen: set,
    placeholder_text: str,
    raw_text: str,
    section: Optional[str],
    page: Optional[int],
    confidence: float,
    reason: str,
):
    normalized = _normalize_placeholder_text(placeholder_text)
    if not normalized:
        return
    key = (normalized.lower(), reason, section or "", page or -1)
    if key in seen:
        return
    seen.add(key)
    placeholders.append(
        {
            "raw_text": raw_text,
            "placeholder_text": normalized,
            "page": page,
            "section": section,
            "confidence": round(confidence, 2),
            "detection_reason": reason,
        }
    )


def _detect_bracket_placeholders(text: str) -> List[str]:
    return [_normalize_placeholder_text(m.group(0)) for m in re.finditer(r"\[[^\]\n]{1,120}\]", text or "")]


def _detect_blank_line_placeholders(text: str) -> List[str]:
    candidates: List[str] = []
    for m in re.finditer(r"_{3,}|\.{4,}|\b\.{3}\b", text or ""):
        candidates.append(_normalize_placeholder_text(m.group(0)))
    return candidates


def _detect_keyword_placeholders(text: str) -> List[str]:
    candidates: List[str] = []
    source = text or ""
    for kw in PLACEHOLDER_KEYWORDS:
        for m in re.finditer(re.escape(kw), source, re.IGNORECASE):
            start = max(0, m.start() - 30)
            end = min(len(source), m.end() + 40)
            snippet = _normalize_placeholder_text(source[start:end])
            if snippet:
                candidates.append(snippet)
    return candidates


def _extract_docx_template_data(file_bytes: bytes) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    try:
        from docx import Document
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"python-docx unavailable: {exc}")

    doc = Document(io.BytesIO(file_bytes))

    text_parts: List[str] = []
    placeholders: List[Dict[str, Any]] = []
    seen = set()

    paragraph_index = 0
    for para in doc.paragraphs:
        paragraph_index += 1
        para_text = para.text or ""
        if para_text.strip():
            text_parts.append(para_text)

        section = f"paragraph_{paragraph_index}"
        # 1) Red-text placeholder signal from runs
        for run in para.runs:
            run_text = _normalize_placeholder_text(run.text)
            if not run_text:
                continue

            rgb_tuple = None
            try:
                if run.font and run.font.color and run.font.color.rgb:
                    rgb_text = str(run.font.color.rgb)
                    rgb_tuple = _hex_to_rgb_tuple(rgb_text)
            except Exception:
                rgb_tuple = None

            if _is_red_rgb(rgb_tuple):
                _append_placeholder_candidate(
                    placeholders,
                    seen,
                    placeholder_text=run_text,
                    raw_text=run.text,
                    section=section,
                    page=None,
                    confidence=0.95,
                    reason="red_text",
                )

        # 2) Bracket text placeholders
        for bracketed in _detect_bracket_placeholders(para_text):
            _append_placeholder_candidate(
                placeholders,
                seen,
                placeholder_text=bracketed,
                raw_text=para_text,
                section=section,
                page=None,
                confidence=0.85,
                reason="bracketed_text",
            )

        # 3) Underline blank placeholders
        for blank in _detect_blank_line_placeholders(para_text):
            _append_placeholder_candidate(
                placeholders,
                seen,
                placeholder_text=blank,
                raw_text=para_text,
                section=section,
                page=None,
                confidence=0.8,
                reason="blank_line",
            )

        # 4) Keyword placeholders
        for keyword_snippet in _detect_keyword_placeholders(para_text):
            _append_placeholder_candidate(
                placeholders,
                seen,
                placeholder_text=keyword_snippet,
                raw_text=para_text,
                section=section,
                page=None,
                confidence=0.65,
                reason="keyword",
            )

    full_text = "\n".join([p for p in text_parts if p]).strip()
    metadata = {
        "source_type": "docx",
        "line_count": len(text_parts),
        "detected_placeholder_count": len(placeholders),
        "detected_dates": _extract_dates_from_text(full_text),
        "detected_title": _extract_title_from_text(full_text),
        "detection_summary": {
            "red_text": len([p for p in placeholders if p.get("detection_reason") == "red_text"]),
            "bracketed_text": len([p for p in placeholders if p.get("detection_reason") == "bracketed_text"]),
            "blank_line": len([p for p in placeholders if p.get("detection_reason") == "blank_line"]),
            "keyword": len([p for p in placeholders if p.get("detection_reason") == "keyword"]),
        },
    }
    return full_text, metadata, placeholders


def _int_color_to_rgb(color_value: Any) -> Optional[Tuple[int, int, int]]:
    if color_value is None:
        return None
    try:
        c = int(color_value)
        return (c >> 16) & 255, (c >> 8) & 255, c & 255
    except Exception:
        return None


def _extract_pdf_template_data(file_bytes: bytes) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    text_parts: List[str] = []
    placeholders: List[Dict[str, Any]] = []
    seen = set()

    span_color_supported = False

    try:
        import fitz  # PyMuPDF

        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        for page_index, page in enumerate(pdf, start=1):
            page_text = page.get_text("text") or ""
            if page_text.strip():
                text_parts.append(page_text)

            # Try color-span detection for red text placeholder signal
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = _normalize_placeholder_text(span.get("text", ""))
                            if not span_text:
                                continue
                            rgb_tuple = _int_color_to_rgb(span.get("color"))
                            if _is_red_rgb(rgb_tuple):
                                span_color_supported = True
                                _append_placeholder_candidate(
                                    placeholders,
                                    seen,
                                    placeholder_text=span_text,
                                    raw_text=span.get("text", ""),
                                    section=f"page_{page_index}",
                                    page=page_index,
                                    confidence=0.9,
                                    reason="red_text",
                                )
            except Exception:
                # Continue with fallback detectors
                pass

            # Fallback detectors at page level
            for bracketed in _detect_bracket_placeholders(page_text):
                _append_placeholder_candidate(
                    placeholders,
                    seen,
                    placeholder_text=bracketed,
                    raw_text=page_text,
                    section=f"page_{page_index}",
                    page=page_index,
                    confidence=0.85,
                    reason="bracketed_text",
                )

            for blank in _detect_blank_line_placeholders(page_text):
                _append_placeholder_candidate(
                    placeholders,
                    seen,
                    placeholder_text=blank,
                    raw_text=page_text,
                    section=f"page_{page_index}",
                    page=page_index,
                    confidence=0.78,
                    reason="blank_line",
                )

            for keyword_snippet in _detect_keyword_placeholders(page_text):
                _append_placeholder_candidate(
                    placeholders,
                    seen,
                    placeholder_text=keyword_snippet,
                    raw_text=page_text,
                    section=f"page_{page_index}",
                    page=page_index,
                    confidence=0.62,
                    reason="keyword",
                )

        pdf.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {exc}")

    full_text = "\n".join([p for p in text_parts if p]).strip()
    metadata = {
        "source_type": "pdf",
        "page_count": len(text_parts),
        "detected_placeholder_count": len(placeholders),
        "detected_dates": _extract_dates_from_text(full_text),
        "detected_title": _extract_title_from_text(full_text),
        "span_color_detection_used": span_color_supported,
        "detection_summary": {
            "red_text": len([p for p in placeholders if p.get("detection_reason") == "red_text"]),
            "bracketed_text": len([p for p in placeholders if p.get("detection_reason") == "bracketed_text"]),
            "blank_line": len([p for p in placeholders if p.get("detection_reason") == "blank_line"]),
            "keyword": len([p for p in placeholders if p.get("detection_reason") == "keyword"]),
        },
    }
    return full_text, metadata, placeholders


async def _store_imported_file(file_bytes: bytes, filename: str) -> Dict[str, Optional[str]]:
    safe = _sanitize_filename(filename)

    if is_supabase_storage_configured():
        result = await upload_to_supabase(file_bytes, safe, folder="template_library/imports")
        return {
            "storage_path": result.get("path"),
            "public_url": result.get("url"),
            "local_path": None,
        }

    local_root = Path(__file__).resolve().parents[2] / "exports" / "template_library" / "imports"
    local_root.mkdir(parents=True, exist_ok=True)
    local_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{safe}"
    local_path = local_root / local_name
    local_path.write_bytes(file_bytes)
    return {
        "storage_path": str(local_path),
        "public_url": None,
        "local_path": str(local_path),
    }


async def _write_document_audit_event(
    *,
    db,
    actor_id: str,
    document_type: str,
    document_id: str,
    action: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
):
    event = {
        "id": str(uuid.uuid4()),
        "document_type": document_type,
        "document_id": document_id,
        "action": action,
        "actor_id": actor_id,
        "timestamp": _utc_now_iso(),
        "before": before or {},
        "after": after or {},
        "reason": reason,
    }
    await db.document_audit_events.insert_one(event)


def _build_placeholder_map_from_detected(detected: List[Dict[str, Any]]) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {}
    for item in detected:
        key = _normalize_placeholder_text(item.get("placeholder_text", ""))
        if not key:
            continue
        mapping[key] = {
            "system_variable": None,
            "status": "detected",
            "confidence": item.get("confidence", 0.0),
            "detection_reason": item.get("detection_reason"),
        }
    return mapping


def _replace_with_context(text: str, context: Dict[str, Any], placeholder_map: Dict[str, Any]) -> str:
    if not text:
        return ""

    resolved = str(text)

    # 1) Explicit placeholder map substitution (e.g. [Company Name] -> company.name)
    for placeholder_text, meta in (placeholder_map or {}).items():
        system_var = (meta or {}).get("system_variable")
        status = (meta or {}).get("status")
        if not system_var or status == "ignored":
            continue

        value = context
        for part in str(system_var).split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if value is None:
            continue

        resolved = resolved.replace(placeholder_text, str(value))

    # 2) Common generated-date token fallback
    generated_date = context.get("document", {}).get("generated_date") if isinstance(context.get("document"), dict) else None
    if generated_date:
        resolved = resolved.replace("[Date]", str(generated_date))

    return resolved


def _render_branded_pdf(
    *,
    template_doc: Dict[str, Any],
    version_doc: Dict[str, Any],
    context: Dict[str, Any],
    completed_by: Optional[str],
    approved_by: Optional[str],
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    brand = colors.HexColor("#004D4D")
    muted = colors.HexColor("#6B7280")
    soft = colors.HexColor("#F8FAFA")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, alignment=TA_CENTER, textColor=brand, spaceAfter=6)
    sub_style = ParagraphStyle("DocSub", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, textColor=muted, spaceAfter=8)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=12, textColor=brand, spaceBefore=8, spaceAfter=4)

    generated_at = _utc_now_iso()
    generated_date = generated_at[:10]

    payload_context = {
        **(context or {}),
        "document": {
            "generated_date": generated_date,
            "review_date": version_doc.get("review_date"),
        },
    }

    title = template_doc.get("title") or version_doc.get("extracted_metadata", {}).get("detected_title") or "Generated Document"
    doc_code = template_doc.get("doc_code") or "N/A"

    extracted_text = version_doc.get("extracted_text") or ""
    placeholder_map = version_doc.get("placeholder_map") or {}
    rendered_text = _replace_with_context(extracted_text, payload_context, placeholder_map)

    elements: List[Any] = []
    elements.append(Paragraph("OsabeaCare", title_style))
    elements.append(Paragraph("Branded Operational Document", sub_style))

    header_data = [
        ["Title", title],
        ["Doc Code", doc_code],
        ["Version", str(version_doc.get("version", 1))],
        ["Effective Date", version_doc.get("effective_date") or ""],
        ["Review Date", version_doc.get("review_date") or ""],
        ["Generated Date", generated_date],
        ["Completed By", completed_by or ""],
        ["Approved By", approved_by or ""],
        ["Source Provider", template_doc.get("source_provider") or ""],
    ]

    table = Table(header_data, colWidths=[40 * mm, 130 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), soft),
                ("TEXTCOLOR", (0, 0), (0, -1), brand),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=1, color=brand))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Generated Content", heading_style))
    if rendered_text.strip():
        for para in rendered_text.splitlines():
            line = para.strip()
            if not line:
                continue
            elements.append(Paragraph(line, body_style))
    else:
        elements.append(Paragraph("No extracted template content available.", body_style))

    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    elements.append(
        Paragraph(
            (
                f"Audit footer: Generated at {generated_at}. "
                f"Template {template_doc.get('id')} version {version_doc.get('version', 1)}. "
                "Internal Osabea review cycle applies independently from source-provider renewal statements."
            ),
            ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=muted, spaceBefore=4),
        )
    )

    doc.build(elements)
    return buffer.getvalue()


async def _save_generated_pdf(pdf_bytes: bytes, filename: str) -> Dict[str, Optional[str]]:
    safe = _sanitize_filename(filename)

    if is_supabase_storage_configured():
        result = await upload_to_supabase(pdf_bytes, safe, folder="template_library/generated")
        return {
            "generated_pdf_path": result.get("path"),
            "generated_pdf_url": result.get("url"),
            "local_path": None,
        }

    local_root = Path(__file__).resolve().parents[2] / "exports" / "template_library" / "generated"
    local_root.mkdir(parents=True, exist_ok=True)
    local_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{safe}"
    local_path = local_root / local_name
    local_path.write_bytes(pdf_bytes)
    return {
        "generated_pdf_path": str(local_path),
        "generated_pdf_url": None,
        "local_path": str(local_path),
    }


def _compute_review_date(effective_date: Optional[str], review_period_months: int) -> Optional[str]:
    if not effective_date:
        return None
    try:
        base = date.fromisoformat(effective_date)
    except Exception:
        return None
    return (base + relativedelta(months=review_period_months)).isoformat()


async def _ensure_renewal_record_for_active_template(
    *,
    db,
    template: Dict[str, Any],
    template_version_id: str,
    actor_id: str,
):
    review_date = None
    current_version = await db.document_template_versions.find_one({"id": template_version_id}, {"_id": 0})
    if current_version:
        review_date = current_version.get("review_date")

    if not review_date:
        review_date = _compute_review_date(current_version.get("effective_date") if current_version else None, template.get("review_period_months", 12))

    if not review_date:
        return

    exists = await db.document_renewals.find_one(
        {
            "template_id": template["id"],
            "template_version_id": template_version_id,
            "renewal_due_date": review_date,
        },
        {"_id": 0, "id": 1},
    )
    if exists:
        return

    renewal_doc = {
        "id": str(uuid.uuid4()),
        "template_id": template["id"],
        "template_version_id": template_version_id,
        "renewal_due_date": review_date,
        "status": "pending",
        "review_outcome": None,
        "reviewed_by": None,
        "approved_by": None,
        "review_notes": None,
        "certificate_pdf_path": None,
        "certificate_pdf_url": None,
        "completed_at": None,
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }
    await db.document_renewals.insert_one(renewal_doc)

    await _write_document_audit_event(
        db=db,
        actor_id=actor_id,
        document_type="document_renewal",
        document_id=renewal_doc["id"],
        action="renewal_task_created",
        before={},
        after={
            "template_id": template["id"],
            "template_version_id": template_version_id,
            "renewal_due_date": review_date,
        },
        reason="Auto-created on template publish",
    )


# ---------------------------------------------------------------------------
# Classification Engine
# ---------------------------------------------------------------------------

def _classify_document(filename: str, text_sample: str = "") -> ClassificationResult:
    """
    Rule-based document classification.
    Accepts a filename and optional text sample extracted from the document.
    Returns structured predictions with confidence scores.
    """
    combined = (filename + " " + text_sample).lower()
    stem = Path(filename).stem.lower().replace("_", " ").replace("-", " ")

    # --- Category & document_type ---
    # Ordered from most specific to least specific
    CAT_RULES: List[Tuple[str, str, List[str]]] = [
        # (category, document_type, trigger_keywords)
        ("Policy", "policy", ["policy", "pol-"]),
        ("Procedure", "procedure", ["procedure", "proc-", "process", "sop"]),
        ("Form", "form", ["form", "sheet", "log", "register"]),
        ("Checklist", "checklist", ["checklist", "check list", "chk-"]),
        ("Assessment", "assessment", ["assessment", "ass-", "appraisal", "evaluation"]),
        ("Agreement", "agreement", ["agreement", "contract", "declaration", "consent"]),
        ("Certificate", "certificate", ["certificate", "cert-", "qualification"]),
        ("Record", "record", ["record", "rec-", "diary", "chart", "tracker"]),
        ("Incident", "incident", ["incident", "accident", "near miss", "datix"]),
        ("Report", "report", ["report", "rpt-"]),
    ]

    cat_value = "Policy"
    cat_doc_type = "policy"
    cat_conf = 0.45
    cat_reasoning = "Default fallback — no category keywords matched"
    for cat, doc_type, kws in CAT_RULES:
        if any(k in combined for k in kws):
            cat_value = cat
            cat_doc_type = doc_type
            cat_conf = 0.90 if any(k in stem for k in kws) else 0.72
            cat_reasoning = f"Matched keyword(s): {[k for k in kws if k in combined]}"
            break

    # --- Workflow area ---
    WF_RULES: List[Tuple[str, List[str], float]] = [
        ("body_map", ["body map", "body chart", "skin integrity"], 0.97),
        ("medication", ["medication", "mar sheet", "medicine", "drug", "controlled drug", "blister", "prescri"], 0.97),
        ("incident_report", ["incident", "accident", "near miss", "datix", "riddor"], 0.95),
        ("risk_assessment", ["risk assessment", "risk assess", "coshh", "lone worker risk", "hazard"], 0.94),
        ("care_plan", ["care plan", "support plan", "daily notes", "outcome-based"], 0.93),
        ("complaint", ["complaint", "compliment", "grievance", "feedback form"], 0.93),
        ("insurance_certificate", ["insurance", "employers liability", "public liability", "indemnity"], 0.96),
        ("audit", ["audit", "cqc audit", "mock inspection", "self assessment"], 0.91),
        ("service_user_record", ["service user", "person centred", "service user record", "su record"], 0.88),
        ("staff_onboarding", ["induction", "onboarding", "dbs", "reference check", "right to work", "new starter", "probation"], 0.90),
        ("compliance_policy", ["policy", "procedure", "health and safety", "fire safety", "information governance", "gdpr", "equality", "whistleblowing"], 0.75),
    ]

    wf_value = "compliance_policy"
    wf_conf = 0.40
    wf_reasoning = "Default fallback — no workflow keyword matched"
    for wf, kws, conf in WF_RULES:
        if any(k in combined for k in kws):
            matched = [k for k in kws if k in combined]
            boost = 0.05 if any(k in stem for k in kws) else 0.0
            wf_value = wf
            wf_conf = min(1.0, conf + boost)
            wf_reasoning = f"Matched: {matched}"
            break

    # --- Usage audience ---
    AUD_RULES: List[Tuple[str, List[str], float]] = [
        ("admin", ["registered manager", "manager only", "senior only", "directors", "leadership", "hr only"], 0.92),
        ("worker", ["support worker", "care worker", "carer", "staff signature", "keyworker"], 0.88),
        ("both", ["all staff", "organisation", "whole team", "everyone", "staff and management"], 0.80),
    ]

    aud_value = "both"
    aud_conf = 0.50
    aud_reasoning = "Default — shared document assumed"
    # Override by document category context
    if cat_value in ("Policy", "Procedure"):
        aud_value = "both"
        aud_conf = 0.65
        aud_reasoning = "Policies and procedures typically apply to all staff"
    if cat_value in ("Assessment", "Checklist", "Form"):
        aud_value = "worker"
        aud_conf = 0.60
        aud_reasoning = "Operational forms typically completed by frontline workers"
    for aud, kws, conf in AUD_RULES:
        if any(k in combined for k in kws):
            aud_value = aud
            aud_conf = conf
            aud_reasoning = f"Matched: {[k for k in kws if k in combined]}"
            break

    # --- Frequency ---
    FREQ_RULES: List[Tuple[str, List[str], float]] = [
        ("daily", ["daily", "every day", "each day", "day sheet", "daily record"], 0.95),
        ("per_shift", ["per shift", "each shift", "shift handover", "handover"], 0.90),
        ("per_incident", ["per incident", "incident-specific", "as and when", "as required", "near miss"], 0.92),
        ("weekly", ["weekly", "each week", "every week"], 0.90),
        ("monthly", ["monthly", "each month", "every month"], 0.90),
        ("quarterly", ["quarterly", "every quarter", "q1", "q2", "q3", "q4"], 0.88),
        ("annual", ["annual", "yearly", "year", "once a year"], 0.85),
        ("one_off", ["one off", "once only", "single use", "initial", "induction", "registration"], 0.85),
    ]

    # Contextual defaults by category
    freq_defaults = {
        "Policy": ("annual", 0.55, "Policies are typically reviewed annually"),
        "Procedure": ("annual", 0.55, "Procedures are typically reviewed annually"),
        "Assessment": ("annual", 0.50, "Assessments are often annual"),
        "Form": ("per_incident", 0.55, "Forms are typically completed per incident or need"),
        "Checklist": ("daily", 0.52, "Checklists are often used daily"),
        "Record": ("daily", 0.52, "Records are usually maintained daily"),
        "Incident": ("per_incident", 0.70, "Incident documents are completed per incident"),
        "Certificate": ("annual", 0.75, "Certificates are typically renewed annually"),
        "Agreement": ("one_off", 0.70, "Agreements are typically one-off documents"),
        "Report": ("monthly", 0.50, "Reports are often produced monthly"),
    }
    freq_value, freq_conf, freq_reasoning = freq_defaults.get(
        cat_value, ("annual", 0.45, "Default fallback")
    )
    for freq, kws, conf in FREQ_RULES:
        if any(k in combined for k in kws):
            freq_value = freq
            freq_conf = conf
            freq_reasoning = f"Matched: {[k for k in kws if k in combined]}"
            break

    # --- Review cycle months ---
    REV_RULES: List[Tuple[int, List[str], float]] = [
        (6, ["six month", "6 month", "half yearly", "half year"], 0.95),
        (12, ["annual review", "annually review", "yearly review", "12 month", "one year review"], 0.95),
        (24, ["two year", "2 year", "every two years", "biennial"], 0.95),
        (36, ["three year", "3 year", "every three years"], 0.95),
    ]

    rev_defaults = {
        "Policy": (12, 0.75, "Policies default to 12-month review cycle"),
        "Procedure": (24, 0.65, "Procedures often reviewed every 2 years"),
        "Form": (12, 0.60, "Forms reviewed annually"),
        "Checklist": (12, 0.60, "Checklists reviewed annually"),
        "Assessment": (12, 0.70, "Assessments reviewed annually"),
        "Agreement": (12, 0.65, "Agreements reviewed annually"),
        "Certificate": (12, 0.85, "Certificates renewed annually"),
        "Record": (12, 0.55, "Records reviewed annually"),
        "Incident": (12, 0.55, "Incident documents reviewed annually"),
        "Report": (12, 0.55, "Reports reviewed annually"),
    }
    rev_months, rev_conf, rev_reasoning = rev_defaults.get(
        cat_value, (12, 0.50, "Default 12-month review cycle")
    )
    for months, kws, conf in REV_RULES:
        if any(k in combined for k in kws):
            rev_months = months
            rev_conf = conf
            rev_reasoning = f"Matched explicit review period keywords: {[k for k in kws if k in combined]}"
            break

    # --- Suggested title ---
    raw_stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    # Strip common noise prefixes
    for noise in ("V1", "V2", "V3", "DRAFT", "FINAL", "COPY", "template"):
        raw_stem = re.sub(rf"\b{noise}\b", "", raw_stem, flags=re.IGNORECASE).strip()
    suggested_title = re.sub(r"\s+", " ", raw_stem).title() if raw_stem else None

    suggested_destination = suggest_service_user_destination_section(
        filename=filename,
        text_sample=text_sample,
        classification={
            "category": {"value": cat_value},
            "document_type": {"value": cat_doc_type},
            "workflow_area": {"value": wf_value},
            "usage_audience": {"value": aud_value},
            "primary_user_role": {"value": pur_value},
            "admin_owner_role": {"value": aor_value},
            "worker_visibility": {"value": vis_value},
            "frequency": {"value": freq_value},
            "review_cycle_months": {"value": str(rev_months)},
            "suggested_title": suggested_title,
        },
    )

    # --- Primary user role --- who primarily completes / uses this document
    PUR_RULES: List[Tuple[str, List[str], float]] = [
        ("nurse",               ["medication", "mar sheet", "medicine", "drug", "controlled drug", "prescri", "clinical"], 0.87),
        ("registered_manager",  ["registered manager", "audit", "cqc", "mock inspection", "complaint", "grievance",
                                  "insurance", "employers liability", "indemnity", "directors"], 0.88),
        ("hr_manager",          ["dbs", "induction", "onboarding", "right to work", "new starter", "probation",
                                  "employment", "reference check", "hr only"], 0.88),
        ("senior_carer",        ["care plan", "support plan", "risk assessment", "risk assess", "body map",
                                  "skin integrity", "outcome-based"], 0.83),
        ("support_worker",      ["daily record", "daily notes", "handover", "daily log", "shift",
                                  "body chart", "observation", "activity"], 0.84),
        ("all_staff",           ["all staff", "whole team", "organisation", "health and safety",
                                  "fire safety", "gdpr", "equality", "whistleblowing"], 0.75),
    ]
    # Category-based defaults
    pur_defaults = {
        "Policy":      ("all_staff",           0.60, "Policies apply to all staff by default"),
        "Procedure":   ("all_staff",           0.55, "Procedures apply to all staff by default"),
        "Form":        ("support_worker",      0.58, "Operational forms typically completed by frontline staff"),
        "Checklist":   ("support_worker",      0.58, "Checklists typically used by frontline staff"),
        "Assessment":  ("senior_carer",        0.62, "Assessments typically led by senior carers"),
        "Agreement":   ("registered_manager", 0.65, "Agreements typically signed off by manager"),
        "Certificate": ("registered_manager", 0.70, "Certificates held by management"),
        "Record":      ("support_worker",      0.60, "Day-to-day records completed by frontline"),
        "Incident":    ("support_worker",      0.65, "Incident forms initiated by frontline staff"),
        "Report":      ("registered_manager", 0.58, "Reports produced by management"),
    }
    pur_value, pur_conf, pur_reasoning = pur_defaults.get(
        cat_value, ("all_staff", 0.45, "Default fallback")
    )
    for role, kws, conf in PUR_RULES:
        if any(k in combined for k in kws):
            pur_value = role
            pur_conf = conf
            pur_reasoning = f"Matched: {[k for k in kws if k in combined]}"
            break

    # --- Admin owner role --- who is responsible for maintaining / approving
    AOR_RULES: List[Tuple[str, List[str], float]] = [
        ("finance",           ["insurance", "employers liability", "public liability", "indemnity",
                               "premium", "renewal certificate", "financial"], 0.87),
        ("hr_manager",        ["dbs", "induction", "onboarding", "right to work", "employment",
                               "reference", "probation", "contract of employment", "new starter"], 0.88),
        ("clinical_lead",     ["medication", "mar sheet", "drug", "controlled drug", "prescri",
                               "care plan", "clinical", "nursing"], 0.84),
        ("compliance_lead",   ["policy", "procedure", "audit", "cqc", "mock inspection",
                               "gdpr", "equality", "health and safety", "fire safety",
                               "information governance", "whistleblowing"], 0.85),
        ("registered_manager", ["complaint", "grievance", "safeguarding", "serious incident",
                                 "risk assessment", "body map", "service user record"], 0.82),
    ]
    aor_value = "registered_manager"
    aor_conf = 0.55
    aor_reasoning = "Default — registered manager owns most operational documents"
    for role, kws, conf in AOR_RULES:
        if any(k in combined for k in kws):
            aor_value = role
            aor_conf = conf
            aor_reasoning = f"Matched: {[k for k in kws if k in combined]}"
            break

    # --- Worker visibility --- can frontline workers see/access this?
    VIS_RULES: List[Tuple[str, List[str], float]] = [
        ("visible",    ["daily record", "daily notes", "handover", "body map", "body chart",
                         "activity", "observation", "care plan", "support plan", "medication",
                         "mar sheet", "daily log", "shift"], 0.86),
        ("restricted", ["incident", "accident", "near miss", "risk assessment",
                         "complaint", "grievance", "riddor"], 0.78),
        ("admin_only", ["audit", "cqc", "mock inspection", "insurance", "employers liability",
                         "indemnity", "dbs", "employment", "contract", "right to work",
                         "induction", "probation", "financial", "directors"], 0.84),
    ]
    # Category-based defaults for visibility
    vis_cat_defaults = {
        "Policy":      ("admin_only",  0.62, "Policies are admin-maintained; worker access read-only after sign-off"),
        "Procedure":   ("admin_only",  0.58, "Procedures admin-maintained"),
        "Form":        ("visible",     0.60, "Operational forms visible to workers"),
        "Checklist":   ("visible",     0.62, "Checklists visible to frontline staff"),
        "Assessment":  ("restricted",  0.58, "Assessments may contain sensitive data"),
        "Agreement":   ("admin_only",  0.65, "Agreements held by admin"),
        "Certificate": ("admin_only",  0.70, "Certificates stored by admin"),
        "Record":      ("visible",     0.62, "Day-to-day records visible to frontline"),
        "Incident":    ("restricted",  0.68, "Incident reports have restricted downstream access"),
        "Report":      ("admin_only",  0.60, "Management reports restricted to admin"),
    }
    vis_value, vis_conf, vis_reasoning = vis_cat_defaults.get(
        cat_value, ("restricted", 0.45, "Default fallback")
    )
    for vis, kws, conf in VIS_RULES:
        if any(k in combined for k in kws):
            vis_value = vis
            vis_conf = conf
            vis_reasoning = f"Matched: {[k for k in kws if k in combined]}"
            break

    # --- System placement --- which UI module should this document appear in?
    PLACE_RULES: List[Tuple[str, List[str], float]] = [
        ("medication_module",    ["medication", "mar sheet", "drug", "controlled drug",
                                   "prescri", "blister", "medicine"], 0.96),
        ("incident_module",      ["incident", "accident", "near miss", "datix", "riddor"], 0.95),
        ("care_plan_module",     ["care plan", "support plan", "outcome-based",
                                   "daily notes", "handover"], 0.92),
        ("care_plan_module",     ["body map", "body chart", "skin integrity"], 0.94),
        ("service_user_record",  ["service user", "person centred", "su record"], 0.90),
        ("staff_profile",        ["dbs", "induction", "onboarding", "right to work", "employment",
                                   "new starter", "probation", "reference check"], 0.91),
        ("compliance_hub",       ["policy", "procedure", "audit", "cqc", "mock inspection",
                                   "health and safety", "fire safety", "gdpr", "equality",
                                   "whistleblowing", "insurance", "indemnity",
                                   "information governance", "complaint", "grievance"], 0.84),
    ]
    place_value = "all_modules"
    place_conf = 0.40
    place_reasoning = "Default fallback — no specific module placement detected"
    for place, kws, conf in PLACE_RULES:
        if any(k in combined for k in kws):
            matched_p = [k for k in kws if k in combined]
            boost_p = 0.03 if any(k in stem for k in kws) else 0.0
            place_value = place
            place_conf = min(1.0, conf + boost_p)
            place_reasoning = f"Matched: {matched_p}"
            break

    return ClassificationResult(
        category=ClassificationPrediction(value=cat_value, confidence=cat_conf, reasoning=cat_reasoning),
        document_type=ClassificationPrediction(value=cat_doc_type, confidence=cat_conf, reasoning=cat_reasoning),
        workflow_area=ClassificationPrediction(value=wf_value, confidence=wf_conf, reasoning=wf_reasoning),
        usage_audience=ClassificationPrediction(value=aud_value, confidence=aud_conf, reasoning=aud_reasoning),
        primary_user_role=ClassificationPrediction(value=pur_value, confidence=pur_conf, reasoning=pur_reasoning),
        admin_owner_role=ClassificationPrediction(value=aor_value, confidence=aor_conf, reasoning=aor_reasoning),
        worker_visibility=ClassificationPrediction(value=vis_value, confidence=vis_conf, reasoning=vis_reasoning),
        system_placement=ClassificationPrediction(value=place_value, confidence=place_conf, reasoning=place_reasoning),
        suggested_destination_section=(
            ClassificationPrediction(
                value=suggested_destination["destination_section"],
                confidence=suggested_destination["confidence"],
                reasoning=suggested_destination["reasoning"],
            )
            if suggested_destination
            else None
        ),
        frequency=ClassificationPrediction(value=freq_value, confidence=freq_conf, reasoning=freq_reasoning),
        review_cycle_months=ClassificationPrediction(value=str(rev_months), confidence=rev_conf, reasoning=rev_reasoning),
        suggested_title=suggested_title,
    )


@router.post("/document-templates/classify")
async def classify_document_template(
    filename: str = Form(...),
    text_sample: Optional[str] = Form(default=""),
    user: dict = Depends(require_admin),
) -> ClassificationResult:
    """
    Lightweight classification endpoint — accepts filename + optional text sample.
    Returns structured predictions with confidence scores and human-readable reasoning.
    No file is stored. Safe to call on file select before import.
    """
    result = _classify_document(filename=filename, text_sample=text_sample or "")
    return result


@router.get("/document-templates/service-user-destination-register")
async def preview_service_user_destination_register(user: dict = Depends(require_admin)):
    register = get_service_user_destination_register()
    return {
        "base_sections": [record for record in register if record.get("section_type") == "tab"],
        "operational_destinations": [record for record in register if record.get("section_type") == "operational"],
        "all_destinations": register,
    }


@router.post("/document-templates/import")
async def import_document_template(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    category: Optional[str] = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    source_provider: Optional[str] = Form(default="CQC Expert"),
    source_renewed_until: Optional[str] = Form(default=None),
    owner_role: Optional[str] = Form(default=None),
    review_period_months: int = Form(default=12),
    workflow_area: str = Form(default="compliance_policy"),
    doc_code: Optional[str] = Form(default=None),
    effective_date: Optional[str] = Form(default=None),
    user: dict = Depends(require_admin),
):
    """
    Import DOCX/PDF template into template library.

    Placeholder detection rules:
    1) red text in DOCX (strong signal)
    2) [bracketed] placeholders
    3) underline blank lines
    4) insert/enter/add-here keywords
    """
    if workflow_area not in WORKFLOW_AREAS:
        raise HTTPException(status_code=422, detail=f"Invalid workflow_area. Allowed: {', '.join(sorted(WORKFLOW_AREAS))}")

    filename = file.filename or "template"
    lower_name = filename.lower()
    if not (lower_name.endswith(".docx") or lower_name.endswith(".pdf")):
        raise HTTPException(status_code=422, detail="Only DOCX or PDF templates are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(file_bytes) > 40 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Template file too large (max 40MB)")

    if lower_name.endswith(".docx"):
        extracted_text, extracted_metadata, detected_placeholders = _extract_docx_template_data(file_bytes)
    else:
        extracted_text, extracted_metadata, detected_placeholders = _extract_pdf_template_data(file_bytes)

    db = get_db()
    await _ensure_template_indexes(db)
    now_iso = _utc_now_iso()

    stored = await _store_imported_file(file_bytes, filename)

    # Re-classify using extracted text (richer signal than filename alone)
    text_sample_for_classify = extracted_text[:3000] if extracted_text else ""
    post_import_classification = _classify_document(
        filename=filename, text_sample=text_sample_for_classify
    ).model_dump()
    suggested_destination_section = (post_import_classification.get("suggested_destination_section") or {}).get("value")

    detected_title = extracted_metadata.get("detected_title")
    final_title = (title or detected_title or "Imported Template").strip()
    final_doc_code = (doc_code or _gen_doc_code(final_title, category)).strip()

    # Build template and version documents (Phase 1 collections)
    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    review_date = _compute_review_date(effective_date, review_period_months)

    template_doc = {
        "id": template_id,
        "doc_code": final_doc_code,
        "title": final_title,
        "category": category,
        "document_type": document_type,
        "source_provider": source_provider,
        "source_renewed_until": source_renewed_until,
        "owner_role": owner_role,
        "review_period_months": review_period_months,
        "current_version_id": version_id,
        "status": "draft",
        "workflow_area": workflow_area,
        "classification": post_import_classification,
        "suggested_destination_section": suggested_destination_section,
        "created_by": user["user_id"],
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    version_doc = {
        "id": version_id,
        "template_id": template_id,
        "version": 1,
        "original_filename": filename,
        "storage_path": stored.get("storage_path"),
        "storage_url": stored.get("public_url"),
        "local_path": stored.get("local_path"),
        "extracted_text": extracted_text,
        "extracted_metadata": extracted_metadata,
        "detected_placeholders": detected_placeholders,
        "placeholder_map": _build_placeholder_map_from_detected(detected_placeholders),
        "effective_date": effective_date,
        "review_date": review_date,
        "published_at": None,
        "published_by": None,
        "status": "draft",
        "created_at": now_iso,
        "updated_at": now_iso,
        "created_by": user["user_id"],
    }

    await db.document_templates.insert_one(template_doc)
    await db.document_template_versions.insert_one(version_doc)

    await _write_document_audit_event(
        db=db,
        actor_id=user["user_id"],
        document_type="document_template",
        document_id=template_id,
        action="import",
        before={},
        after={
            "doc_code": final_doc_code,
            "title": final_title,
            "workflow_area": workflow_area,
            "template_version_id": version_id,
            "detected_placeholders": len(detected_placeholders),
        },
        reason="Template imported",
    )

    await log_audit_action(
        user["user_id"],
        "import_document_template",
        "document_template",
        template_id,
        {
            "doc_code": final_doc_code,
            "version_id": version_id,
            "placeholder_count": len(detected_placeholders),
        },
    )

    return {
        "template": template_doc,
        "version": version_doc,
        "classification": post_import_classification,
    }


@router.get("/document-templates")
async def list_document_templates(
    status: Optional[str] = Query(default=None),
    workflow_area: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    await _ensure_template_indexes(db)
    is_admin = _is_admin_user(user)

    if not is_admin and not workflow_area:
        raise HTTPException(status_code=422, detail="workflow_area is required for non-admin users")

    filt: Dict[str, Any] = {}
    if status and is_admin:
        filt["status"] = status
    elif not is_admin:
        filt["status"] = "active"
    if workflow_area:
        filt["workflow_area"] = workflow_area
    if category:
        filt["category"] = category

    docs = await db.document_templates.find(filt, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return docs


@router.get("/document-templates/by-workflow/{workflow_area}")
async def list_templates_by_workflow(workflow_area: str, user: dict = Depends(get_current_user)):
    if workflow_area not in WORKFLOW_AREAS:
        raise HTTPException(status_code=404, detail="Unknown workflow area")

    db = get_db()
    await _ensure_template_indexes(db)
    docs = await db.document_templates.find(
        {"workflow_area": workflow_area, "status": "active"},
        {"_id": 0},
    ).sort("updated_at", -1).to_list(300)
    return docs


@router.get("/document-templates/{template_id}")
async def get_document_template(template_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    await _ensure_template_indexes(db)
    template = await db.document_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    versions = await db.document_template_versions.find(
        {"template_id": template_id},
        {"_id": 0},
    ).sort("version", -1).to_list(100)

    return {
        "template": template,
        "versions": versions,
    }


@router.put("/document-template-versions/{version_id}/placeholder-map")
async def update_placeholder_map(
    version_id: str,
    body: PlaceholderMappingUpdate,
    user: dict = Depends(require_admin),
):
    db = get_db()
    await _ensure_template_indexes(db)
    version_doc = await db.document_template_versions.find_one({"id": version_id})
    if not version_doc:
        raise HTTPException(status_code=404, detail="Template version not found")

    if version_doc.get("status") != "draft":
        raise HTTPException(status_code=409, detail="Only draft versions can be modified")

    before_map = version_doc.get("placeholder_map") or {}
    new_map = dict(before_map)

    for m in body.mappings:
        key = _normalize_placeholder_text(m.placeholder_text)
        if not key:
            continue
        new_map[key] = {
            "system_variable": m.system_variable,
            "status": m.status,
            "notes": m.notes,
        }

    for manual in body.manually_added_placeholders:
        key = _normalize_placeholder_text(manual)
        if not key:
            continue
        new_map.setdefault(
            key,
            {
                "system_variable": None,
                "status": "manual",
                "notes": "Manually added placeholder",
            },
        )

    now_iso = _utc_now_iso()
    await db.document_template_versions.update_one(
        {"id": version_id},
        {
            "$set": {
                "placeholder_map": new_map,
                "updated_at": now_iso,
            }
        },
    )

    await _write_document_audit_event(
        db=db,
        actor_id=user["user_id"],
        document_type="document_template_version",
        document_id=version_id,
        action="placeholder_mapping",
        before={"placeholder_map": before_map},
        after={"placeholder_map": new_map},
        reason="Updated placeholder mapping",
    )

    await log_audit_action(
        user["user_id"],
        "update_placeholder_mapping",
        "document_template_version",
        version_id,
        {"mapped_count": len(new_map)},
    )

    updated = await db.document_template_versions.find_one({"id": version_id}, {"_id": 0})
    return updated


@router.post("/document-templates/{template_id}/new-version")
async def create_new_template_version(template_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    await _ensure_template_indexes(db)
    template = await db.document_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    current_version_id = template.get("current_version_id")
    current_version = None
    if current_version_id:
        current_version = await db.document_template_versions.find_one({"id": current_version_id})

    if not current_version:
        raise HTTPException(status_code=404, detail="Current version not found")

    if current_version.get("status") != "published":
        raise HTTPException(status_code=409, detail="New versions can only be created from published versions")

    next_version_no = int(current_version.get("version", 1)) + 1
    now_iso = _utc_now_iso()
    new_version_id = str(uuid.uuid4())

    new_version_doc = {
        **{k: v for k, v in current_version.items() if k != "_id"},
        "id": new_version_id,
        "version": next_version_no,
        "status": "draft",
        "published_at": None,
        "published_by": None,
        "created_at": now_iso,
        "updated_at": now_iso,
        "created_by": user["user_id"],
    }

    await db.document_template_versions.insert_one(new_version_doc)
    await db.document_templates.update_one(
        {"id": template_id},
        {
            "$set": {
                "current_version_id": new_version_id,
                "status": "draft",
                "updated_at": now_iso,
            }
        },
    )

    await _write_document_audit_event(
        db=db,
        actor_id=user["user_id"],
        document_type="document_template",
        document_id=template_id,
        action="new_version",
        before={"current_version_id": current_version_id},
        after={"current_version_id": new_version_id},
        reason="Create editable draft version",
    )

    return new_version_doc


@router.post("/document-templates/{template_id}/publish")
async def publish_document_template(
    template_id: str,
    body: PublishTemplateRequest,
    user: dict = Depends(require_admin),
):
    db = get_db()
    await _ensure_template_indexes(db)
    template = await db.document_templates.find_one({"id": template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    version_id = body.template_version_id or template.get("current_version_id")
    if not version_id:
        raise HTTPException(status_code=422, detail="No template version selected")

    version_doc = await db.document_template_versions.find_one({"id": version_id})
    if not version_doc:
        raise HTTPException(status_code=404, detail="Template version not found")

    if version_doc.get("status") != "draft":
        raise HTTPException(status_code=409, detail="Only draft versions can be published")

    suggested_destination = (template.get("classification") or {}).get("suggested_destination_section") or {}
    suggested_destination_section = suggested_destination.get("value")
    confirmed_destination_section = (body.confirmed_destination_section or "").strip()
    if not confirmed_destination_section:
        raise HTTPException(status_code=422, detail="Destination confirmation is required before publish")
    if suggested_destination_section and confirmed_destination_section != suggested_destination_section:
        raise HTTPException(
            status_code=409,
            detail=f"Destination confirmation must match the suggested destination: {suggested_destination_section}",
        )

    destination_record = next(
        (item for item in get_service_user_destination_register() if item.get("destination_section") == confirmed_destination_section),
        None,
    )
    if not destination_record:
        raise HTTPException(status_code=422, detail="Selected destination is not part of the service-user destination register")

    now_iso = _utc_now_iso()
    effective_date = body.effective_date or version_doc.get("effective_date") or now_iso[:10]
    review_date = body.review_date or _compute_review_date(effective_date, int(template.get("review_period_months") or 12))

    before_version = {"status": version_doc.get("status"), "effective_date": version_doc.get("effective_date"), "review_date": version_doc.get("review_date")}

    await db.document_template_versions.update_one(
        {"id": version_id},
        {
            "$set": {
                "status": "published",
                "effective_date": effective_date,
                "review_date": review_date,
                "published_at": now_iso,
                "published_by": user["user_id"],
                "updated_at": now_iso,
                "destination_section": confirmed_destination_section,
                "destination_confirmed_at": now_iso,
                "destination_confirmed_by": user["user_id"],
            }
        },
    )

    update_set = {
        "status": "active",
        "current_version_id": version_id,
        "updated_at": now_iso,
        "destination_section": confirmed_destination_section,
        "destination_confirmed_at": now_iso,
        "destination_confirmed_by": user["user_id"],
    }
    if template.get("import_status"):
        update_set["import_status"] = "imported"

    await db.document_templates.update_one(
        {"id": template_id},
        {"$set": update_set},
    )

    # Archive other published versions for immutability and single active stream
    await db.document_template_versions.update_many(
        {
            "template_id": template_id,
            "id": {"$ne": version_id},
            "status": "published",
        },
        {"$set": {"status": "archived", "updated_at": now_iso}},
    )

    template_after = await db.document_templates.find_one({"id": template_id}, {"_id": 0})
    await _ensure_renewal_record_for_active_template(
        db=db,
        template=template_after,
        template_version_id=version_id,
        actor_id=user["user_id"],
    )

    await _write_document_audit_event(
        db=db,
        actor_id=user["user_id"],
        document_type="document_template_version",
        document_id=version_id,
        action="publish",
        before=before_version,
        after={"status": "published", "effective_date": effective_date, "review_date": review_date},
        reason="Published template version",
    )

    await log_audit_action(
        user["user_id"],
        "publish_document_template",
        "document_template",
        template_id,
        {"template_version_id": version_id, "review_date": review_date},
    )

    return {
        "message": "Template published",
        "template_id": template_id,
        "template_version_id": version_id,
        "effective_date": effective_date,
        "review_date": review_date,
        "destination_section": confirmed_destination_section,
        "destination_title": destination_record["title"],
    }


@router.post("/generated-documents")
async def generate_document_from_template(
    body: GenerateDocumentRequest,
    user: dict = Depends(require_admin),
):
    db = get_db()
    await _ensure_template_indexes(db)

    if body.workflow_area not in WORKFLOW_AREAS:
        raise HTTPException(status_code=422, detail="Invalid workflow_area")

    template = await db.document_templates.find_one({"id": body.template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    version_id = body.template_version_id or template.get("current_version_id")
    if not version_id:
        raise HTTPException(status_code=422, detail="No template version selected")

    version_doc = await db.document_template_versions.find_one({"id": version_id})
    if not version_doc:
        raise HTTPException(status_code=404, detail="Template version not found")

    if version_doc.get("status") != "published":
        raise HTTPException(status_code=409, detail="Only published template versions can be used for generation")

    context = body.context or {}
    completed_by = context.get("completed_by") or user.get("email") or user.get("user_id")
    approved_by = context.get("approved_by")

    pdf_bytes = _render_branded_pdf(
        template_doc=template,
        version_doc=version_doc,
        context=context,
        completed_by=completed_by,
        approved_by=approved_by,
    )

    filename = f"{_sanitize_filename(template.get('doc_code') or template.get('title') or 'document')}_v{version_doc.get('version', 1)}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    saved = await _save_generated_pdf(pdf_bytes, filename)

    now_iso = _utc_now_iso()
    generated_id = str(uuid.uuid4())
    generated_doc = {
        "id": generated_id,
        "template_id": body.template_id,
        "template_version_id": version_id,
        "workflow_area": body.workflow_area,
        "related_entity_type": body.related_entity_type,
        "related_entity_id": body.related_entity_id,
        "generated_pdf_path": saved.get("generated_pdf_path"),
        "generated_pdf_url": saved.get("generated_pdf_url"),
        "status": "final",
        "generated_by": user["user_id"],
        "generated_at": now_iso,
        "signed_by": None,
        "signed_at": None,
        "audit_snapshot": {
            "doc_code": template.get("doc_code"),
            "title": template.get("title"),
            "template_version": version_doc.get("version"),
            "effective_date": version_doc.get("effective_date"),
            "review_date": version_doc.get("review_date"),
            "source_provider": template.get("source_provider"),
            "context": context,
        },
    }

    await db.generated_documents.insert_one(generated_doc)

    await _write_document_audit_event(
        db=db,
        actor_id=user["user_id"],
        document_type="generated_document",
        document_id=generated_id,
        action="generate_pdf",
        before={},
        after={
            "template_id": body.template_id,
            "template_version_id": version_id,
            "workflow_area": body.workflow_area,
            "generated_pdf_path": generated_doc.get("generated_pdf_path"),
            "generated_pdf_url": generated_doc.get("generated_pdf_url"),
        },
        reason="Generated branded document PDF",
    )

    await log_audit_action(
        user["user_id"],
        "generate_document_pdf",
        "generated_document",
        generated_id,
        {
            "template_id": body.template_id,
            "workflow_area": body.workflow_area,
            "related_entity_type": body.related_entity_type,
            "related_entity_id": body.related_entity_id,
        },
    )

    return generated_doc


@router.get("/generated-documents/{generated_document_id}")
async def get_generated_document(generated_document_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    await _ensure_template_indexes(db)
    doc = await db.generated_documents.find_one({"id": generated_document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Generated document not found")
    return doc


@router.get("/generated-documents/{generated_document_id}/pdf")
async def stream_generated_document_pdf(generated_document_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    await _ensure_template_indexes(db)
    doc = await db.generated_documents.find_one({"id": generated_document_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Generated document not found")

    pdf_bytes: Optional[bytes] = None
    source_name = f"generated_{generated_document_id}.pdf"

    if doc.get("generated_pdf_url"):
        pdf_bytes = await download_file_from_storage(doc["generated_pdf_url"])
    elif doc.get("generated_pdf_path"):
        path = doc["generated_pdf_path"]
        p = Path(path)
        if p.exists() and p.is_file():
            pdf_bytes = p.read_bytes()
            source_name = p.name

    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Generated PDF bytes not found")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{source_name}"'},
    )


@router.get("/document-renewals/due")
async def list_due_renewals(
    days_ahead: int = Query(default=30, ge=1, le=180),
    status: Optional[str] = Query(default=None),
    user: dict = Depends(require_admin),
):
    db = get_db()
    await _ensure_template_indexes(db)

    now = date.today()
    due_cutoff = now + timedelta(days=days_ahead)

    filt: Dict[str, Any] = {
        "renewal_due_date": {
            "$lte": due_cutoff.isoformat(),
        }
    }
    if status:
        filt["status"] = status

    docs = await db.document_renewals.find(filt, {"_id": 0}).sort("renewal_due_date", 1).to_list(500)

    # Dynamic overdue/pending classification
    for d in docs:
        due = d.get("renewal_due_date")
        if due and d.get("status") in {None, "pending"}:
            try:
                due_date = date.fromisoformat(due)
                if due_date < now:
                    d["status"] = "overdue"
                elif d.get("status") is None:
                    d["status"] = "pending"
            except Exception:
                pass

    return docs


def _render_renewal_certificate_pdf(
    *,
    template_doc: Dict[str, Any],
    version_doc: Dict[str, Any],
    renewal_doc: Dict[str, Any],
    review_outcome: str,
    review_notes: Optional[str],
    reviewed_by: str,
    approved_by: Optional[str],
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    brand = colors.HexColor("#004D4D")
    muted = colors.HexColor("#6B7280")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=18, textColor=brand)

    now_iso = _utc_now_iso()

    elements: List[Any] = []
    elements.append(Paragraph("OsabeaCare Template Renewal Certificate", title_style))
    elements.append(Spacer(1, 10))

    table_data = [
        ["Doc Code", template_doc.get("doc_code") or ""],
        ["Template Title", template_doc.get("title") or ""],
        ["Template Version", str(version_doc.get("version", 1))],
        ["Renewal Due Date", renewal_doc.get("renewal_due_date") or ""],
        ["Review Outcome", review_outcome],
        ["Reviewed By", reviewed_by],
        ["Approved By", approved_by or ""],
        ["Completed At", now_iso[:19]],
    ]

    table = Table(table_data, colWidths=[55 * mm, 115 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFA")),
                ("TEXTCOLOR", (0, 0), (0, -1), brand),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(table)

    if review_notes:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Review Notes", ParagraphStyle("H", parent=styles["Heading2"], fontSize=12, textColor=brand)))
        elements.append(Paragraph(review_notes, ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("This certificate records Osabea internal annual review/approval and does not represent source-provider renewal.", ParagraphStyle("Foot", parent=styles["Normal"], fontSize=8, textColor=muted)))

    doc.build(elements)
    return buffer.getvalue()


@router.post("/document-renewals/{renewal_id}/complete")
async def complete_document_renewal(
    renewal_id: str,
    body: RenewalCompleteRequest,
    user: dict = Depends(require_admin),
):
    if body.review_outcome not in {"no_change", "updated", "retired"}:
        raise HTTPException(status_code=422, detail="review_outcome must be one of: no_change, updated, retired")

    db = get_db()
    await _ensure_template_indexes(db)
    renewal = await db.document_renewals.find_one({"id": renewal_id})
    if not renewal:
        raise HTTPException(status_code=404, detail="Renewal record not found")

    template = await db.document_templates.find_one({"id": renewal.get("template_id")})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    version = await db.document_template_versions.find_one({"id": renewal.get("template_version_id")})
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")

    before = {k: renewal.get(k) for k in ["status", "review_outcome", "review_notes", "completed_at"]}
    now_iso = _utc_now_iso()

    certificate_pdf = _render_renewal_certificate_pdf(
        template_doc=template,
        version_doc=version,
        renewal_doc=renewal,
        review_outcome=body.review_outcome,
        review_notes=body.review_notes,
        reviewed_by=user["user_id"],
        approved_by=body.approved_by,
    )
    cert_name = f"renewal_{_sanitize_filename(template.get('doc_code') or template.get('title') or renewal_id)}_{now_iso[:10]}.pdf"
    cert_saved = await _save_generated_pdf(certificate_pdf, cert_name)

    update = {
        "status": "completed",
        "review_outcome": body.review_outcome,
        "reviewed_by": user["user_id"],
        "approved_by": body.approved_by,
        "review_notes": body.review_notes,
        "certificate_pdf_path": cert_saved.get("generated_pdf_path"),
        "certificate_pdf_url": cert_saved.get("generated_pdf_url"),
        "completed_at": now_iso,
        "updated_at": now_iso,
    }

    await db.document_renewals.update_one({"id": renewal_id}, {"$set": update})

    # Outcome handling
    if body.review_outcome == "retired":
        await db.document_templates.update_one(
            {"id": template["id"]},
            {"$set": {"status": "retired", "updated_at": now_iso}},
        )
        await db.document_template_versions.update_many(
            {"template_id": template["id"], "status": "published"},
            {"$set": {"status": "archived", "updated_at": now_iso}},
        )

    elif body.review_outcome == "updated":
        # Archive current published version and create a new draft copy
        await db.document_template_versions.update_one(
            {"id": version["id"]},
            {"$set": {"status": "archived", "updated_at": now_iso}},
        )
        next_version_no = int(version.get("version", 1)) + 1
        new_version_id = str(uuid.uuid4())
        new_version = {
            **{k: v for k, v in version.items() if k != "_id"},
            "id": new_version_id,
            "version": next_version_no,
            "status": "draft",
            "published_at": None,
            "published_by": None,
            "created_at": now_iso,
            "updated_at": now_iso,
            "created_by": user["user_id"],
        }
        await db.document_template_versions.insert_one(new_version)
        await db.document_templates.update_one(
            {"id": template["id"]},
            {
                "$set": {
                    "status": "draft",
                    "current_version_id": new_version_id,
                    "updated_at": now_iso,
                }
            },
        )

    else:  # no_change
        # Schedule next internal renewal based on review_period_months
        review_period_months = int(template.get("review_period_months") or 12)
        base = date.today()
        next_due = (base + relativedelta(months=review_period_months)).isoformat()

        new_renewal = {
            "id": str(uuid.uuid4()),
            "template_id": template["id"],
            "template_version_id": version["id"],
            "renewal_due_date": next_due,
            "status": "pending",
            "review_outcome": None,
            "reviewed_by": None,
            "approved_by": None,
            "review_notes": None,
            "certificate_pdf_path": None,
            "certificate_pdf_url": None,
            "completed_at": None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        await db.document_renewals.insert_one(new_renewal)

    await _write_document_audit_event(
        db=db,
        actor_id=user["user_id"],
        document_type="document_renewal",
        document_id=renewal_id,
        action="renew",
        before=before,
        after=update,
        reason="Internal annual review completed",
    )

    await log_audit_action(
        user["user_id"],
        "complete_document_renewal",
        "document_renewal",
        renewal_id,
        {
            "review_outcome": body.review_outcome,
            "template_id": template["id"],
            "template_version_id": version["id"],
        },
    )

    return {
        "message": "Renewal completed",
        "renewal_id": renewal_id,
        "review_outcome": body.review_outcome,
    }


@router.get("/document-audit-events")
async def list_document_audit_events(
    document_type: Optional[str] = None,
    document_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=2000),
    user: dict = Depends(require_admin),
):
    db = get_db()
    await _ensure_template_indexes(db)
    filt: Dict[str, Any] = {}
    if document_type:
        filt["document_type"] = document_type
    if document_id:
        filt["document_id"] = document_id
    if action:
        filt["action"] = action

    docs = await db.document_audit_events.find(filt, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return docs


# ============================================================================
# Archive Import Fast-Track Implementation (Phase 1 + Phase 2)
# ============================================================================

def _load_import_manifest() -> Dict[str, Any]:
    """Load IMPORT_MANIFEST.json from workspace root."""
    try:
        manifest_path = Path(__file__).resolve().parents[2] / "IMPORT_MANIFEST.json"
        if manifest_path.exists():
            import json
            with open(manifest_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load IMPORT_MANIFEST.json: {e}")
    return {"archive_root": "", "total_templates": 0, "phases": {}}


async def _check_duplicate_template(
    db, filename: str, folder_path: str, file_hash: str
) -> Optional[Dict[str, Any]]:
    """Check if template already exists (by filename, normalized title, or hash)."""
    # Check by exact filename + folder path
    existing = await db.document_templates.find_one({
        "archive_filename": filename,
        "archive_source": folder_path,
    }, {"_id": 0, "id": 1, "title": 1})
    if existing:
        return {
            "type": "exact_filename_match",
            "existing_id": existing["id"],
            "existing_title": existing.get("title"),
        }
    
    # Check by filename alone (case-insensitive)
    filename_lower = filename.lower()
    existing = await db.document_templates.find_one({
        "archive_filename": {"$regex": f"^{re.escape(filename)}$", "$options": "i"},
    }, {"_id": 0, "id": 1, "title": 1})
    if existing:
        return {
            "type": "filename_match_case_insensitive",
            "existing_id": existing["id"],
            "existing_title": existing.get("title"),
        }
    
    # Check by file hash
    if file_hash:
        existing = await db.document_templates.find_one({
            "archive_hash": file_hash,
        }, {"_id": 0, "id": 1, "title": 1})
        if existing:
            return {
                "type": "hash_match",
                "existing_id": existing["id"],
                "existing_title": existing.get("title"),
            }
    
    return None


@router.get("/document-templates/archive/import-manifest")
async def get_archive_import_manifest(
    phase: Optional[str] = Query(default=None),
    folder: Optional[str] = Query(default=None),
    user: dict = Depends(require_admin),
):
    """
    Load IMPORT_MANIFEST.json for archive import preview.
    Supports phase and folder filtering.
    """
    manifest = _load_import_manifest()
    
    if not manifest.get("phases"):
        raise HTTPException(status_code=404, detail="Import manifest not found or empty")
    
    # Filter by phase if requested
    if phase:
        templates = manifest.get("phases", {}).get(phase, [])
    else:
        # Return Phase 1 + Phase 2 by default (Fast-Track)
        phase1 = manifest.get("phases", {}).get("phase_1_critical", [])
        phase2 = manifest.get("phases", {}).get("phase_2_high", [])
        templates = phase1 + phase2
    
    # Filter by folder if requested
    if folder:
        templates = [t for t in templates if t.get("folder_path") == folder]
    
    # Add priority labels and status
    for template in templates:
        if not template.get("priority"):
            phase_key = next(
                (k for k, v in manifest.get("phases", {}).items() if template in v),
                None
            )
            if "critical" in str(phase_key):
                template["priority"] = "CRITICAL"
            elif "high" in str(phase_key):
                template["priority"] = "HIGH"
            else:
                template["priority"] = "MEDIUM"
        template["import_status"] = "pending"
    
    return {
        "archive_root": manifest.get("archive_root"),
        "total_templates": len(templates),
        "templates": templates,
        "phase_selected": phase or "phase_1_critical+phase_2_high",
        "folder_selected": folder,
    }


@router.post("/document-templates/archive/preview-batch")
async def preview_archive_batch_import(
    body: ArchiveImportRequest,
    user: dict = Depends(require_admin),
):
    """
    Preview templates before batch import.
    Check for duplicates and conflicts.
    """
    db = get_db()
    manifest = _load_import_manifest()
    
    # Get templates from manifest
    all_templates = []
    for phase_key, phase_templates in manifest.get("phases", {}).items():
        if body.phase and body.phase != phase_key:
            continue
        all_templates.extend(phase_templates)
    
    # Filter by selected filenames if specified
    if body.templates:
        all_templates = [t for t in all_templates if t.get("filename") in body.templates]
    
    # Filter by folder if specified
    if body.folder_filter:
        all_templates = [t for t in all_templates if t.get("folder_path") == body.folder_filter]
    
    preview_items = []
    for template in all_templates:
        filename = template.get("filename")
        folder_path = template.get("folder_path")
        file_hash = template.get("file_hash")
        
        # Check for duplicates
        duplicate_info = await _check_duplicate_template(db, filename, folder_path, file_hash)
        
        preview_item = {
            "filename": filename,
            "folder_path": folder_path,
            "detected_type": template.get("detected_type"),
            "destination_section": template.get("destination_section"),
            "confidence": template.get("confidence"),
            "priority": template.get("priority", "MEDIUM"),
            "import_status": "skipped" if duplicate_info else "pending",
            "duplicate_check": duplicate_info,
            "file_size": template.get("file_size"),
            "file_hash": file_hash,
        }
        preview_items.append(preview_item)
    
    # Count by status and priority
    pending_count = len([t for t in preview_items if t["import_status"] == "pending"])
    skipped_count = len([t for t in preview_items if t["import_status"] == "skipped"])
    critical_count = len([t for t in preview_items if t["priority"] == "CRITICAL"])
    high_count = len([t for t in preview_items if t["priority"] == "HIGH"])
    
    return {
        "total_templates": len(preview_items),
        "pending": pending_count,
        "skipped": skipped_count,
        "critical": critical_count,
        "high": high_count,
        "preview_items": preview_items,
    }


@router.post("/document-templates/archive/batch-import")
async def batch_import_from_archive(
    body: ArchiveImportBatchRequest,
    user: dict = Depends(require_admin),
):
    """
    Batch import templates from archive.
    Templates are created as DRAFT with import_status='pending'.
    No automatic publish — requires admin confirmation via publish endpoint.
    """
    if not body.confirmed:
        raise HTTPException(
            status_code=422,
            detail="Admin must confirm batch import before proceeding"
        )
    
    db = get_db()
    await _ensure_template_indexes(db)
    now_iso = _utc_now_iso()
    
    manifest = _load_import_manifest()
    archive_root = manifest.get("archive_root")
    
    imported_ids = []
    skipped_items = []
    failed_items = []
    
    for manifest_item in body.manifest_items:
        try:
            filename = manifest_item.filename
            folder_path = manifest_item.folder_path
            file_hash = manifest_item.file_hash
            detected_type = manifest_item.detected_type
            destination_section = manifest_item.destination_section
            priority = manifest_item.priority
            
            # Check for duplicate
            duplicate_info = await _check_duplicate_template(db, filename, folder_path, file_hash)
            if duplicate_info:
                skipped_items.append({
                    "filename": filename,
                    "reason": f"Duplicate: {duplicate_info['type']}",
                    "conflict": duplicate_info,
                })
                continue
            
            # Create template record with import metadata
            template_id = str(uuid.uuid4())
            version_id = str(uuid.uuid4())
            
            # Build title from filename
            title = filename.replace(".docx", "").replace(".pdf", "").replace("_", " ")
            title = re.sub(r"\s+", " ", title).title()
            
            # Generate doc code
            doc_code = _gen_doc_code(title, detected_type)
            
            # Classify based on archive metadata
            classification = _classify_document(filename, "")  # Use filename-only for now
            
            # Create template doc with import status
            template_doc = {
                "id": template_id,
                "doc_code": doc_code,
                "title": title,
                "category": classification.category.value,
                "document_type": classification.document_type.value,
                "source_provider": "Archive Migration",
                "owner_role": classification.admin_owner_role.value,
                "review_period_months": int(classification.review_cycle_months.value),
                "current_version_id": version_id,
                "status": "draft",
                "workflow_area": classification.workflow_area.value,
                "classification": classification.model_dump(),
                "suggested_destination_section": destination_section,
                # Import metadata for tracking
                "import_status": "pending",
                "import_source": "archive_migration",
                "import_phase": priority,
                "archive_source": folder_path,
                "archive_filename": filename,
                "archive_hash": file_hash,
                "archive_detected_type": detected_type,
                "imported_at": now_iso,
                "imported_by": user["user_id"],
                "created_by": user["user_id"],
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            
            # Create version doc
            version_doc = {
                "id": version_id,
                "template_id": template_id,
                "version": 1,
                "original_filename": filename,
                "storage_path": None,  # Will be populated if file is retrieved from archive
                "storage_url": None,
                "local_path": None,
                "extracted_text": "",  # Will be extracted on-demand from archive
                "extracted_metadata": {
                    "source_type": "archive",
                    "archive_folder": folder_path,
                    "archive_filename": filename,
                    "detected_type": detected_type,
                },
                "detected_placeholders": [],
                "placeholder_map": {},
                "effective_date": now_iso[:10],
                "review_date": _compute_review_date(now_iso[:10], int(classification.review_cycle_months.value)),
                "published_at": None,
                "published_by": None,
                "status": "draft",
                "created_at": now_iso,
                "updated_at": now_iso,
                "created_by": user["user_id"],
            }
            
            await db.document_templates.insert_one(template_doc)
            await db.document_template_versions.insert_one(version_doc)
            
            await _write_document_audit_event(
                db=db,
                actor_id=user["user_id"],
                document_type="document_template",
                document_id=template_id,
                action="archive_import_batch",
                before={},
                after={
                    "doc_code": doc_code,
                    "title": title,
                    "archive_source": folder_path,
                    "archive_filename": filename,
                    "import_status": "pending",
                },
                reason=f"Imported from archive migration batch (Phase: {priority})",
            )
            
            imported_ids.append(template_id)
            
        except Exception as e:
            failed_items.append({
                "filename": manifest_item.filename,
                "error": str(e),
            })
            logging.error(f"Failed to import {manifest_item.filename}: {e}")
    
    await log_audit_action(
        user["user_id"],
        "batch_import_archive",
        "document_template",
        "batch",
        {
            "imported_count": len(imported_ids),
            "skipped_count": len(skipped_items),
            "failed_count": len(failed_items),
        },
    )
    
    return {
        "message": "Batch import completed",
        "imported_count": len(imported_ids),
        "imported_template_ids": imported_ids,
        "skipped_count": len(skipped_items),
        "skipped_items": skipped_items,
        "failed_count": len(failed_items),
        "failed_items": failed_items,
    }


@router.get("/document-templates/archive/import-status")
async def get_archive_import_status(
    user: dict = Depends(require_admin),
):
    """Get status of pending archive imports."""
    db = get_db()
    
    pending_imports = await db.document_templates.find(
        {
            "import_status": {"$in": ["pending", "needs_review"]},
        },
        {"_id": 0}
    ).sort("imported_at", -1).to_list(1000)
    
    published_imports = await db.document_templates.find(
        {
            "import_status": "imported",
        },
        {"_id": 0}
    ).sort("updated_at", -1).to_list(1000)
    
    skipped_imports = await db.document_templates.find(
        {
            "import_status": "skipped",
        },
        {"_id": 0}
    ).sort("updated_at", -1).to_list(1000)
    
    return {
        "pending": {
            "count": len(pending_imports),
            "templates": pending_imports,
        },
        "published": {
            "count": len(published_imports),
            "templates": published_imports,
        },
        "skipped": {
            "count": len(skipped_imports),
            "templates": skipped_imports,
        },
    }


# ============================================================================
# Advanced Archive Features (10 Extended Capabilities)
# ============================================================================

def _suggest_naming(filename: str, detected_type: str, folder_path: str) -> Dict[str, str]:
    """Generate auto-naming suggestions based on archive metadata."""
    base = filename.replace(".docx", "").replace(".pdf", "")
    
    suggestions = {
        "original": base,
        "normalized": re.sub(r"[_-]", " ", base).title(),
        "with_type": f"{base} ({detected_type.replace('_', ' ').title()})",
        "folder_qualified": f"{folder_path}: {base}".title(),
        "abbreviated": "".join([w[0].upper() for w in base.split()])[:8] or "DOC",
    }
    return suggestions


def _score_placeholder_completeness(version_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Score placeholder mapping completeness (0-100)."""
    placeholder_map = version_doc.get("placeholder_map", {})
    detected = version_doc.get("detected_placeholders", [])
    
    if not detected:
        return {"score": 100, "mapped": 0, "total": 0, "rating": "complete"}
    
    mapped_count = len([p for p in placeholder_map.values() if p.get("system_variable")])
    total_count = len(detected)
    score = int((mapped_count / max(total_count, 1)) * 100)
    
    rating = "complete" if score >= 90 else "mostly_mapped" if score >= 70 else "partial" if score >= 50 else "unmapped"
    
    return {
        "score": score,
        "mapped": mapped_count,
        "total": total_count,
        "rating": rating,
        "priority": "high" if score < 50 else "medium" if score < 80 else "low",
    }


def _identify_missing_legal_documents() -> Dict[str, List[str]]:
    """Identify commonly required legal/compliance templates not in archive."""
    required_categories = {
        "Staff Safety": [
            "Health & Safety Policy",
            "Risk Assessment Template",
            "COSHH Assessment",
            "Incident Report Form",
            "Lone Worker Risk Assessment",
        ],
        "Data Protection": [
            "GDPR Privacy Notice",
            "Data Protection Policy",
            "Information Governance Policy",
            "Data Breach Log Template",
            "Subject Access Request Form",
        ],
        "Recruitment": [
            "Job Description Template",
            "Person Specification",
            "DBS Checklist",
            "Right to Work Verification",
            "Employment Contract Template",
        ],
        "Care Quality": [
            "Service User Agreement",
            "Safeguarding Policy",
            "Complaint Procedure",
            "Care Plan Template",
            "Activity Log Template",
        ],
        "Compliance": [
            "Fire Safety Checklist",
            "Quality Audit Template",
            "Medication Policy",
            "Supervision Agreement",
            "Training Record Template",
        ],
    }
    return required_categories


def _generate_visibility_preview(classification: Dict[str, Any]) -> Dict[str, Any]:
    """Generate worker/admin visibility preview."""
    worker_visibility = classification.get("worker_visibility", {}).get("value", "restricted")
    usage_audience = classification.get("usage_audience", {}).get("value", "both")
    system_placement = classification.get("system_placement", {}).get("value", "all_modules")
    
    return {
        "worker_visible": worker_visibility in ["visible", "admin_only"],
        "admin_only": worker_visibility == "admin_only",
        "restricted_access": worker_visibility == "restricted",
        "audience": usage_audience,
        "placement": system_placement,
        "preview_text": f"Workers: {worker_visibility} | Audience: {usage_audience} | Placement: {system_placement}",
    }


async def _score_service_user_completeness(db) -> Dict[str, Any]:
    """Score which service-user sections will be populated by imported templates."""
    sections = {
        "care_plans": {"required": True, "count": 0, "status": "pending"},
        "medical_records": {"required": True, "count": 0, "status": "pending"},
        "behavioral_records": {"required": True, "count": 0, "status": "pending"},
        "incident_reports": {"required": True, "count": 0, "status": "pending"},
        "activity_logs": {"required": True, "count": 0, "status": "pending"},
        "risk_assessments": {"required": True, "count": 0, "status": "pending"},
        "body_maps": {"required": False, "count": 0, "status": "pending"},
        "medication_records": {"required": True, "count": 0, "status": "pending"},
        "training_records": {"required": False, "count": 0, "status": "pending"},
    }
    
    # Count imported templates by section
    imports = await db.document_templates.find(
        {"import_status": "pending"},
        {"_id": 0, "workflow_area": 1, "category": 1}
    ).to_list(None)
    
    for imp in imports:
        workflow = imp.get("workflow_area", "")
        if "care_plan" in workflow:
            sections["care_plans"]["count"] += 1
            sections["care_plans"]["status"] = "partial"
        if "medication" in workflow:
            sections["medication_records"]["count"] += 1
            sections["medication_records"]["status"] = "partial"
        if "incident" in workflow:
            sections["incident_reports"]["count"] += 1
            sections["incident_reports"]["status"] = "partial"
        if "body_map" in workflow:
            sections["body_maps"]["count"] += 1
            sections["body_maps"]["status"] = "partial"
        if "risk_assessment" in workflow:
            sections["risk_assessments"]["count"] += 1
            sections["risk_assessments"]["status"] = "partial"
    
    complete_sections = len([s for s in sections.values() if s["status"] == "partial"])
    required_sections = len([s for s in sections.values() if s["required"]])
    completeness_pct = int((complete_sections / max(required_sections, 1)) * 100)
    
    return {
        "sections": sections,
        "completeness_percentage": completeness_pct,
        "complete_sections": complete_sections,
        "required_sections": required_sections,
        "status": "ready" if completeness_pct >= 80 else "in_progress" if completeness_pct > 0 else "not_started",
    }


def _generate_renewal_calendar(templates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate compliance renewal calendar based on review cycles."""
    from datetime import datetime, timedelta
    
    events = []
    for template in templates:
        if not template.get("effective_date") or not template.get("review_period_months"):
            continue
        
        try:
            effective = datetime.fromisoformat(template["effective_date"])
            months = int(template.get("review_period_months", 12))
            renewal_date = effective + timedelta(days=30*months)
            
            events.append({
                "template_id": template.get("id"),
                "title": template.get("title"),
                "renewal_date": renewal_date.isoformat(),
                "days_until": (renewal_date - datetime.now()).days,
                "priority": "urgent" if (renewal_date - datetime.now()).days < 30 else "scheduled",
            })
        except Exception:
            continue
    
    return {
        "total_events": len(events),
        "urgent_count": len([e for e in events if e["priority"] == "urgent"]),
        "events": sorted(events, key=lambda e: e["renewal_date"]),
    }


def _map_competency_requirements(classification: Dict[str, Any]) -> Dict[str, List[str]]:
    """Map templates to required competencies."""
    primary_role = classification.get("primary_user_role", {}).get("value", "support_worker")
    workflow = classification.get("workflow_area", {}).get("value", "compliance_policy")
    
    competency_map = {
        "support_worker": {
            "care_plan": ["Care Planning", "Person-Centred Practice", "Communication"],
            "medication": ["Medication Administration", "Health & Safety", "Record Keeping"],
            "incident_report": ["Safeguarding", "Incident Analysis", "Communication"],
            "body_map": ["Health Assessment", "Observation Skills", "Documentation"],
        },
        "senior_carer": {
            "care_plan": ["Care Planning", "Supervision", "Quality Assurance"],
            "risk_assessment": ["Risk Management", "Leadership", "Decision Making"],
            "incident_report": ["Safeguarding", "Investigation", "Root Cause Analysis"],
        },
        "registered_manager": {
            "audit": ["Quality Assurance", "Compliance", "Leadership"],
            "policy": ["Governance", "Legal Compliance", "Strategic Planning"],
            "complaint": ["Dispute Resolution", "Safeguarding", "Documentation"],
        },
        "nurse": {
            "medication": ["Pharmacology", "Clinical Assessment", "Patient Safety"],
            "medical": ["Clinical Practice", "Health Literacy", "Evidence-Based Care"],
        },
    }
    
    return competency_map.get(primary_role, {}).get(workflow, ["General Competency"])


async def _generate_assignment_policies(
    db, template_ids: List[str]
) -> Dict[str, Any]:
    """Generate automatic policy assignments for imported templates."""
    assignments = []
    
    templates = await db.document_templates.find(
        {"id": {"$in": template_ids}},
        {"_id": 0, "id": 1, "title": 1, "category": 1, "status": 1}
    ).to_list(None)
    
    for template in templates:
        category = template.get("category", "")
        roles = []
        
        if "policy" in category.lower() or "procedure" in category.lower():
            roles = ["registered_manager", "all_staff"]
        elif "form" in category.lower():
            roles = ["support_worker", "senior_carer"]
        elif "audit" in category.lower():
            roles = ["registered_manager"]
        elif "assessment" in category.lower():
            roles = ["senior_carer", "registered_manager"]
        
        for role in roles:
            assignments.append({
                "template_id": template["id"],
                "template_title": template["title"],
                "assigned_role": role,
                "assignment_type": "automatic",
                "confidence": 0.85,
            })
    
    return {
        "total_assignments": len(assignments),
        "assignments": assignments,
        "requires_confirmation": len(assignments) > 0,
    }


def _calculate_migration_progress(
    total_archive: int,
    pending_imports: int,
    published_count: int,
    skipped_count: int,
) -> Dict[str, Any]:
    """Calculate overall migration progress."""
    completed = published_count
    in_progress = pending_imports
    remaining = total_archive - completed - in_progress - skipped_count
    
    progress_pct = int((completed / max(total_archive, 1)) * 100)
    estimated_completion = 3 if progress_pct == 0 else max(1, int((total_archive - completed) / max(pending_imports, 10)) // 24)
    
    return {
        "total_templates": total_archive,
        "completed": completed,
        "in_progress": in_progress,
        "skipped": skipped_count,
        "remaining": remaining,
        "progress_percentage": progress_pct,
        "status": "complete" if progress_pct >= 95 else "on_track" if progress_pct >= 50 else "starting",
        "estimated_days": estimated_completion,
        "timeline": {
            "phase_1_critical": {"target": 57, "current": min(57, completed + in_progress)},
            "phase_2_high": {"target": 43, "current": min(43, max(0, completed + in_progress - 57))},
            "phase_3_medium": {"target": 103, "current": 0},
            "phase_4_low": {"target": 502, "current": 0},
        },
    }


@router.post("/document-templates/archive/bulk-update-destination")
async def bulk_update_destination(
    template_ids: List[str] = [],
    destination_section: str = "",
    user: dict = Depends(require_admin),
):
    """Bulk update destination section for multiple templates."""
    if not template_ids or not destination_section:
        raise HTTPException(status_code=422, detail="template_ids and destination_section required")
    
    db = get_db()
    now_iso = _utc_now_iso()
    
    # Verify destination exists
    register = get_service_user_destination_register()
    if not any(d["destination_section"] == destination_section for d in register):
        raise HTTPException(status_code=422, detail="Invalid destination_section")
    
    result = await db.document_templates.update_many(
        {"id": {"$in": template_ids}},
        {
            "$set": {
                "suggested_destination_section": destination_section,
                "updated_at": now_iso,
            }
        },
    )
    
    return {
        "message": "Bulk update completed",
        "modified_count": result.modified_count,
        "destination_section": destination_section,
    }


@router.get("/document-templates/archive/advanced-analytics")
async def get_advanced_archive_analytics(
    user: dict = Depends(require_admin),
):
    """Get comprehensive analytics for archive import dashboard."""
    db = get_db()
    manifest = _load_import_manifest()
    
    # Counts
    pending_imports = await db.document_templates.count_documents(
        {"import_status": "pending"}
    )
    published_imports = await db.document_templates.count_documents(
        {"import_status": "imported"}
    )
    skipped_imports = await db.document_templates.count_documents(
        {"import_status": "skipped"}
    )
    
    total_archive = manifest.get("total_templates", 705)
    
    # Service-user completeness
    su_completeness = await _score_service_user_completeness(db)
    
    # Migration progress
    migration_progress = _calculate_migration_progress(
        total_archive, pending_imports, published_imports, skipped_imports
    )
    
    # Missing legal documents
    missing_docs = _identify_missing_legal_documents()
    
    # Renewal calendar
    all_templates = await db.document_templates.find({}, {"_id": 0}).to_list(None)
    renewal_calendar = _generate_renewal_calendar(all_templates)
    
    return {
        "migration_progress": migration_progress,
        "service_user_completeness": su_completeness,
        "renewal_calendar": renewal_calendar,
        "missing_legal_documents": missing_docs,
        "counts": {
            "pending": pending_imports,
            "published": published_imports,
            "skipped": skipped_imports,
            "total": total_archive,
        },
    }


@router.post("/document-templates/archive/apply-policy-assignments")
async def apply_policy_assignments(
    template_ids: List[str] = [],
    user: dict = Depends(require_admin),
):
    """Apply automatic policy assignments to templates."""
    assignments = await _generate_assignment_policies(get_db(), template_ids)
    
    return {
        "message": "Policy assignments generated",
        "assignments": assignments["assignments"],
        "count": assignments["total_assignments"],
        "requires_confirmation": assignments["requires_confirmation"],
    }


@router.post("/document-templates/{template_id}/archive")
async def archive_document_template(
    template_id: str,
    user: dict = Depends(require_admin),
):
    """Archive a template and all its versions. Archived templates cannot be used for generation."""
    db = get_db()
    now_iso = datetime.utcnow().isoformat()
    actor_id = user.get("id") or user.get("_id") or "unknown"

    template = await db.document_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.get("status") == "archived":
        raise HTTPException(status_code=400, detail="Template is already archived")

    before_snapshot = {k: v for k, v in template.items() if k not in ("extracted_text",)}

    # Archive the template
    await db.document_templates.update_one(
        {"id": template_id},
        {"$set": {"status": "archived", "updated_at": now_iso}},
    )

    # Archive all versions
    await db.document_template_versions.update_many(
        {"template_id": template_id, "status": {"$ne": "archived"}},
        {"$set": {"status": "archived", "updated_at": now_iso}},
    )

    # Cancel any pending renewals
    await db.document_renewals.update_many(
        {"template_id": template_id, "status": {"$in": ["pending", "overdue"]}},
        {"$set": {"status": "cancelled", "updated_at": now_iso}},
    )

    await _write_document_audit_event(
        db=db,
        document_type="template",
        document_id=template_id,
        action="archive",
        actor_id=actor_id,
        before=before_snapshot,
        after={"status": "archived"},
        reason="Admin manual archive",
    )

    return {"message": "Template archived", "template_id": template_id}

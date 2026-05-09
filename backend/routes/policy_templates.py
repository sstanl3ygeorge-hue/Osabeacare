"""
Policy Templates Routes

Provides company-owned renderable policy templates.
MVP scope: Whistleblowing Policy only.

Endpoints:
  GET    /policy-templates
  GET    /policy-templates/{id}
  POST   /policy-templates
  PUT    /policy-templates/{id}
  POST   /policy-templates/{id}/publish
  GET    /policy-templates/{id}/pdf
  POST   /policy-templates/{id}/new-version
"""

import uuid
import io
import logging
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from .dependencies import get_db, get_current_user, require_admin, log_audit_action

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Policy Templates"])


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────

class PolicyTemplateContent(BaseModel):
    purpose: Optional[str] = ""
    principles: Optional[str] = ""
    scope: Optional[str] = ""
    procedure: Optional[str] = ""
    protections: Optional[str] = ""
    exclusions: Optional[str] = ""
    responsibilities: Optional[str] = ""
    references: Optional[str] = ""


class PolicyTemplateCreate(BaseModel):
    policy_key: str = "whistleblowing"
    title: str
    module: Optional[str] = "Governance"
    owner_name: Optional[str] = ""
    effective_date: Optional[str] = None   # ISO date string YYYY-MM-DD
    review_period_months: Optional[int] = 12
    content: Optional[PolicyTemplateContent] = None


class PolicyTemplateUpdate(BaseModel):
    title: Optional[str] = None
    module: Optional[str] = None
    owner_name: Optional[str] = None
    effective_date: Optional[str] = None
    review_period_months: Optional[int] = None
    content: Optional[PolicyTemplateContent] = None


class PolicyTemplateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    policy_key: str
    status: str
    version: int
    title: str
    module: Optional[str] = None
    owner_name: Optional[str] = None
    effective_date: Optional[str] = None
    review_period_months: int
    next_review_date: Optional[str] = None
    content: Optional[dict] = None
    render_artifact_url: Optional[str] = None
    render_artifact_filename: Optional[str] = None
    published_at: Optional[str] = None
    published_by: Optional[str] = None
    source_policy_id: Optional[str] = None
    created_at: str
    updated_at: str


# ─────────────────────────────────────────────────────────
# PDF rendering helper
# ─────────────────────────────────────────────────────────

def _render_policy_pdf(template: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    brand = colors.HexColor("#004D4D")
    light = colors.HexColor("#F8FAFA")

    title_style = ParagraphStyle(
        "PolicyTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=brand,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "PolicySubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#6B7280"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=brand,
        spaceBefore=14,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )

    content = template.get("content") or {}
    sections = [
        ("Statement of Purpose", content.get("purpose", "")),
        ("Principles", content.get("principles", "")),
        ("Scope", content.get("scope", "")),
        ("Procedure", content.get("procedure", "")),
        ("Protections", content.get("protections", "")),
        ("Exclusions", content.get("exclusions", "")),
        ("Responsibilities", content.get("responsibilities", "")),
        ("References", content.get("references", "")),
    ]

    elements = []

    # Header table
    version_str = f"v{template.get('version', 1)}"
    eff_date = template.get("effective_date") or ""
    review_date = template.get("next_review_date") or ""

    header_data = [
        ["Policy Title", template.get("title", "Policy")],
        ["Module", template.get("module", "")],
        ["Owner", template.get("owner_name", "")],
        ["Version", version_str],
        ["Effective Date", eff_date],
        ["Next Review Date", review_date],
    ]

    header_table = Table(header_data, colWidths=[50 * mm, 120 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), light),
                ("TEXTCOLOR", (0, 0), (0, -1), brand),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(Paragraph(template.get("title", "Policy"), title_style))
    elements.append(Paragraph("Osabeacares Ltd — Company Policy", subtitle_style))
    elements.append(header_table)
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, color=brand))

    for heading, body in sections:
        if body and body.strip():
            elements.append(Paragraph(heading, section_heading_style))
            # Handle newlines in text
            for para in body.strip().split("\n"):
                if para.strip():
                    elements.append(Paragraph(para.strip(), body_style))

    # Footer note
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    footer_text = (
        f"This policy was published on {template.get('published_at', '')[:10] if template.get('published_at') else 'N/A'}. "
        f"Version {version_str}. Next review: {review_date}. "
        "Osabeacares Ltd. All rights reserved."
    )
    elements.append(
        Paragraph(
            footer_text,
            ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=7,
                textColor=colors.HexColor("#9CA3AF"),
                spaceBefore=4,
            ),
        )
    )

    doc.build(elements)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@router.get("/policy-templates")
async def list_policy_templates(
    policy_key: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    filt = {}
    if policy_key:
        filt["policy_key"] = policy_key
    if status:
        filt["status"] = status
    docs = await db.policy_templates.find(filt, {"_id": 0}).sort("version", -1).to_list(length=200)
    return docs


@router.get("/policy-templates/{template_id}")
async def get_policy_template(template_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.policy_templates.find_one({"id": template_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return doc


@router.post("/policy-templates", response_model=PolicyTemplateResponse)
async def create_policy_template(
    body: PolicyTemplateCreate,
    user: dict = Depends(require_admin),
):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "policy_key": body.policy_key,
        "status": "draft",
        "version": 1,
        "title": body.title,
        "module": body.module,
        "owner_name": body.owner_name,
        "effective_date": body.effective_date,
        "review_period_months": body.review_period_months or 12,
        "next_review_date": None,
        "content": body.content.model_dump() if body.content else {},
        "render_artifact_url": None,
        "render_artifact_filename": None,
        "published_at": None,
        "published_by": None,
        "source_policy_id": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user["user_id"],
        "updated_by": user["user_id"],
    }
    await db.policy_templates.insert_one(doc)
    doc.pop("_id", None)
    await log_audit_action(user["user_id"], "create_policy_template", "policy_template", doc["id"], {"title": body.title})
    return doc


@router.put("/policy-templates/{template_id}", response_model=PolicyTemplateResponse)
async def update_policy_template(
    template_id: str,
    body: PolicyTemplateUpdate,
    user: dict = Depends(require_admin),
):
    db = get_db()
    doc = await db.policy_templates.find_one({"id": template_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if doc.get("status") == "published":
        raise HTTPException(
            status_code=409,
            detail="Cannot edit a published template. Use /new-version to create an editable draft.",
        )

    now = datetime.now(timezone.utc).isoformat()
    update = {"updated_at": now, "updated_by": user["user_id"]}

    if body.title is not None:
        update["title"] = body.title
    if body.module is not None:
        update["module"] = body.module
    if body.owner_name is not None:
        update["owner_name"] = body.owner_name
    if body.effective_date is not None:
        update["effective_date"] = body.effective_date
    if body.review_period_months is not None:
        update["review_period_months"] = body.review_period_months
    if body.content is not None:
        update["content"] = body.content.model_dump()

    await db.policy_templates.update_one({"id": template_id}, {"$set": update})
    updated = await db.policy_templates.find_one({"id": template_id}, {"_id": 0})
    await log_audit_action(user["user_id"], "update_policy_template", "policy_template", template_id, {})
    return updated


@router.post("/policy-templates/{template_id}/publish")
async def publish_policy_template(template_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.policy_templates.find_one({"id": template_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if doc.get("status") == "published":
        raise HTTPException(status_code=409, detail="Template already published")

    # Validate required fields
    content = doc.get("content") or {}
    errors = []
    for field in ("title", "module", "owner_name"):
        if not doc.get(field, "").strip():
            errors.append(field)
    if not doc.get("effective_date"):
        errors.append("effective_date")
    review_months = doc.get("review_period_months") or 0
    if review_months <= 0:
        errors.append("review_period_months")
    for section in ("purpose", "scope", "procedure"):
        if not content.get(section, "").strip():
            errors.append(f"content.{section}")
    if errors:
        raise HTTPException(status_code=422, detail=f"Missing required fields: {', '.join(errors)}")

    # Compute next review date
    try:
        eff = date.fromisoformat(doc["effective_date"])
        next_review = eff + relativedelta(months=review_months)
        next_review_str = next_review.isoformat()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid effective_date format (expected YYYY-MM-DD)")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Build updated doc for rendering
    doc_for_render = {**doc, "next_review_date": next_review_str, "published_at": now_iso}

    # Render PDF
    try:
        pdf_bytes = _render_policy_pdf(doc_for_render)
    except Exception as e:
        logger.error(f"PDF render failed for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="PDF rendering failed")

    # Store PDF
    file_url = None
    filename = f"policy_{doc.get('policy_key', 'template')}_v{doc.get('version', 1)}.pdf"
    try:
        from supabase_storage import upload_to_supabase, is_supabase_storage_configured
        if is_supabase_storage_configured():
            result = await upload_to_supabase(pdf_bytes, filename, folder="policies")
            file_url = result.get("url")
    except Exception as e:
        logger.warning(f"Could not upload rendered PDF to storage: {e}")

    # Mark published
    update = {
        "status": "published",
        "next_review_date": next_review_str,
        "published_at": now_iso,
        "published_by": user["user_id"],
        "render_artifact_url": file_url,
        "render_artifact_filename": filename,
        "updated_at": now_iso,
        "updated_by": user["user_id"],
    }
    await db.policy_templates.update_one({"id": template_id}, {"$set": update})

    # DUAL-PATH BOUNDARY: Sync to org_policies row (if linked or matched by name).
    # This is intentional — policy_templates is the STRUCTURED AUTHORING path for
    # rendered policies (currently Whistleblowing only). Template Library
    # (document_templates) is the FILE-IMPORT path and must NOT be wired to write
    # org_policies on publish, or it would overwrite the version managed here.
    # The two collections serve different purposes and must remain isolated.
    try:
        existing_policy = await db.org_policies.find_one(
            {"name": {"$regex": doc.get("title", ""), "$options": "i"}}
        )
        if not existing_policy and doc.get("source_policy_id"):
            existing_policy = await db.org_policies.find_one({"id": doc["source_policy_id"]})
        if existing_policy and file_url:
            await db.org_policies.update_one(
                {"id": existing_policy["id"]},
                {
                    "$set": {
                        "file_url": file_url,
                        "original_filename": filename,
                        "version": f"v{doc.get('version', 1)}",
                        "review_date": next_review_str,
                        "last_reviewed_at": now_iso,
                        "reviewed_by": user["user_id"],
                        "status": "active",
                        "source_type": "rendered_template",
                        "source_template_id": template_id,
                        "notes": "Published from rendered template",
                        "updated_at": now_iso,
                    }
                },
            )
    except Exception as e:
        logger.warning(f"Could not sync template publish to org_policies: {e}")

    await log_audit_action(
        user["user_id"],
        "publish_policy_template",
        "policy_template",
        template_id,
        {"version": doc.get("version"), "filename": filename},
    )
    return {
        "message": "Policy published",
        "version": doc.get("version"),
        "next_review_date": next_review_str,
        "render_artifact_url": file_url,
        "render_artifact_filename": filename,
    }


@router.get("/policy-templates/{template_id}/pdf")
async def stream_policy_template_pdf(template_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.policy_templates.find_one({"id": template_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        pdf_bytes = _render_policy_pdf(doc)
    except Exception as e:
        logger.error(f"PDF render failed: {e}")
        raise HTTPException(status_code=500, detail="PDF rendering failed")

    filename = f"policy_{doc.get('policy_key', 'template')}_v{doc.get('version', 1)}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/policy-templates/{template_id}/new-version")
async def new_version_policy_template(template_id: str, user: dict = Depends(require_admin)):
    db = get_db()
    doc = await db.policy_templates.find_one({"id": template_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if doc.get("status") != "published":
        raise HTTPException(status_code=409, detail="Only published templates can be versioned")

    now = datetime.now(timezone.utc).isoformat()
    new_doc = {
        **{k: v for k, v in doc.items() if k != "_id"},
        "id": str(uuid.uuid4()),
        "status": "draft",
        "version": doc.get("version", 1) + 1,
        "render_artifact_url": None,
        "render_artifact_filename": None,
        "published_at": None,
        "published_by": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user["user_id"],
        "updated_by": user["user_id"],
    }
    await db.policy_templates.insert_one(new_doc)
    new_doc.pop("_id", None)

    # Archive old
    await db.policy_templates.update_one({"id": template_id}, {"$set": {"status": "archived"}})

    await log_audit_action(user["user_id"], "new_version_policy_template", "policy_template", new_doc["id"], {"previous_id": template_id})
    return new_doc

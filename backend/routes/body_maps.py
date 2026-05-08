"""
Body Map Routes

Workers record observable injuries/marks during care visits.
Admins can review, update status, and download PDFs.

Fields match the Osabea Body Map – Male/Female CQC Expert templates:
  - Name of Individual
  - Date body map was completed
  - Date of when injury occurred (if known)
  - Name of Staff
  - Reported to
  - Additional information
  - Marked body regions (with descriptions)
"""

import uuid
import io
import base64
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from .dependencies import get_db, get_current_user, get_current_worker, require_admin, log_audit_action

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Body Maps"])

# ── Template image loader ────────────────────────────────────────────────────
# Images are embedded as base64 so they work in any deployment environment.
# Fallback to filesystem (backend/assets/body_maps/) if data module absent.

def _get_body_map_image_bytes(gender_raw: str) -> Optional[bytes]:
    """Return PNG bytes for the given gender, or None if unavailable."""
    g = gender_raw.strip().lower()
    is_male   = g in ("male", "m", "man")
    is_female = g in ("female", "f", "woman")
    if not is_male and not is_female:
        return None
    # Try embedded data module first (always works in production)
    try:
        from . import body_maps_data as _bmd
        b64 = _bmd.BODY_MAP_MALE_PNG_B64 if is_male else _bmd.BODY_MAP_FEMALE_PNG_B64
        return base64.b64decode(b64)
    except Exception:
        pass
    # Fallback: filesystem relative to this file
    assets_dir = Path(__file__).resolve().parent.parent / "assets" / "body_maps"
    filename = "body_map_male.png" if is_male else "body_map_female.png"
    candidate = assets_dir / filename
    if candidate.exists():
        return candidate.read_bytes()
    return None

# All named body regions — front and back, used in dropdown selector
BODY_REGIONS = [
    # Head & Face
    "Head – top",
    "Forehead",
    "Left eye / cheek",
    "Right eye / cheek",
    "Nose",
    "Mouth / lips",
    "Left ear",
    "Right ear",
    "Chin / jaw",
    # Neck & Trunk
    "Neck – front",
    "Neck – back",
    "Left shoulder",
    "Right shoulder",
    "Chest – left",
    "Chest – right",
    "Abdomen – left",
    "Abdomen – right",
    "Upper back – left",
    "Upper back – right",
    "Lower back – left",
    "Lower back – right",
    "Buttocks – left",
    "Buttocks – right",
    "Sacrum / coccyx",
    "Groin / perineal area",
    # Arms
    "Left upper arm",
    "Left elbow",
    "Left forearm",
    "Left wrist",
    "Left hand / fingers",
    "Right upper arm",
    "Right elbow",
    "Right forearm",
    "Right wrist",
    "Right hand / fingers",
    # Legs
    "Left hip",
    "Left thigh",
    "Left knee",
    "Left lower leg / shin",
    "Left ankle",
    "Left foot / toes",
    "Right hip",
    "Right thigh",
    "Right knee",
    "Right lower leg / shin",
    "Right ankle",
    "Right foot / toes",
]


def _annotate_body_map_image(img_bytes: bytes, marks: list) -> bytes:
    """
    Draws numbered red circle markers on the CQC Expert body-map template image
    at anatomically accurate positions for each recorded region.
    Returns PNG bytes of the annotated image.

    Coordinate convention:
    - Portrait images: head on RIGHT, feet on LEFT in each figure.
    - Four stacked views: front (y 0-22%), right-side, left-side, back (y 65-92%).
    - Anatomical LEFT = upper side. Anatomical RIGHT = lower side.
    - (x_pct, y_pct) are % of full image W/H.
    """
    from PIL import Image, ImageDraw, ImageFont

    # (x%, y%) mapped to each named region across front + back views
    # Calibrated to CQC Expert template: body horizontal, head on RIGHT, feet on LEFT
    REGION_COORDS_PCT: dict = {
        # ── Front view (y 0-24%) ──────────────────────────────────────────
        "Head \u2013 top":            (77.0,  7.0),   # top of head
        "Forehead":              (76.0,  8.0),
        "Left eye / cheek":      (74.0,  9.5),   # anatomical left = upper/top side of face
        "Right eye / cheek":     (74.0, 13.5),
        "Nose":                  (75.0, 11.5),
        "Mouth / lips":          (75.0, 12.5),
        "Left ear":              (80.0,  9.0),
        "Right ear":             (80.0, 14.0),
        "Chin / jaw":            (75.5, 14.5),
        "Neck \u2013 front":          (68.0, 16.5),
        "Neck \u2013 back":           (68.0, 16.5),
        "Left shoulder":         (62.0, 13.0),  # anatomical left = above center
        "Right shoulder":        (62.0, 19.0),  # anatomical right = below center
        "Chest \u2013 left":          (54.0, 14.0),
        "Chest \u2013 right":         (54.0, 18.0),
        "Abdomen \u2013 left":        (45.0, 16.0),
        "Abdomen \u2013 right":       (45.0, 18.0),
        "Groin / perineal area": (35.0, 18.0),
        # Left arm (anatomical left = upper side in lying position)
        "Left upper arm":        (65.0,  8.0),
        "Left elbow":            (50.0,  5.0),
        "Left forearm":          (38.0,  4.0),
        "Left wrist":            (28.0,  3.5),
        "Left hand / fingers":   (18.0,  3.0),
        # Right arm (anatomical right = lower side in lying position)
        "Right upper arm":       (65.0, 22.0),
        "Right elbow":           (50.0, 24.0),
        "Right forearm":         (38.0, 24.5),
        "Right wrist":           (28.0, 24.8),
        "Right hand / fingers":  (18.0, 25.0),
        # Legs front (y 18-45%)
        "Left hip":              (35.0, 10.0),   # left leg extends upward from body
        "Left thigh":            (25.0, 10.0),
        "Left knee":             (15.0, 10.0),
        "Left lower leg / shin": ( 8.0, 10.0),
        "Left ankle":            ( 3.0, 11.0),
        "Left foot / toes":      ( 1.0, 13.0),
        "Right hip":             (35.0, 22.0),  # right leg extends downward
        "Right thigh":           (33.0, 16.5),
        "Right knee":            (24.0, 17.0),
        "Right lower leg / shin":(16.0, 17.2),
        "Right ankle":           ( 9.0, 17.5),
        "Right foot / toes":     ( 3.5, 17.0),
        # ── Back view (y 66-90%) ──────────────────────────────────────────
        "Upper back \u2013 left":     (65.0, 70.0),
        "Upper back \u2013 right":    (65.0, 81.0),
        "Lower back \u2013 left":     (52.0, 73.0),
        "Lower back \u2013 right":    (52.0, 80.0),
        "Sacrum / coccyx":       (42.0, 78.0),
        "Buttocks \u2013 left":       (40.0, 71.0),
        "Buttocks \u2013 right":      (40.0, 82.0),
    }

    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    r = max(8, W // 45)  # circle radius scales with image width — smaller markers

    font = None
    for font_path in ["arial.ttf", "Arial.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            font = ImageFont.truetype(font_path, max(10, W // 28))
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    for i, mark in enumerate(marks, 1):
        region = mark.get("region", "")
        coord = REGION_COORDS_PCT.get(region)
        if coord is None:
            continue
        x = int(W * coord[0] / 100)
        y = int(H * coord[1] / 100)
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill=(220, 30, 30, 230),
                     outline=(255, 255, 255, 200))
        label = str(i)
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = r, r
        draw.text((x - tw // 2, y - th // 2), label,
                  fill=(255, 255, 255, 255), font=font)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    combined.save(buf, "PNG")
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────

class BodyMapMark(BaseModel):
    region: str
    description: str  # size, colour, type of mark


class WorkerBodyMapCreate(BaseModel):
    service_user_id: Optional[str] = None
    related_shift_id: Optional[str] = None
    gender: Optional[str] = "unknown"   # male | female | unknown
    injury_date: Optional[str] = None   # YYYY-MM-DD
    reported_to: Optional[str] = ""
    additional_information: Optional[str] = ""
    marks: List[BodyMapMark] = []


class AdminBodyMapUpdate(BaseModel):
    status: Optional[str] = None        # submitted | reviewed | closed
    reported_to: Optional[str] = None
    additional_information: Optional[str] = None
    review_notes: Optional[str] = None


# ─────────────────────────────────────────────────────────
# Body figure drawing (ReportLab vector, no external files)
# ─────────────────────────────────────────────────────────

def _draw_body_figure(marks: list, width: float = 160, height: float = 320):
    """
    Draws a simple front-view body outline using ReportLab shapes.
    Numbered red markers are placed at the recorded body regions.
    L/R labels follow anatomical convention (person's left = image right).
    """
    from reportlab.graphics.shapes import (
        Drawing, Circle, Rect, Ellipse, String, Polygon,
    )
    from reportlab.lib import colors

    d = Drawing(width, height)
    skin = colors.HexColor("#EDE0D0")
    oc = colors.HexColor("#004D4D")
    mark_c = colors.HexColor("#DC2626")
    cx = width / 2  # 80

    # ── Head ──────────────────────────────────────────────────────────────────
    d.add(Circle(cx, 293, 24, fillColor=skin, strokeColor=oc, strokeWidth=1.5))

    # ── Neck ──────────────────────────────────────────────────────────────────
    d.add(Rect(cx - 9, 258, 18, 21, fillColor=skin, strokeColor=oc, strokeWidth=1.5))

    # ── Torso (polygon: wider at shoulders, tapers to waist, flares at hips) ─
    d.add(Polygon([
        cx - 9,  279,   # neck-torso L
        cx - 44, 272,   # L shoulder (person's left = image right perspective: this is image left = person's right)
        cx - 38, 155,   # L waist
        cx - 40, 120,   # L hip
        cx + 40, 120,   # R hip
        cx + 38, 155,   # R waist
        cx + 44, 272,   # R shoulder
        cx + 9,  279,   # neck-torso R
    ], fillColor=skin, strokeColor=oc, strokeWidth=1.5))

    # ── Left arm (person's left = image right, x > cx) ────────────────────────
    d.add(Polygon([
        cx + 44, 272, cx + 62, 268,
        cx + 64, 200, cx + 47, 204,
    ], fillColor=skin, strokeColor=oc, strokeWidth=1.5))
    d.add(Polygon([
        cx + 47, 204, cx + 64, 200,
        cx + 62, 148, cx + 46, 151,
    ], fillColor=skin, strokeColor=oc, strokeWidth=1.5))
    d.add(Ellipse(cx + 54, 143, 12, 7, fillColor=skin, strokeColor=oc, strokeWidth=1.5))

    # ── Right arm (person's right = image left, x < cx) ──────────────────────
    d.add(Polygon([
        cx - 44, 272, cx - 62, 268,
        cx - 64, 200, cx - 47, 204,
    ], fillColor=skin, strokeColor=oc, strokeWidth=1.5))
    d.add(Polygon([
        cx - 47, 204, cx - 64, 200,
        cx - 62, 148, cx - 46, 151,
    ], fillColor=skin, strokeColor=oc, strokeWidth=1.5))
    d.add(Ellipse(cx - 54, 143, 12, 7, fillColor=skin, strokeColor=oc, strokeWidth=1.5))

    # ── Left leg (person's left = image right) ────────────────────────────────
    d.add(Rect(cx + 4, 28, 32, 92, fillColor=skin, strokeColor=oc, strokeWidth=1.5))
    d.add(Ellipse(cx + 20, 23, 18, 8, fillColor=skin, strokeColor=oc, strokeWidth=1.5))

    # ── Right leg (person's right = image left) ───────────────────────────────
    d.add(Rect(cx - 36, 28, 32, 92, fillColor=skin, strokeColor=oc, strokeWidth=1.5))
    d.add(Ellipse(cx - 20, 23, 18, 8, fillColor=skin, strokeColor=oc, strokeWidth=1.5))

    # ── Side labels ───────────────────────────────────────────────────────────
    grey = colors.HexColor("#9CA3AF")
    d.add(String(cx - 70, 250, "R", fontSize=7, fillColor=grey))
    d.add(String(cx + 68, 250, "L", fontSize=7, fillColor=grey))
    d.add(String(cx - 22, 4, "Front view", fontSize=6, fillColor=grey))

    # ── Region → (x, y) coordinate map ───────────────────────────────────────
    # Anatomical: person's LEFT = image RIGHT (x > cx), person's RIGHT = image LEFT (x < cx)
    COORDS = {
        "Head – top":            (cx,       316),
        "Forehead":              (cx,       307),
        "Left eye / cheek":      (cx + 11,  295),
        "Right eye / cheek":     (cx - 11,  295),
        "Nose":                  (cx,       290),
        "Mouth / lips":          (cx,       282),
        "Left ear":              (cx + 26,  293),
        "Right ear":             (cx - 26,  293),
        "Chin / jaw":            (cx,       270),
        "Neck – front":          (cx,       267),
        "Neck – back":           (cx,       267),
        "Left shoulder":         (cx + 50,  273),
        "Right shoulder":        (cx - 50,  273),
        "Chest – left":          (cx + 18,  255),
        "Chest – right":         (cx - 18,  255),
        "Abdomen – left":        (cx + 16,  205),
        "Abdomen – right":       (cx - 16,  205),
        "Upper back – left":     (cx + 18,  248),
        "Upper back – right":    (cx - 18,  248),
        "Lower back – left":     (cx + 16,  168),
        "Lower back – right":    (cx - 16,  168),
        "Buttocks – left":       (cx + 18,  130),
        "Buttocks – right":      (cx - 18,  130),
        "Sacrum / coccyx":       (cx,       118),
        "Groin / perineal area": (cx,       124),
        "Left upper arm":        (cx + 57,  246),
        "Left elbow":            (cx + 57,  212),
        "Left forearm":          (cx + 56,  182),
        "Left wrist":            (cx + 55,  158),
        "Left hand / fingers":   (cx + 54,  143),
        "Right upper arm":       (cx - 57,  246),
        "Right elbow":           (cx - 57,  212),
        "Right forearm":         (cx - 56,  182),
        "Right wrist":           (cx - 55,  158),
        "Right hand / fingers":  (cx - 54,  143),
        "Left hip":              (cx + 30,  117),
        "Left thigh":            (cx + 20,   88),
        "Left knee":             (cx + 20,   68),
        "Left lower leg / shin": (cx + 20,   50),
        "Left ankle":            (cx + 20,   33),
        "Left foot / toes":      (cx + 20,   21),
        "Right hip":             (cx - 30,  117),
        "Right thigh":           (cx - 20,   88),
        "Right knee":            (cx - 20,   68),
        "Right lower leg / shin":(cx - 20,   50),
        "Right ankle":           (cx - 20,   33),
        "Right foot / toes":     (cx - 20,   21),
    }

    for i, mark in enumerate(marks, 1):
        coord = COORDS.get(mark.get("region", ""))
        if coord:
            x, y = coord
            d.add(Circle(x, y, 8, fillColor=mark_c, strokeColor=colors.white, strokeWidth=1))
            d.add(String(x - 3.5, y - 3, str(i), fontSize=7, fillColor=colors.white))

    return d


def _make_drawing_flowable(drawing):
    """
    Wraps a ReportLab Drawing in a proper Flowable so it renders
    correctly inside Platypus documents and Tables.
    """
    from reportlab.platypus import Flowable
    from reportlab.graphics import renderPDF

    class _Inner(Flowable):
        def __init__(self, d):
            super().__init__()
            self._d = d
            self.width = d.width
            self.height = d.height

        def wrap(self, aW, aH):
            return self.width, self.height

        def draw(self):
            renderPDF.draw(self._d, self.canv, 0, 0)

    return _Inner(drawing)


# ─────────────────────────────────────────────────────────
# PDF renderer
# ─────────────────────────────────────────────────────────

def _render_body_map_pdf(doc: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    doc_pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    brand = colors.HexColor("#004D4D")
    light = colors.HexColor("#F8FAFA")

    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, textColor=brand, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#6B7280"), alignment=TA_CENTER, spaceAfter=10)
    instruction_style = ParagraphStyle("Instr", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#374151"), leading=12, spaceAfter=6)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=11, textColor=brand, spaceBefore=12, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=13, spaceAfter=4)

    # Normalize stored gender (service users use "Male"/"Female")
    raw_gender = (doc.get("gender", "") or "").strip().lower()
    if raw_gender in ("male", "m", "man"):
        gender_label = "Male"
    elif raw_gender in ("female", "f", "woman"):
        gender_label = "Female"
    else:
        gender_label = None  # don't print "unknown" in the title

    title = f"Body Map \u2013 {gender_label}" if gender_label else "Body Map"

    marks = doc.get("marks", [])

    elements = [
        Paragraph(title, title_style),
        Paragraph("Osabea Healthcare Solutions Ltd", subtitle_style),
        HRFlowable(width="100%", thickness=1, color=brand),
        Spacer(1, 6),
        Paragraph(
            "Staff must not carry out any physical inspection of Individuals if they have reason to suspect harm. "
            "This is the role of medical practitioners when there is a need.",
            instruction_style
        ),
        Paragraph(
            "The body map is for recording injuries that the Staff may have observed whilst carrying out their "
            "normal care and support activities. Where appropriate use this form to provide further information "
            "to support a safeguarding concern.",
            instruction_style
        ),
        Paragraph(
            "Record the area/site of any injury, marks, bruising, etc. Please also indicate the rough size in "
            "centimetres or use a comparison, for example, the same size as a 10p coin. Record details such as "
            "the colour of bruising, swelling and shape.",
            instruction_style
        ),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")),
    ]

    # ── Metadata table ────────────────────────────────────────────────────────
    meta = [
        ["Name of Individual:", doc.get("service_user_name", "")],
        ["Date body map was completed:", doc.get("completed_date", "")[:10] if doc.get("completed_date") else ""],
        ["Date of when injury occurred (if known):", doc.get("injury_date", "") or "Not specified"],
        ["Name of Staff:", doc.get("staff_name", "")],
        ["Reported to:", doc.get("reported_to", "") or "—"],
    ]
    meta_table = Table(meta, colWidths=[80 * mm, 90 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), light),
        ("TEXTCOLOR", (0, 0), (0, -1), brand),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(Spacer(1, 8))
    elements.append(meta_table)

    # ── Body figure diagram ───────────────────────────────────────────────────
    elements.append(Paragraph("Body Diagram", section_style))
    diagram_note = ParagraphStyle("FigNote", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#6B7280"), spaceAfter=6)

    img_path = _get_body_map_image_bytes(raw_gender)
    if img_path is None and raw_gender not in ("male", "female"):
        img_path = _get_body_map_image_bytes("male")  # default to male outline if no gender recorded
    if img_path:
        elements.append(Paragraph(
            "Red numbered markers show the location of each recorded mark. "
            "L\u2009=\u2009person\u2019s left, R\u2009=\u2009person\u2019s right (anatomical). "
            "Front view at top; back view at bottom.",
            diagram_note,
        ))
        annotated_bytes = _annotate_body_map_image(img_path, marks)
        diagram = Image(io.BytesIO(annotated_bytes))
        diagram.drawHeight = 200 * mm  # larger, more vertical emphasis
        diagram.drawWidth = diagram.drawHeight * (diagram.imageWidth / float(diagram.imageHeight))
        img_table = Table([[diagram]], colWidths=[170 * mm])
        img_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(img_table)
    else:
        elements.append(Paragraph(
            "Template image unavailable, showing fallback diagram. "
            "Red numbered markers indicate recorded mark locations.",
            diagram_note,
        ))
        figure = _draw_body_figure(marks, width=160, height=320)
        fig_table = Table([[_make_drawing_flowable(figure)]], colWidths=[170 * mm])
        fig_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(fig_table)

    # ── Marks table ───────────────────────────────────────────────────────────
    if marks:
        elements.append(Paragraph("Recorded Marks / Injuries", section_style))
        marks_data = [["#", "Body Region", "Description"]]
        for i, mark in enumerate(marks, 1):
            marks_data.append([str(i), mark.get("region", ""), mark.get("description", "")])
        marks_table = Table(marks_data, colWidths=[10 * mm, 65 * mm, 95 * mm])
        marks_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), brand),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
        ]))
        elements.append(marks_table)
    else:
        elements.append(Paragraph("Recorded Marks / Injuries", section_style))
        elements.append(Paragraph("No marks recorded.", body_style))

    # ── Additional information ────────────────────────────────────────────────
    elements.append(Paragraph("Additional Information", section_style))
    elements.append(Paragraph(doc.get("additional_information", "") or "None provided.", body_style))

    # ── Manager review notes ──────────────────────────────────────────────────
    if doc.get("review_notes"):
        elements.append(Paragraph("Manager Review Notes", section_style))
        elements.append(Paragraph(doc["review_notes"], body_style))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    reviewed_str = f"Reviewed: {doc['reviewed_at'][:10]}. " if doc.get("reviewed_at") else ""
    footer = (
        f"Submitted by {doc.get('staff_name', '')} on "
        f"{doc.get('completed_date', '')[:10] if doc.get('completed_date') else 'N/A'}. "
        f"{reviewed_str}"
        "Osabea Healthcare Solutions Ltd — Body Map Record."
    )
    elements.append(Paragraph(footer, ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#9CA3AF"), spaceBefore=4)))

    doc_pdf.build(elements)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────
# Worker endpoints
# ─────────────────────────────────────────────────────────

@router.post("/worker/body-maps")
async def worker_create_body_map(
    payload: WorkerBodyMapCreate,
    worker: dict = Depends(get_current_worker),
):
    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to worker account")

    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "first_name": 1, "last_name": 1, "status": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.get("status") != "active":
        raise HTTPException(status_code=403, detail="Body map recording is only available for active employees")

    staff_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()

    # Auto-resolve service user info
    service_user_id = payload.service_user_id
    service_user_name = ""
    gender = payload.gender or "unknown"

    if payload.related_shift_id:
        shift = await db.shifts.find_one({"id": payload.related_shift_id}, {"_id": 0, "service_user_id": 1})
        if shift and shift.get("service_user_id"):
            service_user_id = shift["service_user_id"]

    if service_user_id:
        su = await db.service_users.find_one({"id": service_user_id}, {"_id": 0, "full_name": 1, "gender": 1})
        if su:
            service_user_name = su.get("full_name", "")
            if not payload.gender or payload.gender == "unknown":
                # Normalize: service users store "Male"/"Female" (capitalized)
                raw = (su.get("gender", "") or "").strip().lower()
                if raw in ("male", "m", "man"):
                    gender = "male"
                elif raw in ("female", "f", "woman"):
                    gender = "female"
                else:
                    gender = raw or "unknown"

    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "service_user_id": service_user_id,
        "service_user_name": service_user_name,
        "gender": gender,
        "completed_date": now.isoformat(),
        "injury_date": payload.injury_date,
        "staff_name": staff_name,
        "submitted_by_employee_id": employee_id,
        "related_shift_id": payload.related_shift_id,
        "reported_to": payload.reported_to or "",
        "additional_information": payload.additional_information or "",
        "marks": [m.model_dump() for m in payload.marks],
        "status": "submitted",
        "review_notes": None,
        "reviewed_at": None,
        "reviewed_by": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.body_maps.insert_one(doc)
    doc.pop("_id", None)
    await log_audit_action(employee_id, "worker_create_body_map", "body_map", doc["id"], {"service_user_id": service_user_id})
    return {"success": True, "body_map": doc}


@router.get("/admins")
async def get_admins_and_managers(db: dict = Depends(get_db)):
    """Return list of admin, manager, and supervisor names for dropdown."""
    users = await db.users.find(
        {"role": {"$in": ["admin", "super_admin", "manager", "branch_manager", "supervisor"]}},
        {"_id": 0, "full_name": 1, "name": 1}
    ).to_list(None)
    
    # Use full_name if available, otherwise name field
    names = []
    for user in users:
        name = user.get("full_name") or user.get("name")
        if name:
            names.append(name)
    
    return {"admins": sorted(set(names))}  # Remove duplicates and sort


@router.get("/worker/body-maps")
async def worker_list_body_maps(worker: dict = Depends(get_current_worker)):
    db = get_db()
    employee_id = worker.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee linked to worker account")
    docs = await db.body_maps.find(
        {"submitted_by_employee_id": employee_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=100)
    return {"body_maps": docs, "total": len(docs)}


# ─────────────────────────────────────────────────────────
# Admin / manager endpoints
# ─────────────────────────────────────────────────────────

@router.get("/compliance/body-maps")
async def list_body_maps(
    service_user_id: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    filt = {}
    if service_user_id:
        filt["service_user_id"] = service_user_id
    if status:
        filt["status"] = status
    docs = await db.body_maps.find(filt, {"_id": 0}).sort("created_at", -1).to_list(length=500)
    return docs


@router.get("/compliance/body-maps/{body_map_id}")
async def get_body_map(body_map_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.body_maps.find_one({"id": body_map_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Body map not found")
    return doc


@router.put("/compliance/body-maps/{body_map_id}")
async def update_body_map(
    body_map_id: str,
    body: AdminBodyMapUpdate,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    doc = await db.body_maps.find_one({"id": body_map_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Body map not found")

    now = datetime.now(timezone.utc).isoformat()
    update = {"updated_at": now}
    if body.status:
        update["status"] = body.status
        if body.status == "reviewed" and not doc.get("reviewed_at"):
            update["reviewed_at"] = now
            update["reviewed_by"] = user["user_id"]
    if body.reported_to is not None:
        update["reported_to"] = body.reported_to
    if body.additional_information is not None:
        update["additional_information"] = body.additional_information
    if body.review_notes is not None:
        update["review_notes"] = body.review_notes

    await db.body_maps.update_one({"id": body_map_id}, {"$set": update})
    updated = await db.body_maps.find_one({"id": body_map_id}, {"_id": 0})
    await log_audit_action(user["user_id"], "update_body_map", "body_map", body_map_id, {"status": body.status})
    return updated


@router.get("/compliance/body-maps/{body_map_id}/pdf")
async def download_body_map_pdf(body_map_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.body_maps.find_one({"id": body_map_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Body map not found")
    # If gender was stored as unknown, try to resolve from service user now
    raw_stored = (doc.get("gender", "") or "").strip().lower()
    if raw_stored in ("unknown", "", None) and doc.get("service_user_id"):
        su = await db.service_users.find_one(
            {"id": doc["service_user_id"]}, {"_id": 0, "gender": 1}
        )
        if su:
            raw = (su.get("gender", "") or "").strip().lower()
            if raw in ("male", "m", "man"):
                doc = {**doc, "gender": "male"}
            elif raw in ("female", "f", "woman"):
                doc = {**doc, "gender": "female"}
    try:
        pdf_bytes = _render_body_map_pdf(doc)
    except Exception as e:
        logger.error(f"Body map PDF render failed: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    gender = doc.get("gender", "unknown")
    su_name = (doc.get("service_user_name", "") or "").replace(" ", "_")
    date_str = (doc.get("completed_date", "") or "")[:10]
    filename = f"body_map_{su_name}_{date_str}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/service-users/{service_user_id}/body-maps")
async def get_service_user_body_maps(service_user_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.body_maps.find(
        {"service_user_id": service_user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=200)
    return docs

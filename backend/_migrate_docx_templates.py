"""
One-shot migration: rewrite zero_hour_contract_template.docx so every legacy
(insert ...) placeholder is replaced with a canonical {{token}} placeholder.

Also merges runs that were split across XML w:r elements so text substitution
in _replace_contract_text() is reliable with a simple str.replace().

Run once:
    python _migrate_docx_templates.py [--dry-run]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from docx import Document

DOCX_PATH = Path(__file__).resolve().parent / "agreement_assets" / "zero_hour_contract_template.docx"
BACKUP_PATH = DOCX_PATH.with_suffix(".docx.bak")

# Ordered list of (old_text, new_text) pairs applied left-to-right on the
# *concatenated* paragraph text.  More-specific patterns come first.
MIGRATIONS: list[tuple[str, str]] = [
    # ── company header paragraph ──────────────────────
    ("iCubeDALPro Limited t/a iCareServicesGroup", "{{company_name}}"),
    # ── body fragments (left-over after company split) ──
    ("iCubeDALPro", "{{company_name}}"),
    (" Limited t/a iCareServicesGroup", ""),
    (" Limited t/a ", ""),
    ("iCareServicesGroup", ""),
    # ── address ───────────────────────────────────────
    ("Unit 12, Harrods Road, Harlow, CM19 5BJ", "{{company_address}}"),
    # ── employee / dates ──────────────────────────────
    ("(Insert Employee Name)", "{{employee_name}}"),
    ("(insert name of employee)", "{{employee_name}}"),
    ("(insert date of issue)", "{{issue_date}}"),
    ("(insert job title)", "{{job_title}}"),
    ("(insert 'will commence' or 'commenced')", "{{commencement_wording}}"),
    ("(insert date this contract starts)", "{{contract_start_date}}"),
    ("(insert continuous service date of employment)", "{{continuous_service_date}}"),
    # ── pay rates ─────────────────────────────────────
    # Keep the '£' prefix that sits in an adjacent run
    ("\xa3(insert amount)", "\xa3{{hourly_rate}}"),   # \xa3 == £
    ("(insert amount)", "{{hourly_rate}}"),
    # Sleep-in: "£40 per night" → "£{{sleep_in_rate}} per night"
    ("\xa340 per night", "\xa3{{sleep_in_rate}} per night"),
]

# Sentinel fragments that get cleaned up after substitution
CLEANUP: list[tuple[str, str]] = [
    # Avoid doubled tokens from multi-run company name
    ("{{company_name}}{{company_name}}", "{{company_name}}"),
    ("{{company_name}} {{company_name}}", "{{company_name}}"),
]


def _migrate_paragraph(para) -> bool:
    """Merge all runs into the first run and apply MIGRATIONS. Returns True if changed."""
    original = para.text

    updated = original
    for old, new in MIGRATIONS:
        if old in updated:
            updated = updated.replace(old, new)
    for old, new in CLEANUP:
        updated = updated.replace(old, new)

    if updated == original:
        return False

    # Write the entire new text into the first non-empty run (or first run if
    # all are empty) then blank out every subsequent run.  This preserves the
    # character-level formatting (bold, italic, font) of the lead run.
    first_run = next((r for r in para.runs if r.text.strip()), None)
    if first_run is None and para.runs:
        first_run = para.runs[0]

    if first_run is not None:
        # Find the index so we can use index-based comparison (para.runs creates
        # new Python wrapper objects on each access, so identity checks fail).
        first_idx = next(
            i for i, r in enumerate(para.runs) if r._r is first_run._r
        )
        for i, run in enumerate(para.runs):
            run.text = updated if i == first_idx else ""
    return True


def migrate(dry_run: bool = False) -> None:
    if not DOCX_PATH.exists():
        raise FileNotFoundError(f"Template not found: {DOCX_PATH}")

    doc = Document(str(DOCX_PATH))

    changed_count = 0
    for i, para in enumerate(doc.paragraphs):
        if _migrate_paragraph(para):
            changed_count += 1
            print(f"  [para {i:03d}] → {para.text[:110]!r}")

    print(f"\n{changed_count} paragraph(s) updated.")

    if dry_run:
        print("[dry-run] No files written.")
        return

    # Back up the original only once; don't overwrite an existing backup.
    if not BACKUP_PATH.exists():
        shutil.copy2(DOCX_PATH, BACKUP_PATH)
        print(f"Backup saved → {BACKUP_PATH.name}")

    doc.save(str(DOCX_PATH))
    print(f"Template saved → {DOCX_PATH.name}")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    migrate(dry_run=dry)

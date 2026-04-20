"""
reference_matching.py — Shared employer name normalisation and matching helpers.

Used by:
  - routes/reference_comparison.py  (API endpoint)
  - stageGates.py                   (recruitment gate)

Keeping this logic in one place ensures the gate and the UI cross-check
panel always produce the same result for the same data.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Suffix list — order matters: strip the longest multi-word suffix first so
# "nhs foundation trust" is removed before "trust" acts alone.
# ---------------------------------------------------------------------------
EMPLOYER_SUFFIXES: list[str] = [
    "nhs foundation trust",
    "foundation trust",
    "nhs trust",
    "community health",
    "healthcare services",
    "health care services",
    "healthcare",
    "health care",
    "support services",
    "care home",
    "limited liability partnership",
    "limited liability",
    "llp",
    "ltd",
    "limited",
    "plc",
    "inc",
    "llc",
    "group",
    "trust",
    "foundation",
]


def strip_employer_suffix(name: str) -> str:
    """Remove one trailing legal / NHS suffix from an already-normalised name."""
    for suffix in EMPLOYER_SUFFIXES:
        if name.endswith(f" {suffix}"):
            return name[: -(len(suffix) + 1)].strip()
    return name


def normalize_employer(name: str) -> str:
    """
    Canonical form for fuzzy employer comparison:
      1. lowercase
      2. replace punctuation → space
      3. collapse whitespace
      4. strip one trailing common suffix

    Example:
      "Kent Community Health NHS Foundation Trust" → "kent community health"
      "Kent Community Health NHS Foundation"       → "kent community health"
    Both normalise to the same root → they MATCH instead of raising a false flag.
    """
    name = (name or "").lower().strip()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return strip_employer_suffix(name)


def match_employers(
    ref_company: str,
    employment_history: list[dict],
) -> tuple[bool, dict | None, str]:
    """
    Match a declared reference company against a list of employment history entries.

    Returns
    -------
    (matched, matching_employer_dict, match_reason)

    match_reason values
    -------------------
    "exact"      — normalised names are identical
    "substring"  — one normalised name is contained in the other
    "normalized" — suffix-stripped forms match (catches "Trust" vs "Foundation Trust")
    "none"       — no match found

    Strategy (applied in order — stops at first match):
      Pass 1: exact + substring on fully-normalised names
      Pass 2: second suffix-strip layer + substring (edge cases, e.g. nested NHSisms)
    """
    ref_norm = normalize_employer(ref_company)
    if not ref_norm:
        return False, None, "none"

    # Pass 1 — normalised exact / substring
    for emp in employment_history:
        emp_norm = normalize_employer(emp.get("employer_name") or "")
        if not emp_norm:
            continue
        if ref_norm == emp_norm:
            return True, emp, "exact"
        if ref_norm in emp_norm or emp_norm in ref_norm:
            return True, emp, "substring"

    # Pass 2 — strip one more suffix layer from both sides
    ref_stripped = strip_employer_suffix(ref_norm)
    if ref_stripped and ref_stripped != ref_norm:
        for emp in employment_history:
            emp_stripped = strip_employer_suffix(normalize_employer(emp.get("employer_name") or ""))
            if emp_stripped and (
                ref_stripped in emp_stripped or emp_stripped in ref_stripped
            ):
                return True, emp, "normalized"

    return False, None, "none"


def identify_most_recent_employer(employment_history: list[dict]) -> str | None:
    """
    Return the *normalised* name of the most-recent employer.

    Priority
    --------
    1. Any entry where is_current = True
    2. Entry with the latest end_date year
    3. First entry in the list (caller should order most-recent first)

    Returns None if the list is empty.
    """
    if not employment_history:
        return None

    current = [e for e in employment_history if e.get("is_current")]
    if current:
        return normalize_employer(current[0].get("employer_name") or "")

    def _year(emp: dict) -> int:
        date_str = emp.get("end_date") or emp.get("start_date") or ""
        m = re.search(r"(\d{4})", str(date_str))
        return int(m.group(1)) if m else 0

    best = max(employment_history, key=_year)
    name = best.get("employer_name") or ""
    return normalize_employer(name) if name else None


def compliance_status_for_match(
    matched: bool,
    matching_employer: dict | None,
    is_most_recent: bool,
    override_reason: str | None = None,
) -> str:
    """
    Return CQC compliance status for a single reference.

    "ok"      — matched AND is the most-recent employer
    "warning" — matched but to an earlier employer (NHS: investigate, not auto-fail)
    "alert"   — no employment-history match at all (blocker unless override_reason set)

    If override_reason is present the caller may downgrade "alert" → "warning".
    """
    if matched and is_most_recent:
        return "ok"
    if matched and not is_most_recent:
        return "warning"
    # No match
    if override_reason:
        return "warning"   # admin has already recorded an explanation
    return "alert"


# Human-readable labels used by both the API response and the gate.
MATCH_REASON_LABELS: dict[str, str] = {
    "exact":      "Exact match",
    "substring":  "Partial match",
    "normalized": "Matched ignoring common suffixes",
    "none":       "No match",
}

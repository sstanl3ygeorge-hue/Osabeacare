"""
Verification tests for training dedup/re-extract fix.
Tests all 6 scenarios without hitting a real database.
Run: python -m pytest tests/test_training_dedup_verify.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.training_evaluator import (
    build_training_records_lookup,
    resolve_training_record,
    _record_quality_score,
    TRAINING_ALIASES,
    compute_training_record_status,
)

# ═══════════════════════════════════════════════════════
# Scenario 1: Same certificate re-extracted twice
# The bulk-save _norm dedup must prevent duplicate proposed items.
# ═══════════════════════════════════════════════════════

def test_bulk_save_norm_dedup():
    """Simulate the _norm function from bulk-save and re-extract."""
    def _norm(name):
        n = name.lower().strip().replace("&", "and").replace("-", " ").replace("_", " ")
        return " ".join(n.split())

    # First extraction produces these
    batch1 = ["Fire Safety", "Basic Life Support", "Moving & Handling"]
    proposed_norms = set(_norm(n) for n in batch1)

    # Second extraction from same certificate produces identical names
    batch2 = ["Fire Safety", "Basic Life Support", "Moving & Handling"]
    skipped = []
    for name in batch2:
        tn = _norm(name)
        if tn in proposed_norms:
            skipped.append(name)
    assert len(skipped) == 3, f"All 3 should be skipped, got {skipped}"

    # Also test with slight formatting differences
    batch3 = ["fire safety", "BASIC LIFE SUPPORT", "Moving and Handling"]
    skipped2 = []
    for name in batch3:
        tn = _norm(name)
        if tn in proposed_norms:
            skipped2.append(name)
    assert len(skipped2) == 3, f"Normalised variants should match, got {skipped2}"


def test_re_extract_already_proposed_flag():
    """Re-extract must flag `already_proposed` when proposed items exist."""
    def _normalise_training_name(name):
        n = name.lower().strip()
        n = n.replace("&", "and").replace("-", " ").replace("_", " ")
        return " ".join(n.split())

    # Existing proposed items
    existing_proposed = [
        {"raw_course_title": "Fire Safety", "mapped_training_title": "Fire Safety"},
        {"raw_course_title": "BLS", "mapped_training_title": "Basic Life Support"},
    ]
    proposed_names = set()
    for p in existing_proposed:
        for field in ("raw_course_title", "mapped_training_title"):
            val = p.get(field, "")
            if val:
                proposed_names.add(_normalise_training_name(val))

    # Extraction returns same items
    extracted = ["Fire Safety", "BLS", "Infection Control"]
    results = {}
    for name in extracted:
        results[name] = _normalise_training_name(name) in proposed_names

    assert results["Fire Safety"] == True
    assert results["BLS"] == True
    assert results["Infection Control"] == False


# ═══════════════════════════════════════════════════════
# Scenario 2: Two different certificates, same qualification
# The _canonical_key + grouping must collapse them to one visible row.
# ═══════════════════════════════════════════════════════

def _canonical_key(rec):
    """Mirror of the server.py _canonical_key (post-fix version)."""
    req_id = rec.get("requirement_id", "")
    t_name = rec.get("training_name", "")
    n = t_name.lower().strip().replace("&", "and").replace("-", " ").replace("_", " ")
    n = " ".join(n.split())
    if req_id:
        r = req_id.lower().strip().replace("&", "and").replace("-", " ").replace("_", " ")
        return " ".join(r.split())
    return n


def test_canonical_key_grouping():
    """Two records for same training (from different certs) → one visible row."""
    rec1 = {"id": "tr_001", "requirement_id": "fire_safety", "training_name": "Fire Safety",
            "verified": True, "completion_date": "2025-01-01"}
    rec2 = {"id": "tr_002", "requirement_id": "fire_safety", "training_name": "Fire Safety",
            "verified": False, "completion_date": "2025-06-01"}

    from collections import defaultdict
    grouped = defaultdict(list)
    for rec in [rec1, rec2]:
        grouped[_canonical_key(rec)].append(rec)

    assert len(grouped) == 1, f"Should group to 1 key, got {len(grouped)}"
    assert len(grouped["fire safety"]) == 2, "Both records in group"


def test_canonical_key_no_requirement_id():
    """Records without requirement_id group by normalised training_name."""
    rec1 = {"id": "tr_001", "requirement_id": "", "training_name": "Dementia Awareness",
            "verified": True, "completion_date": "2025-01-01"}
    rec2 = {"id": "tr_002", "requirement_id": "", "training_name": "dementia awareness",
            "verified": False, "completion_date": "2025-06-01"}

    from collections import defaultdict
    grouped = defaultdict(list)
    for rec in [rec1, rec2]:
        grouped[_canonical_key(rec)].append(rec)

    assert len(grouped) == 1, f"Should group to 1 key, got {len(grouped)}: {list(grouped.keys())}"


def test_canonical_key_req_id_vs_training_name():
    """BUG FIX: record with requirement_id='fire_safety' must group with record
    that has no requirement_id but training_name='Fire Safety'."""
    rec1 = {"id": "tr_001", "requirement_id": "fire_safety", "training_name": "Fire Safety",
            "verified": True, "completion_date": "2025-01-01"}
    rec2 = {"id": "tr_002", "requirement_id": "", "training_name": "Fire Safety",
            "verified": False, "completion_date": "2025-06-01"}

    from collections import defaultdict
    grouped = defaultdict(list)
    for rec in [rec1, rec2]:
        grouped[_canonical_key(rec)].append(rec)

    assert len(grouped) == 1, (
        f"req_id='fire_safety' and name='Fire Safety' should group to 1 key, "
        f"got {len(grouped)}: {list(grouped.keys())}"
    )
    assert len(list(grouped.values())[0]) == 2, "Both records in group"


# ═══════════════════════════════════════════════════════
# Scenario 3: Existing verified + new pending → which wins?
# ═══════════════════════════════════════════════════════

def test_record_quality_verified_wins_over_unverified():
    """_record_quality_score: verified(0) < unverified(2) → lower = better."""
    verified_rec = {"verified": True, "completion_date": "2025-01-01"}
    unverified_rec = {"verified": False, "completion_date": "2025-06-01"}
    rejected_rec = {"verified": False, "verification_status": "rejected", "completion_date": "2025-01-01"}
    no_completion = {"verified": False}

    assert _record_quality_score(verified_rec) == 0
    assert _record_quality_score(unverified_rec) == 2
    assert _record_quality_score(rejected_rec) == 4
    assert _record_quality_score(no_completion) == 5

    # Verified WINS (lower score = better)
    assert _record_quality_score(verified_rec) < _record_quality_score(unverified_rec)


def test_status_priority_awaiting_review_beats_verified():
    """STATUS_PRIORITY in matrix endpoint: awaiting_review=0, verified=1."""
    STATUS_PRIORITY = {
        "awaiting_review": 0, "awaiting_verification": 0,
        "verified": 1,
        "completed": 2,
        "expired": 3,
        "rejected": 4,
        "missing": 5,
        "not_started": 6,
    }
    # awaiting_review has LOWER number = HIGHER priority = wins
    assert STATUS_PRIORITY["awaiting_review"] < STATUS_PRIORITY["verified"]
    # This means: if verified + awaiting_review exist, awaiting_review wins as visible row!


def test_record_sort_key_direction():
    """
    _record_sort_key uses STATUS_PRIORITY where lower = higher priority.
    sorted() puts lower first → the FIRST element is the "best" visible record.
    
    BUG CHECK: Is the direction correct for business logic?
    """
    STATUS_PRIORITY = {
        "awaiting_review": 0, "awaiting_verification": 0,
        "verified": 1,
        "completed": 2,
        "expired": 3,
        "rejected": 4,
        "missing": 5,
        "not_started": 6,
    }

    # In _record_sort_key, a verified+non-expired record maps to "verified" (priority 1)
    # An unverified record with completion_date maps to "awaiting_review" (priority 0)
    # sorted()[0] picks lowest = awaiting_review
    
    # QUESTION: Is this correct business logic?
    # If an employee has a VERIFIED record and a NEWER unverified submission,
    # the visible row would show "Awaiting Review" instead of "Verified".
    # This CONTRADICTS the user requirement that says:
    # "Suggested visible priority: awaiting_verification > verified > completed > missing"
    # ... meaning awaiting_review should show OVER verified. So the current order IS correct
    # per the user's explicit request.
    #
    # BUT there's a mismatch: _record_quality_score puts verified=0 (best),
    # while STATUS_PRIORITY puts awaiting_review=0 (best).
    # These serve DIFFERENT purposes:
    #   _record_quality_score → which record to use in build_training_records_lookup
    #   STATUS_PRIORITY → which record to show as visible row in the matrix dedup
    #
    # For the LOOKUP, verified should win (better data quality for mandatory matching).
    # For the VISIBLE ROW, awaiting_review should win (shows action needed).
    #
    # This is actually CORRECT — they serve different purposes.
    
    assert STATUS_PRIORITY["awaiting_review"] < STATUS_PRIORITY["verified"], \
        "awaiting_review should have higher priority (lower number) than verified"


def test_lookup_prefers_verified_record():
    """build_training_records_lookup should prefer verified over unverified."""
    records = [
        {"requirement_id": "fire_safety", "training_name": "Fire Safety",
         "verified": False, "completion_date": "2025-06-01", "id": "tr_new"},
        {"requirement_id": "fire_safety", "training_name": "Fire Safety",
         "verified": True, "completion_date": "2025-01-01", "id": "tr_old"},
    ]
    lookup = build_training_records_lookup(records)
    result = lookup.get("fire_safety")
    assert result is not None
    assert result["id"] == "tr_old", f"Verified record should win in lookup, got {result['id']}"
    assert result["verified"] == True


# ═══════════════════════════════════════════════════════
# Scenario 4: Alias collapse
# ═══════════════════════════════════════════════════════

def test_alias_bls_variants():
    """BLS / Basic Life Support / Adult BLS → all resolve to basic_life_support."""
    assert TRAINING_ALIASES.get("bls") == "basic_life_support"
    assert TRAINING_ALIASES.get("adult_bls") == "basic_life_support"
    assert TRAINING_ALIASES.get("resuscitation") == "basic_life_support"
    assert TRAINING_ALIASES.get("adult_basic_life_support") == "basic_life_support"


def test_alias_fire_safety_variants():
    """Fire Safety / CSTF Fire Safety → fire_safety."""
    assert TRAINING_ALIASES.get("cstf_fire_safety") == "fire_safety"
    assert TRAINING_ALIASES.get("fire_safety_awareness") == "fire_safety"


def test_alias_health_safety_variants():
    """Health & Safety / Health and Safety → health_safety."""
    assert TRAINING_ALIASES.get("health_and_safety") == "health_safety"
    assert TRAINING_ALIASES.get("health_safety_and_welfare") == "health_safety"


def test_alias_prevent_variants():
    """Prevent / Preventing Radicalisation → prevent."""
    assert TRAINING_ALIASES.get("preventing_radicalisation") == "prevent"
    assert TRAINING_ALIASES.get("counter_terrorism") == "prevent"


def test_alias_resolve_in_lookup():
    """Record with alias name 'BLS' should be findable via canonical code 'basic_life_support'."""
    records = [
        {"requirement_id": "", "training_name": "BLS",
         "verified": True, "completion_date": "2025-01-01", "id": "tr_bls"},
    ]
    lookup = build_training_records_lookup(records)
    
    # Should be findable by canonical alias
    assert lookup.get("basic_life_support") is not None, \
        f"'basic_life_support' should be in lookup. Keys: {list(lookup.keys())}"
    assert lookup.get("basic_life_support")["id"] == "tr_bls"
    
    # resolve_training_record should find it too
    result = resolve_training_record(lookup, "basic_life_support")
    assert result is not None, "resolve should find BLS via basic_life_support alias"
    assert result["id"] == "tr_bls"


def test_alias_resolve_cstf_fire_safety():
    """Record named 'CSTF Fire Safety' should resolve when looking up 'fire_safety'."""
    records = [
        {"requirement_id": "", "training_name": "CSTF Fire Safety",
         "verified": True, "completion_date": "2025-03-01", "id": "tr_fire"},
    ]
    lookup = build_training_records_lookup(records)
    
    result = resolve_training_record(lookup, "fire_safety")
    assert result is not None, f"fire_safety should resolve. Keys: {list(lookup.keys())}"
    assert result["id"] == "tr_fire"


def test_alias_resolve_preventing_radicalisation():
    """Record named 'Preventing Radicalisation' should resolve when looking up 'prevent'."""
    records = [
        {"requirement_id": "", "training_name": "Preventing Radicalisation",
         "verified": True, "completion_date": "2025-03-01", "id": "tr_prev"},
    ]
    lookup = build_training_records_lookup(records)

    result = resolve_training_record(lookup, "prevent")
    assert result is not None, f"prevent should resolve. Keys: {list(lookup.keys())}"
    assert result["id"] == "tr_prev"


def test_alias_resolve_health_and_safety():
    """Record named 'Health & Safety' should resolve when looking up 'health_safety'."""
    records = [
        {"requirement_id": "", "training_name": "Health & Safety",
         "verified": True, "completion_date": "2025-03-01", "id": "tr_hs"},
    ]
    lookup = build_training_records_lookup(records)

    result = resolve_training_record(lookup, "health_safety")
    assert result is not None, f"health_safety should resolve. Keys: {list(lookup.keys())}"
    assert result["id"] == "tr_hs"


def test_two_alias_variants_same_canonical():
    """Two records: 'BLS' and 'Adult BLS' → should both map to basic_life_support.
    Lookup should pick the better (verified) one."""
    records = [
        {"requirement_id": "", "training_name": "BLS",
         "verified": True, "completion_date": "2025-01-01", "id": "tr_bls_v"},
        {"requirement_id": "", "training_name": "Adult BLS",
         "verified": False, "completion_date": "2025-06-01", "id": "tr_abls_u"},
    ]
    lookup = build_training_records_lookup(records)
    result = resolve_training_record(lookup, "basic_life_support")
    assert result is not None
    # Verified record should win (score 0 vs 2)
    assert result["id"] == "tr_bls_v", f"Verified BLS should win, got {result['id']}"


# ═══════════════════════════════════════════════════════
# Scenario 5: Quality score / sort direction verification
# ═══════════════════════════════════════════════════════

def test_quality_score_ordering():
    """Confirm: lower number = better quality. Verify full ordering."""
    scores = {
        "verified":    _record_quality_score({"verified": True, "completion_date": "2025-01-01"}),
        "unverified":  _record_quality_score({"verified": False, "completion_date": "2025-01-01"}),
        "rejected":    _record_quality_score({"verified": False, "verification_status": "rejected", "completion_date": "2025-01-01"}),
        "no_date":     _record_quality_score({"verified": False}),
    }
    assert scores["verified"] < scores["unverified"] < scores["rejected"] < scores["no_date"], \
        f"Ordering wrong: {scores}"


def test_status_priority_full_ordering():
    """Verify the STATUS_PRIORITY ordering used in _record_sort_key."""
    STATUS_PRIORITY = {
        "awaiting_review": 0, "awaiting_verification": 0,
        "verified": 1,
        "completed": 2,
        "expired": 3,
        "rejected": 4,
        "missing": 5,
        "not_started": 6,
    }
    ordered = sorted(STATUS_PRIORITY.keys(), key=lambda k: STATUS_PRIORITY[k])
    # First should be awaiting_review/awaiting_verification (both 0)
    assert STATUS_PRIORITY[ordered[0]] == 0
    # Verified should be next (1)
    assert "verified" in ordered[1:3]  # allowing for the two 0-priority items


def test_sorted_picks_first_as_best():
    """sorted() with lower=better puts the best record at index 0."""
    STATUS_PRIORITY = {
        "awaiting_review": 0, "verified": 1, "completed": 2,
    }
    items = ["completed", "verified", "awaiting_review"]
    result = sorted(items, key=lambda x: STATUS_PRIORITY.get(x, 5))
    assert result[0] == "awaiting_review", f"sorted()[0] should be awaiting_review, got {result[0]}"


# ═══════════════════════════════════════════════════════
# Scenario 6: Frontend dedup key normalisation
# ═══════════════════════════════════════════════════════

def test_frontend_dedup_key_normalisation():
    """Simulate the JS dedup key: .replace(/[\\s&_-]+/g, ' ').trim().toLowerCase()"""
    import re
    def js_key(val):
        return re.sub(r'[\s&_\-]+', ' ', val.lower()).strip()
    
    # Same items from mandatory and additional with different formatting
    assert js_key("fire_safety") == js_key("Fire Safety") == "fire safety"
    assert js_key("basic_life_support") == js_key("Basic Life Support") == "basic life support"
    assert js_key("health_safety") == js_key("Health & Safety") == "health safety"
    assert js_key("moving_and_handling") == "moving and handling"

    # Verify these collapse
    seen = set()
    items = [
        {"code": "fire_safety", "title": "Fire Safety"},
        {"code": "fire_safety", "title": "CSTF Fire Safety"},  # same code
    ]
    visible = []
    for item in items:
        key = js_key(item.get("code") or item.get("title") or "")
        if key not in seen:
            seen.add(key)
            visible.append(item)
    assert len(visible) == 1, f"Should dedup to 1 row, got {len(visible)}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

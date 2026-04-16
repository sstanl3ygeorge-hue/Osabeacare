"""
Reference Slot Hardening Regression Tests

Validates that every reference endpoint enforcing a slot (ref_num / reference_id)
correctly rejects anything other than 1 or 2, and that legacy endpoints return 409.

Uses FastAPI TestClient with dependency overrides — no live DB required.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Patch db at module-level BEFORE importing server so the module body
# (which references `db` at import time) doesn't blow up.
# ---------------------------------------------------------------------------

_fake_db = MagicMock()

# Make all collection method calls return coroutines that resolve to None/[]
_collection_mock = MagicMock()
_collection_mock.find_one = AsyncMock(return_value={
    "id": "emp-test-001",
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "role": "admin",
})
_collection_mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
_collection_mock.find = MagicMock(return_value=MagicMock(to_list=AsyncMock(return_value=[])))
_collection_mock.update_many = AsyncMock()
_collection_mock.count_documents = AsyncMock(return_value=0)

# MagicMock doesn't allow setting __getattr__, so use spec-free approach:
# Any attribute access on _fake_db (e.g. _fake_db.employees) returns the mock collection
_fake_db._mock_children = {}
_fake_db.configure_mock(**{})
type(_fake_db).__getitem__ = lambda self, key: _collection_mock

# Intercept attribute access on the fake db to always return _collection_mock
_original_getattr = type(_fake_db).__getattr__


class _DbProxy:
    """Proxy that returns the same collection mock for any attribute."""
    def __getattr__(self, name):
        return _collection_mock
    def __getitem__(self, name):
        return _collection_mock


_fake_db = _DbProxy()

# Patch the module-level db in both server and dependencies
with patch.dict("os.environ", {
    "MONGO_URL": "mongodb://localhost:27017",
    "DB_NAME": "test_db",
    "JWT_SECRET": "test-secret",
    "RESEND_API_KEY": "",
}):
    import sys, types

    # Patch routes.dependencies db before import
    from routes import dependencies as _deps
    _deps.db = _fake_db
    _deps.set_database(_fake_db)

    # Now import server — it will use the patched db
    import server as _server_module
    _server_module.db = _fake_db

    from server import app

    # Override auth dependencies from BOTH sources:
    # 1) routes.dependencies (used by routes/references.py)
    from routes.dependencies import (
        get_current_user as routes_get_current_user,
        require_admin as routes_require_admin,
        require_manager_or_admin as routes_require_manager_or_admin,
    )
    # 2) server.py local definitions (used by inline server.py routes)
    from server import (
        get_current_user as server_get_current_user,
        require_admin as server_require_admin,
        require_manager_or_admin as server_require_manager_or_admin,
    )

    _fake_admin_user = {
        "user_id": "admin-test-001",
        "email": "admin@test.com",
        "role": "admin",
        "name": "Test Admin",
    }

    app.dependency_overrides[routes_get_current_user] = lambda: _fake_admin_user
    app.dependency_overrides[routes_require_admin] = lambda: _fake_admin_user
    app.dependency_overrides[routes_require_manager_or_admin] = lambda: _fake_admin_user
    app.dependency_overrides[server_get_current_user] = lambda: _fake_admin_user
    app.dependency_overrides[server_require_admin] = lambda: _fake_admin_user
    app.dependency_overrides[server_require_manager_or_admin] = lambda: _fake_admin_user


client = TestClient(app, raise_server_exceptions=False)

EMPLOYEE_ID = "emp-test-001"
VALID_REF_BODY = {
    "referee_name": "Jane Doe",
    "referee_email": "jane@example.com",
    "referee_phone": "01onal",
    "referee_organisation": "Acme Ltd",
    "referee_position": "Manager",
    "referee_relationship": "Line manager",
    "edit_reason": "Initial entry for testing",
}


# =====================================================================
# 1. PUT /api/employees/{eid}/references/{reference_id}  — slot guard
# =====================================================================

class TestPutUpdateReferenceSlotGuard:
    """PUT update_reference in server.py must only accept reference_id '1' or '2'."""

    def test_put_reference_1_accepted(self):
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/1",
            json=VALID_REF_BODY,
        )
        # Should NOT be 400; may be 200 or any non-400
        assert resp.status_code != 400, f"Slot 1 was wrongly rejected: {resp.text}"

    def test_put_reference_2_accepted(self):
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/2",
            json=VALID_REF_BODY,
        )
        assert resp.status_code != 400, f"Slot 2 was wrongly rejected: {resp.text}"

    def test_put_reference_foo_rejected(self):
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/foo",
            json=VALID_REF_BODY,
        )
        assert resp.status_code == 400
        assert "1" in resp.json()["detail"] and "2" in resp.json()["detail"]

    def test_put_reference_0_rejected(self):
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/0",
            json=VALID_REF_BODY,
        )
        assert resp.status_code == 400

    def test_put_reference_3_rejected(self):
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/3",
            json=VALID_REF_BODY,
        )
        assert resp.status_code == 400

    def test_put_reference_99_rejected(self):
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/99",
            json=VALID_REF_BODY,
        )
        assert resp.status_code == 400

    def test_put_reference_negative_rejected(self):
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/-1",
            json=VALID_REF_BODY,
        )
        assert resp.status_code == 400

    def test_put_reference_sqli_rejected(self):
        """Confirm SQL-injection-style payloads are blocked."""
        resp = client.put(
            f"/api/employees/{EMPLOYEE_ID}/references/1%20OR%201=1",
            json=VALID_REF_BODY,
        )
        assert resp.status_code == 400


# =====================================================================
# 2. POST override-mismatch  — slot guard
# =====================================================================

class TestOverrideMismatchSlotGuard:
    """POST /api/references/{eid}/{ref_num}/override-mismatch must enforce 1 or 2."""

    def test_override_mismatch_ref1_accepted(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/1/override-mismatch",
            json={"override_reason": "This is a detailed override reason exceeding twenty chars"},
        )
        assert resp.status_code != 400, f"Slot 1 was wrongly rejected: {resp.text}"

    def test_override_mismatch_ref2_accepted(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/2/override-mismatch",
            json={"override_reason": "This is a detailed override reason exceeding twenty chars"},
        )
        assert resp.status_code != 400, f"Slot 2 was wrongly rejected: {resp.text}"

    def test_override_mismatch_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/override-mismatch",
            json={"override_reason": "This is a detailed override reason exceeding twenty chars"},
        )
        assert resp.status_code == 400
        assert "1" in resp.json()["detail"] or "2" in resp.json()["detail"]

    def test_override_mismatch_ref0_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/0/override-mismatch",
            json={"override_reason": "twenty char reason is exactly here okay"},
        )
        assert resp.status_code == 400


# =====================================================================
# 3. POST reject  — slot guard
# =====================================================================

class TestRejectReferenceSlotGuard:
    """POST /api/references/{eid}/{ref_num}/reject must enforce 1 or 2."""

    def test_reject_ref1_accepted(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/1/reject",
            json={"rejection_reason": "Referee unresponsive after 3 attempts"},
        )
        assert resp.status_code != 400, f"Slot 1 was wrongly rejected: {resp.text}"

    def test_reject_ref2_accepted(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/2/reject",
            json={"rejection_reason": "Referee unresponsive after 3 attempts"},
        )
        assert resp.status_code != 400, f"Slot 2 was wrongly rejected: {resp.text}"

    def test_reject_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/reject",
            json={"rejection_reason": "Referee unresponsive after 3 attempts"},
        )
        assert resp.status_code == 400

    def test_reject_ref_negative_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/-5/reject",
            json={"rejection_reason": "Negative slot test"},
        )
        assert resp.status_code == 400


# =====================================================================
# 4. Legacy routes/references.py create/update/verify → 409
# =====================================================================

class TestLegacyReferenceEndpointsReturn409:
    """Legacy create/update/verify endpoints in routes/references.py must return 409."""

    def test_legacy_create_returns_409(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/1/create",
            json={
                "referee_name": "John",
                "referee_email": "john@example.com",
                "is_professional": True,
            },
        )
        assert resp.status_code == 409, f"Expected 409 got {resp.status_code}: {resp.text}"
        detail = resp.json()["detail"]
        assert "disabled" in detail.lower()
        assert "/employees/" in detail, "Should redirect to canonical endpoint"

    def test_legacy_update_returns_409(self):
        resp = client.put(
            f"/api/references/{EMPLOYEE_ID}/1/update",
            json={"referee_name": "Updated Name"},
        )
        assert resp.status_code == 409, f"Expected 409 got {resp.status_code}: {resp.text}"
        detail = resp.json()["detail"]
        assert "disabled" in detail.lower()
        assert "change-referee" in detail, "Should redirect to change-referee endpoint"

    def test_legacy_verify_returns_409(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/1/verify",
            json={"notes": "Test verify"},
        )
        assert resp.status_code == 409, f"Expected 409 got {resp.status_code}: {resp.text}"
        detail = resp.json()["detail"]
        assert "disabled" in detail.lower()

    def test_legacy_create_slot2_also_409(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/2/create",
            json={
                "referee_name": "Jane",
                "referee_email": "jane@example.com",
                "is_professional": True,
            },
        )
        assert resp.status_code == 409

    def test_legacy_update_slot2_also_409(self):
        resp = client.put(
            f"/api/references/{EMPLOYEE_ID}/2/update",
            json={"referee_name": "Updated Name"},
        )
        assert resp.status_code == 409


# =====================================================================
# 5. Additional slot-guarded endpoints spot checks
# =====================================================================

class TestAdditionalSlotGuards:
    """Spot-check other endpoints that take ref_num."""

    def test_reset_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/reset",
            json={"reset_reason": "This is a test reset reason over ten chars"},
        )
        assert resp.status_code == 400

    def test_request_replacement_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/request-replacement",
            json={"replacement_reason": "Unresponsive referee after 3 attempts"},
        )
        assert resp.status_code == 400

    def test_change_referee_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/change-referee",
            json={
                "new_name": "New Ref",
                "new_email": "new@example.com",
                "change_reason": "Referee left employment and is unreachable",
            },
        )
        assert resp.status_code == 400

    def test_set_response_source_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/set-response-source",
            json={"source": "external_submission"},
        )
        assert resp.status_code == 400

    def test_record_alternative_path_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/record-alternative-path",
            json={
                "original_referee_attempts": [{"date": "2026-01-01", "method": "email"}],
                "alternative_reason": "Referee unresponsive after multiple documented attempts spanning several weeks",
                "alternative_source": "HR department of previous employer",
            },
        )
        assert resp.status_code == 400

    def test_review_mismatch_explanation_ref99_rejected(self):
        resp = client.post(
            f"/api/references/{EMPLOYEE_ID}/99/review-mismatch-explanation",
            json={"decision": "accepted", "admin_notes": "Explanation acceptable"},
        )
        assert resp.status_code == 400

    def test_integrity_ref99_rejected(self):
        resp = client.get(f"/api/references/{EMPLOYEE_ID}/99/integrity")
        assert resp.status_code == 400

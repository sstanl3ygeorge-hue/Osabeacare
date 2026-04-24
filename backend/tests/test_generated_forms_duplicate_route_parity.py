import os
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.forms as forms
import routes.generated_forms as generated_forms


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._limit = None

    def sort(self, field, direction):
        reverse = direction == -1
        self._docs.sort(key=lambda item: item.get(field, ""), reverse=reverse)
        return self

    def limit(self, value):
        self._limit = value
        return self

    async def to_list(self, length):
        effective_limit = self._limit if self._limit is not None else length
        if effective_limit is None:
            return list(self._docs)
        return list(self._docs[:effective_limit])


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    @staticmethod
    def _matches(doc, query):
        for key, expected in (query or {}).items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, query=None, projection=None):
        for doc in self.docs:
            if self._matches(doc, query or {}):
                return dict(doc)
        return None

    def find(self, query=None, projection=None):
        filtered = [dict(doc) for doc in self.docs if self._matches(doc, query or {})]
        return _FakeCursor(filtered)

    async def insert_one(self, document):
        self.docs.append(dict(document))
        return SimpleNamespace(inserted_id=document.get("id"))

    async def update_one(self, query, update):
        for index, doc in enumerate(self.docs):
            if self._matches(doc, query or {}):
                new_doc = dict(doc)
                if "$set" in update:
                    new_doc.update(update["$set"])
                if "$unset" in update:
                    for field in update["$unset"].keys():
                        new_doc.pop(field, None)
                self.docs[index] = new_doc
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


class _FakeDb:
    def __init__(self):
        self.generated_forms = _FakeCollection([])
        self.templates = _FakeCollection([])
        self.employees = _FakeCollection([])
        self.employee_documents = _FakeCollection([])
        self.document_types = _FakeCollection([])


def _expected_duplicate_paths():
    return {
        ("POST", "/generated-forms"),
        ("GET", "/generated-forms"),
        ("GET", "/generated-forms/{form_id}"),
        ("PUT", "/generated-forms/{form_id}"),
        ("POST", "/generated-forms/{form_id}/signoff"),
        ("POST", "/generated-forms/{form_id}/archive"),
    }


def _extract_duplicate_paths():
    generated_routes = set()
    forms_routes = set()

    for route in generated_forms.router.routes:
        for method in sorted(getattr(route, "methods", set())):
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                generated_routes.add((method, route.path))

    for route in forms.router.routes:
        for method in sorted(getattr(route, "methods", set())):
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                forms_routes.add((method, route.path))

    return generated_routes & forms_routes


async def _fake_audit(*args, **kwargs):
    return None


async def _fake_auto_fill(employee_id):
    return {"auto_field": f"auto-for-{employee_id}"}


async def _fake_auto_generate_form_pdf(form_id, user):
    return None


def _make_form_doc(form_id="form-1", access_token="token-1", *, locked=False, status="draft"):
    return {
        "id": form_id,
        "template_id": "tmpl-1",
        "template_name": "Risk Assessment",
        "template_category": "care",
        "employee_id": "emp-1",
        "employee_name": "A Worker",
        "employee_code": "E001",
        "form_data": {"existing": "value"},
        "status": status,
        "employee_signature": None,
        "employee_signed_at": None,
        "admin_signature": None,
        "admin_signed_at": None,
        "admin_signoff_by": None,
        "pdf_url": None,
        "locked": locked,
        "notes": None,
        "version": 1,
        "access_token": access_token,
        "created_at": "2026-04-24T10:00:00+00:00",
        "updated_at": "2026-04-24T10:00:00+00:00",
        "sent_at": None,
        "viewed_at": None,
        "completed_at": None,
        "reviewed_at": None,
        "signed_off_at": None,
    }


def _seed_common_records(db, *, template_active=True):
    db.templates.docs.append(
        {
            "id": "tmpl-1",
            "name": "Risk Assessment",
            "category": "care",
            "active": template_active,
        }
    )
    db.employees.docs.append(
        {
            "id": "emp-1",
            "first_name": "A",
            "last_name": "Worker",
            "employee_code": "E001",
            "email": "worker@example.com",
        }
    )


def _build_client(monkeypatch, *, include_generated_forms, include_forms, template_active=True):
    fake_db = _FakeDb()
    _seed_common_records(fake_db, template_active=template_active)

    monkeypatch.setattr(generated_forms, "get_db", lambda: fake_db)
    monkeypatch.setattr(forms, "get_db", lambda: fake_db)
    monkeypatch.setattr(generated_forms, "log_audit_action", _fake_audit)
    monkeypatch.setattr(forms, "log_audit_action", _fake_audit)
    monkeypatch.setattr(generated_forms, "get_auto_fill_employee_data", lambda: _fake_auto_fill)
    monkeypatch.setattr(generated_forms, "get_auto_generate_form_pdf", lambda: _fake_auto_generate_form_pdf)
    monkeypatch.setattr(forms, "auto_fill_employee_data", _fake_auto_fill)
    monkeypatch.setattr(generated_forms, "get_document_status", lambda: SimpleNamespace(APPROVED="approved"))

    app = FastAPI()
    if include_generated_forms:
        app.include_router(generated_forms.router, prefix="/api")
    if include_forms:
        app.include_router(forms.router, prefix="/api")

    admin_user = {"user_id": "admin-1", "role": "admin", "name": "Admin User"}
    manager_user = {"user_id": "manager-1", "role": "admin", "name": "Manager User"}

    app.dependency_overrides[generated_forms.get_current_user] = lambda: admin_user
    app.dependency_overrides[generated_forms.require_admin] = lambda: admin_user
    app.dependency_overrides[generated_forms.require_manager_or_admin] = lambda: manager_user
    app.dependency_overrides[forms.get_current_user] = lambda: admin_user
    app.dependency_overrides[forms.require_admin] = lambda: admin_user
    app.dependency_overrides[forms.require_manager_or_admin] = lambda: manager_user

    return TestClient(app), fake_db


def test_generated_form_duplicate_paths_are_confirmed():
    assert _extract_duplicate_paths() == _expected_duplicate_paths()


def test_effective_owner_create_matches_canonical_and_shadows_legacy(monkeypatch):
    payload = {"template_id": "tmpl-1", "employee_id": "emp-1", "form_data": {"custom": "value"}}

    effective_client, _ = _build_client(
        monkeypatch,
        include_generated_forms=True,
        include_forms=True,
        template_active=False,
    )
    effective_response = effective_client.post("/api/generated-forms", json=payload)
    canonical_client, _ = _build_client(
        monkeypatch,
        include_generated_forms=True,
        include_forms=False,
        template_active=False,
    )
    canonical_response = canonical_client.post("/api/generated-forms", json=payload)
    legacy_client, _ = _build_client(
        monkeypatch,
        include_generated_forms=False,
        include_forms=True,
        template_active=False,
    )
    legacy_response = legacy_client.post("/api/generated-forms", json=payload)

    assert effective_response.status_code == 200
    assert canonical_response.status_code == 200
    assert legacy_response.status_code == 404

    effective_json = effective_response.json()
    canonical_json = canonical_response.json()

    assert effective_json["template_name"] == canonical_json["template_name"] == "Risk Assessment"
    assert effective_json["status"] == canonical_json["status"] == "draft"
    assert effective_json["form_data"]["custom"] == "value"
    assert effective_json["form_data"]["auto_field"] == "auto-for-emp-1"
    assert effective_json["employee_code"] == canonical_json["employee_code"] == "E001"


def test_effective_owner_list_get_and_update_match_canonical(monkeypatch):
    effective_client, effective_db = _build_client(monkeypatch, include_generated_forms=True, include_forms=True)
    effective_db.generated_forms.docs.append(_make_form_doc())

    effective_list = effective_client.get("/api/generated-forms")
    canonical_client, canonical_db = _build_client(monkeypatch, include_generated_forms=True, include_forms=False)
    canonical_db.generated_forms.docs.append(_make_form_doc())
    canonical_list = canonical_client.get("/api/generated-forms")
    assert effective_list.status_code == canonical_list.status_code == 200
    assert effective_list.json() == canonical_list.json()

    effective_get = effective_client.get("/api/generated-forms/form-1")
    canonical_get = canonical_client.get("/api/generated-forms/form-1")
    assert effective_get.status_code == canonical_get.status_code == 200
    assert effective_get.json() == canonical_get.json()

    update_payload = {"form_data": {"existing": "updated", "new_field": "added"}, "notes": "Updated notes"}
    effective_update = effective_client.put("/api/generated-forms/form-1", json=update_payload)
    canonical_update = canonical_client.put("/api/generated-forms/form-1", json=update_payload)

    assert effective_update.status_code == canonical_update.status_code == 200
    assert effective_update.json()["form_data"] == canonical_update.json()["form_data"]
    assert effective_update.json()["notes"] == canonical_update.json()["notes"] == "Updated notes"


def test_effective_owner_signoff_locks_form_and_blocks_update(monkeypatch):
    effective_client, effective_db = _build_client(monkeypatch, include_generated_forms=True, include_forms=True)
    effective_db.generated_forms.docs.append(_make_form_doc())

    effective_signoff = effective_client.post(
        "/api/generated-forms/form-1/signoff",
        params={"admin_signature": "admin-signature", "notes": "Approved"},
    )
    canonical_client, canonical_db = _build_client(monkeypatch, include_generated_forms=True, include_forms=False)
    canonical_db.generated_forms.docs.append(_make_form_doc())
    canonical_signoff = canonical_client.post(
        "/api/generated-forms/form-1/signoff",
        params={"admin_signature": "admin-signature", "notes": "Approved"},
    )

    assert effective_signoff.status_code == canonical_signoff.status_code == 200
    assert effective_signoff.json()["status"] == canonical_signoff.json()["status"] == "signed_off"
    assert effective_signoff.json()["locked"] is True
    assert effective_signoff.json()["notes"] == "Approved"

    blocked_update = effective_client.put("/api/generated-forms/form-1", json={"notes": "Should fail"})
    assert blocked_update.status_code == 403
    assert "locked" in blocked_update.json()["detail"].lower()

    second_signoff = effective_client.post(
        "/api/generated-forms/form-1/signoff",
        params={"admin_signature": "admin-signature"},
    )
    assert second_signoff.status_code == 403


def test_effective_owner_archive_matches_canonical_shape(monkeypatch):
    effective_client, effective_db = _build_client(monkeypatch, include_generated_forms=True, include_forms=True)
    effective_db.generated_forms.docs.append(_make_form_doc())

    effective_archive = effective_client.post("/api/generated-forms/form-1/archive")
    canonical_client, canonical_db = _build_client(monkeypatch, include_generated_forms=True, include_forms=False)
    canonical_db.generated_forms.docs.append(_make_form_doc())
    canonical_archive = canonical_client.post("/api/generated-forms/form-1/archive")

    assert effective_archive.status_code == canonical_archive.status_code == 200
    assert effective_archive.json() == canonical_archive.json() == {"message": "Form archived"}
    assert effective_db.generated_forms.docs[0]["status"] == "archived"


def test_public_token_access_and_submit_flow(monkeypatch):
    client, db = _build_client(monkeypatch, include_generated_forms=True, include_forms=True)
    db.generated_forms.docs.append(_make_form_doc(access_token="token-public"))

    access_response = client.get("/api/forms/access/token-public")
    assert access_response.status_code == 200
    access_payload = access_response.json()
    assert access_payload["form"]["id"] == "form-1"
    assert access_payload["template"]["id"] == "tmpl-1"
    assert db.generated_forms.docs[0]["viewed_at"] is not None

    submit_response = client.put(
        "/api/forms/access/token-public/submit",
        json={"form_data": {"worker_note": "done"}, "employee_signature": "worker-signature"},
    )
    assert submit_response.status_code == 200
    assert submit_response.json() == {"message": "Form submitted successfully"}

    updated = db.generated_forms.docs[0]
    assert updated["status"] == "completed"
    assert updated["employee_signature"] == "worker-signature"
    assert updated["form_data"]["worker_note"] == "done"

    updated["locked"] = True
    locked_response = client.get("/api/forms/access/token-public")
    assert locked_response.status_code == 403
    assert "locked" in locked_response.json()["detail"].lower()
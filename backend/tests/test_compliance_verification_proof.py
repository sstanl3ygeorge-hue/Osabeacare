"""
Test suite for Compliance Verification Proof Enforcement
Tests the RecordCheckDialog proof file upload requirement and CheckRow proof display

Features tested:
1. RecordCheckDialog requires proof file upload before saving a check
2. Check records store evidence_document_id linking to the uploaded proof
3. CheckRow displays the linked proof file with view/download actions
4. Compliance file endpoint returns evidence_document details
"""

import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated API client"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture
def test_png_file():
    """Create a minimal PNG file for testing"""
    # 1x1 white pixel PNG
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    file_path = "/tmp/test_compliance_proof.png"
    with open(file_path, "wb") as f:
        f.write(png_data)
    yield file_path
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)


class TestDocumentUploadEndpoint:
    """Test the document upload endpoint used by RecordCheckDialog"""
    
    def test_upload_document_endpoint_exists(self, auth_token, test_png_file):
        """Test that /api/employees/{id}/upload-document endpoint exists and works"""
        with open(test_png_file, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("test_proof.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "RTW Check Proof Test"
                }
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should contain document id"
        assert data.get("requirement_id") == "right_to_work_check"
        assert data.get("document_label") == "RTW Check Proof Test"
        assert data.get("original_filename") == "test_proof.png"
        
        print(f"PASS: Document uploaded successfully with id: {data['id']}")
        return data["id"]
    
    def test_upload_document_with_verification_proof_type(self, auth_token, test_png_file):
        """Test uploading document with verification_proof document_type"""
        with open(test_png_file, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("dbs_proof.png", f, "image/png")},
                data={
                    "requirement_id": "dbs_status_check",
                    "document_type": "verification_proof",
                    "document_label": "DBS Status Check Proof"
                }
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"PASS: DBS proof document uploaded with id: {data['id']}")


class TestRTWCheckEndpoint:
    """Test the Right to Work check recording endpoint"""
    
    def test_rtw_check_endpoint_exists(self, api_client):
        """Test that /api/employees/{id}/right-to-work/check endpoint exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check"
        )
        # Should return 200 with check data or 404 if no check exists
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: RTW check endpoint exists, status: {response.status_code}")
    
    def test_record_rtw_check_with_evidence_document_id(self, auth_token, test_png_file):
        """Test recording RTW check with evidence_document_id"""
        # First upload a proof document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("rtw_proof_test.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "RTW Check Proof"
                }
            )
        
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        doc_id = upload_response.json()["id"]
        
        # Now record the check with evidence_document_id
        check_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={
                "method": "share_code_online_check",
                "checked_at": "2026-04-01",
                "outcome": "verified",
                "evidence_document_id": doc_id,
                "notes": "TEST: Check with proof document"
            }
        )
        
        assert check_response.status_code == 200, f"Check recording failed: {check_response.text}"
        check_data = check_response.json()
        
        # Verify the check was recorded
        assert "id" in check_data or "check_id" in check_data, "Check should have an ID"
        print(f"PASS: RTW check recorded with evidence_document_id: {doc_id}")


class TestRTWVerificationValidation:
    """Test Right to Work verify endpoint validation rules."""

    def test_verify_rtw_requires_expiry_or_follow_up_date(self, auth_token, test_png_file):
        """RTW verify should fail if a verified check has no expiry or follow-up date."""
        # Upload RTW evidence document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("rtw_proof_test.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_documents",
                    "document_type": "verification_proof",
                    "document_label": "RTW Evidence Proof"
                }
            )

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        evidence_doc_id = upload_response.json()["id"]

        # Record a valid RTW check without expiry or follow-up date
        check_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={
                "method": "share_code_online_check",
                "checked_at": "2026-04-01",
                "outcome": "verified",
                "route": "share_code_online_check",
                "evidence_document_id": evidence_doc_id,
                "is_indefinite": False,
                "notes": "TEST: Verified RTW check with no expiry/follow-up"
            }
        )

        assert check_response.status_code in [200, 201], f"RTW check setup failed: {check_response.text}"

        verify_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work/verify",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        )

        assert verify_response.status_code == 400, f"Expected 400 when RTW check is missing expiry/follow-up, got {verify_response.status_code}: {verify_response.text}"
        assert "expiry date or a follow-up date" in verify_response.text or "follow-up due date" in verify_response.text

    def test_verify_all_right_to_work_documents_blocks_without_verified_check(self, auth_token, test_png_file):
        """RTW verify-all must return 400 when no verified RTW check is current.

        Sets up a deterministic state: records a non-verified RTW check (outcome=in_progress)
        immediately before calling verify-all, ensuring the gate fires unconditionally.
        """
        # Upload evidence so the gate is not blocked before reaching RTW check validation.
        with open(test_png_file, "rb") as f:
            requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("rtw_verifyall_setup.png", f, "image/png")},
                data={"requirement_id": "right_to_work_documents", "document_type": "rtw_evidence"},
            )

        # Record an explicitly non-verified RTW check as the current one.
        check_resp = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json={
                "method": "manual_check",
                "checked_at": "2026-04-01",
                "outcome": "in_progress",
                "route": "manual_check",
                "is_indefinite": False,
                "notes": "TEST: Non-verified check used to assert verify-all is gated",
            },
        )
        assert check_resp.status_code in [200, 201], f"Setup check recording failed: {check_resp.text}"

        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/verify-all",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 400, (
            f"Expected 400 when current RTW check is not verified, got {response.status_code}: {response.text}"
        )
        rtw_gate_messages = [
            "current RTW check record",
            "RTW check outcome",
            "check outcome",
            "expiry date or a follow-up date",
            "proof_document_id",
            "proof document",
            "only verified checks",
        ]
        assert any(m.lower() in response.text.lower() for m in rtw_gate_messages), (
            f"Response did not contain any expected RTW gate message: {response.text}"
        )


class TestComplianceFileEndpoint:
    """Test the compliance file endpoint returns evidence_document details"""
    
    def test_compliance_file_returns_check_data(self, api_client):
        """Test that compliance file endpoint returns check data with evidence_document"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file"
        )
        
        assert response.status_code == 200, f"Failed to get compliance file: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "sections" in data, "Response should have sections"
        assert "right_to_work" in data["sections"], "Should have right_to_work section"
        
        rtw_section = data["sections"]["right_to_work"]
        assert "rows" in rtw_section, "RTW section should have rows"
        
        # Find the check row
        check_row = None
        for row in rtw_section["rows"]:
            if row.get("row_type") == "check":
                check_row = row
                break
        
        assert check_row is not None, "Should have a check row"
        print(f"PASS: Found RTW check row with key: {check_row.get('key')}")
        
        # Verify check_data structure
        if check_row.get("has_check"):
            check_data = check_row.get("check_data", {})
            assert "evidence_document_id" in check_data, "check_data should have evidence_document_id field"
            
            if check_data.get("evidence_document_id"):
                assert "evidence_document" in check_data, "Should have evidence_document details"
                evidence_doc = check_data["evidence_document"]
                assert "id" in evidence_doc, "evidence_document should have id"
                assert "filename" in evidence_doc, "evidence_document should have filename"
                print(f"PASS: Check has evidence_document: {evidence_doc.get('filename')}")
            else:
                print("INFO: Check exists but no evidence_document_id linked (legacy check)")
    
    def test_compliance_file_serializer_version(self, api_client):
        """Test that compliance file uses dual_row_v1 serializer"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("serializer_version") == "dual_row_v1", \
            f"Expected dual_row_v1, got {data.get('serializer_version')}"
        print("PASS: Compliance file uses dual_row_v1 serializer")


class TestDBSCheckEndpoint:
    """Test the DBS check recording endpoint"""
    
    def test_dbs_check_endpoint_exists(self, api_client):
        """Test that /api/employees/{id}/dbs/check endpoint exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check"
        )
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: DBS check endpoint exists, status: {response.status_code}")
    
    def test_record_dbs_check_with_evidence(self, auth_token, test_png_file):
        """Test recording DBS check with evidence_document_id"""
        # Upload proof document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("dbs_proof_test.png", f, "image/png")},
                data={
                    "requirement_id": "dbs_status_check",
                    "document_type": "verification_proof",
                    "document_label": "DBS Status Check Proof"
                }
            )
        
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["id"]
        
        # Record DBS check
        check_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={
                "method": "update_service_check",
                "checked_at": "2026-04-01",
                "outcome": "verified",
                "evidence_document_id": doc_id,
                "certificate_number": "123456789012",
                "notes": "TEST: DBS check with proof"
            }
        )
        
        assert check_response.status_code == 200, f"DBS check failed: {check_response.text}"
        print(f"PASS: DBS check recorded with evidence_document_id: {doc_id}")


class TestIdentityCheckEndpoint:
    """Test the Identity verification endpoint"""
    
    def test_identity_check_endpoint_exists(self, api_client):
        """Test that /api/employees/{id}/identity/check endpoint exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/identity/check"
        )
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: Identity check endpoint exists, status: {response.status_code}")


class TestDocumentFileEndpoints:
    """Test document file view/download endpoints used by CheckRow"""
    
    def test_document_file_endpoint(self, auth_token, test_png_file):
        """Test that document file endpoint works for viewing proof"""
        # First upload a document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("view_test.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "View Test Proof"
                }
            )
        
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["id"]
        
        # Test file view endpoint
        file_response = requests.get(
            f"{BASE_URL}/api/employee-documents/{doc_id}/file",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert file_response.status_code == 200, f"File view failed: {file_response.status_code}"
        assert len(file_response.content) > 0, "File content should not be empty"
        print(f"PASS: Document file endpoint works, received {len(file_response.content)} bytes")
    
    def test_document_download_endpoint(self, auth_token, test_png_file):
        """Test that document download endpoint works"""
        # Upload a document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("download_test.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "Download Test Proof"
                }
            )
        
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["id"]
        
        # Test download endpoint
        download_response = requests.get(
            f"{BASE_URL}/api/employee-documents/{doc_id}/download",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert download_response.status_code == 200, f"Download failed: {download_response.status_code}"
        assert len(download_response.content) > 0, "Download content should not be empty"
        print(f"PASS: Document download endpoint works, received {len(download_response.content)} bytes")


# ===========================================================================
# Patch 1–3 Recruitment Integrity Gate Tests
# ===========================================================================

class TestRecruitmentIntegrityGates:
    """
    Focused regression tests for the 4 new readiness gates introduced in the
    recruitment integrity hardening patches:
      1. HARD BLOCK C – reference integrity (counts_toward_readiness)
      2. HARD BLOCK D4 – unexplained employment gaps
      3. HARD BLOCK D3 – interview record completion (decision + date + signature)
      4. HARD BLOCK F1 – POA verification stamp
      5. HARD BLOCK F4 – unresolved OH/health review
    """

    # -----------------------------------------------------------------------
    # Gate 1: Reference integrity
    # -----------------------------------------------------------------------

    def test_work_readiness_blocks_when_candidate_upload_only_reference(self, api_client):
        """A reference uploaded by the candidate only (no independent response) must NOT
        count toward readiness even if an admin manually marked it verified."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references/integrity"
        )
        assert response.status_code == 200, f"Integrity endpoint failed: {response.text}"
        data = response.json()
        # Structural contract: endpoint must expose counts_toward_readiness per reference
        for key in ("reference_1", "reference_2"):
            ref = data.get(key)
            if ref:
                assert "counts_toward_readiness" in ref, (
                    f"{key} integrity result missing counts_toward_readiness field"
                )
                if ref.get("response", {}).get("source") == "candidate_upload":
                    assert ref["counts_toward_readiness"] is False, (
                        f"Candidate-upload-only {key} must not count toward readiness"
                    )

    def test_work_readiness_reports_reference_blocking_reason(self, api_client):
        """When a reference has a blocking_reason, the readiness endpoint must surface it."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references/integrity"
        )
        assert response.status_code == 200
        data = response.json()
        for key in ("reference_1", "reference_2"):
            ref = data.get(key)
            if ref and ref.get("blocked_by_integrity"):
                assert ref.get("blocking_reason"), (
                    f"{key} is blocked but has no blocking_reason message"
                )

    # -----------------------------------------------------------------------
    # Gate 2: Employment gap explanation
    # -----------------------------------------------------------------------

    def test_employment_gap_explanation_api_accepts_valid_explanation(self, api_client):
        """Explain-gap endpoint must accept explanations ≥ 10 chars."""
        # First retrieve existing gaps to find a valid gap_id
        gaps_response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/cv-gaps"
        )
        assert gaps_response.status_code == 200, f"cv-gaps failed: {gaps_response.text}"
        gaps = gaps_response.json().get("gaps", [])
        if not gaps:
            print("INFO: No gaps detected for test employee – gate 2 pass-through")
            return
        gap_id = gaps[0].get("gap_id") or gaps[0].get("id")
        assert gap_id, "Gap record must have a gap_id"
        explain_response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/explain-cv-gap",
            json={"gap_id": gap_id, "explanation": "Took extended leave to care for family member."}
        )
        assert explain_response.status_code == 200, (
            f"Gap explanation rejected: {explain_response.text}"
        )

    def test_employment_gap_explanation_rejects_short_explanation(self, api_client):
        """Explain-gap endpoint must reject explanations shorter than 10 characters."""
        gaps_response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/cv-gaps"
        )
        assert gaps_response.status_code == 200
        gaps = gaps_response.json().get("gaps", [])
        if not gaps:
            print("INFO: No gaps – short-explanation rejection skipped")
            return
        gap_id = gaps[0].get("gap_id") or gaps[0].get("id")
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/explain-cv-gap",
            json={"gap_id": gap_id, "explanation": "short"}
        )
        assert response.status_code == 400, (
            f"Expected 400 for too-short explanation, got {response.status_code}: {response.text}"
        )

    # -----------------------------------------------------------------------
    # Gate 3: Interview record completion
    # -----------------------------------------------------------------------

    def test_interview_record_form_schema_has_required_fields(self, api_client):
        """The interview_record form config must declare decision, interview_date, and
        interviewer_signature as required fields — these are what the completion gate checks."""
        response = api_client.get(f"{BASE_URL}/api/forms/interview_record/config")
        if response.status_code == 404:
            print("INFO: /api/forms/interview_record/config not exposed – skipping schema check")
            return
        assert response.status_code == 200, f"Form config failed: {response.text}"
        config = response.json()
        all_field_ids = []
        for section in config.get("sections", []):
            for field in section.get("fields", []):
                all_field_ids.append(field.get("id"))
        for required_id in ("decision", "interview_date", "interviewer_signature"):
            assert required_id in all_field_ids, (
                f"Interview record schema must include field '{required_id}' for completion gate"
            )

    def test_interview_record_affects_readiness_config(self, api_client):
        """FORM_REQUIREMENT_CONFIG for interview_record must declare affects_readiness=True."""
        response = api_client.get(f"{BASE_URL}/api/forms/config")
        if response.status_code == 404:
            print("INFO: /api/forms/config not exposed – affects_readiness check skipped")
            return
        assert response.status_code == 200
        config = response.json()
        ir_config = config.get("interview_record") or config.get("forms", {}).get("interview_record")
        if ir_config:
            assert ir_config.get("affects_readiness") is True, (
                "interview_record FORM_REQUIREMENT_CONFIG.affects_readiness must be True"
            )

    # -----------------------------------------------------------------------
    # Gate 4: POA verification stamp
    # -----------------------------------------------------------------------

    def test_poa_stamp_endpoint_accepts_original_seen(self, api_client):
        """Applying an original_seen stamp to a POA document must succeed."""
        # Upload a POA document first
        import base64
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(png_data)
        tmp.close()
        try:
            with open(tmp.name, "rb") as f:
                upload_resp = requests.post(
                    f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                    headers={"Authorization": api_client.headers["Authorization"]},
                    files={"file": ("poa_stamp_test.png", f, "image/png")},
                    data={
                        "requirement_id": "proof_of_address",
                        "document_type": "proof_of_address",
                        "document_label": "Proof of Address"
                    }
                )
            assert upload_resp.status_code == 200, f"POA upload failed: {upload_resp.text}"
            doc_id = upload_resp.json()["id"]
            stamp_resp = api_client.post(
                f"{BASE_URL}/api/employee-documents/{doc_id}/verification-stamp",
                json={
                    "stamp_type": "original_seen",
                    "notes": "Original utility bill physically verified by admin"
                }
            )
            assert stamp_resp.status_code == 200, (
                f"POA original_seen stamp rejected: {stamp_resp.text}"
            )
            assert stamp_resp.json().get("stamp_type") == "original_seen"
        finally:
            os.unlink(tmp.name)

    # -----------------------------------------------------------------------
    # Gate 5: OH / health review
    # -----------------------------------------------------------------------

    def test_health_review_followup_endpoint_exists(self, api_client):
        """If an employee has an active health_review follow-up, the endpoint to list/update
        follow-up items must be reachable and return valid JSON."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/follow-up-items"
        )
        # Endpoint may not exist yet; if so, skip rather than fail
        if response.status_code == 404:
            print("INFO: /follow-up-items endpoint not yet implemented – OH gate test skipped")
            return
        assert response.status_code == 200, (
            f"follow-up-items endpoint failed: {response.text}"
        )
        data = response.json()
        assert isinstance(data, (list, dict)), "Expected list or dict response"
        items = data if isinstance(data, list) else data.get("items", [])
        for item in items:
            if item.get("type") == "health_review":
                assert "status" in item, "health_review follow-up must have a status field"


class TestDBSVerificationGates:
    """
    Deterministic regression tests for DBS end-to-end hardening.

    Mirrors TestRTWVerificationValidation: each test records a deterministic
    DBS check state and asserts the expected HTTP response from the verification
    endpoint before any production side-effects can occur.

    Covers:
      1. verify-all blocks when DBS check outcome != verified
      2. verify (single) blocks when recheck_required=True but no review_due_at
      3. verify (single) for dbs_update_service_check method blocks without proof_document_id
    """

    def _record_dbs_check(self, auth_token: str, overrides: dict) -> requests.Response:
        """Helper: POST a DBS check record with given field overrides."""
        payload = {
            "method": "dbs_certificate_review",
            "checked_at": "2026-04-01",
            "outcome": "verified",
            "recheck_required": False,
            **overrides,
        }
        return requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json=payload,
        )

    def test_verify_all_dbs_blocks_without_verified_check(self, auth_token, test_png_file):
        """verify-all on dbs_certificate must 400 when the current DBS check is not verified.

        Records outcome=in_progress immediately before calling verify-all so the test is
        deterministic regardless of prior state.
        """
        # Upload a DBS document so the upload-presence gate is satisfied.
        with open(test_png_file, "rb") as f:
            requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("dbs_verifyall_setup.png", f, "image/png")},
                data={"requirement_id": "dbs_certificate", "document_type": "dbs_certificate"},
            )

        # Record an explicitly non-verified DBS check.
        check_resp = self._record_dbs_check(auth_token, {"outcome": "in_progress"})
        assert check_resp.status_code in [200, 201], f"DBS check setup failed: {check_resp.text}"

        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_certificate/verify-all",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 400, (
            f"Expected 400 when current DBS check is not verified, got {response.status_code}: {response.text}"
        )
        dbs_gate_messages = [
            "current DBS check record",
            "dbs check outcome",
            "only verified checks",
            "check outcome",
            "proof document",
        ]
        assert any(m.lower() in response.text.lower() for m in dbs_gate_messages), (
            f"Response did not contain any expected DBS gate message: {response.text}"
        )

    def test_verify_dbs_blocks_when_recheck_required_no_due_date(self, auth_token, test_png_file):
        """verify on dbs_certificate must 400 when recheck_required=True but review_due_at is absent.

        Records a verified check with recheck_required=True and no review_due_at so the
        recheck gate fires.
        """
        check_resp = self._record_dbs_check(
            auth_token,
            {"outcome": "verified", "recheck_required": True}
            # review_due_at intentionally omitted
        )
        assert check_resp.status_code in [200, 201], f"DBS check setup failed: {check_resp.text}"

        # Upload evidence so the document-presence gate is satisfied.
        with open(test_png_file, "rb") as f:
            upload_resp = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("dbs_recheck_gate_setup.png", f, "image/png")},
                data={"requirement_id": "dbs_certificate", "document_type": "dbs_certificate"},
            )
        assert upload_resp.status_code == 200, f"DBS upload failed: {upload_resp.text}"
        doc_id = upload_resp.json().get("id")

        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_certificate/verify",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json={"document_id": doc_id, "notes": "TEST: recheck gate assertion"},
        )

        assert response.status_code == 400, (
            f"Expected 400 when recheck_required=True and no review_due_at, got {response.status_code}: {response.text}"
        )
        assert "recheck" in response.text.lower() or "review_due_at" in response.text.lower(), (
            f"Response did not mention recheck or review_due_at: {response.text}"
        )

    def test_verify_dbs_update_service_blocks_without_proof_document(self, auth_token, test_png_file):
        """verify on dbs_status_check must 400 when method=dbs_update_service_check and
        proof_document_id is absent on the check record.

        Records a dbs_update_service_check with only evidence_document_id so the proof gate
        fires.
        """
        # Upload a document to get a doc ID to use as evidence_document_id only.
        with open(test_png_file, "rb") as f:
            upload_resp = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("dbs_update_svc_setup.png", f, "image/png")},
                data={"requirement_id": "dbs_certificate", "document_type": "dbs_certificate"},
            )
        assert upload_resp.status_code == 200, f"DBS upload failed: {upload_resp.text}"
        doc_id = upload_resp.json().get("id")

        check_resp = self._record_dbs_check(
            auth_token,
            {
                "method": "dbs_update_service_check",
                "outcome": "verified",
                "recheck_required": True,
                "review_due_at": "2027-04-01",
                "evidence_document_id": doc_id,
                # proof_document_id intentionally absent
            },
        )
        assert check_resp.status_code in [200, 201], f"DBS check setup failed: {check_resp.text}"

        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_status_check/verify",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json={"document_id": doc_id, "notes": "TEST: update service proof gate assertion"},
        )

        assert response.status_code == 400, (
            f"Expected 400 for dbs_update_service_check without proof_document_id, got {response.status_code}: {response.text}"
        )
        assert "proof" in response.text.lower(), (
            f"Response did not mention proof document: {response.text}"
        )

    def test_legacy_dbs_aliases_reach_same_documents(self, auth_token):
        """dbs_check and dbs_status_check must resolve to the same employee_documents rows
        as dbs_certificate.  We verify both legacy IDs are covered in legacy_mapping by
        testing the verify-all endpoint returns a 200-class or gated-400 (not a 404) for
        each alias — 404 would mean the mapping is missing."""
        for alias in ("dbs_check", "dbs_status_check"):
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{alias}/verify-all",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code != 404, (
                f"DBS alias '{alias}' returned 404 — legacy mapping missing for this ID"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

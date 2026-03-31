"""
Test Reference Integrity Hardening - Step 7
Tests 3-layer reference truth model and compliance page restructure.

Key features tested:
1. GET /api/references/{employee_id}/{ref_num}/integrity - 3-layer truth model
2. Reference with no independent response has counts_toward_readiness=false
3. Candidate-upload-only reference has mismatch_flag 'candidate_upload_only'
4. Name mismatch detection sets identity_confidence='mismatch'
5. POST /api/references/{employee_id}/{ref_num}/override-mismatch - requires 20+ char reason
6. POST /api/references/{employee_id}/{ref_num}/reject - marks reference as rejected
7. GET /api/employees/{employee_id}/references-integrity - shows both refs and valid_count
8. GET /api/employees/{employee_id}/compliance-structured - returns 7 sections
9. address_verification section shows verified_count and minimum_required=2
10. recruitment_integrity section shows reference lifecycle and identity confidence
11. POST /api/employees/{employee_id}/request-missing-items - creates requests for missing items
12. Reference verification.status shows lifecycle states
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID from context
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestReferenceIntegrityEndpoints:
    """Test reference integrity 3-layer truth model endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    # ==================== Reference Integrity Endpoint Tests ====================
    
    def test_get_reference_1_integrity_returns_3_layer_model(self):
        """GET /api/references/{employee_id}/1/integrity returns 3-layer truth model."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify 3-layer structure exists
        assert "declared_referee" in data, "Missing declared_referee layer"
        assert "response" in data, "Missing response layer"
        assert "comparison" in data, "Missing comparison layer"
        
        # Verify declared_referee fields
        declared = data["declared_referee"]
        assert "name" in declared
        assert "email" in declared
        assert "organisation" in declared
        
        # Verify response fields
        resp = data["response"]
        assert "source" in resp
        assert "responder_name" in resp
        assert "submitted_at" in resp
        
        # Verify comparison fields
        comparison = data["comparison"]
        assert "identity_confidence" in comparison
        assert "mismatch_flags" in comparison
        
        print(f"Reference 1 integrity: declared={declared.get('name')}, identity_confidence={comparison.get('identity_confidence')}")
    
    def test_get_reference_2_integrity_returns_3_layer_model(self):
        """GET /api/references/{employee_id}/2/integrity returns 3-layer truth model."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/integrity")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify 3-layer structure
        assert "declared_referee" in data
        assert "response" in data
        assert "comparison" in data
        assert "verification" in data
        assert "counts_toward_readiness" in data
        assert "lifecycle_status" in data
        
        print(f"Reference 2 integrity: counts_toward_readiness={data.get('counts_toward_readiness')}")
    
    def test_reference_without_independent_response_does_not_count(self):
        """Reference with no independent response has counts_toward_readiness=false."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200
        
        data = response.json()
        resp = data.get("response", {})
        
        # If no submitted_at or source is candidate_upload, should not count
        if not resp.get("submitted_at") or resp.get("source") == "candidate_upload":
            assert data.get("counts_toward_readiness") == False, \
                "Reference without independent response should not count toward readiness"
            print("PASS: Reference without independent response correctly does not count")
        else:
            print(f"Reference has independent response: source={resp.get('source')}, submitted_at={resp.get('submitted_at')}")
    
    def test_candidate_upload_only_has_mismatch_flag(self):
        """Candidate-upload-only reference has mismatch_flag 'candidate_upload_only'."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200
        
        data = response.json()
        resp = data.get("response", {})
        comparison = data.get("comparison", {})
        
        if resp.get("source") == "candidate_upload":
            assert "candidate_upload_only" in comparison.get("mismatch_flags", []), \
                "Candidate upload should have 'candidate_upload_only' mismatch flag"
            print("PASS: Candidate upload has 'candidate_upload_only' flag")
        else:
            print(f"Reference source is: {resp.get('source')}")
    
    def test_verification_status_shows_lifecycle(self):
        """Reference verification.status shows lifecycle states."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200
        
        data = response.json()
        verification = data.get("verification", {})
        lifecycle = data.get("lifecycle_status", {})
        
        # Verify verification status is one of expected values
        valid_statuses = ["not_started", "declared", "request_sent", "awaiting_review", 
                         "awaiting_verification", "verified", "rejected"]
        assert verification.get("status") in valid_statuses, \
            f"Invalid verification status: {verification.get('status')}"
        
        # Verify lifecycle fields exist
        assert "declared" in lifecycle
        assert "request_sent" in lifecycle
        assert "viewed" in lifecycle
        assert "response_received" in lifecycle
        assert "awaiting_review" in lifecycle
        assert "reviewed" in lifecycle
        assert "verified" in lifecycle
        assert "rejected" in lifecycle
        
        print(f"Verification status: {verification.get('status')}, lifecycle: {lifecycle}")
    
    def test_invalid_ref_num_returns_400(self):
        """Invalid ref_num (not 1 or 2) returns 400."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/3/integrity")
        assert response.status_code == 400, f"Expected 400 for invalid ref_num, got {response.status_code}"
        print("PASS: Invalid ref_num returns 400")
    
    def test_nonexistent_employee_returns_404(self):
        """Nonexistent employee returns 404."""
        response = self.session.get(f"{BASE_URL}/api/references/nonexistent-id/1/integrity")
        assert response.status_code == 404, f"Expected 404 for nonexistent employee, got {response.status_code}"
        print("PASS: Nonexistent employee returns 404")
    
    # ==================== Override Mismatch Tests ====================
    
    def test_override_mismatch_requires_20_char_reason(self):
        """POST /api/references/{employee_id}/{ref_num}/override-mismatch requires 20+ char reason."""
        # Test with short reason (should fail)
        response = self.session.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/override-mismatch",
            json={"override_reason": "Too short"}
        )
        assert response.status_code == 422 or response.status_code == 400, \
            f"Expected 400/422 for short reason, got {response.status_code}"
        print("PASS: Short override reason rejected")
    
    def test_override_mismatch_with_valid_reason(self):
        """POST /api/references/{employee_id}/{ref_num}/override-mismatch with valid reason succeeds."""
        valid_reason = "Verified via phone call with referee on 2024-01-15. Confirmed identity and employment details."
        
        response = self.session.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/override-mismatch",
            json={"override_reason": valid_reason}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success"
        assert "override_reason" in data
        print(f"PASS: Override mismatch recorded: {data}")
    
    # ==================== Reject Reference Tests ====================
    
    def test_reject_reference_marks_as_rejected(self):
        """POST /api/references/{employee_id}/{ref_num}/reject marks reference as rejected."""
        response = self.session.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/reject",
            json={"rejection_reason": "Reference could not be verified - contact details invalid"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success"
        print(f"PASS: Reference rejected: {data}")
        
        # Verify rejection is reflected in integrity endpoint
        integrity_response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/integrity")
        assert integrity_response.status_code == 200
        
        integrity_data = integrity_response.json()
        lifecycle = integrity_data.get("lifecycle_status", {})
        assert lifecycle.get("rejected") == True, "Reference should be marked as rejected"
        print("PASS: Rejection reflected in integrity data")


class TestReferencesIntegrityEndpoint:
    """Test GET /api/employees/{employee_id}/references-integrity endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_references_integrity_returns_both_references(self):
        """GET /api/employees/{employee_id}/references-integrity shows both references."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-integrity")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify both references present
        assert "reference_1" in data
        assert "reference_2" in data
        
        # Verify valid_count and minimum
        assert "valid_reference_count" in data
        assert "minimum_required" in data
        assert data["minimum_required"] == 2
        assert "meets_minimum" in data
        
        print(f"References integrity: valid_count={data.get('valid_reference_count')}, meets_minimum={data.get('meets_minimum')}")
    
    def test_references_integrity_shows_blocking_issues(self):
        """GET /api/employees/{employee_id}/references-integrity shows blocking issues."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-integrity")
        assert response.status_code == 200
        
        data = response.json()
        assert "blocking_issues" in data
        
        print(f"Blocking issues: {data.get('blocking_issues')}")
    
    def test_nonexistent_employee_returns_404(self):
        """Nonexistent employee returns 404."""
        response = self.session.get(f"{BASE_URL}/api/employees/nonexistent-id/references-integrity")
        assert response.status_code == 404
        print("PASS: Nonexistent employee returns 404")


class TestComplianceStructuredEndpoint:
    """Test GET /api/employees/{employee_id}/compliance-structured endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_compliance_structured_returns_7_sections(self):
        """GET /api/employees/{employee_id}/compliance-structured returns 7 sections."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify all 7 sections exist
        expected_sections = [
            "work_readiness_summary",
            "identity_legal",
            "address_verification",
            "recruitment_integrity",
            "health_forms",
            "training",
            "request_trail"
        ]
        
        for section in expected_sections:
            assert section in data, f"Missing section: {section}"
        
        print(f"PASS: All 7 sections present: {list(data.keys())}")
    
    def test_work_readiness_summary_section(self):
        """work_readiness_summary section has required fields."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200
        
        section = response.json().get("work_readiness_summary", {})
        
        assert "status" in section
        assert "can_work" in section
        assert "blockers" in section
        assert "missing_count" in section
        assert "pending_count" in section
        
        print(f"Work readiness: status={section.get('status')}, can_work={section.get('can_work')}")
    
    def test_identity_legal_section(self):
        """identity_legal section has ID, RTW, DBS."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200
        
        section = response.json().get("identity_legal", {})
        
        assert "id_document" in section
        assert "right_to_work" in section
        assert "dbs_certificate" in section
        
        print(f"Identity legal: {list(section.keys())}")
    
    def test_address_verification_section_shows_minimum_2(self):
        """address_verification section shows verified_count and minimum_required=2."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200
        
        section = response.json().get("address_verification", {})
        
        assert "verified_count" in section
        assert "minimum_required" in section
        assert section["minimum_required"] == 2, "Minimum required should be 2"
        assert "meets_minimum" in section
        assert "documents" in section
        assert "status" in section
        
        print(f"Address verification: verified_count={section.get('verified_count')}, minimum_required={section.get('minimum_required')}, meets_minimum={section.get('meets_minimum')}")
    
    def test_recruitment_integrity_section_shows_reference_lifecycle(self):
        """recruitment_integrity section shows reference lifecycle and identity confidence."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200
        
        section = response.json().get("recruitment_integrity", {})
        
        # Verify reference 1 fields
        ref1 = section.get("reference_1", {})
        assert "declared" in ref1
        assert "response_source" in ref1
        assert "identity_confidence" in ref1
        assert "mismatch_flags" in ref1
        assert "verification_status" in ref1
        assert "counts_toward_readiness" in ref1
        assert "lifecycle" in ref1
        
        # Verify reference 2 fields
        ref2 = section.get("reference_2", {})
        assert "declared" in ref2
        assert "lifecycle" in ref2
        
        # Verify aggregate fields
        assert "valid_reference_count" in section
        assert "minimum_required" in section
        
        print(f"Recruitment integrity: ref1_confidence={ref1.get('identity_confidence')}, ref2_confidence={ref2.get('identity_confidence')}, valid_count={section.get('valid_reference_count')}")
    
    def test_health_forms_section(self):
        """health_forms section has required forms."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200
        
        section = response.json().get("health_forms", {})
        
        assert "health_declaration" in section
        assert "interview_form" in section
        assert "hmrc_checklist" in section
        
        print(f"Health forms: {list(section.keys())}")
    
    def test_training_section(self):
        """training section has status and items."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200
        
        section = response.json().get("training", {})
        
        assert "overall_status" in section
        assert "blocker_count" in section
        assert "items" in section
        assert "is_work_ready_from_training" in section
        
        print(f"Training: overall={section.get('overall_status')}, blockers={section.get('blocker_count')}")
    
    def test_request_trail_section(self):
        """request_trail section has pending requests."""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-structured")
        assert response.status_code == 200
        
        section = response.json().get("request_trail", {})
        
        assert "pending_requests" in section
        assert "total_pending" in section
        
        print(f"Request trail: total_pending={section.get('total_pending')}")
    
    def test_nonexistent_employee_returns_404(self):
        """Nonexistent employee returns 404."""
        response = self.session.get(f"{BASE_URL}/api/employees/nonexistent-id/compliance-structured")
        assert response.status_code == 404
        print("PASS: Nonexistent employee returns 404")


class TestRequestMissingItemsEndpoint:
    """Test POST /api/employees/{employee_id}/request-missing-items endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_request_missing_items_creates_requests(self):
        """POST /api/employees/{employee_id}/request-missing-items creates requests for missing items."""
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-missing-items",
            params={
                "include_proof_of_address": True,
                "include_references": True,
                "include_training": True,
                "include_forms": True
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert "employee_id" in data
        assert "requests_created" in data
        assert "requests_skipped" in data
        assert "items" in data
        
        print(f"Request missing items: created={data.get('requests_created')}, skipped={data.get('requests_skipped')}")
    
    def test_request_missing_items_with_custom_message(self):
        """POST /api/employees/{employee_id}/request-missing-items with custom message."""
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-missing-items",
            params={
                "include_proof_of_address": True,
                "include_references": False,
                "include_training": False,
                "include_forms": False,
                "custom_message": "Please upload your proof of address documents urgently."
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "items" in data
        print(f"Request with custom message: {data}")
    
    def test_request_missing_items_nonexistent_employee(self):
        """Nonexistent employee returns 404."""
        response = self.session.post(
            f"{BASE_URL}/api/employees/nonexistent-id/request-missing-items"
        )
        assert response.status_code == 404
        print("PASS: Nonexistent employee returns 404")


class TestReferenceLifecycleStates:
    """Test reference verification.status lifecycle states."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_lifecycle_status_fields_exist(self):
        """Lifecycle status has all expected fields."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200
        
        lifecycle = response.json().get("lifecycle_status", {})
        
        expected_fields = [
            "declared",
            "request_sent",
            "request_sent_at",
            "viewed",
            "viewed_at",
            "response_received",
            "response_received_at",
            "awaiting_review",
            "reviewed",
            "reviewed_at",
            "verified",
            "verified_at",
            "rejected",
            "rejected_at"
        ]
        
        for field in expected_fields:
            assert field in lifecycle, f"Missing lifecycle field: {field}"
        
        print(f"PASS: All lifecycle fields present")
    
    def test_verification_status_values(self):
        """Verification status is one of expected values."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200
        
        verification = response.json().get("verification", {})
        status = verification.get("status")
        
        valid_statuses = [
            "not_started",
            "declared",
            "request_sent",
            "awaiting_review",
            "awaiting_verification",
            "verified",
            "rejected"
        ]
        
        assert status in valid_statuses, f"Invalid status: {status}"
        print(f"PASS: Verification status '{status}' is valid")


class TestIdentityConfidenceLevels:
    """Test identity confidence detection."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_identity_confidence_values(self):
        """Identity confidence is one of expected values."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200
        
        comparison = response.json().get("comparison", {})
        confidence = comparison.get("identity_confidence")
        
        valid_confidences = ["match", "partial_match", "mismatch", "review_required"]
        
        assert confidence in valid_confidences, f"Invalid confidence: {confidence}"
        print(f"PASS: Identity confidence '{confidence}' is valid")
    
    def test_mismatch_flags_array(self):
        """Mismatch flags is an array."""
        response = self.session.get(f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/integrity")
        assert response.status_code == 200
        
        comparison = response.json().get("comparison", {})
        flags = comparison.get("mismatch_flags")
        
        assert isinstance(flags, list), "mismatch_flags should be a list"
        
        # Valid flag values
        valid_flags = [
            "referee_name_mismatch",
            "referee_email_mismatch",
            "organisation_mismatch",
            "candidate_upload_only",
            "unlinked_reference_document"
        ]
        
        for flag in flags:
            assert flag in valid_flags, f"Invalid mismatch flag: {flag}"
        
        print(f"PASS: Mismatch flags: {flags}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Phase 26: Agreement Routes Extraction Tests

Tests all 16 endpoints extracted from server.py to routes/agreements.py:

Agreement Acknowledgement Endpoints:
1. POST /api/employees/{employee_id}/agreements/send - Send agreement form
2. POST /api/employees/{employee_id}/agreements/complete - Complete agreement (with CQC compliance check)
3. GET /api/employees/{employee_id}/agreements - Get employee agreements
4. POST /api/employees/{employee_id}/agreements/{acknowledgement_id}/verify - Verify agreement
5. POST /api/employees/{employee_id}/agreements/{acknowledgement_id}/reject - Reject agreement
6. POST /api/employees/{employee_id}/agreements/{acknowledgement_id}/unverify - Unverify agreement
7. POST /api/admin/agreements/supersede-admin-contracts - Supersede admin-signed contracts

Agreement Template Endpoints:
8. GET /api/agreement-templates - List agreement templates
9. GET /api/agreement-templates/{template_id} - Get specific template

Agreement Submission Endpoints:
10. POST /api/employees/{employee_id}/agreement-submissions - Create submission
11. GET /api/employees/{employee_id}/agreement-submissions - Get employee submissions
12. GET /api/agreement-submissions/{submission_id} - Get specific submission
13. POST /api/agreement-submissions/{submission_id}/verify - Verify submission
14. POST /api/agreement-submissions/{submission_id}/reject - Reject submission
15. POST /api/agreement-submissions/{submission_id}/unverify - Unverify submission
16. GET /api/agreement-submissions/{submission_id}/pdf - Export submission PDF

CQC COMPLIANCE: contract_acceptance type cannot be completed with admin_assisted or phone_assisted mode
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee ID
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    return data["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


# ==================== HEALTH CHECK ====================

class TestHealthCheck:
    """Verify backend is running."""
    
    def test_health_endpoint(self):
        """Health endpoint should return 200."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ Backend health check passed")


class TestAuthLogin:
    """Verify authentication works."""
    
    def test_admin_login(self):
        """Admin login should succeed."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        print("✓ Admin login successful")


# ==================== ENDPOINT 8: GET /api/agreement-templates ====================

class TestListAgreementTemplates:
    """Tests for GET /api/agreement-templates endpoint."""
    
    def test_list_templates_success(self, api_client):
        """Should return list of agreement templates."""
        response = api_client.get(f"{BASE_URL}/api/agreement-templates")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "templates" in data
        assert isinstance(data["templates"], list)
        assert len(data["templates"]) >= 2  # At least ZERO_HOUR_CONTRACT_V1 and EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1
        
        # Verify template structure
        for template in data["templates"]:
            assert "template_id" in template
            assert "template_name" in template
            assert "version" in template
            assert "section_count" in template
        
        print(f"✓ Listed {len(data['templates'])} agreement templates")
    
    def test_list_templates_requires_auth(self):
        """Should require authentication."""
        response = requests.get(f"{BASE_URL}/api/agreement-templates")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Template list requires authentication")


# ==================== ENDPOINT 9: GET /api/agreement-templates/{template_id} ====================

class TestGetAgreementTemplate:
    """Tests for GET /api/agreement-templates/{template_id} endpoint."""
    
    def test_get_zero_hour_contract_template(self, api_client):
        """Should return ZERO_HOUR_CONTRACT_V1 template with full content."""
        response = api_client.get(f"{BASE_URL}/api/agreement-templates/ZERO_HOUR_CONTRACT_V1")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["template_id"] == "ZERO_HOUR_CONTRACT_V1"
        assert data["template_name"] == "Zero Hour Contract - Statement of Main Terms"
        assert "sections" in data
        assert "company_name" in data
        assert "version" in data
        
        print("✓ Retrieved ZERO_HOUR_CONTRACT_V1 template")
    
    def test_get_handbook_template(self, api_client):
        """Should return EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1 template."""
        response = api_client.get(f"{BASE_URL}/api/agreement-templates/EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["template_id"] == "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"
        assert "sections" in data
        
        print("✓ Retrieved EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1 template")
    
    def test_get_nonexistent_template(self, api_client):
        """Should return 404 for non-existent template."""
        response = api_client.get(f"{BASE_URL}/api/agreement-templates/NONEXISTENT_TEMPLATE")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent template returns 404")


# ==================== ENDPOINT 3: GET /api/employees/{employee_id}/agreements ====================

class TestGetEmployeeAgreements:
    """Tests for GET /api/employees/{employee_id}/agreements endpoint."""
    
    def test_get_employee_agreements_success(self, api_client):
        """Should return employee agreements and pending requests."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "acknowledgements" in data
        assert "pending_requests" in data
        assert isinstance(data["acknowledgements"], list)
        assert isinstance(data["pending_requests"], list)
        
        # Verify acknowledgement structure if any exist
        if data["acknowledgements"]:
            ack = data["acknowledgements"][0]
            assert "id" in ack
            assert "employee_id" in ack
            assert "agreement_type" in ack
            assert "verification_status" in ack
        
        print(f"✓ Retrieved {len(data['acknowledgements'])} agreements for employee")
    
    def test_get_agreements_nonexistent_employee(self, api_client):
        """Should handle non-existent employee gracefully."""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f"{BASE_URL}/api/employees/{fake_id}/agreements")
        # May return empty list or 404 depending on implementation
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print("✓ Non-existent employee handled correctly")


# ==================== ENDPOINT 2: POST /api/employees/{employee_id}/agreements/complete ====================

class TestCompleteAgreement:
    """Tests for POST /api/employees/{employee_id}/agreements/complete endpoint."""
    
    def test_complete_handbook_admin_assisted(self, api_client):
        """Should allow handbook acknowledgement with admin_assisted mode."""
        unique_version = f"TEST_Handbook-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/complete",
            json={
                "agreement_type": "handbook_acknowledgement",
                "completion_mode": "admin_assisted",
                "version_acknowledged": unique_version
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "id" in data or "acknowledgement" in data
        print("✓ Handbook acknowledgement with admin_assisted succeeded")
    
    def test_complete_handbook_phone_assisted(self, api_client):
        """Should allow handbook acknowledgement with phone_assisted mode."""
        unique_version = f"TEST_Handbook-Phone-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/complete",
            json={
                "agreement_type": "handbook_acknowledgement",
                "completion_mode": "phone_assisted",
                "version_acknowledged": unique_version,
                "call_note": "TEST: Employee confirmed understanding over phone"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Handbook acknowledgement with phone_assisted succeeded")
    
    def test_cqc_compliance_contract_admin_assisted_blocked(self, api_client):
        """CQC COMPLIANCE: contract_acceptance with admin_assisted should be BLOCKED."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/complete",
            json={
                "agreement_type": "contract_acceptance",
                "completion_mode": "admin_assisted",
                "version_acknowledged": "TEST-CQC-VIOLATION"
            }
        )
        assert response.status_code == 403, f"Expected 403 for CQC violation, got {response.status_code}"
        data = response.json()
        assert "CQC Compliance" in data.get("detail", ""), "Should mention CQC Compliance"
        print("✓ CQC Compliance: contract_acceptance with admin_assisted correctly blocked")
    
    def test_cqc_compliance_contract_phone_assisted_blocked(self, api_client):
        """CQC COMPLIANCE: contract_acceptance with phone_assisted should be BLOCKED."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/complete",
            json={
                "agreement_type": "contract_acceptance",
                "completion_mode": "phone_assisted",
                "version_acknowledged": "TEST-CQC-VIOLATION-PHONE"
            }
        )
        assert response.status_code == 403, f"Expected 403 for CQC violation, got {response.status_code}"
        data = response.json()
        assert "CQC Compliance" in data.get("detail", ""), "Should mention CQC Compliance"
        print("✓ CQC Compliance: contract_acceptance with phone_assisted correctly blocked")
    
    def test_cqc_compliance_contract_self_completed_allowed(self, api_client):
        """CQC COMPLIANCE: contract_acceptance with self_completed should be ALLOWED."""
        unique_version = f"TEST_Contract-Self-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/complete",
            json={
                "agreement_type": "contract_acceptance",
                "completion_mode": "self_completed",
                "version_acknowledged": unique_version
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ CQC Compliance: contract_acceptance with self_completed allowed")
    
    def test_complete_agreement_nonexistent_employee(self, api_client):
        """Should return 404 for non-existent employee."""
        fake_id = str(uuid.uuid4())
        response = api_client.post(
            f"{BASE_URL}/api/employees/{fake_id}/agreements/complete",
            json={
                "agreement_type": "handbook_acknowledgement",
                "completion_mode": "admin_assisted",
                "version_acknowledged": "TEST"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent employee returns 404")


# ==================== ENDPOINT 1: POST /api/employees/{employee_id}/agreements/send ====================

class TestSendAgreementForm:
    """Tests for POST /api/employees/{employee_id}/agreements/send endpoint."""
    
    def test_send_agreement_form_success(self, api_client):
        """Should send agreement form to employee."""
        unique_version = f"TEST_Contract-Send-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/send",
            json={
                "agreement_type": "contract_acceptance",
                "version_label": unique_version,
                "custom_message": "TEST: Please review and sign your contract",
                "due_days": 7
            }
        )
        # May return 200 or 201 depending on implementation
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        print("✓ Agreement form sent successfully")
    
    def test_send_agreement_nonexistent_employee(self, api_client):
        """Should return 404 for non-existent employee."""
        fake_id = str(uuid.uuid4())
        response = api_client.post(
            f"{BASE_URL}/api/employees/{fake_id}/agreements/send",
            json={
                "agreement_type": "contract_acceptance",
                "version_label": "TEST",
                "due_days": 7
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent employee returns 404")


# ==================== ENDPOINT 4, 5, 6: Verify/Reject/Unverify Agreement ====================

class TestAgreementVerificationWorkflow:
    """Tests for agreement verification workflow endpoints."""
    
    @pytest.fixture
    def test_acknowledgement(self, api_client):
        """Create a test acknowledgement for verification tests."""
        unique_version = f"TEST_Verify-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/complete",
            json={
                "agreement_type": "handbook_acknowledgement",
                "completion_mode": "admin_assisted",
                "version_acknowledged": unique_version
            }
        )
        assert response.status_code == 200, f"Failed to create test acknowledgement: {response.text}"
        data = response.json()
        # Handle different response structures
        ack_id = data.get("id") or data.get("acknowledgement", {}).get("id")
        assert ack_id, f"No acknowledgement ID in response: {data}"
        return ack_id
    
    def test_verify_agreement(self, api_client, test_acknowledgement):
        """Should verify an agreement acknowledgement."""
        ack_id = test_acknowledgement
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/{ack_id}/verify",
            json="TEST: Verified during testing"
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("verification_status") == "verified"
        print("✓ Agreement verified successfully")
    
    def test_unverify_agreement(self, api_client, test_acknowledgement):
        """Should unverify an agreement acknowledgement."""
        ack_id = test_acknowledgement
        
        # First verify it
        api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/{ack_id}/verify",
            json="Verified for unverify test"
        )
        
        # Then unverify
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/{ack_id}/unverify",
            json={"reason": "TEST: Unverifying for testing purposes"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("verification_status") in ["pending", "awaiting_review"]
        print("✓ Agreement unverified successfully")
    
    def test_unverify_requires_reason(self, api_client, test_acknowledgement):
        """Should require reason for unverify."""
        ack_id = test_acknowledgement
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/{ack_id}/unverify",
            json={"reason": "ab"}  # Too short
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Unverify requires minimum reason length")
    
    def test_reject_agreement(self, api_client):
        """Should reject an agreement acknowledgement."""
        # Create a new acknowledgement for rejection
        unique_version = f"TEST_Reject-{uuid.uuid4().hex[:8]}"
        create_response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/complete",
            json={
                "agreement_type": "handbook_acknowledgement",
                "completion_mode": "admin_assisted",
                "version_acknowledged": unique_version
            }
        )
        assert create_response.status_code == 200
        data = create_response.json()
        ack_id = data.get("id") or data.get("acknowledgement", {}).get("id")
        
        # Reject it
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/{ack_id}/reject",
            json={"reason": "TEST: Rejecting for testing purposes"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("verification_status") == "rejected"
        print("✓ Agreement rejected successfully")
    
    def test_verify_nonexistent_acknowledgement(self, api_client):
        """Should return 404 for non-existent acknowledgement."""
        fake_id = f"agr_ack_{uuid.uuid4().hex[:12]}"
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreements/{fake_id}/verify",
            json="Test"
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent acknowledgement returns 404")


# ==================== ENDPOINT 7: POST /api/admin/agreements/supersede-admin-contracts ====================

class TestSupersedeAdminContracts:
    """Tests for POST /api/admin/agreements/supersede-admin-contracts endpoint."""
    
    def test_supersede_admin_contracts(self, api_client):
        """Should supersede admin-signed contracts (CQC compliance fix)."""
        response = api_client.post(f"{BASE_URL}/api/admin/agreements/supersede-admin-contracts")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "success" in data
        assert data["success"] == True
        assert "message" in data
        assert "count" in data
        
        print(f"✓ Supersede admin contracts: {data['message']}")
    
    def test_supersede_requires_admin(self):
        """Should require admin authentication."""
        response = requests.post(f"{BASE_URL}/api/admin/agreements/supersede-admin-contracts")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Supersede requires admin authentication")


# ==================== ENDPOINT 10: POST /api/employees/{employee_id}/agreement-submissions ====================

class TestCreateAgreementSubmission:
    """Tests for POST /api/employees/{employee_id}/agreement-submissions endpoint."""
    
    def test_create_submission_success(self, api_client):
        """Should create agreement submission from template."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreement-submissions",
            json={
                "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
                "form_data": {
                    "employee_name": "Test Employee",
                    "employee_role": "Healthcare Assistant",
                    "ack_received": True,
                    "ack_read": True,
                    "ack_policies": True,
                    "ack_updates": True,
                    "ack_ask_questions": True,
                    "ack_compliance": True,
                    "signature_name": "Test Employee",
                    "signature_date": datetime.now().strftime("%Y-%m-%d")
                },
                "completion_mode": "admin_assisted",
                "admin_note": "TEST: Created during automated testing"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["template_id"] == "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        
        print(f"✓ Created agreement submission: {data['id']}")
        return data["id"]
    
    def test_create_submission_nonexistent_employee(self, api_client):
        """Should return 404 for non-existent employee."""
        fake_id = str(uuid.uuid4())
        response = api_client.post(
            f"{BASE_URL}/api/employees/{fake_id}/agreement-submissions",
            json={
                "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
                "form_data": {"employee_name": "Test"},
                "completion_mode": "admin_assisted"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent employee returns 404")


# ==================== ENDPOINT 11: GET /api/employees/{employee_id}/agreement-submissions ====================

class TestGetEmployeeSubmissions:
    """Tests for GET /api/employees/{employee_id}/agreement-submissions endpoint."""
    
    def test_get_employee_submissions(self, api_client):
        """Should return employee's agreement submissions."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreement-submissions")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "submissions" in data
        assert isinstance(data["submissions"], list)
        
        if data["submissions"]:
            sub = data["submissions"][0]
            assert "id" in sub
            assert "template_id" in sub
            assert "employee_id" in sub
            assert "verification_status" in sub
        
        print(f"✓ Retrieved {len(data['submissions'])} submissions for employee")


# ==================== ENDPOINT 12: GET /api/agreement-submissions/{submission_id} ====================

class TestGetSubmission:
    """Tests for GET /api/agreement-submissions/{submission_id} endpoint."""
    
    def test_get_submission_success(self, api_client):
        """Should return specific submission with template."""
        # First get list to find a submission ID
        list_response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreement-submissions")
        assert list_response.status_code == 200
        submissions = list_response.json().get("submissions", [])
        
        if not submissions:
            pytest.skip("No submissions available to test")
        
        submission_id = submissions[0]["id"]
        response = api_client.get(f"{BASE_URL}/api/agreement-submissions/{submission_id}")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "submission" in data
        assert "template" in data
        assert data["submission"]["id"] == submission_id
        
        print(f"✓ Retrieved submission {submission_id}")
    
    def test_get_nonexistent_submission(self, api_client):
        """Should return 404 for non-existent submission."""
        fake_id = f"agr_sub_{uuid.uuid4().hex[:12]}"
        response = api_client.get(f"{BASE_URL}/api/agreement-submissions/{fake_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent submission returns 404")


# ==================== ENDPOINT 13, 14, 15: Verify/Reject/Unverify Submission ====================

class TestSubmissionVerificationWorkflow:
    """Tests for submission verification workflow endpoints."""
    
    @pytest.fixture
    def test_submission(self, api_client):
        """Create a test submission for verification tests."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreement-submissions",
            json={
                "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
                "form_data": {
                    "employee_name": f"Test-{uuid.uuid4().hex[:8]}",
                    "employee_role": "Healthcare Assistant",
                    "ack_received": True,
                    "ack_read": True,
                    "ack_policies": True,
                    "ack_updates": True,
                    "ack_ask_questions": True,
                    "ack_compliance": True,
                    "signature_name": "Test Employee",
                    "signature_date": datetime.now().strftime("%Y-%m-%d")
                },
                "completion_mode": "admin_assisted",
                "admin_note": "TEST: Created for verification workflow test"
            }
        )
        assert response.status_code == 200, f"Failed to create test submission: {response.text}"
        return response.json()["id"]
    
    def test_verify_submission(self, api_client, test_submission):
        """Should verify a submission."""
        response = api_client.post(
            f"{BASE_URL}/api/agreement-submissions/{test_submission}/verify",
            json={"notes": "TEST: Verified during automated testing"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("verification_status") == "verified"
        print("✓ Submission verified successfully")
    
    def test_unverify_submission(self, api_client, test_submission):
        """Should unverify a submission."""
        # First verify it
        api_client.post(
            f"{BASE_URL}/api/agreement-submissions/{test_submission}/verify",
            json={"notes": "Verified for unverify test"}
        )
        
        # Then unverify
        response = api_client.post(
            f"{BASE_URL}/api/agreement-submissions/{test_submission}/unverify",
            json={"reason": "TEST: Unverifying for testing purposes"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("verification_status") == "pending"
        print("✓ Submission unverified successfully")
    
    def test_unverify_submission_requires_reason(self, api_client, test_submission):
        """Should require reason for unverify."""
        response = api_client.post(
            f"{BASE_URL}/api/agreement-submissions/{test_submission}/unverify",
            json={"reason": "ab"}  # Too short
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Unverify submission requires minimum reason length")
    
    def test_reject_submission(self, api_client):
        """Should reject a submission."""
        # Create a new submission for rejection
        create_response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreement-submissions",
            json={
                "template_id": "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1",
                "form_data": {
                    "employee_name": f"Reject-Test-{uuid.uuid4().hex[:8]}",
                    "employee_role": "Healthcare Assistant",
                    "ack_received": True,
                    "ack_read": True,
                    "ack_policies": True,
                    "ack_updates": True,
                    "ack_ask_questions": True,
                    "ack_compliance": True,
                    "signature_name": "Test Employee",
                    "signature_date": datetime.now().strftime("%Y-%m-%d")
                },
                "completion_mode": "admin_assisted",
                "admin_note": "TEST: Created for rejection test"
            }
        )
        assert create_response.status_code == 200, f"Failed to create submission: {create_response.text}"
        submission_id = create_response.json()["id"]
        
        # Reject it
        response = api_client.post(
            f"{BASE_URL}/api/agreement-submissions/{submission_id}/reject",
            json={"reason": "TEST: Rejecting for testing purposes - incomplete information"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("verification_status") == "rejected"
        print("✓ Submission rejected successfully")
    
    def test_reject_submission_requires_reason(self, api_client, test_submission):
        """Should require minimum 10 character reason for rejection."""
        response = api_client.post(
            f"{BASE_URL}/api/agreement-submissions/{test_submission}/reject",
            json={"reason": "short"}  # Less than 10 characters
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Reject submission requires minimum 10 character reason")
    
    def test_verify_nonexistent_submission(self, api_client):
        """Should return 404 for non-existent submission."""
        fake_id = f"agr_sub_{uuid.uuid4().hex[:12]}"
        response = api_client.post(
            f"{BASE_URL}/api/agreement-submissions/{fake_id}/verify",
            json={"notes": "Test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent submission returns 404")


# ==================== ENDPOINT 16: GET /api/agreement-submissions/{submission_id}/pdf ====================

class TestExportSubmissionPDF:
    """Tests for GET /api/agreement-submissions/{submission_id}/pdf endpoint."""
    
    def test_export_pdf_success(self, api_client):
        """Should export submission as PDF (HTML content)."""
        # First get list to find a submission ID
        list_response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/agreement-submissions")
        assert list_response.status_code == 200
        submissions = list_response.json().get("submissions", [])
        
        if not submissions:
            pytest.skip("No submissions available to test")
        
        submission_id = submissions[0]["id"]
        response = api_client.get(f"{BASE_URL}/api/agreement-submissions/{submission_id}/pdf")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "submission_id" in data
        assert "html_content" in data
        assert "filename" in data
        assert data["submission_id"] == submission_id
        assert ".pdf" in data["filename"]
        
        print(f"✓ Exported PDF for submission {submission_id}")
    
    def test_export_pdf_nonexistent_submission(self, api_client):
        """Should return 404 for non-existent submission."""
        fake_id = f"agr_sub_{uuid.uuid4().hex[:12]}"
        response = api_client.get(f"{BASE_URL}/api/agreement-submissions/{fake_id}/pdf")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent submission PDF returns 404")


# ==================== REGRESSION TESTS ====================

class TestRegressionPreviousPhases:
    """Regression tests for endpoints from previous phases."""
    
    def test_recurring_compliance_endpoint(self, api_client):
        """Phase 25: Recurring compliance endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance")
        assert response.status_code == 200, f"Phase 25 regression failed: {response.text}"
        print("✓ Phase 25 recurring compliance endpoint working")
    
    def test_employment_gaps_endpoint(self, api_client):
        """Phase 24: Employment gaps endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps")
        assert response.status_code == 200, f"Phase 24 regression failed: {response.text}"
        print("✓ Phase 24 employment gaps endpoint working")
    
    def test_bulk_schedules_endpoint(self, api_client):
        """Phase 22: Bulk schedules endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/bulk/schedules")
        assert response.status_code == 200, f"Phase 22 regression failed: {response.text}"
        print("✓ Phase 22 bulk schedules endpoint working")
    
    def test_policy_assignments_endpoint(self, api_client):
        """Phase 20: Policy assignments endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/policy-assignments")
        assert response.status_code == 200, f"Phase 20 regression failed: {response.text}"
        print("✓ Phase 20 policy assignments endpoint working")

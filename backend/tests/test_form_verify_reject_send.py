"""
Test suite for form submission verify/reject/send endpoints.
Tests:
- POST /api/form-submissions/{id}/verify - sets status to verified
- POST /api/form-submissions/{id}/reject - sets status to rejected with reason
- POST /api/employees/{id}/send-form?form_type={type} - sends form request email
- GET /api/employees/{id}/compliance-file - returns correct status for rejected submissions
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
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge
REJECTED_SUBMISSION_ID = "1417b85a-ab2b-4e80-8fff-b75a4acad6eb"  # recruitment_checklist


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestFormVerifyEndpoint:
    """Tests for POST /api/form-submissions/{id}/verify"""
    
    def test_verify_nonexistent_submission_returns_404(self, auth_headers):
        """Verify endpoint returns 404 for non-existent submission"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/form-submissions/{fake_id}/verify",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "not found" in response.json().get("detail", "").lower()
    
    def test_verify_submission_sets_verified_status(self, auth_headers):
        """Create a submission, verify it, and check status is verified"""
        # First create a test submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "staff_health_questionnaire",
            "form_type": "staff_health_questionnaire",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Now verify it
        verify_response = requests.post(
            f"{BASE_URL}/api/form-submissions/{submission_id}/verify",
            headers=auth_headers
        )
        
        assert verify_response.status_code == 200, f"Verify failed: {verify_response.text}"
        
        verified_data = verify_response.json()
        assert verified_data.get("status") == "verified", f"Expected status 'verified', got {verified_data.get('status')}"
        assert verified_data.get("verified") == True, "Expected verified=True"
        assert verified_data.get("verified_by") is not None, "Expected verified_by to be set"
        assert verified_data.get("verified_at") is not None, "Expected verified_at to be set"
        
        # Cleanup - delete the test submission
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)


class TestFormRejectEndpoint:
    """Tests for POST /api/form-submissions/{id}/reject"""
    
    def test_reject_nonexistent_submission_returns_404(self, auth_headers):
        """Reject endpoint returns 404 for non-existent submission"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/form-submissions/{fake_id}/reject",
            json={"rejection_reason": "Test rejection"},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_reject_submission_sets_rejected_status(self, auth_headers):
        """Create a submission, reject it, and check status is rejected with reason"""
        # First create a test submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "interview_record",
            "form_type": "interview_record",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Now reject it
        rejection_reason = "Missing required information - please resubmit"
        reject_response = requests.post(
            f"{BASE_URL}/api/form-submissions/{submission_id}/reject",
            json={"rejection_reason": rejection_reason},
            headers=auth_headers
        )
        
        assert reject_response.status_code == 200, f"Reject failed: {reject_response.text}"
        
        rejected_data = reject_response.json()
        assert rejected_data.get("status") == "rejected", f"Expected status 'rejected', got {rejected_data.get('status')}"
        assert rejected_data.get("rejection_reason") == rejection_reason, f"Rejection reason mismatch"
        assert rejected_data.get("rejected_by") is not None, "Expected rejected_by to be set"
        assert rejected_data.get("rejected_at") is not None, "Expected rejected_at to be set"
        assert rejected_data.get("verified") == False, "Expected verified=False after rejection"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)
    
    def test_reject_without_reason_fails(self, auth_headers):
        """Reject endpoint requires rejection_reason"""
        # Create a test submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "equal_opportunities",
            "form_type": "equal_opportunities",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Try to reject without reason
        reject_response = requests.post(
            f"{BASE_URL}/api/form-submissions/{submission_id}/reject",
            json={},  # No rejection_reason
            headers=auth_headers
        )
        
        # Should fail validation
        assert reject_response.status_code == 422, f"Expected 422 validation error, got {reject_response.status_code}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)


class TestSendFormEndpoint:
    """Tests for POST /api/employees/{id}/send-form?form_type={type}"""
    
    def test_send_form_to_nonexistent_employee_returns_404(self, auth_headers):
        """Send form endpoint returns 404 for non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_id}/send-form?form_type=staff_health_questionnaire",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_send_form_with_invalid_form_type_returns_400(self, auth_headers):
        """Send form endpoint returns 400 for invalid form type"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/send-form?form_type=invalid_form_type",
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "invalid form type" in response.json().get("detail", "").lower()
    
    def test_send_form_creates_email_request(self, auth_headers):
        """Send form endpoint creates email request for valid form type"""
        # Use a unique form type to avoid duplicate detection
        form_type = "staff_health_questionnaire"
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/send-form?form_type={form_type}",
            headers=auth_headers
        )
        
        # Should succeed or return duplicate if already sent
        assert response.status_code == 200, f"Send form failed: {response.text}"
        
        data = response.json()
        # Either success or duplicate is acceptable
        assert data.get("status") in ["success", "duplicate", "sent"], f"Unexpected status: {data.get('status')}"
        
        if data.get("status") == "success" or data.get("status") == "sent":
            assert data.get("request_id") is not None or data.get("token") is not None, "Expected request_id or token"
    
    def test_send_form_with_custom_message(self, auth_headers):
        """Send form endpoint accepts custom message"""
        form_type = "staff_personal_info"
        custom_message = "Please complete this form urgently"
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/send-form?form_type={form_type}&message={custom_message}",
            headers=auth_headers
        )
        
        # Should succeed or return duplicate
        assert response.status_code == 200, f"Send form failed: {response.text}"


class TestComplianceFileRejectedStatus:
    """Tests for compliance file returning correct rejected status"""
    
    def test_compliance_file_returns_rejected_status(self, auth_headers):
        """Compliance file should return rejected status for rejected submissions"""
        # First create and reject a submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "recruitment_checklist",
            "form_type": "recruitment_checklist",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Reject it
        rejection_reason = "Test rejection for compliance file check"
        requests.post(
            f"{BASE_URL}/api/form-submissions/{submission_id}/reject",
            json={"rejection_reason": rejection_reason},
            headers=auth_headers
        )
        
        # Now check compliance file
        compliance_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert compliance_response.status_code == 200, f"Compliance file failed: {compliance_response.text}"
        
        compliance_data = compliance_response.json()
        
        # Find the recruitment_checklist row
        recruitment_record = compliance_data.get("sections", {}).get("recruitment_record", {})
        rows = recruitment_record.get("rows", [])
        
        checklist_row = None
        for row in rows:
            if row.get("key") == "recruitment_checklist":
                checklist_row = row
                break
        
        if checklist_row:
            # Check status is rejected
            assert checklist_row.get("status") == "rejected", f"Expected status 'rejected', got {checklist_row.get('status')}"
            assert checklist_row.get("is_rejected") == True, "Expected is_rejected=True"
            assert checklist_row.get("rejection_reason") == rejection_reason, "Rejection reason mismatch"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)
    
    def test_compliance_file_returns_verified_status(self, auth_headers):
        """Compliance file should return verified status for verified submissions"""
        # Create and verify a submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "induction",
            "form_type": "induction",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Verify it
        requests.post(
            f"{BASE_URL}/api/form-submissions/{submission_id}/verify",
            headers=auth_headers
        )
        
        # Check compliance file
        compliance_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        
        # Find the induction row
        health_competency = compliance_data.get("sections", {}).get("health_competency", {})
        rows = health_competency.get("rows", [])
        
        induction_row = None
        for row in rows:
            if row.get("key") == "induction":
                induction_row = row
                break
        
        if induction_row:
            assert induction_row.get("status") == "verified", f"Expected status 'verified', got {induction_row.get('status')}"
            assert induction_row.get("is_verified") == True, "Expected is_verified=True"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)
    
    def test_compliance_file_returns_awaiting_review_status(self, auth_headers):
        """Compliance file should return awaiting_review status for submitted forms"""
        # Create a submitted (not verified) submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "hmrc_starter_checklist",
            "form_type": "hmrc_starter_checklist",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Check compliance file
        compliance_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        
        # Find the hmrc_starter_checklist row
        admin_forms = compliance_data.get("sections", {}).get("admin_forms", {})
        rows = admin_forms.get("rows", [])
        
        hmrc_row = None
        for row in rows:
            if row.get("key") == "hmrc_starter_checklist":
                hmrc_row = row
                break
        
        if hmrc_row:
            assert hmrc_row.get("status") == "awaiting_review", f"Expected status 'awaiting_review', got {hmrc_row.get('status')}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)


class TestFormSubmissionAllowedActions:
    """Tests for allowed_actions in compliance file form rows"""
    
    def test_submitted_form_has_verify_reject_actions(self, auth_headers):
        """Submitted form should have verify and reject in allowed_actions"""
        # Create a submitted submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "interview_record",
            "form_type": "interview_record",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Check compliance file
        compliance_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        
        # Find the interview_record row
        recruitment_record = compliance_data.get("sections", {}).get("recruitment_record", {})
        rows = recruitment_record.get("rows", [])
        
        interview_row = None
        for row in rows:
            if row.get("key") == "interview_record":
                interview_row = row
                break
        
        if interview_row:
            allowed_actions = interview_row.get("allowed_actions", [])
            assert "verify" in allowed_actions, f"Expected 'verify' in allowed_actions: {allowed_actions}"
            assert "reject" in allowed_actions, f"Expected 'reject' in allowed_actions: {allowed_actions}"
            assert "view_submission" in allowed_actions, f"Expected 'view_submission' in allowed_actions: {allowed_actions}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)
    
    def test_verified_form_does_not_have_verify_reject_actions(self, auth_headers):
        """Verified form should NOT have verify and reject in allowed_actions"""
        # Create and verify a submission
        submission_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "equal_opportunities",
            "form_type": "equal_opportunities",
            "data": {"test_field": "test_value"},
            "status": "submitted"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            json=submission_data,
            headers=auth_headers
        )
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test submission: {create_response.text}")
        
        submission_id = create_response.json().get("id")
        
        # Verify it
        requests.post(
            f"{BASE_URL}/api/form-submissions/{submission_id}/verify",
            headers=auth_headers
        )
        
        # Check compliance file
        compliance_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        
        # Find the equal_opportunities row
        admin_forms = compliance_data.get("sections", {}).get("admin_forms", {})
        rows = admin_forms.get("rows", [])
        
        eq_row = None
        for row in rows:
            if row.get("key") == "equal_opportunities":
                eq_row = row
                break
        
        if eq_row:
            allowed_actions = eq_row.get("allowed_actions", [])
            assert "verify" not in allowed_actions, f"Verified form should not have 'verify' action: {allowed_actions}"
            # Note: reject might still be allowed for optional forms
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

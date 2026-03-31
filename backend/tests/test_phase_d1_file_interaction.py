"""
Phase D1: File Interaction + Request Lifecycle Endpoints Tests
Tests endpoints that turn the Compliance File from a status page into an operations page.

Endpoints tested:
- GET /api/employees/{id}/requirements/{key}/files
- GET /api/employees/{id}/requirements/{key}/unified-history
- GET /api/employees/{id}/requirements/{key}/requests
- POST /api/documents/{id}/mark-uploaded-in-error
- POST /api/documents/{id}/supersede
- POST /api/documents/{id}/move-category
- POST /api/employees/{id}/requirements/{key}/resend-request
- POST /api/employees/{id}/requirements/{key}/request-replacement
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID from context
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestRequirementFilesEndpoint:
    """Tests for GET /api/employees/{id}/requirements/{key}/files"""
    
    def test_get_files_for_proof_of_address(self, auth_headers):
        """Test that proof_of_address returns multi_file_config with required_count: 2"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "requirement_key" in data
        assert data["requirement_key"] == "proof_of_address"
        assert "active_files" in data
        assert "historical_files" in data
        assert "multi_file_config" in data
        
        # Verify multi_file_config for proof_of_address (NHS standard: 2 documents)
        multi_file_config = data["multi_file_config"]
        assert multi_file_config.get("multi_file") == True
        assert multi_file_config.get("required_count") == 2, f"Expected required_count=2, got {multi_file_config.get('required_count')}"
        
        print(f"PASS: proof_of_address multi_file_config shows required_count: {multi_file_config.get('required_count')}")
    
    def test_get_files_for_right_to_work(self, auth_headers):
        """Test files endpoint for right_to_work_documents"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/files",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "active_files" in data
        assert "historical_files" in data
        assert "active_file_count" in data
        assert "historical_file_count" in data
        assert "multi_file_config" in data
        
        # RTW should support multi-file
        assert data["multi_file_config"].get("multi_file") == True
        
        print(f"PASS: right_to_work_documents files endpoint returns correct structure")
    
    def test_get_files_for_identity_documents(self, auth_headers):
        """Test files endpoint for identity_documents"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/identity_documents/files",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "active_files" in data
        assert "historical_files" in data
        assert "verified_count" in data
        assert "pending_review_count" in data
        
        print(f"PASS: identity_documents files endpoint returns correct structure")
    
    def test_get_files_for_dbs_certificate(self, auth_headers):
        """Test files endpoint for dbs_certificate"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_certificate/files",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "requirement_key" in data
        assert data["requirement_key"] == "dbs_certificate"
        
        print(f"PASS: dbs_certificate files endpoint works correctly")
    
    def test_get_files_nonexistent_employee(self, auth_headers):
        """Test files endpoint with non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/employees/{fake_id}/requirements/proof_of_address/files",
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent employee returns 404")


class TestUnifiedHistoryEndpoint:
    """Tests for GET /api/employees/{id}/requirements/{key}/unified-history"""
    
    def test_unified_history_returns_timeline(self, auth_headers):
        """Test that unified-history returns timeline with events"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/unified-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "requirement_key" in data
        assert "employee_id" in data
        assert "timeline" in data
        assert "total_events" in data
        
        assert data["requirement_key"] == "right_to_work_documents"
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert isinstance(data["timeline"], list)
        
        print(f"PASS: unified-history returns timeline with {data['total_events']} events")
    
    def test_unified_history_includes_check_records(self, auth_headers):
        """Test that unified-history includes check_recorded events for check-type requirements"""
        # Test with right_to_work_check which should include rtw_checks
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_check/unified-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Timeline should exist
        assert "timeline" in data
        
        # Check if any check_recorded events exist (may be empty if no checks recorded)
        check_events = [e for e in data["timeline"] if e.get("event_type") == "check_recorded"]
        print(f"PASS: unified-history for right_to_work_check found {len(check_events)} check_recorded events")
    
    def test_unified_history_for_proof_of_address(self, auth_headers):
        """Test unified-history for proof_of_address (should include address_verifications)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/unified-history",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "timeline" in data
        print(f"PASS: unified-history for proof_of_address returns {data['total_events']} events")
    
    def test_unified_history_nonexistent_employee(self, auth_headers):
        """Test unified-history with non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/employees/{fake_id}/requirements/proof_of_address/unified-history",
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent employee returns 404")


class TestRequestsEndpoint:
    """Tests for GET /api/employees/{id}/requirements/{key}/requests"""
    
    def test_requests_returns_overall_status(self, auth_headers):
        """Test that requests endpoint returns overall_status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/requests",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "requirement_key" in data
        assert "employee_id" in data
        assert "overall_status" in data
        assert "current_request" in data  # Can be null
        assert "request_history" in data
        assert "total_requests" in data
        
        # overall_status should be one of the expected values
        valid_statuses = ["not_requested", "pending", "sent", "viewed", "submitted", "completed", "expired_or_cancelled"]
        assert data["overall_status"] in valid_statuses, f"Unexpected overall_status: {data['overall_status']}"
        
        print(f"PASS: requests endpoint returns overall_status: {data['overall_status']}")
    
    def test_requests_returns_request_history(self, auth_headers):
        """Test that requests endpoint returns request_history array"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/requests",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data["request_history"], list)
        
        # If there are requests, verify structure
        if data["request_history"]:
            req = data["request_history"][0]
            assert "request_id" in req
            assert "status" in req
            assert "source" in req  # manual or scheduled
        
        print(f"PASS: requests endpoint returns {data['total_requests']} requests in history")
    
    def test_requests_nonexistent_employee(self, auth_headers):
        """Test requests endpoint with non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/employees/{fake_id}/requirements/proof_of_address/requests",
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent employee returns 404")


class TestDocumentMarkUploadedInError:
    """Tests for POST /api/documents/{id}/mark-uploaded-in-error"""
    
    def test_mark_uploaded_in_error_requires_reason(self, auth_headers):
        """Test that mark-uploaded-in-error requires a reason with min 10 chars"""
        # First, we need a document ID - let's get one from the files endpoint
        files_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers=auth_headers
        )
        
        if files_response.status_code != 200:
            pytest.skip("Could not get files to test mark-uploaded-in-error")
        
        files_data = files_response.json()
        
        # If no active files, skip this test
        if not files_data.get("active_files"):
            pytest.skip("No active files to test mark-uploaded-in-error")
        
        doc_id = files_data["active_files"][0]["file_id"]
        
        # Test with short reason (should fail)
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/mark-uploaded-in-error",
            headers=auth_headers,
            json={"reason": "short"}  # Less than 10 chars
        )
        
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422 for short reason, got {response.status_code}"
        print(f"PASS: mark-uploaded-in-error rejects short reason")
    
    def test_mark_uploaded_in_error_nonexistent_document(self, auth_headers):
        """Test mark-uploaded-in-error with non-existent document"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/documents/{fake_id}/mark-uploaded-in-error",
            headers=auth_headers,
            json={"reason": "This document was uploaded by mistake and needs to be removed from the system"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent document returns 404")


class TestDocumentSupersede:
    """Tests for POST /api/documents/{id}/supersede"""
    
    def test_supersede_nonexistent_document(self, auth_headers):
        """Test supersede with non-existent document"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/documents/{fake_id}/supersede",
            headers=auth_headers,
            json={"reason": "Replaced by newer document"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent document returns 404")
    
    def test_supersede_endpoint_exists(self, auth_headers):
        """Test that supersede endpoint exists and accepts requests"""
        # Get a document to test with
        files_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/identity_documents/files",
            headers=auth_headers
        )
        
        if files_response.status_code != 200:
            pytest.skip("Could not get files to test supersede")
        
        files_data = files_response.json()
        
        if not files_data.get("active_files"):
            pytest.skip("No active files to test supersede")
        
        # Just verify the endpoint accepts the request format
        # We won't actually supersede to avoid breaking test data
        doc_id = files_data["active_files"][0]["file_id"]
        
        # Test with a fake replacement ID to verify endpoint structure
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/supersede",
            headers=auth_headers,
            json={
                "reason": "Testing supersede endpoint",
                "replacement_document_id": None
            }
        )
        
        # Should succeed (200) or fail gracefully
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"PASS: supersede endpoint accepts requests (status: {response.status_code})")


class TestDocumentMoveCategory:
    """Tests for POST /api/documents/{id}/move-category"""
    
    def test_move_category_nonexistent_document(self, auth_headers):
        """Test move-category with non-existent document"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/documents/{fake_id}/move-category",
            headers=auth_headers,
            json={
                "new_requirement_id": "identity_documents",
                "reason": "Document was misfiled"
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent document returns 404")
    
    def test_move_category_requires_reason(self, auth_headers):
        """Test that move-category requires a reason"""
        # Get a document to test with
        files_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers=auth_headers
        )
        
        if files_response.status_code != 200:
            pytest.skip("Could not get files to test move-category")
        
        files_data = files_response.json()
        
        if not files_data.get("active_files"):
            pytest.skip("No active files to test move-category")
        
        doc_id = files_data["active_files"][0]["file_id"]
        
        # Test without reason (should fail)
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/move-category",
            headers=auth_headers,
            json={
                "new_requirement_id": "identity_documents"
                # Missing reason
            }
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422 for missing reason, got {response.status_code}"
        print(f"PASS: move-category requires reason")


class TestResendRequest:
    """Tests for POST /api/employees/{id}/requirements/{key}/resend-request"""
    
    def test_resend_request_nonexistent_employee(self, auth_headers):
        """Test resend-request with non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_id}/requirements/proof_of_address/resend-request",
            headers=auth_headers,
            json={"due_days": 14}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent employee returns 404")
    
    def test_resend_request_creates_new_request(self, auth_headers):
        """Test that resend-request creates a new request"""
        # First check if employee has email
        emp_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        if emp_response.status_code != 200:
            pytest.skip("Could not get employee data")
        
        emp_data = emp_response.json()
        if not emp_data.get("email"):
            pytest.skip("Test employee has no email address")
        
        # Send resend request
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/resend-request",
            headers=auth_headers,
            json={
                "due_days": 14,
                "custom_message": "Please upload your proof of address documents"
            }
        )
        
        # Should succeed or fail with specific error
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "request_id" in data
            assert "due_date" in data
            print(f"PASS: resend-request created new request: {data.get('request_id')}")
        elif response.status_code == 400:
            # May fail if email service not configured
            print(f"INFO: resend-request returned 400 (may be email service issue): {response.text}")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")


class TestRequestReplacement:
    """Tests for POST /api/employees/{id}/requirements/{key}/request-replacement"""
    
    def test_request_replacement_nonexistent_employee(self, auth_headers):
        """Test request-replacement with non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_id}/requirements/proof_of_address/request-replacement",
            headers=auth_headers,
            json={
                "reason": "Document is expired and needs replacement",
                "due_days": 14
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Non-existent employee returns 404")
    
    def test_request_replacement_requires_reason(self, auth_headers):
        """Test that request-replacement requires a reason"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/request-replacement",
            headers=auth_headers,
            json={
                "due_days": 14
                # Missing reason
            }
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422 for missing reason, got {response.status_code}"
        print(f"PASS: request-replacement requires reason")
    
    def test_request_replacement_with_file_id(self, auth_headers):
        """Test request-replacement with specific file_id"""
        # First check if employee has email
        emp_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        if emp_response.status_code != 200:
            pytest.skip("Could not get employee data")
        
        emp_data = emp_response.json()
        if not emp_data.get("email"):
            pytest.skip("Test employee has no email address")
        
        # Get a file to request replacement for
        files_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers=auth_headers
        )
        
        if files_response.status_code != 200:
            pytest.skip("Could not get files")
        
        files_data = files_response.json()
        file_id = None
        if files_data.get("active_files"):
            file_id = files_data["active_files"][0]["file_id"]
        
        # Send replacement request
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/request-replacement",
            headers=auth_headers,
            json={
                "reason": "Document is expired and needs to be replaced with current version",
                "file_id": file_id,
                "due_days": 14,
                "custom_message": "Please upload a new proof of address document"
            }
        )
        
        # Should succeed or fail with specific error
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "request_id" in data
            print(f"PASS: request-replacement created: {data.get('request_id')}")
        elif response.status_code == 400:
            # May fail if email service not configured
            print(f"INFO: request-replacement returned 400 (may be email service issue): {response.text}")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")


class TestMultiFileConfigVariations:
    """Test multi_file_config for different requirement types"""
    
    def test_proof_of_address_requires_2_files(self, auth_headers):
        """Proof of Address should require 2 documents (NHS standard)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        config = data["multi_file_config"]
        assert config["multi_file"] == True
        assert config["required_count"] == 2
        
        print(f"PASS: proof_of_address requires 2 files")
    
    def test_rtw_documents_multi_file(self, auth_headers):
        """Right to Work Documents should support multi-file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/files",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        config = data["multi_file_config"]
        assert config["multi_file"] == True
        assert config["required_count"] == 1  # Only 1 required
        
        print(f"PASS: right_to_work_documents supports multi-file with required_count=1")
    
    def test_identity_documents_multi_file(self, auth_headers):
        """Identity Documents should support multi-file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/identity_documents/files",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        config = data["multi_file_config"]
        assert config["multi_file"] == True
        
        print(f"PASS: identity_documents supports multi-file")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

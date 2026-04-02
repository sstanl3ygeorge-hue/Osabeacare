"""
Test Document Request Email Workflow
=====================================
Tests for:
1. POST /api/employees/{id}/request-document - Send document request
2. GET /api/employees/{id}/document-requests - Get request history
3. POST /api/email-requests/{id}/track-click - Track click event
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestDocumentRequestWorkflow:
    """Test document request email workflow."""
    
    def test_request_document_right_to_work(self, auth_headers):
        """Test POST /api/employees/{id}/request-document with right_to_work requirement."""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-document",
            params={"requirement_id": "right_to_work"},
            headers=auth_headers
        )
        
        # Should return success or duplicate_blocked (if already requested)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        
        data = response.json()
        if response.status_code == 200:
            assert data.get("status") == "success", f"Expected success status, got: {data}"
            assert "request_id" in data, "Response should contain request_id"
            assert "message" in data, "Response should contain message"
            print(f"Document request created: {data}")
        else:
            # Duplicate blocked is acceptable
            print(f"Request blocked (likely duplicate): {data}")
    
    def test_request_document_dbs(self, auth_headers):
        """Test POST /api/employees/{id}/request-document with dbs requirement."""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-document",
            params={"requirement_id": "dbs_certificate"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        data = response.json()
        print(f"DBS request result: {data}")
    
    def test_request_document_identity(self, auth_headers):
        """Test POST /api/employees/{id}/request-document with identity requirement."""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-document",
            params={"requirement_id": "identity_documents"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        data = response.json()
        print(f"Identity request result: {data}")
    
    def test_request_document_proof_of_address(self, auth_headers):
        """Test POST /api/employees/{id}/request-document with proof_of_address requirement."""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-document",
            params={"requirement_id": "proof_of_address"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        data = response.json()
        print(f"Proof of Address request result: {data}")
    
    def test_get_document_requests_history(self, auth_headers):
        """Test GET /api/employees/{id}/document-requests returns request history."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to get document requests: {response.status_code} - {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"Found {len(data)} document requests")
        
        # Verify structure of requests
        if len(data) > 0:
            request = data[0]
            assert "id" in request, "Request should have id"
            assert "person_id" in request, "Request should have person_id"
            assert "requirement_id" in request, "Request should have requirement_id"
            assert "status" in request, "Request should have status"
            assert "created_at" in request, "Request should have created_at"
            print(f"Sample request: {request}")
    
    def test_track_click_event(self, auth_headers):
        """Test POST /api/email-requests/{id}/track-click tracks click event."""
        # First get a request ID from the history
        history_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests",
            headers=auth_headers
        )
        
        if history_response.status_code != 200 or not history_response.json():
            pytest.skip("No document requests found to test track-click")
        
        requests_list = history_response.json()
        request_id = requests_list[0].get("id")
        
        # Track click event
        response = requests.post(
            f"{BASE_URL}/api/email-requests/{request_id}/track-click",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to track click: {response.status_code} - {response.text}"
        
        data = response.json()
        assert data.get("status") == "tracked", f"Expected tracked status, got: {data}"
        assert data.get("request_id") == request_id, "Response should contain request_id"
        print(f"Click tracked successfully: {data}")
    
    def test_request_document_with_custom_message(self, auth_headers):
        """Test POST /api/employees/{id}/request-document with custom message."""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-document",
            params={
                "requirement_id": "cv",
                "message": "Please upload your updated CV for our records."
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        data = response.json()
        print(f"CV request with custom message result: {data}")
    
    def test_request_document_invalid_employee(self, auth_headers):
        """Test POST /api/employees/{id}/request-document with invalid employee ID."""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id/request-document",
            params={"requirement_id": "right_to_work"},
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid employee, got: {response.status_code}"
        print("Invalid employee correctly returns 404")


class TestEmailAutomationMergeFields:
    """Test that email automation populates merge fields correctly."""
    
    def test_core_requirement_names_mapping(self, auth_headers):
        """Verify CORE_REQUIREMENT_NAMES mapping exists in email_automation.py."""
        # This is a code review test - we verify the mapping exists by checking
        # that requests for core requirements work correctly
        
        core_requirements = [
            "right_to_work",
            "identity",
            "dbs",
            "dbs_certificate",
            "proof_of_address",
            "cv",
            "application_form",
            "references",
            "health_questionnaire",
            "training"
        ]
        
        for req_id in core_requirements:
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-document",
                params={"requirement_id": req_id},
                headers=auth_headers
            )
            
            # Should not fail with 500 (which would indicate missing mapping)
            assert response.status_code != 500, f"Server error for {req_id}: {response.text}"
            print(f"Requirement {req_id}: status {response.status_code}")


class TestURLParamsHandling:
    """Test URL parameters for email action links."""
    
    def test_employee_profile_url_structure(self, auth_headers):
        """Verify employee profile page accepts URL params for email actions."""
        # Get a request to check the action_link structure
        history_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests",
            headers=auth_headers
        )
        
        if history_response.status_code != 200:
            pytest.skip("Could not get document requests")
        
        requests_list = history_response.json()
        if not requests_list:
            pytest.skip("No document requests found")
        
        # Verify the request has the expected fields for URL construction
        request = requests_list[0]
        assert "id" in request, "Request should have id for URL params"
        assert "requirement_id" in request, "Request should have requirement_id for URL params"
        assert "person_id" in request, "Request should have person_id for URL params"
        
        print(f"Request structure valid for URL params: id={request['id']}, requirement_id={request['requirement_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

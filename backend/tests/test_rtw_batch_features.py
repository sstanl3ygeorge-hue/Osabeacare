"""
Test RTW Extraction and Batch Document Request Features

Tests:
1. RTW extraction endpoint `/api/rtw/extract` - works with images and PDFs
2. Batch document request endpoint `/api/employees/{id}/request-documents/batch`
3. Batch request creates single consolidated email content
"""

import pytest
import requests
import os
import base64
import json

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
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestRTWExtraction:
    """Tests for RTW extraction endpoint `/api/rtw/extract`."""
    
    def test_rtw_extract_endpoint_exists(self, api_client):
        """Test that RTW extraction endpoint exists and accepts requests."""
        # Use a minimal 1x1 PNG image for testing
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            params={"employee_id": TEST_EMPLOYEE_ID},
            json={
                "file_base64": test_image_base64,
                "file_type": "image/png"
            }
        )
        
        assert response.status_code == 200, f"RTW extract failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] is True, f"Extraction not successful: {data}"
        assert "extraction" in data, "Response missing 'extraction' field"
        
    def test_rtw_extract_returns_expected_fields(self, api_client):
        """Test that RTW extraction returns all expected fields."""
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            params={"employee_id": TEST_EMPLOYEE_ID},
            json={
                "file_base64": test_image_base64,
                "file_type": "image/png"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check extraction structure
        extraction = data.get("extraction", {})
        fields = extraction.get("fields", {})
        
        # Verify expected RTW fields are present
        expected_fields = [
            "holder_name", "document_type", "check_date", "reference_number",
            "permission_type", "permission_start_date", "permission_end_date",
            "share_code", "work_permitted", "restrictions", "hours_limit",
            "is_expired", "is_indefinite", "requires_followup"
        ]
        
        for field in expected_fields:
            assert field in fields, f"Missing expected field: {field}"
            
    def test_rtw_extract_includes_employee_name(self, api_client):
        """Test that RTW extraction includes employee name for validation."""
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            params={"employee_id": TEST_EMPLOYEE_ID},
            json={
                "file_base64": test_image_base64,
                "file_type": "image/png"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include employee name for name matching
        assert "employee_name" in data, "Response missing employee_name"
        assert data["employee_name"] is not None, "Employee name should not be None"
        
    def test_rtw_extract_handles_pdf_type(self, api_client):
        """Test that RTW extraction accepts PDF file type."""
        # Minimal PDF (will fail conversion but should accept the request)
        # This tests that the endpoint handles PDF type parameter
        test_pdf_base64 = base64.b64encode(b"%PDF-1.4 minimal").decode()
        
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            params={"employee_id": TEST_EMPLOYEE_ID},
            json={
                "file_base64": test_pdf_base64,
                "file_type": "application/pdf"
            }
        )
        
        # Should either succeed or return a proper error (not 500)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
    def test_rtw_extract_requires_file_or_document_id(self, api_client):
        """Test that RTW extraction requires either file_base64 or document_id."""
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            params={"employee_id": TEST_EMPLOYEE_ID},
            json={}
        )
        
        assert response.status_code == 400, "Should require file_base64 or document_id"


class TestBatchDocumentRequest:
    """Tests for batch document request endpoint."""
    
    def test_batch_request_endpoint_exists(self, api_client):
        """Test that batch request endpoint exists and accepts requests."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-documents/batch",
            json={
                "requirement_ids": ["test_req_1"],
                "requirements": [{"id": "test_req_1", "name": "Test Document"}],
                "due_days": 14
            }
        )
        
        assert response.status_code == 200, f"Batch request failed: {response.text}"
        data = response.json()
        assert "success" in data, "Response missing 'success' field"
        
    def test_batch_request_creates_single_record(self, api_client):
        """Test that batch request creates a single batch request record."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-documents/batch",
            json={
                "requirement_ids": ["rtw_check", "dbs_check", "id_check"],
                "requirements": [
                    {"id": "rtw_check", "name": "Right to Work", "description": "RTW proof"},
                    {"id": "dbs_check", "name": "DBS Certificate", "description": "Enhanced DBS"},
                    {"id": "id_check", "name": "ID Document", "description": "Photo ID"}
                ],
                "due_days": 7
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a single batch_request_id
        assert "batch_request_id" in data, "Response missing batch_request_id"
        assert data["batch_request_id"].startswith("batch_req_"), "Invalid batch request ID format"
        
        # Should report correct requirement count
        assert data.get("requirement_count") == 3, "Should report 3 requirements"
        
    def test_batch_request_includes_due_date(self, api_client):
        """Test that batch request includes due date in response."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-documents/batch",
            json={
                "requirement_ids": ["test_due_date"],
                "requirements": [{"id": "test_due_date", "name": "Test"}],
                "due_days": 21
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "due_date" in data, "Response missing due_date"
        assert data["due_date"] is not None, "Due date should not be None"
        
    def test_batch_request_with_custom_message(self, api_client):
        """Test that batch request accepts custom message."""
        custom_msg = "Please upload these documents urgently."
        
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-documents/batch",
            json={
                "requirement_ids": ["custom_msg_test"],
                "requirements": [{"id": "custom_msg_test", "name": "Test Doc"}],
                "custom_message": custom_msg,
                "due_days": 14
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        
    def test_batch_request_requires_requirements(self, api_client):
        """Test that batch request requires at least one requirement."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-documents/batch",
            json={
                "requirement_ids": [],
                "requirements": [],
                "due_days": 14
            }
        )
        
        assert response.status_code == 400, "Should reject empty requirements"
        
    def test_batch_request_reports_email_status(self, api_client):
        """Test that batch request reports email sent status."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-documents/batch",
            json={
                "requirement_ids": ["email_status_test"],
                "requirements": [{"id": "email_status_test", "name": "Test"}],
                "due_days": 14
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should report email_sent status (may be false if RESEND_API_KEY not configured)
        assert "email_sent" in data, "Response missing email_sent status"
        assert isinstance(data["email_sent"], bool), "email_sent should be boolean"
        
    def test_batch_request_invalid_employee(self, api_client):
        """Test that batch request returns 404 for invalid employee."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/request-documents/batch",
            json={
                "requirement_ids": ["test"],
                "requirements": [{"id": "test", "name": "Test"}],
                "due_days": 14
            }
        )
        
        assert response.status_code == 404, "Should return 404 for invalid employee"


class TestIntegration:
    """Integration tests for RTW and batch request features."""
    
    def test_employee_exists(self, api_client):
        """Verify test employee exists."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}")
        assert response.status_code == 200, f"Test employee not found: {response.text}"
        
    def test_employee_has_email(self, api_client):
        """Verify test employee has email for batch requests."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("email"), "Test employee should have email address"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

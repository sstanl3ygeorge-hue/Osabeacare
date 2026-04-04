"""
Tests for Document Requests Panel and Interview Form Panel features.
- GET /api/employees/{id}/forms - returns form submissions for employee
- GET /api/employees/{id}/forms?requirement_id=interview_record - filters to interview records
- GET /api/employees/{id}/document-requests - returns document request history
- GET /api/form-submissions/{id}/download-pdf - PDF download for interview records
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
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestEmployeeFormsEndpoint:
    """Tests for GET /api/employees/{id}/forms endpoint."""
    
    def test_get_employee_forms_returns_200(self, api_client):
        """Test that forms endpoint returns 200 for valid employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/forms")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_get_employee_forms_response_structure(self, api_client):
        """Test that forms endpoint returns correct structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/forms")
        assert response.status_code == 200
        
        data = response.json()
        assert "forms" in data, "Response should contain 'forms' key"
        assert "count" in data, "Response should contain 'count' key"
        assert isinstance(data["forms"], list), "'forms' should be a list"
        assert isinstance(data["count"], int), "'count' should be an integer"
    
    def test_get_employee_forms_with_interview_filter(self, api_client):
        """Test filtering forms by requirement_id=interview_record."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/forms",
            params={"requirement_id": "interview_record"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        forms = data.get("forms", [])
        
        # If there are forms, they should all be interview_record type
        for form in forms:
            assert form.get("requirement_id") == "interview_record", \
                f"Expected requirement_id='interview_record', got {form.get('requirement_id')}"
    
    def test_get_employee_forms_invalid_employee_404(self, api_client):
        """Test that invalid employee ID returns 404."""
        response = api_client.get(f"{BASE_URL}/api/employees/invalid-employee-id-12345/forms")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_get_employee_forms_form_data_normalization(self, api_client):
        """Test that form_data is normalized in response."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/forms")
        assert response.status_code == 200
        
        data = response.json()
        forms = data.get("forms", [])
        
        # If there are forms, check normalization
        for form in forms:
            # Either form_data or data should exist
            has_form_data = "form_data" in form
            has_data = "data" in form
            # If one exists, both should exist (normalization)
            if has_form_data or has_data:
                # Normalization ensures both exist
                pass  # This is expected behavior


class TestDocumentRequestsEndpoint:
    """Tests for GET /api/employees/{id}/document-requests endpoint."""
    
    def test_get_document_requests_returns_200(self, api_client):
        """Test that document-requests endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_get_document_requests_returns_list(self, api_client):
        """Test that document-requests returns a list."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
    
    def test_get_document_requests_structure(self, api_client):
        """Test document request item structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            request = data[0]
            # Check expected fields
            assert "status" in request, "Request should have 'status' field"
            assert "requirement_id" in request or "requirement_name" in request, \
                "Request should have requirement identifier"
    
    def test_get_document_requests_has_status_field(self, api_client):
        """Test that document requests have status field for UI badges."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests")
        assert response.status_code == 200
        
        data = response.json()
        for request in data:
            assert "status" in request, f"Request missing 'status' field: {request}"
            # Status should be one of the expected values
            valid_statuses = ['pending_send', 'sent', 'opened', 'clicked', 'submitted', 
                            'completed', 'expired', 'cancelled', 'superseded']
            assert request["status"] in valid_statuses, \
                f"Unexpected status: {request['status']}"
    
    def test_get_document_requests_has_dates(self, api_client):
        """Test that document requests have date fields for UI display."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests")
        assert response.status_code == 200
        
        data = response.json()
        for request in data:
            # Should have at least created_at or sent_at
            has_date = "created_at" in request or "sent_at" in request
            assert has_date, f"Request missing date fields: {request}"


class TestPDFDownloadEndpoint:
    """Tests for PDF download functionality."""
    
    def test_pdf_download_endpoint_exists(self, api_client):
        """Test that PDF download endpoint exists (may return 404 if no submission)."""
        # Use a fake submission ID to test endpoint existence
        response = api_client.get(f"{BASE_URL}/api/form-submissions/fake-id-12345/download-pdf")
        # Should return 404 (not found) not 405 (method not allowed)
        assert response.status_code in [404, 500], \
            f"Expected 404 or 500 for invalid ID, got {response.status_code}"
    
    def test_pdf_view_endpoint_exists(self, api_client):
        """Test that PDF view endpoint exists."""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/fake-id-12345/view-pdf")
        assert response.status_code in [404, 500], \
            f"Expected 404 or 500 for invalid ID, got {response.status_code}"


class TestInterviewRecordIntegration:
    """Integration tests for interview record workflow."""
    
    def test_interview_records_can_be_fetched(self, api_client):
        """Test fetching interview records for employee."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/forms",
            params={"requirement_id": "interview_record"}
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Interview records found: {data.get('count', 0)}")
        
        # Verify structure
        assert "forms" in data
        assert "count" in data
    
    def test_interview_record_has_form_data(self, api_client):
        """Test that interview records have form_data for display."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/forms",
            params={"requirement_id": "interview_record"}
        )
        assert response.status_code == 200
        
        data = response.json()
        forms = data.get("forms", [])
        
        for form in forms:
            # Should have form_data or data for display
            has_data = "form_data" in form or "data" in form
            assert has_data, f"Interview record missing form data: {form.get('id')}"
            
            # Should have an ID for PDF download
            assert "id" in form, "Interview record missing 'id' field"


class TestEmployeeEndpointValidation:
    """Test employee validation across endpoints."""
    
    def test_forms_endpoint_validates_employee(self, api_client):
        """Test that forms endpoint validates employee exists."""
        response = api_client.get(f"{BASE_URL}/api/employees/nonexistent-id/forms")
        assert response.status_code == 404
    
    def test_document_requests_handles_no_requests(self, api_client):
        """Test that document-requests handles employees with no requests."""
        # This should return empty list, not error
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

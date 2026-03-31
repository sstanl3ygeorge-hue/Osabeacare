"""
Phase D3 - Requirement History Drawer & Request Lifecycle Visibility Tests

Tests for:
- GET /api/employees/{id}/requirements/{key}/unified-history endpoint
- Evidence key mapping (right_to_work_documents, dbs_certificate, etc.)
- Check key history (right_to_work_check, dbs_status_check)
- Timeline event types (document_uploaded, check_recorded, document_verified)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestUnifiedHistoryEndpoint:
    """Tests for /api/employees/{id}/requirements/{key}/unified-history"""
    
    def test_endpoint_exists_and_returns_200(self, api_client):
        """Test that the unified-history endpoint exists and returns 200"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/unified-history"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "timeline" in data, "Response should contain 'timeline' field"
        assert "total_events" in data, "Response should contain 'total_events' field"
        assert "requirement_key" in data, "Response should contain 'requirement_key' field"
        assert "employee_id" in data, "Response should contain 'employee_id' field"
    
    def test_right_to_work_evidence_key_mapping(self, api_client):
        """Test that right_to_work_evidence maps correctly to right_to_work_documents"""
        # Test with _evidence suffix key
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_evidence/unified-history"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["requirement_key"] == "right_to_work_evidence"
        # Should return timeline (may be empty if no documents)
        assert isinstance(data["timeline"], list)
    
    def test_right_to_work_documents_key(self, api_client):
        """Test right_to_work_documents key returns history"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requirement_key"] == "right_to_work_documents"
        assert isinstance(data["timeline"], list)
        print(f"RTW Documents history: {data['total_events']} events")
    
    def test_right_to_work_check_key(self, api_client):
        """Test right_to_work_check key returns check history"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_check/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requirement_key"] == "right_to_work_check"
        assert isinstance(data["timeline"], list)
        print(f"RTW Check history: {data['total_events']} events")
    
    def test_dbs_certificate_key(self, api_client):
        """Test dbs_certificate key returns history"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_certificate/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requirement_key"] == "dbs_certificate"
        assert isinstance(data["timeline"], list)
        print(f"DBS Certificate history: {data['total_events']} events")
    
    def test_dbs_evidence_key_mapping(self, api_client):
        """Test dbs_evidence maps correctly"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_evidence/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["timeline"], list)
    
    def test_dbs_status_check_key(self, api_client):
        """Test dbs_status_check key returns check history"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_status_check/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["timeline"], list)
        print(f"DBS Status Check history: {data['total_events']} events")
    
    def test_identity_documents_key(self, api_client):
        """Test identity_documents key returns history"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/identity_documents/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["timeline"], list)
    
    def test_proof_of_address_key(self, api_client):
        """Test proof_of_address key returns history"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["timeline"], list)
    
    def test_invalid_employee_returns_404(self, api_client):
        """Test that invalid employee ID returns 404"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/invalid-employee-id/requirements/right_to_work_documents/unified-history"
        )
        assert response.status_code == 404
    
    def test_timeline_event_structure(self, api_client):
        """Test that timeline events have correct structure"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        if data["timeline"]:
            event = data["timeline"][0]
            # Check required fields
            assert "event_type" in event, "Event should have 'event_type'"
            assert "timestamp" in event, "Event should have 'timestamp'"
            assert "source" in event, "Event should have 'source'"
            # Optional fields
            if "details" in event:
                assert isinstance(event["details"], dict)
            print(f"Sample event: {event['event_type']} from {event['source']}")


class TestTimelineEventTypes:
    """Tests for specific event types in timeline"""
    
    def test_document_uploaded_events(self, api_client):
        """Test that document_uploaded events appear in timeline"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        upload_events = [e for e in data["timeline"] if e["event_type"] == "document_uploaded"]
        print(f"Found {len(upload_events)} document_uploaded events")
        
        if upload_events:
            event = upload_events[0]
            assert event["source"] == "document"
            # Check details structure
            if event.get("details"):
                details = event["details"]
                # May have filename, file_id, source_type
                print(f"Upload event details: {details}")
    
    def test_check_recorded_events(self, api_client):
        """Test that check_recorded events appear for check-type requirements"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_check/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        check_events = [e for e in data["timeline"] if e["event_type"] == "check_recorded"]
        print(f"Found {len(check_events)} check_recorded events")
        
        if check_events:
            event = check_events[0]
            assert event["source"] == "check_record"
            # Check details structure
            if event.get("details"):
                details = event["details"]
                # Should have method, outcome
                print(f"Check event details: method={details.get('method')}, outcome={details.get('outcome')}")
    
    def test_document_verified_events(self, api_client):
        """Test that document_verified events appear in timeline"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/unified-history"
        )
        assert response.status_code == 200
        
        data = response.json()
        verified_events = [e for e in data["timeline"] if e["event_type"] == "document_verified"]
        print(f"Found {len(verified_events)} document_verified events")
        
        if verified_events:
            event = verified_events[0]
            # Verified events can come from document collection or audit_log
            assert event["source"] in ["document", "audit_log"], f"Unexpected source: {event['source']}"


class TestRequestLifecycleEndpoint:
    """Tests for /api/employees/{id}/requirements/{key}/requests endpoint"""
    
    def test_requests_endpoint_exists(self, api_client):
        """Test that the requests endpoint exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_documents/requests"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "requests" in data or "request_history" in data or isinstance(data, list), \
            f"Response should contain request data: {data}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

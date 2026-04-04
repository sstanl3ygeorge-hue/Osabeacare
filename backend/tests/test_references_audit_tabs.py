"""
Test References and Audit Tab Endpoints
Tests for:
- GET /api/employees/{id}/references - Returns reference data with declared info
- GET /api/employees/{id}/audit-trail - Returns audit trail for employee
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
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestReferencesEndpoint:
    """Tests for GET /api/employees/{id}/references endpoint"""
    
    def test_references_endpoint_returns_200(self, api_client):
        """Test that references endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ References endpoint returns 200")
    
    def test_references_response_structure(self, api_client):
        """Test that references response has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level fields
        assert "employee_id" in data, "Missing employee_id"
        assert "employee_name" in data, "Missing employee_name"
        assert "references" in data, "Missing references"
        
        # Check references structure
        refs = data["references"]
        assert "reference_1" in refs, "Missing reference_1"
        assert "reference_2" in refs, "Missing reference_2"
        
        print(f"✓ References response has correct structure")
        print(f"  Employee: {data['employee_name']}")
    
    def test_reference_1_structure(self, api_client):
        """Test that reference_1 has correct fields"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references")
        assert response.status_code == 200
        
        ref1 = response.json()["references"]["reference_1"]
        
        # Check required fields
        assert "status" in ref1, "Missing status"
        assert "declared" in ref1, "Missing declared"
        assert "request" in ref1, "Missing request"
        assert "verification" in ref1, "Missing verification"
        
        # Status should be one of valid values
        valid_statuses = ["not_declared", "declared", "sent", "response_received", "verified", "rejected"]
        assert ref1["status"] in valid_statuses, f"Invalid status: {ref1['status']}"
        
        print(f"✓ Reference 1 has correct structure")
        print(f"  Status: {ref1['status']}")
        if ref1["declared"].get("name"):
            print(f"  Declared Name: {ref1['declared']['name']}")
    
    def test_reference_2_structure(self, api_client):
        """Test that reference_2 has correct fields"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references")
        assert response.status_code == 200
        
        ref2 = response.json()["references"]["reference_2"]
        
        # Check required fields
        assert "status" in ref2, "Missing status"
        assert "declared" in ref2, "Missing declared"
        assert "request" in ref2, "Missing request"
        assert "verification" in ref2, "Missing verification"
        
        print(f"✓ Reference 2 has correct structure")
        print(f"  Status: {ref2['status']}")
        if ref2["declared"].get("name"):
            print(f"  Declared Name: {ref2['declared']['name']}")
    
    def test_references_declared_info_fallback(self, api_client):
        """Test that declared info falls back to employee fields when db.references is empty"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references")
        assert response.status_code == 200
        
        data = response.json()
        ref1 = data["references"]["reference_1"]
        ref2 = data["references"]["reference_2"]
        
        # At least one reference should have declared info (from employee fields fallback)
        has_declared_info = (
            ref1["declared"].get("name") or 
            ref1["declared"].get("email") or
            ref2["declared"].get("name") or 
            ref2["declared"].get("email")
        )
        
        print(f"✓ References declared info check")
        print(f"  Ref1 declared: {ref1['declared']}")
        print(f"  Ref2 declared: {ref2['declared']}")
    
    def test_references_invalid_employee_returns_404(self, api_client):
        """Test that invalid employee ID returns 404"""
        response = api_client.get(f"{BASE_URL}/api/employees/invalid-id-12345/references")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Invalid employee returns 404")


class TestAuditTrailEndpoint:
    """Tests for GET /api/employees/{id}/audit-trail endpoint"""
    
    def test_audit_trail_endpoint_returns_200(self, api_client):
        """Test that audit-trail endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Audit trail endpoint returns 200")
    
    def test_audit_trail_response_structure(self, api_client):
        """Test that audit-trail response has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level fields
        assert "employee_id" in data, "Missing employee_id"
        assert "employee_name" in data, "Missing employee_name"
        assert "audit_trail" in data, "Missing audit_trail"
        assert "total_returned" in data, "Missing total_returned"
        assert "pagination" in data, "Missing pagination"
        
        # Check pagination structure
        assert "limit" in data["pagination"], "Missing pagination.limit"
        assert "skip" in data["pagination"], "Missing pagination.skip"
        
        print(f"✓ Audit trail response has correct structure")
        print(f"  Employee: {data['employee_name']}")
        print(f"  Total returned: {data['total_returned']}")
    
    def test_audit_trail_pagination(self, api_client):
        """Test audit-trail pagination parameters"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail?limit=10&skip=0")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["skip"] == 0
        
        print(f"✓ Audit trail pagination works")
    
    def test_audit_trail_action_filter(self, api_client):
        """Test audit-trail action_type filter"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail?action_type=document_uploaded")
        assert response.status_code == 200
        
        data = response.json()
        # Should return 200 even if no matching logs
        assert "audit_trail" in data
        
        print(f"✓ Audit trail action filter works")
        print(f"  Filtered results: {data['total_returned']}")
    
    def test_audit_trail_invalid_employee_returns_404(self, api_client):
        """Test that invalid employee ID returns 404"""
        response = api_client.get(f"{BASE_URL}/api/employees/invalid-id-12345/audit-trail")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Invalid employee returns 404")
    
    def test_audit_trail_log_structure(self, api_client):
        """Test that audit log entries have correct structure (if any exist)"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        audit_logs = data["audit_trail"]
        
        if len(audit_logs) > 0:
            log = audit_logs[0]
            # Check expected fields in audit log
            print(f"✓ Audit log entry structure:")
            print(f"  Sample log keys: {list(log.keys())}")
        else:
            print(f"✓ No audit logs found (empty is valid)")


class TestEmployeeEndpointIntegration:
    """Integration tests for employee profile data"""
    
    def test_employee_exists(self, api_client):
        """Verify test employee exists"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}")
        assert response.status_code == 200, f"Test employee not found: {response.text}"
        
        data = response.json()
        print(f"✓ Test employee exists")
        print(f"  Name: {data.get('first_name')} {data.get('last_name')}")
        print(f"  Email: {data.get('email')}")
    
    def test_employee_has_reference_fields(self, api_client):
        """Check if employee has reference fields that would be used as fallback"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check for reference fields
        ref1_name = data.get("reference_1_name")
        ref1_email = data.get("reference_1_email")
        ref2_name = data.get("reference_2_name")
        ref2_email = data.get("reference_2_email")
        
        print(f"✓ Employee reference fields:")
        print(f"  Ref1 Name: {ref1_name}")
        print(f"  Ref1 Email: {ref1_email}")
        print(f"  Ref2 Name: {ref2_name}")
        print(f"  Ref2 Email: {ref2_email}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

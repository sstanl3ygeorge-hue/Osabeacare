"""
Test suite for Recurring Compliance Engine features:
- Dashboard summary endpoint
- Employee recurring compliance items
- Record completion modal
- Document request endpoints
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"

# Test employee IDs from the problem statement
EMPLOYEE_OLAKUNLE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"
EMPLOYEE_LAWRENCE_ID = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    # API returns 'token' not 'access_token'
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


class TestRecurringComplianceDashboardSummary:
    """Tests for GET /api/recurring-compliance/dashboard-summary endpoint."""
    
    def test_dashboard_summary_returns_200(self, api_client):
        """Dashboard summary endpoint should return 200."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance/dashboard-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_dashboard_summary_structure(self, api_client):
        """Dashboard summary should have correct structure."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance/dashboard-summary")
        assert response.status_code == 200
        data = response.json()
        
        # Check summary object exists
        assert "summary" in data, "Missing 'summary' in response"
        summary = data["summary"]
        
        # Check required fields in summary
        assert "overdue" in summary, "Missing 'overdue' in summary"
        assert "due" in summary, "Missing 'due' in summary"
        assert "upcoming" in summary, "Missing 'upcoming' in summary"
        assert "total_active" in summary, "Missing 'total_active' in summary"
        
        # Check item lists exist
        assert "overdue_items" in data, "Missing 'overdue_items' in response"
        assert "due_items" in data, "Missing 'due_items' in response"
        assert "upcoming_items" in data, "Missing 'upcoming_items' in response"
        
        # Verify types
        assert isinstance(summary["overdue"], int)
        assert isinstance(summary["due"], int)
        assert isinstance(summary["upcoming"], int)
        assert isinstance(data["overdue_items"], list)
        assert isinstance(data["due_items"], list)
        assert isinstance(data["upcoming_items"], list)
    
    def test_dashboard_summary_item_structure(self, api_client):
        """Items in dashboard summary should have employee_name and item_name."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance/dashboard-summary")
        assert response.status_code == 200
        data = response.json()
        
        # Check any items that exist
        all_items = data.get("overdue_items", []) + data.get("due_items", []) + data.get("upcoming_items", [])
        
        for item in all_items:
            assert "employee_name" in item, f"Missing employee_name in item: {item}"
            assert "item_name" in item, f"Missing item_name in item: {item}"
            assert "employee_id" in item, f"Missing employee_id in item: {item}"
            assert "computed_status" in item, f"Missing computed_status in item: {item}"


class TestEmployeeRecurringCompliance:
    """Tests for GET /api/employees/{id}/recurring-compliance endpoint."""
    
    def test_employee_recurring_compliance_returns_200(self, api_client):
        """Employee recurring compliance endpoint should return 200."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE_ID}/recurring-compliance")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_employee_recurring_compliance_structure(self, api_client):
        """Employee recurring compliance should have correct structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE_ID}/recurring-compliance")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "employee_id" in data, "Missing 'employee_id' in response"
        assert "summary" in data, "Missing 'summary' in response"
        assert "items" in data, "Missing 'items' in response"
        
        # Check summary structure
        summary = data["summary"]
        assert "total" in summary, "Missing 'total' in summary"
        assert "overdue" in summary, "Missing 'overdue' in summary"
        assert "due" in summary, "Missing 'due' in summary"
        assert "upcoming" in summary, "Missing 'upcoming' in summary"
        
        # Verify employee_id matches
        assert data["employee_id"] == EMPLOYEE_OLAKUNLE_ID
    
    def test_employee_recurring_compliance_item_structure(self, api_client):
        """Items should have required fields for UI display."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE_ID}/recurring-compliance")
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        for item in items:
            # Required fields for RecurringComplianceSection component
            assert "id" in item, f"Missing 'id' in item"
            assert "item_name" in item, f"Missing 'item_name' in item"
            assert "item_type" in item, f"Missing 'item_type' in item"
            assert "frequency" in item, f"Missing 'frequency' in item"
            assert "next_due_date" in item, f"Missing 'next_due_date' in item"
            assert "computed_status" in item, f"Missing 'computed_status' in item"
            
            # Verify computed_status is valid
            valid_statuses = ["overdue", "due", "upcoming", "scheduled", "completed"]
            assert item["computed_status"] in valid_statuses, f"Invalid status: {item['computed_status']}"
    
    def test_employee_not_found_returns_404(self, api_client):
        """Non-existent employee should return 404."""
        response = api_client.get(f"{BASE_URL}/api/employees/non-existent-id/recurring-compliance")
        assert response.status_code == 404


class TestRecordCompletion:
    """Tests for POST /api/recurring-compliance/{id}/complete endpoint."""
    
    def test_record_completion_requires_auth(self):
        """Record completion should require authentication."""
        response = requests.post(f"{BASE_URL}/api/recurring-compliance/test-id/complete", json={
            "completed_date": "2025-01-15",
            "outcome": "satisfactory",
            "notes": "Test completion"
        })
        assert response.status_code == 401 or response.status_code == 403
    
    def test_record_completion_invalid_item_returns_404(self, api_client):
        """Non-existent item should return 404."""
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance/non-existent-id/complete", json={
            "completed_date": "2025-01-15",
            "outcome": "satisfactory",
            "notes": "Test completion"
        })
        assert response.status_code == 404
    
    def test_record_completion_invalid_outcome_returns_400(self, api_client):
        """Invalid outcome should return 400."""
        # First get a valid item ID
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE_ID}/recurring-compliance")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                item_id = items[0]["id"]
                response = api_client.post(f"{BASE_URL}/api/recurring-compliance/{item_id}/complete", json={
                    "completed_date": "2025-01-15",
                    "outcome": "invalid_outcome",
                    "notes": "Test completion"
                })
                assert response.status_code == 400, f"Expected 400 for invalid outcome, got {response.status_code}"


class TestDocumentRequest:
    """Tests for POST /api/employees/{id}/request-document endpoint."""
    
    def test_request_document_requires_auth(self):
        """Request document should require authentication."""
        response = requests.post(
            f"{BASE_URL}/api/employees/{EMPLOYEE_LAWRENCE_ID}/request-document",
            params={"requirement_id": "test-req"}
        )
        assert response.status_code == 401 or response.status_code == 403
    
    def test_request_document_employee_not_found(self, api_client):
        """Non-existent employee should return 404."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/non-existent-id/request-document",
            params={"requirement_id": "test-req"}
        )
        assert response.status_code == 404
    
    def test_request_document_endpoint_exists(self, api_client):
        """Request document endpoint should exist and accept requests."""
        # Get compliance requirements to find a valid requirement_id
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_LAWRENCE_ID}/compliance-requirements")
        if response.status_code == 200:
            data = response.json()
            requirements = data.get("requirements", [])
            # Find a missing requirement
            missing_reqs = [r for r in requirements if r.get("status") in ["missing", "not_started", "required"]]
            if missing_reqs:
                req_id = missing_reqs[0]["id"]
                response = api_client.post(
                    f"{BASE_URL}/api/employees/{EMPLOYEE_LAWRENCE_ID}/request-document",
                    params={"requirement_id": req_id, "message": "Test request", "due_days": 14}
                )
                # Should return 200 or 500 (if email service not configured)
                assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"


class TestRequestMissingItems:
    """Tests for POST /api/employees/{id}/request-missing-items endpoint."""
    
    def test_request_missing_items_requires_auth(self):
        """Request missing items should require authentication."""
        response = requests.post(f"{BASE_URL}/api/employees/{EMPLOYEE_LAWRENCE_ID}/request-missing-items")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_request_missing_items_employee_not_found(self, api_client):
        """Non-existent employee should return 404."""
        response = api_client.post(f"{BASE_URL}/api/employees/non-existent-id/request-missing-items")
        assert response.status_code == 404
    
    def test_request_missing_items_endpoint_exists(self, api_client):
        """Request missing items endpoint should exist."""
        response = api_client.post(f"{BASE_URL}/api/employees/{EMPLOYEE_LAWRENCE_ID}/request-missing-items")
        # Should return 200 (success or no_action) or 500 (email service error)
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Missing 'status' in response"


class TestRecurringComplianceList:
    """Tests for GET /api/recurring-compliance endpoint."""
    
    def test_recurring_compliance_list_returns_200(self, api_client):
        """Recurring compliance list endpoint should return 200."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance")
        assert response.status_code == 200
    
    def test_recurring_compliance_list_filter_by_employee(self, api_client):
        """Should filter by employee_id."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance", params={
            "employee_id": EMPLOYEE_OLAKUNLE_ID
        })
        assert response.status_code == 200
        data = response.json()
        
        # All items should belong to the specified employee
        for item in data:
            assert item.get("employee_id") == EMPLOYEE_OLAKUNLE_ID
    
    def test_recurring_compliance_list_filter_by_type(self, api_client):
        """Should filter by item_type."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance", params={
            "item_type": "supervision"
        })
        assert response.status_code == 200
        data = response.json()
        
        # All items should be of the specified type
        for item in data:
            assert item.get("item_type") == "supervision"


class TestCreateRecurringItem:
    """Tests for POST /api/recurring-compliance endpoint."""
    
    def test_create_recurring_item_requires_auth(self):
        """Create recurring item should require authentication."""
        response = requests.post(f"{BASE_URL}/api/recurring-compliance", json={
            "employee_id": EMPLOYEE_OLAKUNLE_ID,
            "item_type": "supervision",
            "next_due_date": "2025-02-01"
        })
        assert response.status_code == 401 or response.status_code == 403
    
    def test_create_recurring_item_invalid_employee(self, api_client):
        """Invalid employee should return 404 or 422 (validation error)."""
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json={
            "employee_id": "non-existent-id",
            "item_type": "supervision",
            "next_due_date": "2025-02-01"
        })
        # 404 if employee lookup fails, 422 if Pydantic validation fails first
        assert response.status_code in [404, 422]
    
    def test_create_recurring_item_invalid_type(self, api_client):
        """Invalid item_type should return 400 or 422 (validation error)."""
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json={
            "employee_id": EMPLOYEE_OLAKUNLE_ID,
            "item_type": "invalid_type",
            "next_due_date": "2025-02-01"
        })
        # 400 if business logic rejects, 422 if Pydantic validation fails first
        assert response.status_code in [400, 422]


class TestGetSingleRecurringItem:
    """Tests for GET /api/recurring-compliance/{item_id} endpoint."""
    
    def test_get_single_item_not_found(self, api_client):
        """Non-existent item should return 404."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance/non-existent-id")
        assert response.status_code == 404
    
    def test_get_single_item_structure(self, api_client):
        """Single item should have full details including employee_name."""
        # First get a valid item ID
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE_ID}/recurring-compliance")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                item_id = items[0]["id"]
                response = api_client.get(f"{BASE_URL}/api/recurring-compliance/{item_id}")
                assert response.status_code == 200
                item = response.json()
                
                # Check for enriched fields
                assert "employee_name" in item, "Missing employee_name"
                assert "assigned_to_name" in item, "Missing assigned_to_name"
                assert "computed_status" in item, "Missing computed_status"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

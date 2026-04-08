"""
Phase 25: Recurring Compliance Routes Extraction Tests

Tests all 8 endpoints extracted from server.py to routes/recurring_compliance.py:
1. POST /api/recurring-compliance - Create recurring compliance item
2. GET /api/recurring-compliance - List all recurring compliance items with filters
3. GET /api/recurring-compliance/dashboard-summary - Organization-wide summary
4. GET /api/recurring-compliance/{item_id} - Get single item with history
5. PUT /api/recurring-compliance/{item_id} - Update recurring item
6. POST /api/recurring-compliance/{item_id}/complete - Record completion
7. GET /api/employees/{employee_id}/recurring-compliance - Employee-specific items
8. POST /api/recurring-compliance/process-reminders - Process reminders (admin only)

Valid item_types: supervision, competency_assessment, spot_check, training_refresh, report_followup
Valid outcomes: satisfactory, needs_improvement, action_required, not_applicable
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

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


@pytest.fixture(scope="module")
def admin_user_id(api_client):
    """Get admin user ID for assigned_to field."""
    response = api_client.get(f"{BASE_URL}/api/users")
    if response.status_code == 200:
        users = response.json()
        for user in users:
            if user.get("email") == ADMIN_EMAIL:
                return user.get("user_id")
    return "admin-user-id"


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


# ==================== ENDPOINT 1: POST /api/recurring-compliance ====================

class TestCreateRecurringItem:
    """Tests for POST /api/recurring-compliance endpoint."""
    
    def test_create_supervision_item(self, api_client, admin_user_id):
        """Create a supervision recurring item."""
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "supervision",
            "item_name": f"TEST_Phase25_Supervision_{uuid.uuid4().hex[:8]}",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Missing id in response"
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert data["item_type"] == "supervision"
        assert "computed_status" in data
        print(f"✓ Created supervision item: {data['id']}")
        return data["id"]
    
    def test_create_competency_assessment_item(self, api_client, admin_user_id):
        """Create a competency_assessment recurring item."""
        future_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "competency_assessment",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert data["item_type"] == "competency_assessment"
        assert data["frequency"] == "six_monthly"  # Default frequency
        print(f"✓ Created competency_assessment item: {data['id']}")
    
    def test_create_spot_check_item(self, api_client, admin_user_id):
        """Create a spot_check recurring item."""
        future_date = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
        payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "spot_check",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert data["item_type"] == "spot_check"
        print(f"✓ Created spot_check item: {data['id']}")
    
    def test_create_training_refresh_item(self, api_client, admin_user_id):
        """Create a training_refresh recurring item."""
        future_date = (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
        payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "training_refresh",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert data["item_type"] == "training_refresh"
        assert data["frequency"] == "annual"  # Default frequency
        print(f"✓ Created training_refresh item: {data['id']}")
    
    def test_create_report_followup_requires_linked_id(self, api_client, admin_user_id):
        """report_followup requires linked_report_id or linked_incident_id."""
        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "report_followup",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ report_followup validation works - requires linked_report_id or linked_incident_id")
    
    def test_create_report_followup_with_linked_id(self, api_client, admin_user_id):
        """Create report_followup with linked_report_id."""
        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "report_followup",
            "next_due_date": future_date,
            "assigned_to": admin_user_id,
            "linked_report_id": "test-report-123"
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert data["item_type"] == "report_followup"
        assert data["linked_report_id"] == "test-report-123"
        print(f"✓ Created report_followup item: {data['id']}")
    
    def test_create_invalid_item_type(self, api_client, admin_user_id):
        """Invalid item_type should return 400."""
        payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "invalid_type",
            "next_due_date": "2026-05-01",
            "assigned_to": admin_user_id
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid item_type validation works")
    
    def test_create_invalid_employee(self, api_client, admin_user_id):
        """Invalid employee_id should return 404."""
        payload = {
            "employee_id": "non-existent-employee",
            "item_type": "supervision",
            "next_due_date": "2026-05-01",
            "assigned_to": admin_user_id
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=payload)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid employee validation works")


# ==================== ENDPOINT 2: GET /api/recurring-compliance ====================

class TestListRecurringItems:
    """Tests for GET /api/recurring-compliance endpoint."""
    
    def test_list_all_items(self, api_client):
        """List all recurring compliance items."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance")
        assert response.status_code == 200, f"List failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} recurring compliance items")
    
    def test_filter_by_employee_id(self, api_client):
        """Filter by employee_id."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance", params={
            "employee_id": TEST_EMPLOYEE_ID
        })
        assert response.status_code == 200
        
        data = response.json()
        for item in data:
            assert item["employee_id"] == TEST_EMPLOYEE_ID
        print(f"✓ Filtered by employee_id: {len(data)} items")
    
    def test_filter_by_item_type(self, api_client):
        """Filter by item_type."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance", params={
            "item_type": "supervision"
        })
        assert response.status_code == 200
        
        data = response.json()
        for item in data:
            assert item["item_type"] == "supervision"
        print(f"✓ Filtered by item_type=supervision: {len(data)} items")
    
    def test_filter_by_status(self, api_client):
        """Filter by computed status."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance", params={
            "status": "scheduled"
        })
        assert response.status_code == 200
        
        data = response.json()
        for item in data:
            assert item["computed_status"] == "scheduled"
        print(f"✓ Filtered by status=scheduled: {len(data)} items")
    
    def test_include_inactive(self, api_client):
        """Include inactive items."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance", params={
            "include_inactive": True
        })
        assert response.status_code == 200
        print("✓ include_inactive parameter works")


# ==================== ENDPOINT 3: GET /api/recurring-compliance/dashboard-summary ====================

class TestDashboardSummary:
    """Tests for GET /api/recurring-compliance/dashboard-summary endpoint."""
    
    def test_dashboard_summary_structure(self, api_client):
        """Dashboard summary should have correct structure."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance/dashboard-summary")
        assert response.status_code == 200, f"Dashboard summary failed: {response.text}"
        
        data = response.json()
        
        # Check summary object
        assert "summary" in data
        summary = data["summary"]
        assert "overdue" in summary
        assert "due" in summary
        assert "upcoming" in summary
        assert "total_active" in summary
        
        # Check item lists
        assert "overdue_items" in data
        assert "due_items" in data
        assert "upcoming_items" in data
        
        assert isinstance(data["overdue_items"], list)
        assert isinstance(data["due_items"], list)
        assert isinstance(data["upcoming_items"], list)
        
        print(f"✓ Dashboard summary: overdue={summary['overdue']}, due={summary['due']}, upcoming={summary['upcoming']}")
    
    def test_dashboard_items_have_employee_name(self, api_client):
        """Dashboard items should include employee_name."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance/dashboard-summary")
        assert response.status_code == 200
        
        data = response.json()
        all_items = data["overdue_items"] + data["due_items"] + data["upcoming_items"]
        
        for item in all_items:
            assert "employee_name" in item, f"Missing employee_name in item: {item.get('id')}"
            assert "item_name" in item
            assert "computed_status" in item
        
        print(f"✓ All {len(all_items)} dashboard items have employee_name")


# ==================== ENDPOINT 4: GET /api/recurring-compliance/{item_id} ====================

class TestGetSingleItem:
    """Tests for GET /api/recurring-compliance/{item_id} endpoint."""
    
    def test_get_single_item(self, api_client):
        """Get a single recurring compliance item with full details."""
        # First get an item ID
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance", params={
            "employee_id": TEST_EMPLOYEE_ID
        })
        assert response.status_code == 200
        items = response.json()
        
        if items:
            item_id = items[0]["id"]
            response = api_client.get(f"{BASE_URL}/api/recurring-compliance/{item_id}")
            assert response.status_code == 200, f"Get single item failed: {response.text}"
            
            data = response.json()
            assert data["id"] == item_id
            assert "employee_name" in data
            assert "assigned_to_name" in data
            assert "computed_status" in data
            assert "completion_history" in data
            print(f"✓ Got single item with employee_name={data['employee_name']}")
        else:
            pytest.skip("No items found for test employee")
    
    def test_get_nonexistent_item(self, api_client):
        """Non-existent item should return 404."""
        response = api_client.get(f"{BASE_URL}/api/recurring-compliance/non-existent-id")
        assert response.status_code == 404
        print("✓ Non-existent item returns 404")


# ==================== ENDPOINT 5: PUT /api/recurring-compliance/{item_id} ====================

class TestUpdateRecurringItem:
    """Tests for PUT /api/recurring-compliance/{item_id} endpoint."""
    
    def test_update_item_name(self, api_client, admin_user_id):
        """Update item_name."""
        # Create a test item first
        future_date = (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d')
        create_payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "supervision",
            "item_name": "TEST_Update_Original",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        create_response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=create_payload)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Update the item
        update_payload = {
            "item_name": "TEST_Update_Modified"
        }
        response = api_client.put(f"{BASE_URL}/api/recurring-compliance/{item_id}", json=update_payload)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        data = response.json()
        assert data["item_name"] == "TEST_Update_Modified"
        print(f"✓ Updated item_name for {item_id}")
    
    def test_update_next_due_date(self, api_client, admin_user_id):
        """Update next_due_date."""
        # Create a test item
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        create_payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "spot_check",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        create_response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=create_payload)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Update due date
        new_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        update_payload = {
            "next_due_date": new_date
        }
        response = api_client.put(f"{BASE_URL}/api/recurring-compliance/{item_id}", json=update_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["next_due_date"] == new_date
        print(f"✓ Updated next_due_date for {item_id}")
    
    def test_update_is_active(self, api_client, admin_user_id):
        """Update is_active to deactivate item."""
        # Create a test item
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        create_payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "supervision",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        create_response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=create_payload)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Deactivate
        update_payload = {
            "is_active": False
        }
        response = api_client.put(f"{BASE_URL}/api/recurring-compliance/{item_id}", json=update_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_active"] == False
        print(f"✓ Deactivated item {item_id}")
    
    def test_update_nonexistent_item(self, api_client):
        """Update non-existent item should return 404."""
        response = api_client.put(f"{BASE_URL}/api/recurring-compliance/non-existent-id", json={
            "item_name": "Test"
        })
        assert response.status_code == 404
        print("✓ Update non-existent item returns 404")


# ==================== ENDPOINT 6: POST /api/recurring-compliance/{item_id}/complete ====================

class TestRecordCompletion:
    """Tests for POST /api/recurring-compliance/{item_id}/complete endpoint."""
    
    def test_record_completion_satisfactory(self, api_client, admin_user_id):
        """Record completion with satisfactory outcome."""
        # Create a test item
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        create_payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "supervision",
            "item_name": "TEST_Completion_Supervision",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        create_response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=create_payload)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Record completion
        completion_payload = {
            "completed_date": datetime.now().strftime('%Y-%m-%d'),
            "outcome": "satisfactory",
            "notes": "Phase 25 test completion - satisfactory"
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance/{item_id}/complete", json=completion_payload)
        assert response.status_code == 200, f"Completion failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "completed"
        assert "next_due_date" in data
        assert "completion_record" in data
        print(f"✓ Recorded satisfactory completion for {item_id}, next_due: {data['next_due_date']}")
    
    def test_record_completion_needs_improvement(self, api_client, admin_user_id):
        """Record completion with needs_improvement outcome."""
        # Create a test item
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        create_payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "spot_check",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        create_response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=create_payload)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Record completion
        completion_payload = {
            "completed_date": datetime.now().strftime('%Y-%m-%d'),
            "outcome": "needs_improvement",
            "notes": "Phase 25 test - needs improvement"
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance/{item_id}/complete", json=completion_payload)
        assert response.status_code == 200
        print(f"✓ Recorded needs_improvement completion for {item_id}")
    
    def test_record_completion_action_required(self, api_client, admin_user_id):
        """Record completion with action_required outcome."""
        # Create a competency assessment item
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        create_payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "competency_assessment",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        create_response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=create_payload)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Record completion with action_required (should create follow-up)
        follow_up_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        completion_payload = {
            "completed_date": datetime.now().strftime('%Y-%m-%d'),
            "outcome": "action_required",
            "notes": "Phase 25 test - action required",
            "support_action_required": "Additional training needed",
            "follow_up_due_date": follow_up_date
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance/{item_id}/complete", json=completion_payload)
        assert response.status_code == 200
        print(f"✓ Recorded action_required completion for {item_id}")
    
    def test_record_completion_invalid_outcome(self, api_client, admin_user_id):
        """Invalid outcome should return 400."""
        # Create a test item
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        create_payload = {
            "employee_id": TEST_EMPLOYEE_ID,
            "item_type": "supervision",
            "next_due_date": future_date,
            "assigned_to": admin_user_id
        }
        create_response = api_client.post(f"{BASE_URL}/api/recurring-compliance", json=create_payload)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Try invalid outcome
        completion_payload = {
            "completed_date": datetime.now().strftime('%Y-%m-%d'),
            "outcome": "invalid_outcome",
            "notes": "Test"
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance/{item_id}/complete", json=completion_payload)
        assert response.status_code == 400
        print("✓ Invalid outcome returns 400")
    
    def test_record_completion_nonexistent_item(self, api_client):
        """Completion on non-existent item should return 404."""
        completion_payload = {
            "completed_date": datetime.now().strftime('%Y-%m-%d'),
            "outcome": "satisfactory",
            "notes": "Test"
        }
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance/non-existent-id/complete", json=completion_payload)
        assert response.status_code == 404
        print("✓ Completion on non-existent item returns 404")


# ==================== ENDPOINT 7: GET /api/employees/{employee_id}/recurring-compliance ====================

class TestEmployeeRecurringCompliance:
    """Tests for GET /api/employees/{employee_id}/recurring-compliance endpoint."""
    
    def test_get_employee_recurring_compliance(self, api_client):
        """Get recurring compliance items for an employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/recurring-compliance")
        assert response.status_code == 200, f"Get employee items failed: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert "summary" in data
        assert "items" in data
        
        summary = data["summary"]
        assert "total" in summary
        assert "overdue" in summary
        assert "due" in summary
        assert "upcoming" in summary
        
        print(f"✓ Employee {TEST_EMPLOYEE_ID} has {summary['total']} recurring items")
    
    def test_employee_items_have_computed_status(self, api_client):
        """Employee items should have computed_status."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/recurring-compliance")
        assert response.status_code == 200
        
        data = response.json()
        for item in data["items"]:
            assert "computed_status" in item
            assert item["computed_status"] in ["overdue", "due", "upcoming", "scheduled", "completed"]
        
        print("✓ All employee items have valid computed_status")
    
    def test_nonexistent_employee(self, api_client):
        """Non-existent employee should return 404."""
        response = api_client.get(f"{BASE_URL}/api/employees/non-existent-employee/recurring-compliance")
        assert response.status_code == 404
        print("✓ Non-existent employee returns 404")


# ==================== ENDPOINT 8: POST /api/recurring-compliance/process-reminders ====================

class TestProcessReminders:
    """Tests for POST /api/recurring-compliance/process-reminders endpoint (admin only)."""
    
    def test_process_reminders_admin(self, api_client):
        """Admin should be able to process reminders."""
        response = api_client.post(f"{BASE_URL}/api/recurring-compliance/process-reminders")
        # Should return 200 (with results) or skipped if email not configured
        assert response.status_code == 200, f"Process reminders failed: {response.text}"
        
        data = response.json()
        # Either has results or was skipped
        if "status" in data and data["status"] == "skipped":
            print(f"✓ Process reminders skipped: {data.get('reason')}")
        else:
            assert "processed" in data
            assert "reminders_sent" in data
            print(f"✓ Process reminders: processed={data['processed']}, sent={data['reminders_sent']}")
    
    def test_process_reminders_requires_auth(self):
        """Process reminders should require authentication."""
        response = requests.post(f"{BASE_URL}/api/recurring-compliance/process-reminders")
        assert response.status_code in [401, 403]
        print("✓ Process reminders requires authentication")


# ==================== REGRESSION TESTS ====================

class TestRegressionPreviousPhases:
    """Regression tests to ensure previous phases still work."""
    
    def test_employment_gaps_endpoint(self, api_client):
        """Phase 24: Employment gaps endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps")
        assert response.status_code == 200
        print("✓ Phase 24 employment gaps endpoint works")
    
    def test_bulk_schedules_endpoint(self, api_client):
        """Phase 22: Bulk schedules endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/bulk/schedules")
        assert response.status_code == 200
        print("✓ Phase 22 bulk schedules endpoint works")
    
    def test_policy_assignments_endpoint(self, api_client):
        """Phase 20: Policy assignments endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/policy-assignments")
        assert response.status_code == 200
        print("✓ Phase 20 policy assignments endpoint works")
    
    def test_contracts_endpoint(self, api_client):
        """Phase 16: Contracts endpoint should still work."""
        response = api_client.get(f"{BASE_URL}/api/contract-templates")
        assert response.status_code == 200
        print("✓ Phase 16 contracts endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

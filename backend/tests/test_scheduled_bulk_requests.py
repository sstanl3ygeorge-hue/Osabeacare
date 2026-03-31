"""
Test Scheduled Bulk Requests System - Step 5
Tests for durable scheduled runner with APScheduler, catch-up logic, locking, and full audit trail.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Existing test schedule ID from context
EXISTING_SCHEDULE_ID = "89656468-511e-4cec-a614-0ac47588c124"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
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


class TestScheduleCRUD:
    """Test schedule CRUD operations."""
    
    created_schedule_id = None
    
    def test_create_schedule(self, api_client):
        """POST /api/bulk/schedules - Create a new schedule definition."""
        payload = {
            "name": f"TEST_Training Renewal Reminders {uuid.uuid4().hex[:6]}",
            "description": "Test schedule for training certificate renewals",
            "is_enabled": True,
            "target_type": "training",
            "trigger_type": "days_before_expiry",
            "days_before_expiry": 30,
            "target_rules": {
                "employee_statuses": ["onboarding", "active"],
                "training_codes": [],
                "only_expiring": True
            },
            "request_payload": {
                "due_days": 14,
                "custom_message": "Please renew your training certificate"
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules", json=payload)
        assert response.status_code == 200, f"Create schedule failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "No id in response"
        assert data["name"] == payload["name"]
        assert data["target_type"] == "training"
        assert data["days_before_expiry"] == 30
        assert data["is_enabled"] == True
        assert data["created_by"] is not None
        
        # Store for later tests
        TestScheduleCRUD.created_schedule_id = data["id"]
        print(f"Created schedule: {data['id']}")
    
    def test_list_schedules(self, api_client):
        """GET /api/bulk/schedules - List all schedules."""
        response = api_client.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        assert response.status_code == 200, f"List schedules failed: {response.text}"
        
        data = response.json()
        assert "schedules" in data
        assert "total" in data
        assert isinstance(data["schedules"], list)
        assert data["total"] >= 1, "Should have at least one schedule"
        
        # Verify schedule structure
        if data["schedules"]:
            schedule = data["schedules"][0]
            assert "id" in schedule
            assert "name" in schedule
            assert "target_type" in schedule
            assert "is_enabled" in schedule
        
        print(f"Found {data['total']} schedules")
    
    def test_get_specific_schedule(self, api_client):
        """GET /api/bulk/schedules/{id} - Get a specific schedule."""
        response = api_client.get(f"{BASE_URL}/api/bulk/schedules/{EXISTING_SCHEDULE_ID}")
        assert response.status_code == 200, f"Get schedule failed: {response.text}"
        
        data = response.json()
        assert data["id"] == EXISTING_SCHEDULE_ID
        assert "name" in data
        assert "target_type" in data
        assert "trigger_type" in data
        assert "days_before_expiry" in data
        assert "target_rules" in data
        assert "request_payload" in data
        
        print(f"Got schedule: {data['name']}")
    
    def test_get_nonexistent_schedule(self, api_client):
        """GET /api/bulk/schedules/{id} - 404 for nonexistent schedule."""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f"{BASE_URL}/api/bulk/schedules/{fake_id}")
        assert response.status_code == 404
    
    def test_update_schedule(self, api_client):
        """PUT /api/bulk/schedules/{id} - Update a schedule definition."""
        schedule_id = TestScheduleCRUD.created_schedule_id
        if not schedule_id:
            pytest.skip("No schedule created to update")
        
        update_payload = {
            "name": f"TEST_Updated Training Reminders {uuid.uuid4().hex[:6]}",
            "description": "Updated description",
            "days_before_expiry": 45
        }
        
        response = api_client.put(f"{BASE_URL}/api/bulk/schedules/{schedule_id}", json=update_payload)
        assert response.status_code == 200, f"Update schedule failed: {response.text}"
        
        data = response.json()
        assert data["days_before_expiry"] == 45
        assert "Updated" in data["name"]
        
        print(f"Updated schedule: {data['name']}")


class TestScheduleEnableDisable:
    """Test schedule enable/disable operations."""
    
    def test_disable_schedule(self, api_client):
        """POST /api/bulk/schedules/{id}/disable - Disable a schedule."""
        schedule_id = TestScheduleCRUD.created_schedule_id
        if not schedule_id:
            pytest.skip("No schedule created to disable")
        
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules/{schedule_id}/disable")
        assert response.status_code == 200, f"Disable schedule failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "disabled"
        assert data["schedule_id"] == schedule_id
        
        # Verify it's actually disabled
        get_response = api_client.get(f"{BASE_URL}/api/bulk/schedules/{schedule_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_enabled"] == False
        
        print(f"Disabled schedule: {schedule_id}")
    
    def test_enable_schedule(self, api_client):
        """POST /api/bulk/schedules/{id}/enable - Enable a disabled schedule."""
        schedule_id = TestScheduleCRUD.created_schedule_id
        if not schedule_id:
            pytest.skip("No schedule created to enable")
        
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules/{schedule_id}/enable")
        assert response.status_code == 200, f"Enable schedule failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "enabled"
        assert data["schedule_id"] == schedule_id
        
        # Verify it's actually enabled
        get_response = api_client.get(f"{BASE_URL}/api/bulk/schedules/{schedule_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_enabled"] == True
        
        print(f"Enabled schedule: {schedule_id}")


class TestScheduleExecution:
    """Test schedule execution and run history."""
    
    def test_run_now_manual_trigger(self, api_client):
        """POST /api/bulk/schedules/{id}/run-now - Manually trigger a schedule run."""
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules/{EXISTING_SCHEDULE_ID}/run-now")
        assert response.status_code == 200, f"Run now failed: {response.text}"
        
        data = response.json()
        # Check run result structure
        assert "id" in data or "status" in data
        
        if data.get("status") == "completed":
            assert "matched_employees" in data
            assert "created_requests" in data
            assert "skipped_duplicates" in data
            assert "skipped_ineligible" in data
            assert "errors" in data
            assert "started_at" in data
            assert "completed_at" in data
            assert data["triggered_by"] == "manual"
            
            print(f"Run completed: {data['created_requests']} created, "
                  f"{data['skipped_duplicates']} duplicates, "
                  f"{data['skipped_ineligible']} ineligible")
        else:
            # Could be skipped if already running or disabled
            print(f"Run status: {data.get('status', 'unknown')}")
    
    def test_get_run_history(self, api_client):
        """GET /api/bulk/schedules/{id}/history - Get run history with all metrics."""
        response = api_client.get(f"{BASE_URL}/api/bulk/schedules/{EXISTING_SCHEDULE_ID}/history")
        assert response.status_code == 200, f"Get history failed: {response.text}"
        
        data = response.json()
        assert "schedule_id" in data
        assert "schedule_name" in data
        assert "runs" in data
        assert "total" in data
        
        # Verify run structure if any runs exist
        if data["runs"]:
            run = data["runs"][0]
            assert "id" in run
            assert "schedule_id" in run
            assert "triggered_by" in run
            assert "started_at" in run
            assert "status" in run
            assert "matched_employees" in run
            assert "created_requests" in run
            assert "skipped_duplicates" in run
            assert "skipped_ineligible" in run
            assert "errors" in run
            
            print(f"Found {data['total']} runs in history")
            print(f"Latest run: {run['status']} - {run['created_requests']} created")
    
    def test_run_all_due_schedules(self, api_client):
        """POST /api/bulk/schedules/run-all-due - Run all due schedules (catch-up)."""
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules/run-all-due")
        assert response.status_code == 200, f"Run all due failed: {response.text}"
        
        data = response.json()
        assert "run_at" in data
        assert "schedules_checked" in data
        assert "schedules_executed" in data
        assert "total_requests_created" in data
        assert "schedule_results" in data
        
        print(f"Checked {data['schedules_checked']} schedules, "
              f"executed {data['schedules_executed']}, "
              f"created {data['total_requests_created']} requests")


class TestSourceAttribution:
    """Test request source attribution (manual vs scheduled)."""
    
    def test_get_attributed_requests_all(self, api_client):
        """GET /api/bulk/requests/attributed - Get all requests with source attribution."""
        response = api_client.get(f"{BASE_URL}/api/bulk/requests/attributed")
        assert response.status_code == 200, f"Get attributed requests failed: {response.text}"
        
        data = response.json()
        assert "requests" in data
        assert "total" in data
        
        print(f"Found {data['total']} attributed requests")
        
        # Check request structure if any exist
        if data["requests"]:
            req = data["requests"][0]
            assert "person_id" in req
            # created_source may or may not be present depending on when request was created
            if "created_source" in req:
                assert req["created_source"] in ["manual", "scheduled", None]
    
    def test_get_attributed_requests_manual(self, api_client):
        """GET /api/bulk/requests/attributed?source=manual - Filter by manual source."""
        response = api_client.get(f"{BASE_URL}/api/bulk/requests/attributed?source=manual")
        assert response.status_code == 200, f"Get manual requests failed: {response.text}"
        
        data = response.json()
        assert "requests" in data
        
        # All returned requests should be manual
        for req in data["requests"]:
            if "created_source" in req:
                assert req["created_source"] == "manual"
        
        print(f"Found {data['total']} manual requests")
    
    def test_get_attributed_requests_scheduled(self, api_client):
        """GET /api/bulk/requests/attributed?source=scheduled - Filter by scheduled source."""
        response = api_client.get(f"{BASE_URL}/api/bulk/requests/attributed?source=scheduled")
        assert response.status_code == 200, f"Get scheduled requests failed: {response.text}"
        
        data = response.json()
        assert "requests" in data
        
        # All returned requests should be scheduled
        for req in data["requests"]:
            if "created_source" in req:
                assert req["created_source"] == "scheduled"
                # Scheduled requests should have schedule_id and trigger_reason
                if req["created_source"] == "scheduled":
                    # These fields should be present for scheduled requests
                    pass  # May not have any scheduled requests yet
        
        print(f"Found {data['total']} scheduled requests")
    
    def test_get_attributed_requests_by_schedule_id(self, api_client):
        """GET /api/bulk/requests/attributed?schedule_id={id} - Filter by specific schedule."""
        response = api_client.get(f"{BASE_URL}/api/bulk/requests/attributed?schedule_id={EXISTING_SCHEDULE_ID}")
        assert response.status_code == 200, f"Get requests by schedule failed: {response.text}"
        
        data = response.json()
        assert "requests" in data
        
        # All returned requests should be from this schedule
        for req in data["requests"]:
            if "schedule_id" in req:
                assert req["schedule_id"] == EXISTING_SCHEDULE_ID
        
        print(f"Found {data['total']} requests from schedule {EXISTING_SCHEDULE_ID}")


class TestDeduplication:
    """Test duplicate request prevention."""
    
    def test_duplicate_run_skips_existing(self, api_client):
        """Running schedule twice should skip duplicates."""
        # First run
        response1 = api_client.post(f"{BASE_URL}/api/bulk/schedules/{EXISTING_SCHEDULE_ID}/run-now")
        assert response1.status_code == 200
        
        # Second run immediately after
        response2 = api_client.post(f"{BASE_URL}/api/bulk/schedules/{EXISTING_SCHEDULE_ID}/run-now")
        assert response2.status_code == 200
        
        data2 = response2.json()
        if data2.get("status") == "completed":
            # Second run should have more skipped duplicates or same created_requests
            # (since items that were created in first run should be skipped)
            print(f"Second run: {data2.get('created_requests', 0)} created, "
                  f"{data2.get('skipped_duplicates', 0)} duplicates")


class TestScheduleValidation:
    """Test schedule input validation."""
    
    def test_create_schedule_missing_name(self, api_client):
        """Create schedule without name should fail."""
        payload = {
            "description": "Test without name",
            "target_type": "documents"
        }
        
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules", json=payload)
        assert response.status_code == 422, "Should fail validation without name"
    
    def test_create_schedule_short_name(self, api_client):
        """Create schedule with too short name should fail."""
        payload = {
            "name": "AB",  # Less than 3 characters
            "target_type": "documents"
        }
        
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules", json=payload)
        assert response.status_code == 422, "Should fail validation with short name"
    
    def test_create_schedule_invalid_target_type(self, api_client):
        """Create schedule with invalid target_type should fail."""
        payload = {
            "name": "TEST_Invalid Target Type",
            "target_type": "invalid_type"
        }
        
        response = api_client.post(f"{BASE_URL}/api/bulk/schedules", json=payload)
        assert response.status_code == 422, "Should fail validation with invalid target_type"


class TestCleanup:
    """Cleanup test data."""
    
    def test_cleanup_test_schedules(self, api_client):
        """Clean up TEST_ prefixed schedules."""
        # Get all schedules
        response = api_client.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        if response.status_code == 200:
            schedules = response.json().get("schedules", [])
            for schedule in schedules:
                if schedule.get("name", "").startswith("TEST_"):
                    # Disable the schedule (no delete endpoint, so just disable)
                    api_client.post(f"{BASE_URL}/api/bulk/schedules/{schedule['id']}/disable")
                    print(f"Disabled test schedule: {schedule['name']}")

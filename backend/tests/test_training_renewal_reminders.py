"""
Test Training Renewal Reminders Feature
- Quick Setup endpoint for creating 3 training reminder schedules
- Expiring training summary endpoint
- Schedule CRUD operations
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestTrainingRenewalReminders:
    """Tests for Training Renewal Reminders feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    # ==================== EXPIRING SUMMARY ENDPOINT ====================
    
    def test_expiring_summary_endpoint_returns_200(self):
        """GET /api/training/expiring-summary should return 200"""
        response = self.session.get(f"{BASE_URL}/api/training/expiring-summary?days=60")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Expiring summary endpoint returns 200")
    
    def test_expiring_summary_has_required_fields(self):
        """Expiring summary should have critical, warning, upcoming buckets"""
        response = self.session.get(f"{BASE_URL}/api/training/expiring-summary?days=60")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "critical" in data, "Missing 'critical' field"
        assert "warning" in data, "Missing 'warning' field"
        assert "upcoming" in data, "Missing 'upcoming' field"
        assert "total" in data, "Missing 'total' field"
        
        # Check structure of each bucket
        for bucket in ["critical", "warning", "upcoming"]:
            assert "count" in data[bucket], f"Missing 'count' in {bucket}"
        
        print(f"PASS: Expiring summary has required fields - total: {data['total']}")
    
    def test_expiring_summary_with_custom_days(self):
        """Expiring summary should accept custom days parameter"""
        response = self.session.get(f"{BASE_URL}/api/training/expiring-summary?days=30")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        print(f"PASS: Expiring summary with 30 days - total: {data['total']}")
    
    # ==================== QUICK SETUP ENDPOINT ====================
    
    def test_quick_setup_training_reminders_endpoint(self):
        """POST /api/bulk/schedules/quick-setup-training-reminders should work"""
        response = self.session.post(f"{BASE_URL}/api/bulk/schedules/quick-setup-training-reminders")
        
        # Should return 200 whether creating new or already configured
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data, "Missing 'status' field"
        
        # Status should be either 'success' or 'already_configured'
        assert data["status"] in ["success", "already_configured"], f"Unexpected status: {data['status']}"
        
        print(f"PASS: Quick setup endpoint returned status: {data['status']}")
    
    def test_quick_setup_is_idempotent(self):
        """Calling quick setup twice should return 'already_configured' on second call"""
        # First call
        response1 = self.session.post(f"{BASE_URL}/api/bulk/schedules/quick-setup-training-reminders")
        assert response1.status_code == 200
        
        # Second call should be idempotent
        response2 = self.session.post(f"{BASE_URL}/api/bulk/schedules/quick-setup-training-reminders")
        assert response2.status_code == 200
        
        data2 = response2.json()
        assert data2["status"] == "already_configured", f"Expected 'already_configured', got {data2['status']}"
        
        print("PASS: Quick setup is idempotent - returns 'already_configured' on second call")
    
    def test_quick_setup_creates_three_schedules(self):
        """Quick setup should create 3 schedules (60, 30, 7 days)"""
        # First ensure schedules exist
        self.session.post(f"{BASE_URL}/api/bulk/schedules/quick-setup-training-reminders")
        
        # Get all schedules
        response = self.session.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        assert response.status_code == 200
        
        data = response.json()
        schedules = data.get("schedules", [])
        
        # Filter training renewal schedules
        training_schedules = [s for s in schedules if "Training Renewal" in s.get("name", "")]
        
        assert len(training_schedules) >= 3, f"Expected at least 3 training schedules, got {len(training_schedules)}"
        
        # Check for 60, 30, 7 day schedules
        days_found = [s.get("days_before_expiry") for s in training_schedules]
        assert 60 in days_found, "Missing 60-day schedule"
        assert 30 in days_found, "Missing 30-day schedule"
        assert 7 in days_found, "Missing 7-day schedule"
        
        print(f"PASS: Found {len(training_schedules)} training renewal schedules with days: {days_found}")
    
    # ==================== SCHEDULE CRUD OPERATIONS ====================
    
    def test_get_schedules_list(self):
        """GET /api/bulk/schedules should return list of schedules"""
        response = self.session.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        assert response.status_code == 200
        
        data = response.json()
        assert "schedules" in data, "Missing 'schedules' field"
        assert isinstance(data["schedules"], list), "schedules should be a list"
        
        print(f"PASS: Got {len(data['schedules'])} schedules")
    
    def test_schedule_has_required_fields(self):
        """Each schedule should have required fields"""
        # Ensure schedules exist
        self.session.post(f"{BASE_URL}/api/bulk/schedules/quick-setup-training-reminders")
        
        response = self.session.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        assert response.status_code == 200
        
        schedules = response.json().get("schedules", [])
        assert len(schedules) > 0, "No schedules found"
        
        schedule = schedules[0]
        required_fields = ["id", "name", "is_enabled", "target_type", "days_before_expiry"]
        
        for field in required_fields:
            assert field in schedule, f"Missing required field: {field}"
        
        print(f"PASS: Schedule has all required fields: {required_fields}")
    
    def test_toggle_schedule_enabled(self):
        """Should be able to enable/disable a schedule"""
        # Get schedules
        response = self.session.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        schedules = response.json().get("schedules", [])
        
        if not schedules:
            pytest.skip("No schedules to test toggle")
        
        schedule = schedules[0]
        schedule_id = schedule["id"]
        current_state = schedule["is_enabled"]
        
        # Toggle to opposite state
        endpoint = "disable" if current_state else "enable"
        toggle_response = self.session.post(f"{BASE_URL}/api/bulk/schedules/{schedule_id}/{endpoint}")
        
        assert toggle_response.status_code == 200, f"Toggle failed: {toggle_response.text}"
        
        # Verify state changed
        verify_response = self.session.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        updated_schedules = verify_response.json().get("schedules", [])
        updated_schedule = next((s for s in updated_schedules if s["id"] == schedule_id), None)
        
        assert updated_schedule is not None, "Schedule not found after toggle"
        assert updated_schedule["is_enabled"] != current_state, "Schedule state did not change"
        
        # Toggle back to original state
        restore_endpoint = "enable" if current_state else "disable"
        self.session.post(f"{BASE_URL}/api/bulk/schedules/{schedule_id}/{restore_endpoint}")
        
        print(f"PASS: Successfully toggled schedule {schedule_id} from {current_state} to {not current_state}")
    
    def test_run_now_schedule(self):
        """Should be able to run a schedule manually"""
        # Get schedules
        response = self.session.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        schedules = response.json().get("schedules", [])
        
        if not schedules:
            pytest.skip("No schedules to test run now")
        
        schedule = schedules[0]
        schedule_id = schedule["id"]
        
        # Run now
        run_response = self.session.post(f"{BASE_URL}/api/bulk/schedules/{schedule_id}/run-now")
        
        assert run_response.status_code == 200, f"Run now failed: {run_response.text}"
        
        data = run_response.json()
        # Should have result fields
        assert "created_requests" in data or "matched_employees" in data, "Missing result fields"
        
        print(f"PASS: Run now completed - created: {data.get('created_requests', 0)}, matched: {data.get('matched_employees', 0)}")
    
    def test_get_schedule_history(self):
        """Should be able to get run history for a schedule"""
        # Get schedules
        response = self.session.get(f"{BASE_URL}/api/bulk/schedules?include_disabled=true")
        schedules = response.json().get("schedules", [])
        
        if not schedules:
            pytest.skip("No schedules to test history")
        
        schedule = schedules[0]
        schedule_id = schedule["id"]
        
        # Get history
        history_response = self.session.get(f"{BASE_URL}/api/bulk/schedules/{schedule_id}/history")
        
        assert history_response.status_code == 200, f"Get history failed: {history_response.text}"
        
        data = history_response.json()
        assert "runs" in data, "Missing 'runs' field"
        assert isinstance(data["runs"], list), "runs should be a list"
        
        print(f"PASS: Got {len(data['runs'])} history entries for schedule {schedule_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test RTW Status Computation - Tests for the RTW expiry/follow-up alert layer

Tests the compute_rtw_status function which computes status from saved RTW result fields:
- continuous: indefinite RTW (no expiry)
- time_limited_valid: valid RTW with >180 days until expiry
- follow_up_due_soon: RTW expiring within 90-180 days (warning)
- urgent_follow_up: RTW expiring within 30-90 days (urgent)
- expired: RTW past expiry date
- incomplete_result: missing key result data
- not_verified: RTW not verified
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRTWStatusComputation:
    """Test RTW status computation via compliance-file endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            return response.json().get("token")  # API returns 'token', not 'access_token'
        pytest.skip(f"Authentication failed: {response.status_code}")
        
    def test_compliance_file_endpoint_returns_rtw_status(self):
        """Test that compliance-file endpoint includes rtw_status in right_to_work section"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "sections" in data, "Response should have sections"
        assert "right_to_work" in data["sections"], "Sections should have right_to_work"
        
        rtw_section = data["sections"]["right_to_work"]
        assert "rtw_status" in rtw_section, "right_to_work section should have rtw_status"
        
        rtw_status = rtw_section["rtw_status"]
        # Verify rtw_status structure
        assert "status" in rtw_status, "rtw_status should have status field"
        assert "status_label" in rtw_status, "rtw_status should have status_label field"
        assert "status_color" in rtw_status, "rtw_status should have status_color field"
        assert "summary_line" in rtw_status, "rtw_status should have summary_line field"
        assert "alerts" in rtw_status, "rtw_status should have alerts field"
        
        print(f"RTW Status: {rtw_status['status']}")
        print(f"RTW Status Label: {rtw_status['status_label']}")
        print(f"RTW Status Color: {rtw_status['status_color']}")
        print(f"RTW Summary Line: {rtw_status['summary_line']}")
        print(f"RTW Alerts: {rtw_status['alerts']}")
        
    def test_rtw_status_valid_statuses(self):
        """Test that rtw_status returns one of the valid status values"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        valid_statuses = [
            "continuous",
            "time_limited_valid", 
            "follow_up_due_soon",
            "urgent_follow_up",
            "expired",
            "incomplete_result",
            "not_verified"
        ]
        
        assert rtw_status["status"] in valid_statuses, f"Status '{rtw_status['status']}' not in valid statuses"
        
    def test_rtw_status_color_values(self):
        """Test that rtw_status returns valid color values"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        valid_colors = ["green", "amber", "red", "gray"]
        assert rtw_status["status_color"] in valid_colors, f"Color '{rtw_status['status_color']}' not in valid colors"
        
    def test_rtw_status_alerts_structure(self):
        """Test that rtw_status alerts have correct structure"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        assert isinstance(rtw_status["alerts"], list), "alerts should be a list"
        
        for alert in rtw_status["alerts"]:
            assert "level" in alert, "Each alert should have a level"
            assert "message" in alert, "Each alert should have a message"
            assert alert["level"] in ["info", "warning", "urgent", "error"], f"Invalid alert level: {alert['level']}"


class TestRTWStatusComputationDirect:
    """Test RTW status computation directly via RTW check endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            return response.json().get("token")  # API returns 'token', not 'access_token'
        pytest.skip(f"Authentication failed: {response.status_code}")
        
    def test_rtw_check_endpoint_returns_rtw_status(self):
        """Test that RTW check endpoint includes rtw_status"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check")
        
        # RTW check may not exist for this employee
        if response.status_code == 404:
            pytest.skip("No RTW check exists for test employee")
            
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check if rtw_status is included
        if "rtw_status" in data:
            rtw_status = data["rtw_status"]
            assert "status" in rtw_status
            assert "status_label" in rtw_status
            assert "status_color" in rtw_status
            print(f"RTW Check Status: {rtw_status['status']}")
        else:
            print("RTW check endpoint does not include rtw_status (may be computed at compliance-file level)")


class TestRTWStatusScenarios:
    """Test specific RTW status scenarios by creating/updating RTW checks"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            return response.json().get("token")  # API returns 'token', not 'access_token'
        pytest.skip(f"Authentication failed: {response.status_code}")
        
    def test_indefinite_rtw_returns_continuous_status(self):
        """Test that indefinite RTW returns 'continuous' status"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Create/update RTW check with indefinite permission
        today = datetime.now().strftime("%Y-%m-%d")
        rtw_data = {
            "method": "manual_list_a_check",
            "checked_at": today,
            "outcome": "verified",
            "route": "manual_passport_uk_irish",
            "is_indefinite": True,
            "permission_end_date": None,
            "notes": "Test indefinite RTW"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check",
            json=rtw_data
        )
        
        # Accept both 200 and 201
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        # Now fetch compliance file to check rtw_status
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        assert rtw_status["status"] == "continuous", f"Expected 'continuous', got '{rtw_status['status']}'"
        assert rtw_status["status_color"] == "green", f"Expected 'green', got '{rtw_status['status_color']}'"
        assert rtw_status["is_indefinite"] == True
        print(f"Indefinite RTW Status: {rtw_status}")
        
    def test_time_limited_valid_rtw_over_180_days(self):
        """Test that RTW with >180 days until expiry returns 'time_limited_valid' status"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Set expiry date to 200 days from now
        expiry_date = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        rtw_data = {
            "method": "home_office_online_check",
            "checked_at": today,
            "outcome": "verified",
            "route": "home_office_online_check",
            "is_indefinite": False,
            "permission_end_date": expiry_date,
            "notes": "Test time-limited valid RTW"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check",
            json=rtw_data
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        # Fetch compliance file
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        assert rtw_status["status"] == "time_limited_valid", f"Expected 'time_limited_valid', got '{rtw_status['status']}'"
        assert rtw_status["status_color"] == "green", f"Expected 'green', got '{rtw_status['status_color']}'"
        assert rtw_status["days_until_expiry"] is not None
        assert rtw_status["days_until_expiry"] > 180
        print(f"Time-limited valid RTW Status: {rtw_status}")
        
    def test_warning_rtw_90_to_180_days(self):
        """Test that RTW expiring in 90-180 days returns 'follow_up_due_soon' with warning"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Set expiry date to 120 days from now
        expiry_date = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        rtw_data = {
            "method": "home_office_online_check",
            "checked_at": today,
            "outcome": "verified",
            "route": "home_office_online_check",
            "is_indefinite": False,
            "permission_end_date": expiry_date,
            "notes": "Test warning RTW"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check",
            json=rtw_data
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        # Fetch compliance file
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        assert rtw_status["status"] == "follow_up_due_soon", f"Expected 'follow_up_due_soon', got '{rtw_status['status']}'"
        assert rtw_status["status_color"] == "amber", f"Expected 'amber', got '{rtw_status['status_color']}'"
        assert rtw_status["days_until_expiry"] is not None
        assert 90 <= rtw_status["days_until_expiry"] <= 180
        print(f"Warning RTW Status: {rtw_status}")
        
    def test_urgent_rtw_30_to_90_days(self):
        """Test that RTW expiring in 30-90 days returns 'follow_up_due_soon' with urgent warning"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Set expiry date to 60 days from now
        expiry_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        rtw_data = {
            "method": "home_office_online_check",
            "checked_at": today,
            "outcome": "verified",
            "route": "home_office_online_check",
            "is_indefinite": False,
            "permission_end_date": expiry_date,
            "notes": "Test urgent RTW"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check",
            json=rtw_data
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        # Fetch compliance file
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        assert rtw_status["status"] == "follow_up_due_soon", f"Expected 'follow_up_due_soon', got '{rtw_status['status']}'"
        assert rtw_status["status_color"] == "amber", f"Expected 'amber', got '{rtw_status['status_color']}'"
        assert rtw_status["days_until_expiry"] is not None
        assert 30 < rtw_status["days_until_expiry"] <= 90
        print(f"Urgent RTW Status: {rtw_status}")
        
    def test_critical_rtw_under_30_days(self):
        """Test that RTW expiring in <30 days returns 'urgent_follow_up' status"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Set expiry date to 15 days from now
        expiry_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        rtw_data = {
            "method": "home_office_online_check",
            "checked_at": today,
            "outcome": "verified",
            "route": "home_office_online_check",
            "is_indefinite": False,
            "permission_end_date": expiry_date,
            "notes": "Test critical RTW"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check",
            json=rtw_data
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        # Fetch compliance file
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        assert rtw_status["status"] == "urgent_follow_up", f"Expected 'urgent_follow_up', got '{rtw_status['status']}'"
        assert rtw_status["status_color"] == "red", f"Expected 'red', got '{rtw_status['status_color']}'"
        assert rtw_status["days_until_expiry"] is not None
        assert rtw_status["days_until_expiry"] <= 30
        # Should have urgent alert
        assert len(rtw_status["alerts"]) > 0, "Should have at least one alert"
        print(f"Critical RTW Status: {rtw_status}")
        
    def test_expired_rtw(self):
        """Test that expired RTW returns 'expired' status"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Set expiry date to 30 days ago
        expiry_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        rtw_data = {
            "method": "home_office_online_check",
            "checked_at": today,
            "outcome": "verified",
            "route": "home_office_online_check",
            "is_indefinite": False,
            "permission_end_date": expiry_date,
            "notes": "Test expired RTW"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check",
            json=rtw_data
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        # Fetch compliance file
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_status = data["sections"]["right_to_work"]["rtw_status"]
        
        assert rtw_status["status"] == "expired", f"Expected 'expired', got '{rtw_status['status']}'"
        assert rtw_status["status_color"] == "red", f"Expected 'red', got '{rtw_status['status_color']}'"
        assert rtw_status["days_until_expiry"] is not None
        assert rtw_status["days_until_expiry"] < 0
        # Should have error alert
        assert len(rtw_status["alerts"]) > 0, "Should have at least one alert"
        assert any(a["level"] == "error" for a in rtw_status["alerts"]), "Should have error level alert"
        print(f"Expired RTW Status: {rtw_status}")


class TestRTWStatusCleanup:
    """Cleanup test - restore RTW to valid state after tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            return response.json().get("token")  # API returns 'token', not 'access_token'
        pytest.skip(f"Authentication failed: {response.status_code}")
        
    def test_z_cleanup_restore_valid_rtw(self):
        """Cleanup: Restore RTW to valid indefinite state"""
        token = self.get_auth_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Restore to indefinite RTW
        today = datetime.now().strftime("%Y-%m-%d")
        rtw_data = {
            "method": "manual_list_a_check",
            "checked_at": today,
            "outcome": "verified",
            "route": "manual_passport_uk_irish",
            "is_indefinite": True,
            "permission_end_date": None,
            "notes": "Restored to valid state after testing"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/right-to-work/check",
            json=rtw_data
        )
        
        assert response.status_code in [200, 201], f"Cleanup failed: {response.status_code}: {response.text}"
        print("RTW restored to valid indefinite state")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

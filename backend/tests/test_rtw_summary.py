"""
RTW Summary Logic Tests
Tests the Right to Work summary logic for:
1. Time-limited employees (with expiry date and days countdown)
2. Permanent employees (no expiry date)
3. Correct status labels (Verified (Time-Limited) vs Verified (Permanent))
4. days_remaining calculation
5. checked_at and checked_by fields from RTW Verification
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employees
AYOMI_LORI_ID = "ca0e267f-faf2-4a4f-bd2e-afe8ea089b1f"  # Time-limited, expires 2026-09-28
OLAKUNLE_ALONGE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Permanent, no expiry


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@osabea.care", "password": "admin123"}
    )
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


class TestRTWSummaryTimeLimited:
    """Tests for time-limited RTW employee (Ayomi Lori)"""
    
    def test_rtw_status_label_shows_time_limited(self, api_client):
        """RTW status label should show 'Verified (Time-Limited)' for employees with expiry"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Status label should indicate time-limited
        assert rtw_summary.get("rtw_status_label") == "Verified (Time-Limited)", \
            f"Expected 'Verified (Time-Limited)', got '{rtw_summary.get('rtw_status_label')}'"
    
    def test_expiry_date_is_set(self, api_client):
        """Time-limited employee should have expiry_date set"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Expiry date should be set
        assert rtw_summary.get("expiry_date") is not None, "expiry_date should not be None"
        assert rtw_summary.get("expiry_date") == "2026-09-28", \
            f"Expected expiry_date '2026-09-28', got '{rtw_summary.get('expiry_date')}'"
    
    def test_days_remaining_is_calculated(self, api_client):
        """days_remaining should be correctly calculated (not None)"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # days_remaining should be a number, not None
        days_remaining = rtw_summary.get("days_remaining")
        assert days_remaining is not None, "days_remaining should not be None for time-limited employee"
        assert isinstance(days_remaining, int), f"days_remaining should be int, got {type(days_remaining)}"
        assert days_remaining > 0, f"days_remaining should be positive, got {days_remaining}"
        
        # Verify it's approximately correct (within 5 days tolerance for test timing)
        # Expected: ~182 days from 2026-03-30 to 2026-09-28
        assert 170 <= days_remaining <= 200, \
            f"days_remaining should be around 182, got {days_remaining}"
    
    def test_permission_type_is_time_limited(self, api_client):
        """permission_type should be 'time_limited'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("permission_type") == "time_limited", \
            f"Expected permission_type 'time_limited', got '{rtw_summary.get('permission_type')}'"
    
    def test_checked_at_is_populated(self, api_client):
        """checked_at should be populated from RTW Verification record"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("checked_at") is not None, "checked_at should be populated"
    
    def test_checked_by_is_populated(self, api_client):
        """checked_by should be populated from RTW Verification record"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("checked_by") is not None, "checked_by should be populated"
    
    def test_next_follow_up_due_matches_expiry(self, api_client):
        """next_follow_up_due should be set to expiry date for time-limited"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # For time-limited, next_follow_up_due should match expiry_date
        assert rtw_summary.get("next_follow_up_due") == rtw_summary.get("expiry_date"), \
            f"next_follow_up_due should match expiry_date"
    
    def test_is_not_blocking(self, api_client):
        """Verified time-limited RTW should not be blocking"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("is_blocking") == False, "Verified RTW should not be blocking"


class TestRTWSummaryPermanent:
    """Tests for permanent RTW employee (Olakunle Alonge)"""
    
    def test_rtw_status_label_shows_permanent(self, api_client):
        """RTW status label should show 'Verified (Permanent)' for employees without expiry"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Status label should indicate permanent
        assert rtw_summary.get("rtw_status_label") == "Verified (Permanent)", \
            f"Expected 'Verified (Permanent)', got '{rtw_summary.get('rtw_status_label')}'"
    
    def test_expiry_date_is_null(self, api_client):
        """Permanent employee should have no expiry_date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Expiry date should be null for permanent
        assert rtw_summary.get("expiry_date") is None, \
            f"expiry_date should be None for permanent, got '{rtw_summary.get('expiry_date')}'"
    
    def test_days_remaining_is_null(self, api_client):
        """days_remaining should be null for permanent employee"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # days_remaining should be null for permanent
        assert rtw_summary.get("days_remaining") is None, \
            f"days_remaining should be None for permanent, got '{rtw_summary.get('days_remaining')}'"
    
    def test_permission_type_is_permanent(self, api_client):
        """permission_type should be 'permanent'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("permission_type") == "permanent", \
            f"Expected permission_type 'permanent', got '{rtw_summary.get('permission_type')}'"
    
    def test_expiry_status_is_permanent(self, api_client):
        """expiry_status should be 'permanent'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("expiry_status") == "permanent", \
            f"Expected expiry_status 'permanent', got '{rtw_summary.get('expiry_status')}'"
    
    def test_checked_at_is_populated(self, api_client):
        """checked_at should be populated from RTW Verification record"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("checked_at") is not None, "checked_at should be populated"
    
    def test_is_not_blocking(self, api_client):
        """Verified permanent RTW should not be blocking"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("is_blocking") == False, "Verified RTW should not be blocking"


class TestRTWCardDisplayConsistency:
    """Tests to ensure RTW card display is consistent and non-contradictory"""
    
    def test_time_limited_no_contradiction(self, api_client):
        """Time-limited should show expiry date, not 'No Expiry'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Should have expiry date
        assert rtw_summary.get("expiry_date") is not None
        # Should NOT be marked as permanent
        assert rtw_summary.get("permission_type") != "permanent"
        # Status label should NOT say "No Expiry"
        assert "No Expiry" not in (rtw_summary.get("rtw_status_label") or "")
    
    def test_permanent_no_contradiction(self, api_client):
        """Permanent should NOT show expiry date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Should NOT have expiry date
        assert rtw_summary.get("expiry_date") is None
        # Should be marked as permanent
        assert rtw_summary.get("permission_type") == "permanent"
        # Status label should indicate permanent
        assert "Permanent" in (rtw_summary.get("rtw_status_label") or "")


class TestRTWStatusBands:
    """Tests for RTW status band logic"""
    
    def test_current_status_band_for_valid_rtw(self, api_client):
        """Verified RTW with >60 days should have 'current' status_band"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # With 182 days remaining, should be 'current'
        assert rtw_summary.get("status_band") == "current", \
            f"Expected status_band 'current', got '{rtw_summary.get('status_band')}'"
    
    def test_green_color_for_verified(self, api_client):
        """Verified RTW should have green color"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("rtw_status_color") == "green", \
            f"Expected rtw_status_color 'green', got '{rtw_summary.get('rtw_status_color')}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

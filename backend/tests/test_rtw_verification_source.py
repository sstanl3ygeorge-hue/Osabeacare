"""
RTW Verification Source Tests (2026-03-30)
Tests the simplified RTW logic where:
- RTW expiry_date is sourced from right_to_work_check (verification) NOT right_to_work_documents
- permission_type is derived from verification record presence of expiry_date
- If verification has expiry_date → time_limited, if not → permanent
- Documents = evidence only, Verification = operational/legal check we monitor

Test Employees:
- Olakunle Alonge (d88335f6-1b18-435a-8086-28af4a583f77): verification expiry 2028-05-13 = time-limited
- Ayomi Lori (ca0e267f-faf2-4a4f-bd2e-afe8ea089b1f): verification expiry 2026-09-28 = time-limited
- Henrietta Omo-Igene (50c8de24-e01f-4617-a2b4-45176e7445f3): verification no expiry = permanent
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employees based on actual data
OLAKUNLE_ALONGE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Time-limited, verification expiry 2028-05-13
AYOMI_LORI_ID = "ca0e267f-faf2-4a4f-bd2e-afe8ea089b1f"  # Time-limited, verification expiry 2026-09-28
HENRIETTA_ID = "50c8de24-e01f-4617-a2b4-45176e7445f3"  # Permanent, no verification expiry


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


class TestRTWVerificationSourceLogic:
    """Tests that RTW expiry comes from verification, not documents"""
    
    def test_rtw_summary_has_source_field(self, api_client):
        """RTW summary should have 'source': 'verification' field"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("source") == "verification", \
            f"Expected source 'verification', got '{rtw_summary.get('source')}'"
    
    def test_expiry_date_from_verification_not_documents(self, api_client):
        """Expiry date should come from verification record (right_to_work_check)"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Olakunle has verification expiry 2028-05-13
        assert rtw_summary.get("expiry_date") == "2028-05-13", \
            f"Expected expiry_date '2028-05-13' from verification, got '{rtw_summary.get('expiry_date')}'"
    
    def test_permission_type_derived_from_verification_expiry(self, api_client):
        """permission_type should be 'time_limited' when verification has expiry_date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Has expiry_date → time_limited
        assert rtw_summary.get("permission_type") == "time_limited", \
            f"Expected permission_type 'time_limited', got '{rtw_summary.get('permission_type')}'"


class TestRTWTimeLimitedEmployee:
    """Tests for time-limited RTW employees (Olakunle Alonge - verification expiry 2028-05-13)"""
    
    def test_rtw_status_label_shows_time_limited(self, api_client):
        """RTW status label should show 'Verified (Time-Limited)' for employees with verification expiry"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("rtw_status_label") == "Verified (Time-Limited)", \
            f"Expected 'Verified (Time-Limited)', got '{rtw_summary.get('rtw_status_label')}'"
    
    def test_expiry_date_is_set(self, api_client):
        """Time-limited employee should have expiry_date set from verification"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("expiry_date") is not None, "expiry_date should not be None"
        assert rtw_summary.get("expiry_date") == "2028-05-13", \
            f"Expected expiry_date '2028-05-13', got '{rtw_summary.get('expiry_date')}'"
    
    def test_days_remaining_is_calculated(self, api_client):
        """days_remaining should be correctly calculated from verification expiry"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        days_remaining = rtw_summary.get("days_remaining")
        assert days_remaining is not None, "days_remaining should not be None for time-limited employee"
        assert isinstance(days_remaining, int), f"days_remaining should be int, got {type(days_remaining)}"
        assert days_remaining > 0, f"days_remaining should be positive, got {days_remaining}"
        
        # Olakunle expires 2028-05-13, should be ~775 days from 2026-03-30
        assert 700 <= days_remaining <= 850, \
            f"days_remaining should be around 775, got {days_remaining}"
    
    def test_verification_on_file_is_true(self, api_client):
        """verification_on_file should be True"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("verification_on_file") == True, \
            "verification_on_file should be True"
    
    def test_is_not_blocking(self, api_client):
        """Verified time-limited RTW should not be blocking"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("is_blocking") == False, "Verified RTW should not be blocking"


class TestRTWTimeLimitedEmployee2:
    """Tests for second time-limited RTW employee (Ayomi Lori - verification expiry 2026-09-28)"""
    
    def test_rtw_status_label_shows_time_limited(self, api_client):
        """RTW status label should show 'Verified (Time-Limited)'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("rtw_status_label") == "Verified (Time-Limited)", \
            f"Expected 'Verified (Time-Limited)', got '{rtw_summary.get('rtw_status_label')}'"
    
    def test_expiry_date_from_verification(self, api_client):
        """Expiry date should be from verification record"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("expiry_date") == "2026-09-28", \
            f"Expected expiry_date '2026-09-28', got '{rtw_summary.get('expiry_date')}'"
    
    def test_days_remaining_calculated(self, api_client):
        """days_remaining should be calculated from verification expiry"""
        response = api_client.get(f"{BASE_URL}/api/employees/{AYOMI_LORI_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        days_remaining = rtw_summary.get("days_remaining")
        assert days_remaining is not None, "days_remaining should not be None"
        # Ayomi expires 2026-09-28, should be ~182 days from 2026-03-30
        assert 150 <= days_remaining <= 200, \
            f"days_remaining should be around 182, got {days_remaining}"


class TestRTWPermanentEmployee:
    """Tests for permanent RTW employee (Henrietta Omo-Igene - no verification expiry)"""
    
    def test_rtw_status_label_shows_permanent(self, api_client):
        """RTW status label should show 'Verified (Permanent)' for employees without verification expiry"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("rtw_status_label") == "Verified (Permanent)", \
            f"Expected 'Verified (Permanent)', got '{rtw_summary.get('rtw_status_label')}'"
    
    def test_expiry_date_is_null(self, api_client):
        """Permanent employee should have no expiry_date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("expiry_date") is None, \
            f"expiry_date should be None for permanent, got '{rtw_summary.get('expiry_date')}'"
    
    def test_days_remaining_is_null(self, api_client):
        """days_remaining should be null for permanent employee"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("days_remaining") is None, \
            f"days_remaining should be None for permanent, got '{rtw_summary.get('days_remaining')}'"
    
    def test_permission_type_is_permanent(self, api_client):
        """permission_type should be 'permanent' when verification has no expiry_date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("permission_type") == "permanent", \
            f"Expected permission_type 'permanent', got '{rtw_summary.get('permission_type')}'"
    
    def test_expiry_status_is_permanent(self, api_client):
        """expiry_status should be 'permanent'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("expiry_status") == "permanent", \
            f"Expected expiry_status 'permanent', got '{rtw_summary.get('expiry_status')}'"
    
    def test_verification_on_file_is_true(self, api_client):
        """verification_on_file should be True"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("verification_on_file") == True, \
            "verification_on_file should be True"
    
    def test_is_not_blocking(self, api_client):
        """Verified permanent RTW should not be blocking"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("is_blocking") == False, "Verified RTW should not be blocking"


class TestRTWCardDisplayConsistency:
    """Tests to ensure RTW card display is consistent and non-contradictory"""
    
    def test_time_limited_no_contradiction(self, api_client):
        """Time-limited should show expiry date, not 'No Expiry'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # Should have expiry date
        assert rtw_summary.get("expiry_date") is not None
        # Should be marked as time_limited
        assert rtw_summary.get("permission_type") == "time_limited"
        # Status label should NOT say "Permanent"
        assert "Permanent" not in (rtw_summary.get("rtw_status_label") or "")
    
    def test_permanent_no_contradiction(self, api_client):
        """Permanent should NOT show expiry date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
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
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        # With 775 days remaining, should be 'current'
        assert rtw_summary.get("status_band") == "current", \
            f"Expected status_band 'current', got '{rtw_summary.get('status_band')}'"
    
    def test_green_color_for_verified(self, api_client):
        """Verified RTW should have green color"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ALONGE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("rtw_status_color") == "green", \
            f"Expected rtw_status_color 'green', got '{rtw_summary.get('rtw_status_color')}'"
    
    def test_permanent_has_current_status_band(self, api_client):
        """Permanent RTW should have 'current' status_band"""
        response = api_client.get(f"{BASE_URL}/api/employees/{HENRIETTA_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        rtw_summary = data.get("rtw_summary", {})
        
        assert rtw_summary.get("status_band") == "current", \
            f"Expected status_band 'current', got '{rtw_summary.get('status_band')}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

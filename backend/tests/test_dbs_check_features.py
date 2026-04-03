"""
Test DBS Check Features - 3-Layer Model (Evidence -> Verification -> DBS Result)

Tests:
1. POST /api/employees/{employee_id}/dbs/check - Record DBS check with all new fields
2. GET /api/employees/{employee_id}/dbs/check - Get current DBS check with computed status
3. POST /api/dbs/extract - Extract DBS fields from document (GPT-5.2 Vision)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestDBSCheckEndpoints:
    """Test DBS check recording and retrieval endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_record_dbs_check_certificate_review(self):
        """Test recording a DBS certificate review check with all new fields."""
        # Calculate dates
        today = datetime.now().strftime("%Y-%m-%d")
        next_recheck = (datetime.now() + timedelta(days=365*3)).strftime("%Y-%m-%d")  # 3 years
        
        payload = {
            "method": "dbs_certificate_review",
            "checked_at": today,
            "outcome": "verified",
            # DBS Result Panel fields
            "dbs_level": "enhanced",
            "certificate_number": "123456789012",
            "certificate_issue_date": "2025-06-15",
            "name_on_certificate": "John Test Smith",
            "workforce": "adult_and_child",
            # Update Service fields (not applicable for certificate review)
            "update_service_registered": False,
            "update_service_status": "not_registered",
            # Recheck tracking
            "recheck_required": True,
            "next_recheck_date": next_recheck,
            "review_due_at": next_recheck,
            # Result details
            "result_status": "clear",
            "information_present": False,
            "result_summary": "Clear - no information disclosed",
            # Notes
            "notes": "DBS certificate reviewed and verified. No disclosures."
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            json=payload
        )
        
        print(f"POST DBS Check Response Status: {response.status_code}")
        print(f"POST DBS Check Response: {response.json()}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all fields are stored correctly
        assert data.get("method") == "dbs_certificate_review"
        assert data.get("outcome") == "verified"
        assert data.get("dbs_level") == "enhanced"
        assert data.get("certificate_number") == "123456789012"
        assert data.get("certificate_issue_date") == "2025-06-15"
        assert data.get("name_on_certificate") == "John Test Smith"
        assert data.get("workforce") == "adult_and_child"
        assert data.get("result_status") == "clear"
        assert data.get("information_present") == False
        assert data.get("recheck_required") == True
        assert data.get("next_recheck_date") == next_recheck
        assert data.get("id") is not None
        assert data.get("is_current") == True
        
        print("✓ DBS certificate review check recorded successfully with all fields")
    
    def test_record_dbs_check_update_service(self):
        """Test recording a DBS Update Service check with all new fields."""
        today = datetime.now().strftime("%Y-%m-%d")
        next_recheck = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")  # 1 year
        
        payload = {
            "method": "dbs_update_service_check",
            "checked_at": today,
            "outcome": "verified",
            # DBS Result Panel fields
            "dbs_level": "enhanced_barred",
            "certificate_number": "987654321098",
            "certificate_issue_date": "2024-03-20",
            "name_on_certificate": "Jane Test Doe",
            "workforce": "child",
            # Update Service fields
            "update_service_registered": True,
            "update_service_status": "active",
            "last_status_check_date": today,
            "update_service_check_result": "no_change",
            # Recheck tracking
            "recheck_required": True,
            "next_recheck_date": next_recheck,
            "review_due_at": next_recheck,
            # Result details
            "result_status": "clear",
            "information_present": False,
            "result_summary": "Update Service check - no changes to disclose",
            # Notes
            "notes": "DBS Update Service checked online. Status: No change."
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            json=payload
        )
        
        print(f"POST DBS Update Service Check Response Status: {response.status_code}")
        print(f"POST DBS Update Service Check Response: {response.json()}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify Update Service specific fields
        assert data.get("method") == "dbs_update_service_check"
        assert data.get("update_service_registered") == True
        assert data.get("update_service_status") == "active"
        assert data.get("last_status_check_date") == today
        assert data.get("update_service_check_result") == "no_change"
        assert data.get("dbs_level") == "enhanced_barred"
        assert data.get("workforce") == "child"
        
        print("✓ DBS Update Service check recorded successfully with all fields")
    
    def test_record_dbs_check_information_present(self):
        """Test recording a DBS check with information present."""
        today = datetime.now().strftime("%Y-%m-%d")
        next_recheck = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")  # 6 months
        
        payload = {
            "method": "dbs_certificate_review",
            "checked_at": today,
            "outcome": "follow_up_required",
            # DBS Result Panel fields
            "dbs_level": "enhanced",
            "certificate_number": "111222333444",
            "certificate_issue_date": "2025-01-10",
            "name_on_certificate": "Test Information Present",
            "workforce": "adult",
            # Result details - information present
            "result_status": "information_present",
            "information_present": True,
            "result_summary": "Information disclosed - requires risk assessment",
            # Recheck tracking
            "recheck_required": True,
            "next_recheck_date": next_recheck,
            # Notes
            "notes": "Certificate shows disclosures. Risk assessment required before clearance."
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            json=payload
        )
        
        print(f"POST DBS Check (Info Present) Response Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify information_present fields
        assert data.get("result_status") == "information_present"
        assert data.get("information_present") == True
        assert data.get("outcome") == "follow_up_required"
        
        print("✓ DBS check with information present recorded successfully")
    
    def test_get_current_dbs_check(self):
        """Test retrieving current DBS check with computed dbs_status."""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check"
        )
        
        print(f"GET DBS Check Response Status: {response.status_code}")
        print(f"GET DBS Check Response: {response.json()}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        current = data.get("current")
        
        if current:
            # Verify computed dbs_status is present
            assert "dbs_status" in current, "dbs_status computed field should be present"
            
            dbs_status = current.get("dbs_status", {})
            assert "status" in dbs_status, "dbs_status should have status field"
            assert "status_label" in dbs_status, "dbs_status should have status_label field"
            assert "status_color" in dbs_status, "dbs_status should have status_color field"
            assert "summary_line" in dbs_status, "dbs_status should have summary_line field"
            
            # Verify checked_by_name resolution
            if current.get("checked_by"):
                assert "checked_by_name" in current, "checked_by_name should be resolved"
            
            print(f"✓ Current DBS check retrieved with computed status: {dbs_status.get('status_label')}")
            print(f"  - Status: {dbs_status.get('status')}")
            print(f"  - Color: {dbs_status.get('status_color')}")
            print(f"  - Summary: {dbs_status.get('summary_line')}")
            print(f"  - Checked by: {current.get('checked_by_name', 'N/A')}")
        else:
            print("No current DBS check found (this is acceptable if no check recorded)")
    
    def test_get_dbs_check_with_history(self):
        """Test retrieving DBS check with history."""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            params={"include_history": True}
        )
        
        print(f"GET DBS Check with History Response Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Should have both current and history
        assert "current" in data, "Response should have 'current' field"
        assert "history" in data, "Response should have 'history' field when include_history=True"
        
        history = data.get("history", [])
        print(f"✓ DBS check history retrieved: {len(history)} records")
    
    def test_dbs_check_required_fields(self):
        """Test that required fields are validated."""
        # Missing method field
        payload = {
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            json=payload
        )
        
        # Should fail validation (422) because method is required
        assert response.status_code == 422, f"Expected 422 for missing required field, got {response.status_code}"
        print("✓ Required field validation working correctly")


class TestDBSExtractEndpoint:
    """Test DBS extraction endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_dbs_extract_endpoint_exists(self):
        """Test that DBS extract endpoint exists and accepts requests."""
        # Send a minimal request to check endpoint exists
        # Using a small base64 encoded test image (1x1 pixel PNG)
        test_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.session.post(
            f"{BASE_URL}/api/dbs/extract",
            json={
                "file_base64": test_base64,
                "file_type": "image/png"
            },
            params={"employee_id": TEST_EMPLOYEE_ID}
        )
        
        print(f"POST DBS Extract Response Status: {response.status_code}")
        
        # Endpoint should exist (not 404) - may return success:false for invalid image
        assert response.status_code != 404, "DBS extract endpoint should exist"
        
        # Should return JSON response
        data = response.json()
        assert "success" in data or "error" in data, "Response should have success or error field"
        
        print(f"✓ DBS extract endpoint exists and responds correctly")
        print(f"  Response: {data}")


class TestDBSStatusComputation:
    """Test DBS status computation logic."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_dbs_status_clear_verified(self):
        """Test DBS status computation for clear verified check."""
        today = datetime.now().strftime("%Y-%m-%d")
        next_recheck = (datetime.now() + timedelta(days=365*3)).strftime("%Y-%m-%d")
        
        # Record a clear verified check
        payload = {
            "method": "dbs_certificate_review",
            "checked_at": today,
            "outcome": "verified",
            "dbs_level": "enhanced",
            "certificate_number": "TEST12345678",
            "result_status": "clear",
            "information_present": False,
            "next_recheck_date": next_recheck
        }
        
        post_response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            json=payload
        )
        
        assert post_response.status_code == 200
        
        # Get the check and verify computed status
        get_response = self.session.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check"
        )
        
        assert get_response.status_code == 200
        
        data = get_response.json()
        current = data.get("current", {})
        dbs_status = current.get("dbs_status", {})
        
        # For a clear verified check with future recheck date, status should be green
        assert dbs_status.get("status") in ["clear", "verified", "recheck_due_soon"], \
            f"Expected clear/verified status, got {dbs_status.get('status')}"
        
        print(f"✓ DBS status computed correctly: {dbs_status.get('status_label')}")
    
    def test_dbs_status_information_present(self):
        """Test DBS status computation for information present check."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Record a check with information present
        payload = {
            "method": "dbs_certificate_review",
            "checked_at": today,
            "outcome": "follow_up_required",
            "dbs_level": "enhanced",
            "certificate_number": "INFO12345678",
            "result_status": "information_present",
            "information_present": True
        }
        
        post_response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            json=payload
        )
        
        assert post_response.status_code == 200
        
        # Get the check and verify computed status
        get_response = self.session.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check"
        )
        
        assert get_response.status_code == 200
        
        data = get_response.json()
        current = data.get("current", {})
        dbs_status = current.get("dbs_status", {})
        
        # Should reflect information present status
        assert dbs_status.get("information_present") == True, "information_present should be True"
        
        print(f"✓ DBS status with information present computed correctly: {dbs_status.get('status_label')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

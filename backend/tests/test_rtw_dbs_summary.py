"""
Test RTW and DBS Summary API endpoints
Tests the single source of truth functions for RTW and DBS status
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRTWDBSSummary:
    """Tests for RTW and DBS summary endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        
        # Login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_compliance_requirements_returns_rtw_summary(self):
        """Test that compliance-requirements endpoint returns rtw_summary"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify rtw_summary is present
        assert "rtw_summary" in data, "rtw_summary missing from response"
        rtw = data["rtw_summary"]
        
        # Verify rtw_summary structure
        assert "rtw_status" in rtw
        assert "rtw_status_label" in rtw
        assert "rtw_status_color" in rtw
        assert "documents_on_file" in rtw
        assert "documents_verified" in rtw
        assert "verification_on_file" in rtw
        assert "verification_verified" in rtw
        
        print(f"RTW Summary: {rtw}")
    
    def test_compliance_requirements_returns_dbs_summary(self):
        """Test that compliance-requirements endpoint returns dbs_summary"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify dbs_summary is present
        assert "dbs_summary" in data, "dbs_summary missing from response"
        dbs = data["dbs_summary"]
        
        # Verify dbs_summary structure
        assert "dbs_status" in dbs
        assert "dbs_status_label" in dbs
        assert "dbs_status_color" in dbs
        assert "certificate_on_file" in dbs
        assert "certificate_verified" in dbs
        assert "update_service_active" in dbs
        assert "update_service_verified" in dbs
        
        print(f"DBS Summary: {dbs}")
    
    def test_rtw_status_verified_when_both_docs_verified(self):
        """Test RTW status is 'verified' when both documents and verification are verified"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        rtw = data["rtw_summary"]
        
        # For test employee with verified RTW docs
        if rtw["documents_on_file"] and rtw["verification_on_file"]:
            if rtw["documents_verified"] and rtw["verification_verified"]:
                assert rtw["rtw_status"] == "verified", f"Expected 'verified', got '{rtw['rtw_status']}'"
                assert rtw["rtw_status_label"] == "Verified", f"Expected 'Verified', got '{rtw['rtw_status_label']}'"
                assert rtw["rtw_status_color"] == "green", f"Expected 'green', got '{rtw['rtw_status_color']}'"
                print("✅ RTW status correctly shows 'Verified' when both docs are verified")
            else:
                assert rtw["rtw_status"] == "pending_verification"
                print("⚠️ RTW docs exist but not all verified - status is 'pending_verification'")
        else:
            print(f"⚠️ RTW docs not complete: docs_on_file={rtw['documents_on_file']}, verification_on_file={rtw['verification_on_file']}")
    
    def test_dbs_status_current_when_verified(self):
        """Test DBS status is 'current' when update service is verified"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        dbs = data["dbs_summary"]
        
        # For test employee with verified DBS
        if dbs["update_service_active"] and dbs["update_service_verified"]:
            assert dbs["dbs_status"] == "current", f"Expected 'current', got '{dbs['dbs_status']}'"
            assert dbs["dbs_status_label"] == "Current", f"Expected 'Current', got '{dbs['dbs_status_label']}'"
            assert dbs["dbs_status_color"] == "green", f"Expected 'green', got '{dbs['dbs_status_color']}'"
            print("✅ DBS status correctly shows 'Current' when update service is verified")
        else:
            print(f"⚠️ DBS update service not verified: active={dbs['update_service_active']}, verified={dbs['update_service_verified']}")
    
    def test_overall_compliance_percentage(self):
        """Test overall compliance percentage is returned correctly"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify statuses.overall_compliance is present
        assert "statuses" in data
        assert "overall_compliance" in data["statuses"]
        
        overall = data["statuses"]["overall_compliance"]
        assert "percentage" in overall
        assert "complete" in overall
        assert "total" in overall
        
        # Verify percentage is calculated correctly
        expected_pct = int((overall["complete"] / overall["total"]) * 100) if overall["total"] > 0 else 0
        assert overall["percentage"] == expected_pct, f"Expected {expected_pct}%, got {overall['percentage']}%"
        
        print(f"✅ Overall compliance: {overall['percentage']}% ({overall['complete']}/{overall['total']})")
    
    def test_requirements_have_verified_field(self):
        """Test that requirements use 'verified' field (not 'is_verified')"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        requirements = data.get("requirements", [])
        assert len(requirements) > 0, "No requirements returned"
        
        # Check that requirements use 'verified' not 'is_verified'
        for req in requirements:
            # 'verified' should be present
            assert "verified" in req, f"Requirement {req.get('id')} missing 'verified' field"
            # 'is_verified' should NOT be present (old field name)
            assert "is_verified" not in req, f"Requirement {req.get('id')} has deprecated 'is_verified' field"
        
        print(f"✅ All {len(requirements)} requirements use correct 'verified' field")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

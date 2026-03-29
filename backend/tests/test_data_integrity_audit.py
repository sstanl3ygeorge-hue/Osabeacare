"""
Data Integrity Audit Tests
==========================
Tests for verifying ONE source of truth, ZERO conflicting values, 
consistent behavior across all UI and APIs.

Focus areas:
1. DBS Register loads without errors
2. Training Safety Engine returns correct required_current_count
3. Employee list completion_percentage matches profile completion_percentage
4. Work readiness status consistent between employee list and profile
5. DBS status consistent between profile dbs_summary and DBS Register
6. RTW status displays correctly on profile
7. Safety engines correctly compute is_blocking for DBS, RTW, Training
8. Profile page loads without errors
9. Dashboard loads without errors
10. Compliance Centre loads without errors
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID from the review request
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestCoreEndpointsLoad:
    """Test that all core endpoints load without errors"""
    
    def test_dashboard_loads(self, auth_headers):
        """Dashboard endpoint should load without errors"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        # Verify dashboard has expected structure
        assert "total_employees" in data or "employees" in data or "stats" in data or "compliance_overview" in data, \
            f"Dashboard missing expected fields: {data.keys()}"
        print(f"✅ Dashboard loads successfully")
    
    def test_dbs_register_loads(self, auth_headers):
        """DBS Register endpoint should load without errors (was KeyError bug)"""
        response = requests.get(f"{BASE_URL}/api/dbs-register", headers=auth_headers)
        assert response.status_code == 200, f"DBS Register failed: {response.text}"
        data = response.json()
        # Verify structure
        assert "register" in data, f"DBS Register missing 'register' field: {data.keys()}"
        assert "stats" in data, f"DBS Register missing 'stats' field: {data.keys()}"
        print(f"✅ DBS Register loads successfully with {len(data['register'])} entries")
        print(f"   Stats: {data['stats']}")
    
    def test_compliance_centre_loads(self, auth_headers):
        """Compliance Centre endpoint should load without errors"""
        response = requests.get(f"{BASE_URL}/api/compliance/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Compliance Centre failed: {response.text}"
        data = response.json()
        print(f"✅ Compliance Centre loads successfully")
    
    def test_employees_list_loads(self, auth_headers):
        """Employees list endpoint should load without errors"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        assert response.status_code == 200, f"Employees list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Employees should be a list: {type(data)}"
        print(f"✅ Employees list loads successfully with {len(data)} employees")


class TestTrainingSafetyEngine:
    """Test Training Safety Engine returns correct required_current_count"""
    
    def test_training_summary_has_correct_counts(self, auth_headers):
        """Training summary should have required_current_count > 0 (was 0/0 bug)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance failed: {response.text}"
        data = response.json()
        
        training_summary = data.get("training_summary", {})
        required_current = training_summary.get("required_current_count", 0)
        required_total = training_summary.get("required_total_count", 0)
        
        print(f"   Training Summary: {required_current}/{required_total}")
        print(f"   Status: {training_summary.get('training_status')}")
        print(f"   Is Blocking: {training_summary.get('is_blocking')}")
        
        # After fix, required_total should be > 0 (was querying empty db.requirements)
        assert required_total > 0, \
            f"Training required_total_count should be > 0, got {required_total}. " \
            f"This indicates the fix for MANDATORY_ITEMS source may not be applied."
        
        print(f"✅ Training Safety Engine: {required_current}/{required_total} (correct)")


class TestDataConsistencyAcrossViews:
    """Test that data is consistent between employee list and profile views"""
    
    def test_completion_percentage_consistency(self, auth_headers):
        """Employee list completion_percentage should match profile completion_percentage"""
        # Get employee from list
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        assert response.status_code == 200
        employees = response.json()
        
        # Find test employee
        test_emp = next((e for e in employees if e.get("id") == TEST_EMPLOYEE_ID), None)
        assert test_emp is not None, f"Test employee {TEST_EMPLOYEE_ID} not found in list"
        
        list_completion = test_emp.get("completion_percentage", 0)
        
        # Get employee profile compliance-requirements (has the safety engine summaries)
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        profile_completion = compliance.get("summary", {}).get("completion_percentage", 0)
        
        print(f"   List completion_percentage: {list_completion}%")
        print(f"   Profile completion_percentage: {profile_completion}%")
        
        # They should match (or be very close due to timing)
        assert abs(list_completion - profile_completion) <= 1, \
            f"Completion percentage mismatch: list={list_completion}%, profile={profile_completion}%"
        
        print(f"✅ Completion percentage consistent: {list_completion}%")
    
    def test_work_readiness_consistency(self, auth_headers):
        """Work readiness status should be consistent between list and profile"""
        # Get employee from list
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        assert response.status_code == 200
        employees = response.json()
        
        test_emp = next((e for e in employees if e.get("id") == TEST_EMPLOYEE_ID), None)
        assert test_emp is not None
        
        list_work_readiness = test_emp.get("work_readiness", {})
        list_status = list_work_readiness.get("status", "unknown")
        
        # Get employee profile compliance-requirements
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        profile_work_readiness = compliance.get("work_readiness", {})
        profile_status = profile_work_readiness.get("status", "unknown")
        
        print(f"   List work_readiness: {list_status} ({list_work_readiness.get('label', '')})")
        print(f"   Profile work_readiness: {profile_status} ({profile_work_readiness.get('label', '')})")
        
        # Statuses should match
        assert list_status == profile_status, \
            f"Work readiness mismatch: list={list_status}, profile={profile_status}"
        
        print(f"✅ Work readiness consistent: {list_status}")


class TestDBSStatusConsistency:
    """Test DBS status is consistent between profile and DBS Register"""
    
    def test_dbs_status_matches_register(self, auth_headers):
        """DBS status in profile should match DBS Register entry"""
        # Get profile DBS summary from compliance-requirements
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        profile_dbs = compliance.get("dbs_summary", {})
        profile_dbs_status = profile_dbs.get("dbs_status", "unknown")
        
        # Get DBS Register
        response = requests.get(f"{BASE_URL}/api/dbs-register", headers=auth_headers)
        assert response.status_code == 200
        register_data = response.json()
        
        # Find employee in register
        register_entry = next(
            (r for r in register_data.get("register", []) if r.get("employee_id") == TEST_EMPLOYEE_ID),
            None
        )
        
        if register_entry:
            register_dbs_status = register_entry.get("dbs_status", "unknown")
            
            print(f"   Profile DBS status: {profile_dbs_status}")
            print(f"   Register DBS status: {register_dbs_status}")
            
            assert profile_dbs_status == register_dbs_status, \
                f"DBS status mismatch: profile={profile_dbs_status}, register={register_dbs_status}"
            
            print(f"✅ DBS status consistent: {profile_dbs_status}")
        else:
            print(f"   Employee not in DBS Register (may be archived)")
            print(f"   Profile DBS status: {profile_dbs_status}")


class TestSafetyEnginesBlocking:
    """Test that safety engines correctly compute is_blocking"""
    
    def test_dbs_safety_engine(self, auth_headers):
        """DBS safety engine should compute is_blocking correctly"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        dbs_summary = compliance.get("dbs_summary", {})
        dbs_status = dbs_summary.get("dbs_status")
        is_blocking = dbs_summary.get("is_blocking")
        blocking_reason = dbs_summary.get("blocking_reason")
        
        print(f"   DBS Status: {dbs_status}")
        print(f"   Is Blocking: {is_blocking}")
        print(f"   Blocking Reason: {blocking_reason}")
        
        # Verify blocking logic is consistent with status
        if dbs_status == "missing":
            assert is_blocking == True, "Missing DBS should be blocking"
        elif dbs_status == "current":
            assert is_blocking == False, "Current DBS should not be blocking"
        
        print(f"✅ DBS Safety Engine: is_blocking={is_blocking}")
    
    def test_rtw_safety_engine(self, auth_headers):
        """RTW safety engine should compute is_blocking correctly"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        rtw_summary = compliance.get("rtw_summary", {})
        rtw_status = rtw_summary.get("rtw_status")
        is_blocking = rtw_summary.get("is_blocking")
        blocking_reason = rtw_summary.get("blocking_reason")
        
        print(f"   RTW Status: {rtw_status}")
        print(f"   Is Blocking: {is_blocking}")
        print(f"   Blocking Reason: {blocking_reason}")
        
        # Verify blocking logic
        if rtw_status == "missing":
            assert is_blocking == True, "Missing RTW should be blocking"
        elif rtw_status == "current":
            assert is_blocking == False, "Current RTW should not be blocking"
        
        print(f"✅ RTW Safety Engine: is_blocking={is_blocking}")
    
    def test_training_safety_engine(self, auth_headers):
        """Training safety engine should compute is_blocking correctly"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        training_summary = compliance.get("training_summary", {})
        training_status = training_summary.get("training_status")
        is_blocking = training_summary.get("is_blocking")
        blocking_reason = training_summary.get("blocking_reason")
        required_current = training_summary.get("required_current_count", 0)
        required_total = training_summary.get("required_total_count", 0)
        
        print(f"   Training Status: {training_status}")
        print(f"   Required: {required_current}/{required_total}")
        print(f"   Is Blocking: {is_blocking}")
        print(f"   Blocking Reason: {blocking_reason}")
        
        # If all required training is current, should not be blocking
        if required_current == required_total and required_total > 0:
            assert is_blocking == False, \
                f"All training current ({required_current}/{required_total}) should not be blocking"
        
        print(f"✅ Training Safety Engine: is_blocking={is_blocking}")


class TestProfilePageData:
    """Test that profile page data is complete and correct"""
    
    def test_employee_profile_loads(self, auth_headers):
        """Employee profile should load with all expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Profile failed: {response.text}"
        employee = response.json()
        
        # Check required fields
        assert "id" in employee
        assert "first_name" in employee
        assert "last_name" in employee
        assert "completion_percentage" in employee
        
        print(f"✅ Employee profile loads: {employee.get('first_name')} {employee.get('last_name')}")
        print(f"   Completion: {employee.get('completion_percentage')}%")
    
    def test_compliance_data_complete(self, auth_headers):
        """Compliance data should have all safety engine summaries"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        # Check all safety engine summaries are present
        assert "dbs_summary" in compliance, "Missing dbs_summary"
        assert "rtw_summary" in compliance, "Missing rtw_summary"
        assert "training_summary" in compliance, "Missing training_summary"
        assert "work_readiness" in compliance, "Missing work_readiness"
        assert "summary" in compliance, "Missing summary"
        
        # Check summary has completion_percentage
        assert "completion_percentage" in compliance.get("summary", {}), \
            "Missing completion_percentage in summary"
        
        print(f"✅ Compliance data complete with all safety engine summaries")


class TestExpectedValues:
    """Test expected values for the test employee (Olakunle Alonge)"""
    
    def test_expected_completion_percentage(self, auth_headers):
        """Test employee should have ~91% completion"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        completion = compliance.get("summary", {}).get("completion_percentage", 0)
        print(f"   Actual completion: {completion}%")
        
        # Should be around 91% (allow some variance)
        assert completion >= 85, f"Completion should be ~91%, got {completion}%"
        print(f"✅ Completion percentage in expected range: {completion}%")
    
    def test_expected_work_readiness(self, auth_headers):
        """Test employee should be work_ready"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        work_readiness = compliance.get("work_readiness", {})
        status = work_readiness.get("status", "unknown")
        
        print(f"   Work readiness status: {status}")
        print(f"   Label: {work_readiness.get('label', '')}")
        
        # Expected to be work_ready
        assert status == "work_ready", f"Expected work_ready, got {status}"
        print(f"✅ Work readiness as expected: {status}")
    
    def test_expected_dbs_status(self, auth_headers):
        """Test employee should have current DBS"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        dbs_summary = compliance.get("dbs_summary", {})
        dbs_status = dbs_summary.get("dbs_status", "unknown")
        
        print(f"   DBS status: {dbs_status}")
        print(f"   Is blocking: {dbs_summary.get('is_blocking')}")
        
        # Expected to be current
        assert dbs_status == "current", f"Expected current DBS, got {dbs_status}"
        print(f"✅ DBS status as expected: {dbs_status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

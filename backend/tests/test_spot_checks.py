"""
Spot Checks API Tests - P2 Feature
Tests for spot check CRUD operations, outcome tracking, and follow-up alerts
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee ID - will be fetched dynamically
TEST_EMPLOYEE_ID = None


class TestSpotChecksAPI:
    """Test suite for Spot Checks API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login and get employee ID"""
        global TEST_EMPLOYEE_ID
        
        # Login to get auth token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get an employee ID for testing
        if TEST_EMPLOYEE_ID is None:
            employees_response = requests.get(
                f"{BASE_URL}/api/employees",
                headers=self.headers
            )
            assert employees_response.status_code == 200, "Failed to get employees"
            employees = employees_response.json()
            assert len(employees) > 0, "No employees found for testing"
            TEST_EMPLOYEE_ID = employees[0]["id"]
        
        self.employee_id = TEST_EMPLOYEE_ID
        print(f"Testing with employee ID: {self.employee_id}")
    
    # ========== GET Spot Checks Tests ==========
    
    def test_get_spot_checks_returns_list(self):
        """Test GET /employees/{id}/spot-checks returns list of spot checks"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "spot_checks" in data, "Response missing 'spot_checks' key"
        assert isinstance(data["spot_checks"], list), "spot_checks should be a list"
        print(f"PASS: GET spot-checks returned {len(data['spot_checks'])} records")
    
    def test_get_spot_checks_unauthorized(self):
        """Test GET spot-checks without auth returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Unauthorized request correctly rejected")
    
    # ========== POST Create Spot Check Tests ==========
    
    def test_create_spot_check_pass_outcome(self):
        """Test creating a spot check with Pass outcome"""
        payload = {
            "type": "observation",
            "area": "medication",
            "outcome": "pass",
            "notes": "TEST_Excellent medication administration observed",
            "follow_up_required": False
        }
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True, "Expected success=True"
        assert "id" in data, "Response missing 'id'"
        assert data["outcome"] == "pass", "Outcome should be 'pass'"
        print(f"PASS: Created spot check with Pass outcome, ID: {data['id']}")
    
    def test_create_spot_check_needs_improvement_outcome(self):
        """Test creating a spot check with Needs Improvement outcome"""
        payload = {
            "type": "document_review",
            "area": "record_keeping",
            "outcome": "needs_improvement",
            "notes": "TEST_Record keeping needs improvement - some entries incomplete",
            "follow_up_required": True,
            "follow_up_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        }
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["outcome"] == "needs_improvement"
        print(f"PASS: Created spot check with Needs Improvement outcome, ID: {data['id']}")
    
    def test_create_spot_check_fail_outcome(self):
        """Test creating a spot check with Fail outcome"""
        payload = {
            "type": "competency_check",
            "area": "safeguarding",
            "outcome": "fail",
            "notes": "TEST_Safeguarding protocol not followed correctly - retraining required",
            "follow_up_required": True,
            "follow_up_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        }
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert data["outcome"] == "fail"
        print(f"PASS: Created spot check with Fail outcome, ID: {data['id']}")
    
    def test_create_spot_check_all_check_types(self):
        """Test creating spot checks with all check types"""
        check_types = ["observation", "document_review", "competency_check", "medication_check"]
        
        for check_type in check_types:
            payload = {
                "type": check_type,
                "area": "communication",
                "outcome": "pass",
                "notes": f"TEST_Spot check for {check_type} type verification",
                "follow_up_required": False
            }
            response = requests.post(
                f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
                json=payload,
                headers=self.headers
            )
            assert response.status_code == 200, f"Failed for type {check_type}: {response.text}"
            print(f"PASS: Created spot check with type '{check_type}'")
    
    def test_create_spot_check_all_areas(self):
        """Test creating spot checks with all area types"""
        areas = [
            "moving_handling", "medication", "record_keeping", 
            "communication", "infection_control", "dignity_respect", "safeguarding"
        ]
        
        for area in areas:
            payload = {
                "type": "observation",
                "area": area,
                "outcome": "pass",
                "notes": f"TEST_Spot check for {area} area verification",
                "follow_up_required": False
            }
            response = requests.post(
                f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
                json=payload,
                headers=self.headers
            )
            assert response.status_code == 200, f"Failed for area {area}: {response.text}"
            print(f"PASS: Created spot check with area '{area}'")
    
    def test_create_spot_check_with_follow_up(self):
        """Test creating a spot check with follow-up date"""
        follow_up_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        payload = {
            "type": "observation",
            "area": "infection_control",
            "outcome": "needs_improvement",
            "notes": "TEST_Follow-up required to verify improvement in infection control practices",
            "follow_up_required": True,
            "follow_up_date": follow_up_date
        }
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        
        # Verify follow-up date is stored
        get_response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            headers=self.headers
        )
        checks = get_response.json()["spot_checks"]
        created_check = next((c for c in checks if c["id"] == data["id"]), None)
        assert created_check is not None, "Created check not found"
        assert created_check["follow_up_required"] is True
        assert follow_up_date in created_check.get("follow_up_date", "")
        print(f"PASS: Created spot check with follow-up date {follow_up_date}")
    
    def test_create_spot_check_notes_validation(self):
        """Test that notes field is accepted (validation is frontend-side)"""
        # Note: Backend accepts any notes, frontend validates min 5 chars
        payload = {
            "type": "observation",
            "area": "medication",
            "outcome": "pass",
            "notes": "TEST_Short note",  # Valid notes
            "follow_up_required": False
        }
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print("PASS: Notes field accepted by backend")
    
    # ========== PUT Update Spot Check Tests ==========
    
    def test_update_spot_check(self):
        """Test updating an existing spot check"""
        # First create a spot check
        create_payload = {
            "type": "observation",
            "area": "dignity_respect",
            "outcome": "needs_improvement",
            "notes": "TEST_Initial observation - needs improvement",
            "follow_up_required": True,
            "follow_up_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        }
        create_response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            json=create_payload,
            headers=self.headers
        )
        assert create_response.status_code == 200
        check_id = create_response.json()["id"]
        
        # Now update it
        update_payload = {
            "type": "observation",
            "area": "dignity_respect",
            "outcome": "pass",
            "notes": "TEST_Follow-up observation - improvement confirmed",
            "follow_up_required": False,
            "follow_up_date": ""
        }
        update_response = requests.put(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks/{check_id}",
            json=update_payload,
            headers=self.headers
        )
        assert update_response.status_code == 200, f"Failed: {update_response.text}"
        data = update_response.json()
        assert data["success"] is True
        assert data["outcome"] == "pass"
        print(f"PASS: Updated spot check {check_id} from needs_improvement to pass")
    
    def test_update_nonexistent_spot_check(self):
        """Test updating a non-existent spot check returns 404"""
        fake_id = str(uuid.uuid4())
        update_payload = {
            "type": "observation",
            "area": "medication",
            "outcome": "pass",
            "notes": "TEST_This should fail",
            "follow_up_required": False
        }
        response = requests.put(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks/{fake_id}",
            json=update_payload,
            headers=self.headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Update non-existent spot check correctly returns 404")
    
    # ========== Spot Check Options Tests ==========
    
    def test_get_spot_check_options(self):
        """Test GET /spot-check-options returns valid options"""
        response = requests.get(
            f"{BASE_URL}/api/spot-check-options",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify structure - API returns 'types' not 'check_types'
        assert "types" in data, "Missing types"
        assert "areas" in data, "Missing areas"
        
        # Verify expected values
        check_types = [ct["value"] for ct in data["types"]]
        assert "observation" in check_types, "Missing observation type"
        assert "document_review" in check_types, "Missing document_review type"
        assert "competency_check" in check_types, "Missing competency_check type"
        assert "medication_check" in check_types, "Missing medication_check type"
        
        areas = [a["value"] for a in data["areas"]]
        assert "medication" in areas, "Missing medication area"
        assert "safeguarding" in areas, "Missing safeguarding area"
        assert "moving_handling" in areas, "Missing moving_handling area"
        
        print(f"PASS: Spot check options returned {len(check_types)} types, {len(areas)} areas")


class TestSpotChecksSummaryStats:
    """Test spot checks summary statistics"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get employee ID
        employees_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.headers
        )
        self.employee_id = employees_response.json()[0]["id"]
    
    def test_spot_checks_contain_outcome_data(self):
        """Test that spot checks contain outcome data for summary stats"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            headers=self.headers
        )
        assert response.status_code == 200
        checks = response.json()["spot_checks"]
        
        if len(checks) > 0:
            # Verify each check has required fields for summary
            for check in checks:
                assert "outcome" in check, f"Check {check.get('id')} missing outcome"
                assert check["outcome"] in ["pass", "needs_improvement", "fail"], f"Invalid outcome: {check['outcome']}"
                assert "follow_up_required" in check, f"Check {check.get('id')} missing follow_up_required"
                assert "date" in check, f"Check {check.get('id')} missing date"
            
            # Count outcomes
            pass_count = sum(1 for c in checks if c["outcome"] == "pass")
            needs_improvement_count = sum(1 for c in checks if c["outcome"] == "needs_improvement")
            fail_count = sum(1 for c in checks if c["outcome"] == "fail")
            
            print(f"PASS: Summary stats - Pass: {pass_count}, Needs Improvement: {needs_improvement_count}, Fail: {fail_count}")
        else:
            print("PASS: No spot checks found (empty state)")
    
    def test_spot_checks_follow_up_tracking(self):
        """Test that follow-up dates are properly tracked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/spot-checks",
            headers=self.headers
        )
        assert response.status_code == 200
        checks = response.json()["spot_checks"]
        
        follow_ups_required = [c for c in checks if c.get("follow_up_required")]
        follow_ups_with_date = [c for c in follow_ups_required if c.get("follow_up_date")]
        
        print(f"PASS: Follow-up tracking - {len(follow_ups_required)} required, {len(follow_ups_with_date)} with dates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

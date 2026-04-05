"""
Test Dashboard & Employee Profile Fixes
- GET /api/employees/{id}/unified-progress
- POST /api/workers/{employee_id}/send-reminder
- POST /api/employees/{employee_id}/request-renewal/{type}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestUnifiedProgressEndpoint:
    """Tests for GET /api/employees/{id}/unified-progress"""
    
    def test_unified_progress_returns_200(self, auth_headers):
        """Test that unified-progress endpoint returns 200 for valid employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: unified-progress returns 200")
    
    def test_unified_progress_schema(self, auth_headers):
        """Test that unified-progress returns correct schema"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "overall_percentage" in data, "Missing overall_percentage"
        assert "completed_requirements" in data, "Missing completed_requirements"
        assert "total_requirements" in data, "Missing total_requirements"
        assert "categories" in data, "Missing categories"
        assert "blockers" in data, "Missing blockers"
        assert "is_work_ready" in data, "Missing is_work_ready"
        
        # Validate types
        assert isinstance(data["overall_percentage"], (int, float)), "overall_percentage should be numeric"
        assert isinstance(data["completed_requirements"], int), "completed_requirements should be int"
        assert isinstance(data["total_requirements"], int), "total_requirements should be int"
        assert isinstance(data["categories"], dict), "categories should be dict"
        assert isinstance(data["blockers"], list), "blockers should be list"
        assert isinstance(data["is_work_ready"], bool), "is_work_ready should be bool"
        
        print(f"PASS: unified-progress schema is correct")
        print(f"  - overall_percentage: {data['overall_percentage']}%")
        print(f"  - completed: {data['completed_requirements']}/{data['total_requirements']}")
        print(f"  - blockers: {len(data['blockers'])}")
    
    def test_unified_progress_categories(self, auth_headers):
        """Test that categories breakdown is correct"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        categories = data.get("categories", {})
        
        # Expected categories
        expected_categories = ["documents", "forms", "training", "references", "agreements", "induction"]
        
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
            assert "completed" in categories[cat], f"Category {cat} missing 'completed'"
            assert "total" in categories[cat], f"Category {cat} missing 'total'"
        
        print(f"PASS: All categories present")
        for cat, vals in categories.items():
            print(f"  - {cat}: {vals['completed']}/{vals['total']}")
    
    def test_unified_progress_blockers_format(self, auth_headers):
        """Test that blockers are properly formatted strings"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        blockers = data.get("blockers", [])
        
        for blocker in blockers:
            assert isinstance(blocker, str), f"Blocker should be string, got {type(blocker)}"
            assert len(blocker) > 0, "Blocker should not be empty"
        
        print(f"PASS: Blockers format correct ({len(blockers)} blockers)")
    
    def test_unified_progress_404_for_invalid_employee(self, auth_headers):
        """Test that 404 is returned for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/unified-progress",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Returns 404 for invalid employee")
    
    def test_unified_progress_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress"
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Requires authentication")


class TestSendReminderEndpoint:
    """Tests for POST /api/workers/{employee_id}/send-reminder"""
    
    def test_send_reminder_returns_success(self, auth_headers):
        """Test that send-reminder endpoint returns success"""
        response = requests.post(
            f"{BASE_URL}/api/workers/{TEST_EMPLOYEE_ID}/send-reminder",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success: true"
        assert "message" in data, "Missing message field"
        assert "employee_id" in data, "Missing employee_id field"
        
        print(f"PASS: send-reminder returns success")
        print(f"  - message: {data.get('message')}")
        print(f"  - email_sent: {data.get('email_sent')}")
    
    def test_send_reminder_with_custom_message(self, auth_headers):
        """Test send-reminder with custom message"""
        response = requests.post(
            f"{BASE_URL}/api/workers/{TEST_EMPLOYEE_ID}/send-reminder",
            json={"custom_message": "Please complete your compliance items by Friday."},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        
        print(f"PASS: send-reminder with custom message works")
    
    def test_send_reminder_returns_portal_link(self, auth_headers):
        """Test that send-reminder returns portal link"""
        response = requests.post(
            f"{BASE_URL}/api/workers/{TEST_EMPLOYEE_ID}/send-reminder",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "portal_link" in data, "Missing portal_link field"
        assert "token=" in data.get("portal_link", ""), "Portal link should contain token"
        
        print(f"PASS: send-reminder returns portal link")
    
    def test_send_reminder_returns_blockers_count(self, auth_headers):
        """Test that send-reminder returns blockers count"""
        response = requests.post(
            f"{BASE_URL}/api/workers/{TEST_EMPLOYEE_ID}/send-reminder",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "blockers_sent" in data, "Missing blockers_sent field"
        assert isinstance(data["blockers_sent"], int), "blockers_sent should be int"
        
        print(f"PASS: send-reminder returns blockers_sent: {data['blockers_sent']}")
    
    def test_send_reminder_404_for_invalid_employee(self, auth_headers):
        """Test that 404 is returned for non-existent employee"""
        response = requests.post(
            f"{BASE_URL}/api/workers/invalid-employee-id-12345/send-reminder",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Returns 404 for invalid employee")
    
    def test_send_reminder_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/workers/{TEST_EMPLOYEE_ID}/send-reminder",
            json={}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Requires authentication")


class TestRequestRenewalEndpoint:
    """Tests for POST /api/employees/{employee_id}/request-renewal/{type}"""
    
    def test_request_renewal_dbs_returns_success(self, auth_headers):
        """Test that request-renewal/dbs returns success"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/dbs",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success: true"
        assert data.get("renewal_type") == "dbs", "Expected renewal_type: dbs"
        assert "item_name" in data, "Missing item_name field"
        
        print(f"PASS: request-renewal/dbs returns success")
        print(f"  - item_name: {data.get('item_name')}")
        print(f"  - email_sent: {data.get('email_sent')}")
    
    def test_request_renewal_right_to_work(self, auth_headers):
        """Test request-renewal for right_to_work"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/right_to_work",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("renewal_type") == "right_to_work"
        
        print(f"PASS: request-renewal/right_to_work works")
    
    def test_request_renewal_training_requires_training_id(self, auth_headers):
        """Test that training renewal requires training_id"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/training",
            json={},
            headers=auth_headers
        )
        # Should return 400 because training_id is required
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"PASS: training renewal requires training_id")
    
    def test_request_renewal_training_with_id(self, auth_headers):
        """Test training renewal with training_id"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/training",
            json={"training_id": "safeguarding"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("renewal_type") == "training"
        
        print(f"PASS: request-renewal/training with training_id works")
    
    def test_request_renewal_identity(self, auth_headers):
        """Test request-renewal for identity"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/identity",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("renewal_type") == "identity"
        
        print(f"PASS: request-renewal/identity works")
    
    def test_request_renewal_proof_of_address(self, auth_headers):
        """Test request-renewal for proof_of_address"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/proof_of_address",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("renewal_type") == "proof_of_address"
        
        print(f"PASS: request-renewal/proof_of_address works")
    
    def test_request_renewal_invalid_type(self, auth_headers):
        """Test that invalid renewal type returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/invalid_type",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: Returns 400 for invalid renewal type")
    
    def test_request_renewal_returns_portal_link(self, auth_headers):
        """Test that request-renewal returns portal link"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/dbs",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "portal_link" in data, "Missing portal_link field"
        assert "token=" in data.get("portal_link", ""), "Portal link should contain token"
        
        print(f"PASS: request-renewal returns portal link")
    
    def test_request_renewal_404_for_invalid_employee(self, auth_headers):
        """Test that 404 is returned for non-existent employee"""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/request-renewal/dbs",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Returns 404 for invalid employee")
    
    def test_request_renewal_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-renewal/dbs",
            json={}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Requires authentication")


class TestDashboardStats:
    """Tests for dashboard stats endpoint"""
    
    def test_dashboard_stats_returns_200(self, auth_headers):
        """Test that dashboard stats returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: dashboard/stats returns 200")
    
    def test_staff_employees_returns_200(self, auth_headers):
        """Test that staff/employees returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/staff/employees",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return employees list
        employees = data.get("employees", data) if isinstance(data, dict) else data
        assert isinstance(employees, list), "Should return list of employees"
        
        print(f"PASS: staff/employees returns {len(employees)} employees")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Phase 18: Promotion Routes Module Tests

Tests for the extracted promotion routes:
- GET /api/employees/{id}/promotion-status - Check promotion eligibility
- POST /api/employees/{id}/auto-promote - Auto-promote if all checks pass
- POST /api/employees/{id}/force-promote - Admin override promotion

Also includes regression tests for previous phases:
- Phase 17: Professional registration endpoints
- Phase 16: Contract endpoints
- Auth and employees endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestAuthLogin:
    """Authentication tests - must pass before other tests"""
    
    def test_admin_login_success(self):
        """Test admin login returns valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["role"] == "admin", "User is not admin"
        print(f"✓ Admin login successful, role: {data['user']['role']}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPromotionStatus:
    """Tests for GET /api/employees/{id}/promotion-status"""
    
    def test_get_promotion_status_success(self, auth_headers):
        """Test getting promotion status for an employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/promotion-status",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "employee_id" in data, "Missing employee_id"
        assert "employee_name" in data, "Missing employee_name"
        assert "current_status" in data, "Missing current_status"
        assert "can_promote" in data, "Missing can_promote"
        assert "checks" in data, "Missing checks"
        assert "passed_count" in data, "Missing passed_count"
        assert "total_count" in data, "Missing total_count"
        assert "missing_checks" in data, "Missing missing_checks"
        assert "nhs_status" in data, "Missing nhs_status"
        
        # Verify data types
        assert isinstance(data["can_promote"], bool), "can_promote should be boolean"
        assert isinstance(data["checks"], dict), "checks should be dict"
        assert isinstance(data["passed_count"], int), "passed_count should be int"
        assert isinstance(data["total_count"], int), "total_count should be int"
        assert isinstance(data["missing_checks"], list), "missing_checks should be list"
        
        print(f"✓ Promotion status retrieved: can_promote={data['can_promote']}, "
              f"passed={data['passed_count']}/{data['total_count']}")
    
    def test_get_promotion_status_invalid_employee(self, auth_headers):
        """Test promotion status for non-existent employee returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/promotion-status",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid employee returns 404")
    
    def test_get_promotion_status_unauthorized(self):
        """Test promotion status without auth returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/promotion-status"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthorized request returns 401")


class TestAutoPromote:
    """Tests for POST /api/employees/{id}/auto-promote"""
    
    def test_auto_promote_endpoint_exists(self, auth_headers):
        """Test auto-promote endpoint is accessible"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/auto-promote",
            headers=auth_headers
        )
        # Should return 200 with success/failure info, not 404
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}, {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Missing success field"
        assert "message" in data, "Missing message field"
        
        if data.get("promoted"):
            assert "new_status" in data, "Missing new_status when promoted"
            print(f"✓ Auto-promote succeeded: {data['message']}")
        else:
            # If not promoted, should have reason
            print(f"✓ Auto-promote response: {data['message']}")
    
    def test_auto_promote_invalid_employee(self, auth_headers):
        """Test auto-promote for non-existent employee returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/auto-promote",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Auto-promote invalid employee returns 404")
    
    def test_auto_promote_unauthorized(self):
        """Test auto-promote without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/auto-promote"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Auto-promote unauthorized returns 401")


class TestForcePromote:
    """Tests for POST /api/employees/{id}/force-promote"""
    
    def test_force_promote_requires_reason(self, auth_headers):
        """Test force-promote requires a reason of at least 10 characters"""
        # Test with short reason
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/force-promote",
            headers=auth_headers,
            json={"reason": "short"}
        )
        # Should fail validation - reason too short
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✓ Force-promote rejects short reason")
    
    def test_force_promote_requires_reason_field(self, auth_headers):
        """Test force-promote requires reason field"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/force-promote",
            headers=auth_headers,
            json={}
        )
        # Should fail validation - missing reason
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Force-promote requires reason field")
    
    def test_force_promote_invalid_employee(self, auth_headers):
        """Test force-promote for non-existent employee returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/force-promote",
            headers=auth_headers,
            json={"reason": "Testing force promote with valid reason length"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Force-promote invalid employee returns 404")
    
    def test_force_promote_unauthorized(self):
        """Test force-promote without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/force-promote",
            json={"reason": "Testing force promote with valid reason length"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Force-promote unauthorized returns 401")


class TestRegressionPhase17ProfessionalRegistration:
    """Regression tests for Phase 17 - Professional Registration endpoints"""
    
    def test_professional_registration_requirements(self, auth_headers):
        """Test GET /api/professional-registration-requirements"""
        response = requests.get(
            f"{BASE_URL}/api/professional-registration-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "valid_bodies" in data, "Missing valid_bodies"
        # valid_bodies is a list of objects with value, label, url
        body_values = [b.get("value") for b in data["valid_bodies"]]
        assert "NMC" in body_values, "NMC should be in valid bodies"
        print(f"✓ Professional registration requirements: {len(data['valid_bodies'])} bodies")
    
    def test_employee_professional_registrations(self, auth_headers):
        """Test GET /api/employees/{id}/professional-registrations"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registrations",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "registrations" in data, "Missing registrations"
        print(f"✓ Employee professional registrations retrieved")


class TestRegressionPhase16Contracts:
    """Regression tests for Phase 16 - Contract endpoints"""
    
    def test_contract_templates(self, auth_headers):
        """Test GET /api/contract-templates"""
        response = requests.get(
            f"{BASE_URL}/api/contract-templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "templates" in data, "Missing templates"
        print(f"✓ Contract templates: {len(data['templates'])} templates")
    
    def test_can_sign_contract(self, auth_headers):
        """Test GET /api/employees/{id}/can-sign-contract"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/can-sign-contract",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "can_sign" in data, "Missing can_sign"
        print(f"✓ Can sign contract: {data['can_sign']}")
    
    def test_contract_preview(self, auth_headers):
        """Test GET /api/employees/{id}/contract/preview"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contract/preview",
            headers=auth_headers
        )
        # May return 200 or 400 depending on employee data
        assert response.status_code in [200, 400], f"Unexpected: {response.status_code}"
        print(f"✓ Contract preview endpoint accessible")


class TestRegressionAuthEmployees:
    """Regression tests for Auth and Employees endpoints"""
    
    def test_employees_list(self, auth_headers):
        """Test GET /api/employees"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"✓ Employees list: {len(data)} employees")
    
    def test_employee_by_id(self, auth_headers):
        """Test GET /api/employees/{id}"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data, "Missing id"
        assert data["id"] == TEST_EMPLOYEE_ID, "ID mismatch"
        print(f"✓ Employee by ID: {data.get('first_name')} {data.get('last_name')}")


class TestRegressionInterviewsForms:
    """Regression tests for Interviews and Forms endpoints"""
    
    def test_interview_config(self, auth_headers):
        """Test GET /api/interview-config/{role}"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/support_worker",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "questions" in data or "role" in data, "Missing expected fields"
        print(f"✓ Interview config retrieved")
    
    def test_form_templates(self, auth_headers):
        """Test GET /api/form-submissions/templates"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"✓ Form templates: {len(data)} templates")


class TestRegressionServiceUsersCompliance:
    """Regression tests for Service Users and Compliance endpoints"""
    
    def test_service_users_list(self, auth_headers):
        """Test GET /api/service-users"""
        response = requests.get(
            f"{BASE_URL}/api/service-users",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"✓ Service users: {len(data)} users")
    
    def test_compliance_policies(self, auth_headers):
        """Test GET /api/compliance/policies"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list"
        print(f"✓ Compliance policies: {len(data)} policies")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

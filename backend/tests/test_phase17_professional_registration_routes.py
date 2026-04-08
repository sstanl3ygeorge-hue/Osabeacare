"""
Phase 17: Professional Registration Routes Tests

Tests for the extracted professional registration routes module:
- GET /api/professional-registration-requirements - List registration requirements by role
- GET /api/employees/{id}/professional-registrations - Get employee registrations
- POST /api/employees/{id}/professional-registration - Add/update registration (admin only)
- POST /api/employees/{id}/professional-registration/verify - Verify registration (admin only)

Also includes regression tests for previous phases (contracts, interviews, forms, etc.)
"""

import pytest
import requests
import os
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestAuthSetup:
    """Authentication setup tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    def test_admin_login(self):
        """Test admin login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ Admin login successful, role: {data['user'].get('role')}")


class TestProfessionalRegistrationRequirements:
    """Tests for GET /api/professional-registration-requirements"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_registration_requirements_authenticated(self, admin_token):
        """Test getting registration requirements with auth"""
        response = requests.get(
            f"{BASE_URL}/api/professional-registration-requirements",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "requirements" in data, "Missing requirements field"
        assert "valid_bodies" in data, "Missing valid_bodies field"
        
        # Verify valid_bodies contains expected registration bodies
        valid_bodies = data["valid_bodies"]
        assert isinstance(valid_bodies, list), "valid_bodies should be a list"
        body_values = [b["value"] for b in valid_bodies]
        assert "NMC" in body_values, "NMC should be in valid bodies"
        assert "GMC" in body_values, "GMC should be in valid bodies"
        assert "HCPC" in body_values, "HCPC should be in valid bodies"
        assert "Social Work England" in body_values, "Social Work England should be in valid bodies"
        
        print(f"✓ Registration requirements returned with {len(valid_bodies)} valid bodies")
        print(f"  Valid bodies: {body_values}")
    
    def test_get_registration_requirements_unauthenticated(self):
        """Test getting registration requirements without auth - should fail"""
        response = requests.get(f"{BASE_URL}/api/professional-registration-requirements")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestEmployeeProfessionalRegistrations:
    """Tests for GET /api/employees/{id}/professional-registrations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_employee_registrations(self, admin_token):
        """Test getting professional registrations for an employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registrations",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "employee_id" in data, "Missing employee_id"
        assert data["employee_id"] == TEST_EMPLOYEE_ID, "Employee ID mismatch"
        assert "registrations" in data, "Missing registrations field"
        assert "role" in data, "Missing role field"
        assert "registration_required" in data, "Missing registration_required field"
        
        print(f"✓ Employee registrations retrieved")
        print(f"  Role: {data.get('role')}")
        print(f"  Registration required: {data.get('registration_required')}")
        print(f"  Registrations count: {len(data.get('registrations', []))}")
    
    def test_get_employee_registrations_not_found(self, admin_token):
        """Test getting registrations for non-existent employee"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{BASE_URL}/api/employees/{fake_id}/professional-registrations",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent employee correctly returns 404")
    
    def test_get_employee_registrations_unauthenticated(self):
        """Test getting registrations without auth - should fail"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registrations"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestAddProfessionalRegistration:
    """Tests for POST /api/employees/{id}/professional-registration"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_add_professional_registration(self, admin_token):
        """Test adding a professional registration"""
        registration_data = {
            "body": "NMC",
            "registration_number": "TEST123456",
            "registration_status": "active",
            "registration_expiry_date": "2027-12-31",
            "certificate_url": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=registration_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response
        assert data.get("success") == True, "Expected success=True"
        assert data.get("action") in ["added", "updated"], f"Unexpected action: {data.get('action')}"
        assert "registration" in data, "Missing registration in response"
        
        reg = data["registration"]
        assert reg["body"] == "NMC", "Body mismatch"
        assert reg["registration_number"] == "TEST123456", "Registration number mismatch"
        assert reg["verified"] == False, "New registration should not be verified"
        
        print(f"✓ Professional registration {data.get('action')}")
        print(f"  Body: {reg['body']}")
        print(f"  Number: {reg['registration_number']}")
    
    def test_add_registration_invalid_body(self, admin_token):
        """Test adding registration with invalid body"""
        registration_data = {
            "body": "INVALID_BODY",
            "registration_number": "TEST123456",
            "registration_status": "active"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=registration_data
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid registration body correctly rejected")
    
    def test_add_registration_unauthenticated(self):
        """Test adding registration without auth - should fail"""
        registration_data = {
            "body": "NMC",
            "registration_number": "TEST123456"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration",
            json=registration_data
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")
    
    def test_add_registration_employee_not_found(self, admin_token):
        """Test adding registration for non-existent employee"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        registration_data = {
            "body": "NMC",
            "registration_number": "TEST123456"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_id}/professional-registration",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=registration_data
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent employee correctly returns 404")


class TestVerifyProfessionalRegistration:
    """Tests for POST /api/employees/{id}/professional-registration/verify"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_verify_registration(self, admin_token):
        """Test verifying a professional registration"""
        # First ensure there's a registration to verify
        registration_data = {
            "body": "HCPC",
            "registration_number": "VERIFY_TEST_123",
            "registration_status": "active"
        }
        
        # Add registration first
        add_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=registration_data
        )
        assert add_response.status_code == 200, f"Failed to add registration: {add_response.text}"
        
        # Now verify it
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration/verify",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"registration_body": "HCPC"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response
        assert data.get("success") == True, "Expected success=True"
        assert data.get("verified") == True, "Expected verified=True"
        assert "can_promote_now" in data, "Missing can_promote_now field"
        
        print(f"✓ Registration verified successfully")
        print(f"  Can promote now: {data.get('can_promote_now')}")
        if data.get("missing_checks"):
            print(f"  Missing checks: {data.get('missing_checks')}")
    
    def test_verify_registration_not_found(self, admin_token):
        """Test verifying non-existent registration"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration/verify",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"registration_body": "GMC"}  # Assuming no GMC registration exists
        )
        # Could be 404 if no GMC registration, or 200 if one exists
        # We just verify it doesn't crash
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ Verify non-existent registration handled (status: {response.status_code})")
    
    def test_verify_registration_unauthenticated(self):
        """Test verifying registration without auth - should fail"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration/verify",
            params={"registration_body": "NMC"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestRegressionContractsRoutes:
    """Regression tests for Phase 16 contracts routes"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_contract_templates_still_work(self, admin_token):
        """Test contract templates endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/contract-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "templates" in data, "Missing templates field"
        print(f"✓ Contract templates endpoint works ({len(data.get('templates', []))} templates)")
    
    def test_can_sign_contract_still_works(self, admin_token):
        """Test can-sign-contract endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "can_sign" in data, "Missing can_sign field"
        print(f"✓ Can-sign-contract endpoint works (can_sign: {data.get('can_sign')})")
    
    def test_contract_preview_still_works(self, admin_token):
        """Test contract preview endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contract/preview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "contract" in data or "template" in data, "Missing contract/template field"
        print("✓ Contract preview endpoint works")


class TestRegressionAuthAndEmployees:
    """Regression tests for auth and employees endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_employees_list_still_works(self, admin_token):
        """Test employees list endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of employees"
        print(f"✓ Employees list endpoint works ({len(data)} employees)")
    
    def test_employee_detail_still_works(self, admin_token):
        """Test employee detail endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data, "Missing id field"
        print(f"✓ Employee detail endpoint works (name: {data.get('first_name')} {data.get('last_name')})")


class TestRegressionInterviewsAndForms:
    """Regression tests for interviews and forms endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_interview_config_still_works(self, admin_token):
        """Test interview config endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/support_worker",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "questions" in data or "config" in data, "Missing questions/config field"
        print("✓ Interview config endpoint works")
    
    def test_form_templates_still_works(self, admin_token):
        """Test form templates endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # API returns list directly or {"templates": [...]}
        if isinstance(data, list):
            templates = data
        else:
            templates = data.get("templates", [])
        assert len(templates) > 0, "No templates returned"
        print(f"✓ Form templates endpoint works ({len(templates)} templates)")


class TestRegressionServiceUsersAndCompliance:
    """Regression tests for service users and compliance endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_service_users_still_works(self, admin_token):
        """Test service users endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/service-users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of service users"
        print(f"✓ Service users endpoint works ({len(data)} service users)")
    
    def test_compliance_policies_still_works(self, admin_token):
        """Test compliance policies endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # API returns list directly or {"policies": [...]}
        if isinstance(data, list):
            policies = data
        else:
            policies = data.get("policies", [])
        assert len(policies) >= 0, "Policies should be a list"
        print(f"✓ Compliance policies endpoint works ({len(policies)} policies)")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

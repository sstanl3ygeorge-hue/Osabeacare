"""
Phase 19: Roles Routes Module Tests

Tests for the extracted roles routes module:
- GET /api/roles - List all available roles
- GET /api/roles/{role}/requirements - Get role-specific requirements
- GET /api/roles/summary - Get summary of all role requirements

Regression tests for previous phases:
- Phase 18: Promotion endpoints
- Phase 17: Professional registration endpoints
- Phase 16: Contract endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestAuthSetup:
    """Authentication setup for tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}


class TestRolesEndpoints(TestAuthSetup):
    """Test Phase 19 roles routes"""
    
    def test_get_roles_list(self):
        """GET /api/roles - List all available roles (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/roles")
        
        assert response.status_code == 200, f"Failed to get roles: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one role"
        
        # Verify expected roles are present
        expected_roles = [
            "Care Assistant",
            "Senior Care Assistant",
            "Support Worker",
            "Healthcare Assistant",
            "Live-in Carer",
            "Night Carer",
            "Team Leader",
            "Care Coordinator"
        ]
        
        for role in expected_roles:
            assert role in data, f"Expected role '{role}' not found in response"
        
        print(f"✓ GET /api/roles returned {len(data)} roles")
    
    def test_get_role_requirements_care_assistant(self, auth_headers):
        """GET /api/roles/{role}/requirements - Get requirements for Care Assistant"""
        role = "Care Assistant"
        response = requests.get(
            f"{BASE_URL}/api/roles/{role}/requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to get role requirements: {response.text}"
        
        data = response.json()
        assert "role" in data, "Response should have 'role' field"
        assert data["role"] == role, f"Role should be '{role}'"
        assert "is_nurse_role" in data, "Response should have 'is_nurse_role' field"
        assert data["is_nurse_role"] == False, "Care Assistant should not be a nurse role"
        assert "requirements" in data, "Response should have 'requirements' field"
        assert "total_gates" in data, "Response should have 'total_gates' field"
        assert data["total_gates"] == 12, "Non-nurse role should have 12 gates"
        assert "gates_breakdown" in data, "Response should have 'gates_breakdown' field"
        
        print(f"✓ GET /api/roles/{role}/requirements - total_gates: {data['total_gates']}")
    
    def test_get_role_requirements_nurse(self, auth_headers):
        """GET /api/roles/{role}/requirements - Get requirements for Nurse role"""
        role = "Nurse"
        response = requests.get(
            f"{BASE_URL}/api/roles/{role}/requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to get nurse requirements: {response.text}"
        
        data = response.json()
        assert data["role"] == role, f"Role should be '{role}'"
        assert data["is_nurse_role"] == True, "Nurse should be a nurse role"
        assert data["total_gates"] == 14, "Nurse role should have 14 gates"
        
        # Check nurse-specific gates breakdown
        gates_breakdown = data.get("gates_breakdown", {})
        assert gates_breakdown.get("base_gates") == 12, "Base gates should be 12"
        assert gates_breakdown.get("nurse_additional") == 2, "Nurse should have 2 additional gates"
        assert "NMC Registration" in gates_breakdown.get("nurse_additions", []), "Should include NMC Registration"
        assert "Professional Indemnity Insurance" in gates_breakdown.get("nurse_additions", []), "Should include Professional Indemnity Insurance"
        
        print(f"✓ GET /api/roles/{role}/requirements - nurse role with {data['total_gates']} gates")
    
    def test_get_role_requirements_support_worker(self, auth_headers):
        """GET /api/roles/{role}/requirements - Get requirements for Support Worker"""
        role = "Support Worker"
        response = requests.get(
            f"{BASE_URL}/api/roles/{role}/requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to get role requirements: {response.text}"
        
        data = response.json()
        assert data["role"] == role
        assert data["is_nurse_role"] == False
        assert data["total_gates"] == 12
        
        print(f"✓ GET /api/roles/{role}/requirements - verified")
    
    def test_get_role_requirements_unauthorized(self):
        """GET /api/roles/{role}/requirements - Should require authentication"""
        role = "Care Assistant"
        response = requests.get(f"{BASE_URL}/api/roles/{role}/requirements")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
        print("✓ GET /api/roles/{role}/requirements requires authentication")
    
    def test_get_roles_summary(self, auth_headers):
        """GET /api/roles/summary - Get summary of all role requirements"""
        response = requests.get(
            f"{BASE_URL}/api/roles/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to get roles summary: {response.text}"
        
        data = response.json()
        assert "roles" in data, "Response should have 'roles' field"
        assert "note" in data, "Response should have 'note' field"
        assert "Osabea" in data["note"], "Note should mention Osabea"
        
        roles_summary = data.get("roles", {})
        assert isinstance(roles_summary, dict), "Roles should be a dictionary"
        
        print(f"✓ GET /api/roles/summary - returned summary with {len(roles_summary)} roles")
    
    def test_get_roles_summary_unauthorized(self):
        """GET /api/roles/summary - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/roles/summary")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
        print("✓ GET /api/roles/summary requires authentication")


class TestRegressionPhase18Promotion(TestAuthSetup):
    """Regression tests for Phase 18 - Promotion endpoints"""
    
    def test_get_promotion_status(self, auth_headers):
        """GET /api/employees/{id}/promotion-status - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/promotion-status",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Promotion status failed: {response.text}"
        
        data = response.json()
        assert "can_promote" in data, "Response should have 'can_promote' field"
        assert "checks" in data, "Response should have 'checks' field"
        
        print(f"✓ Phase 18 regression: GET /api/employees/{TEST_EMPLOYEE_ID}/promotion-status works")
    
    def test_auto_promote_endpoint_exists(self, auth_headers):
        """POST /api/employees/{id}/auto-promote - Endpoint should exist"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/auto-promote",
            headers=auth_headers
        )
        
        # Should return 200 (success) or 400 (cannot promote) - not 404
        assert response.status_code != 404, "Auto-promote endpoint should exist"
        
        print(f"✓ Phase 18 regression: POST /api/employees/{TEST_EMPLOYEE_ID}/auto-promote endpoint exists")
    
    def test_force_promote_requires_reason(self, auth_headers):
        """POST /api/employees/{id}/force-promote - Should require reason"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/force-promote",
            headers=auth_headers,
            json={}  # No reason provided
        )
        
        # Should return 422 (validation error) for missing reason
        assert response.status_code in [400, 422], f"Expected 400/422 for missing reason, got {response.status_code}"
        
        print("✓ Phase 18 regression: Force promote requires reason")


class TestRegressionPhase17ProfessionalRegistration(TestAuthSetup):
    """Regression tests for Phase 17 - Professional registration endpoints"""
    
    def test_get_professional_registration_requirements(self, auth_headers):
        """GET /api/professional-registration-requirements - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/professional-registration-requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Professional registration requirements failed: {response.text}"
        
        data = response.json()
        # Response is a dict with 'requirements' and 'valid_bodies' keys
        assert "requirements" in data, "Response should have 'requirements' field"
        assert "valid_bodies" in data, "Response should have 'valid_bodies' field"
        
        print(f"✓ Phase 17 regression: GET /api/professional-registration-requirements works")
    
    def test_get_employee_professional_registrations(self, auth_headers):
        """GET /api/employees/{id}/professional-registrations - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registrations",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Employee professional registrations failed: {response.text}"
        
        data = response.json()
        assert "registrations" in data, "Response should have 'registrations' field"
        
        print(f"✓ Phase 17 regression: GET /api/employees/{TEST_EMPLOYEE_ID}/professional-registrations works")


class TestRegressionPhase16Contracts(TestAuthSetup):
    """Regression tests for Phase 16 - Contract endpoints"""
    
    def test_get_contract_templates(self, auth_headers):
        """GET /api/contract-templates - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/contract-templates",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Contract templates failed: {response.text}"
        
        data = response.json()
        # Response is a dict with 'templates' key
        assert "templates" in data, "Response should have 'templates' field"
        assert isinstance(data["templates"], list), "Templates should be a list"
        
        print(f"✓ Phase 16 regression: GET /api/contract-templates works")
    
    def test_can_sign_contract(self, auth_headers):
        """GET /api/employees/{id}/can-sign-contract - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/can-sign-contract",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Can sign contract failed: {response.text}"
        
        data = response.json()
        assert "can_sign" in data, "Response should have 'can_sign' field"
        
        print(f"✓ Phase 16 regression: GET /api/employees/{TEST_EMPLOYEE_ID}/can-sign-contract works")
    
    def test_contract_preview(self, auth_headers):
        """GET /api/employees/{id}/contract/preview - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contract/preview",
            headers=auth_headers
        )
        
        # Should return 200 or 400 (if employee not eligible) - not 404
        assert response.status_code != 404, "Contract preview endpoint should exist"
        
        print(f"✓ Phase 16 regression: GET /api/employees/{TEST_EMPLOYEE_ID}/contract/preview endpoint exists")


class TestRegressionCoreEndpoints(TestAuthSetup):
    """Regression tests for core endpoints"""
    
    def test_auth_login(self):
        """POST /api/auth/login - Should still work"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        assert "token" in response.json(), "Login should return token"
        
        print("✓ Core regression: POST /api/auth/login works")
    
    def test_get_employees(self, auth_headers):
        """GET /api/employees - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Get employees failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Core regression: GET /api/employees works ({len(data)} employees)")
    
    def test_get_employee_by_id(self, auth_headers):
        """GET /api/employees/{id} - Should still work"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Get employee failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have 'id' field"
        assert data["id"] == TEST_EMPLOYEE_ID, "Employee ID should match"
        
        print(f"✓ Core regression: GET /api/employees/{TEST_EMPLOYEE_ID} works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

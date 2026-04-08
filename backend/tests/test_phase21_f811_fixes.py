"""
Phase 21: F811 Duplicate Definition Fixes - Regression Tests

Tests to verify that the F811 fixes (duplicate definitions removal) in server.py
did not break any functionality. Tests cover:
1. Auth login and employee listing
2. Employment history update endpoint
3. Regression tests for Phases 16-20 (contracts, professional registration, promotion, roles, policy assignments)

F811 fixes applied:
- Removed duplicate update_employment_history function
- Renamed extract_employment_history_from_cv helper to _extract_cv_employment_history_helper
- Removed duplicate PIL import (already imported as PILImage)
- Removed duplicate MIN_GAP_DAYS (imported from employment_gap_engine)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

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
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}


# ==================== CORE AUTH & EMPLOYEE TESTS ====================

class TestAuthLogin(TestAuthSetup):
    """Tests for authentication login endpoint"""
    
    def test_auth_login_success(self):
        """Test POST /api/auth/login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user info"
        print("✓ POST /api/auth/login working with valid credentials")
    
    def test_auth_login_invalid_credentials(self):
        """Test POST /api/auth/login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 400], f"Expected 401/400, got {response.status_code}"
        print("✓ POST /api/auth/login correctly rejects invalid credentials")


class TestEmployeeListing(TestAuthSetup):
    """Tests for employee listing endpoint"""
    
    def test_get_employees_list(self, auth_headers):
        """Test GET /api/employees returns list of employees"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/employees returned {len(data)} employees")
    
    def test_get_employees_unauthenticated(self):
        """Test GET /api/employees without auth is rejected"""
        response = requests.get(f"{BASE_URL}/api/employees")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/employees correctly rejects unauthenticated requests")


# ==================== EMPLOYMENT HISTORY TESTS ====================

class TestEmploymentHistoryUpdate(TestAuthSetup):
    """Tests for employment history update endpoint"""
    
    def test_add_employment_history_entry(self, auth_headers):
        """Test POST /api/employees/{id}/employment-history-add"""
        test_entry = {
            "employer": "Test Company Ltd",
            "job_title": "Care Assistant",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "is_current": False,
            "duties": "Providing care to elderly residents",
            "reason_for_leaving": "Career progression"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-history-add",
            json=test_entry,
            headers=auth_headers
        )
        
        # Could be 200 (success) or 404 (employee not found)
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Response should indicate success"
            assert "entry_id" in data, "Response should contain entry_id"
            print(f"✓ Employment history entry added: {data.get('entry_id')}")
        elif response.status_code == 404:
            print(f"✓ Employee {TEST_EMPLOYEE_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, {response.text}")
    
    def test_add_employment_history_invalid_employee(self, auth_headers):
        """Test adding employment history to non-existent employee"""
        fake_id = str(uuid.uuid4())
        test_entry = {
            "employer": "Test Company",
            "job_title": "Test Role",
            "start_date": "2023-01-01"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_id}/employment-history-add",
            json=test_entry,
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent employee correctly returns 404")
    
    def test_add_employment_history_unauthenticated(self):
        """Test adding employment history without auth is rejected"""
        test_entry = {
            "employer": "Test Company",
            "job_title": "Test Role",
            "start_date": "2023-01-01"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-history-add",
            json=test_entry
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Employment history add correctly rejects unauthenticated requests")


# ==================== PHASE 20: POLICY ASSIGNMENTS REGRESSION ====================

class TestRegressionPhase20PolicyAssignments(TestAuthSetup):
    """Regression tests for Phase 20 - Policy Assignments endpoints"""
    
    def test_list_policy_assignments(self, auth_headers):
        """Test GET /api/policy-assignments"""
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/policy-assignments returned {len(data)} assignments")
    
    def test_list_policy_assignments_with_filter(self, auth_headers):
        """Test GET /api/policy-assignments with employee_id filter"""
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"employee_id": TEST_EMPLOYEE_ID},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/policy-assignments with filter returned {len(data)} assignments")


# ==================== PHASE 19: ROLES REGRESSION ====================

class TestRegressionPhase19Roles(TestAuthSetup):
    """Regression tests for Phase 19 - Roles endpoints"""
    
    def test_get_roles_list(self):
        """Test GET /api/roles returns list of roles"""
        response = requests.get(f"{BASE_URL}/api/roles")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one role"
        print(f"✓ GET /api/roles returned {len(data)} roles")
    
    def test_get_role_requirements(self, auth_headers):
        """Test GET /api/roles/{role}/requirements"""
        response = requests.get(
            f"{BASE_URL}/api/roles/Care%20Assistant/requirements",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "role" in data, "Response should contain role"
        assert "requirements" in data, "Response should contain requirements"
        print(f"✓ GET /api/roles/Care Assistant/requirements returned {data.get('total_gates', 0)} gates")
    
    def test_get_roles_summary(self, auth_headers):
        """Test GET /api/roles/summary"""
        response = requests.get(
            f"{BASE_URL}/api/roles/summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "roles" in data, "Response should contain roles"
        print(f"✓ GET /api/roles/summary returned {len(data.get('roles', {}))} role summaries")


# ==================== PHASE 18: PROMOTION REGRESSION ====================

class TestRegressionPhase18Promotion(TestAuthSetup):
    """Regression tests for Phase 18 - Promotion endpoints"""
    
    def test_get_promotion_status(self, auth_headers):
        """Test GET /api/employees/{id}/promotion-status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/promotion-status",
            headers=auth_headers
        )
        # Could be 200 or 404 if employee doesn't exist
        if response.status_code == 200:
            data = response.json()
            assert "employee_id" in data or "current_status" in data, \
                "Response should contain promotion status info"
            print(f"✓ GET /api/employees/{TEST_EMPLOYEE_ID}/promotion-status returned status")
        elif response.status_code == 404:
            print(f"✓ Employee {TEST_EMPLOYEE_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_auto_promote_endpoint_exists(self, auth_headers):
        """Test POST /api/employees/{id}/auto-promote endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/auto-promote",
            headers=auth_headers
        )
        # Should not be 404 (endpoint not found) or 405 (method not allowed)
        assert response.status_code not in [404, 405], \
            f"Endpoint should exist, got {response.status_code}"
        print(f"✓ POST /api/employees/{TEST_EMPLOYEE_ID}/auto-promote endpoint exists (status: {response.status_code})")
    
    def test_force_promote_endpoint_exists(self, auth_headers):
        """Test POST /api/employees/{id}/force-promote endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/force-promote",
            json={"target_status": "active", "reason": "Test"},
            headers=auth_headers
        )
        # Should not be 404 (endpoint not found) or 405 (method not allowed)
        assert response.status_code not in [404, 405], \
            f"Endpoint should exist, got {response.status_code}"
        print(f"✓ POST /api/employees/{TEST_EMPLOYEE_ID}/force-promote endpoint exists (status: {response.status_code})")


# ==================== PHASE 17: PROFESSIONAL REGISTRATION REGRESSION ====================

class TestRegressionPhase17ProfessionalRegistration(TestAuthSetup):
    """Regression tests for Phase 17 - Professional Registration endpoints"""
    
    def test_get_professional_registrations(self, auth_headers):
        """Test GET /api/employees/{id}/professional-registrations"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registrations",
            headers=auth_headers
        )
        # Could be 200 or 404 if employee doesn't exist
        if response.status_code == 200:
            data = response.json()
            # API returns object with registrations list
            assert isinstance(data, dict), "Response should be a dict"
            assert "registrations" in data, "Response should contain registrations key"
            registrations = data.get("registrations", [])
            assert isinstance(registrations, list), "registrations should be a list"
            print(f"✓ GET /api/employees/{TEST_EMPLOYEE_ID}/professional-registrations returned {len(registrations)} registrations")
        elif response.status_code == 404:
            print(f"✓ Employee {TEST_EMPLOYEE_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_get_professional_registration_requirements(self, auth_headers):
        """Test GET /api/professional-registration-requirements"""
        response = requests.get(
            f"{BASE_URL}/api/professional-registration-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
        print(f"✓ GET /api/professional-registration-requirements returned requirements")
    
    def test_add_professional_registration_endpoint_exists(self, auth_headers):
        """Test POST /api/employees/{id}/professional-registration endpoint exists"""
        # Test with minimal data to check endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/professional-registration",
            json={
                "registration_type": "NMC",
                "registration_number": "TEST123456",
                "expiry_date": "2026-12-31"
            },
            headers=auth_headers
        )
        # Should not be 404 (endpoint not found) or 405 (method not allowed)
        assert response.status_code not in [404, 405], \
            f"Endpoint should exist, got {response.status_code}"
        print(f"✓ POST /api/employees/{TEST_EMPLOYEE_ID}/professional-registration endpoint exists (status: {response.status_code})")


# ==================== PHASE 16: CONTRACTS REGRESSION ====================

class TestRegressionPhase16Contracts(TestAuthSetup):
    """Regression tests for Phase 16 - Contracts endpoints"""
    
    def test_get_contract_templates(self, auth_headers):
        """Test GET /api/contract-templates"""
        response = requests.get(
            f"{BASE_URL}/api/contract-templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # API returns object with templates list
        assert isinstance(data, dict), "Response should be a dict"
        assert "templates" in data, "Response should contain templates key"
        templates = data.get("templates", [])
        assert isinstance(templates, list), "templates should be a list"
        print(f"✓ GET /api/contract-templates returned {len(templates)} templates")
    
    def test_get_employee_can_sign_contract(self, auth_headers):
        """Test GET /api/employees/{id}/can-sign-contract"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/can-sign-contract",
            headers=auth_headers
        )
        # Could be 200 or 404 if employee doesn't exist
        if response.status_code == 200:
            data = response.json()
            assert "can_sign" in data, "Response should contain can_sign field"
            print(f"✓ GET /api/employees/{TEST_EMPLOYEE_ID}/can-sign-contract returned can_sign={data.get('can_sign')}")
        elif response.status_code == 404:
            print(f"✓ Employee {TEST_EMPLOYEE_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_get_employee_contracts(self, auth_headers):
        """Test GET /api/employees/{id}/contracts"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contracts",
            headers=auth_headers
        )
        # Could be 200 or 404 if employee doesn't exist
        if response.status_code == 200:
            data = response.json()
            # API returns object with contracts list
            assert isinstance(data, dict), "Response should be a dict"
            assert "contracts" in data, "Response should contain contracts key"
            contracts = data.get("contracts", [])
            assert isinstance(contracts, list), "contracts should be a list"
            print(f"✓ GET /api/employees/{TEST_EMPLOYEE_ID}/contracts returned {len(contracts)} contracts")
        elif response.status_code == 404:
            print(f"✓ Employee {TEST_EMPLOYEE_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_get_employee_contract_status(self, auth_headers):
        """Test GET /api/employees/{id}/contract/status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contract/status",
            headers=auth_headers
        )
        # Could be 200 or 404 if employee doesn't exist
        if response.status_code == 200:
            data = response.json()
            assert "has_contract" in data or "status" in data, \
                "Response should contain contract status info"
            print(f"✓ GET /api/employees/{TEST_EMPLOYEE_ID}/contract/status returned status")
        elif response.status_code == 404:
            print(f"✓ Employee {TEST_EMPLOYEE_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


# ==================== HEALTH CHECK ====================

class TestHealthCheck:
    """Health check endpoint test"""
    
    def test_health_check(self):
        """Test GET /api/health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ GET /api/health working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

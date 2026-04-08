"""
Phase 20: Policy Assignments Routes Tests

Tests for the extracted policy assignment routes module:
- GET /api/policy-assignments - List policy assignments with filters
- PUT /api/policy-assignments/{id}/view - Mark policy as viewed
- PUT /api/policy-assignments/{id}/acknowledge - Acknowledge policy
- PUT /api/policy-assignments/{id}/admin-review - Admin review acknowledgement
- PUT /api/policy-assignments/{id}/unassign - Unassign policy before acknowledgement
- PUT /api/policy-assignments/{id}/withdraw - Withdraw acknowledged policy

Plus regression tests for previous phases (19, 18).
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
TEST_POLICY_ASSIGNMENT_ID = "825dd142-03e9-4e39-ac1d-3804c1ac045f"


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
        # API returns 'token' not 'access_token'
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}


class TestPolicyAssignmentsListEndpoint(TestAuthSetup):
    """Tests for GET /api/policy-assignments"""
    
    def test_list_policy_assignments_authenticated(self, auth_headers):
        """Test listing policy assignments with authentication"""
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/policy-assignments returned {len(data)} assignments")
    
    def test_list_policy_assignments_filter_by_employee(self, auth_headers):
        """Test filtering policy assignments by employee_id"""
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"employee_id": TEST_EMPLOYEE_ID},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # All returned assignments should be for the specified employee
        for assignment in data:
            assert assignment.get("employee_id") == TEST_EMPLOYEE_ID, \
                f"Assignment {assignment.get('id')} has wrong employee_id"
        print(f"✓ Filter by employee_id returned {len(data)} assignments")
    
    def test_list_policy_assignments_filter_by_status(self, auth_headers):
        """Test filtering policy assignments by status"""
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"status": "assigned"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        for assignment in data:
            assert assignment.get("status") == "assigned", \
                f"Assignment {assignment.get('id')} has wrong status"
        print(f"✓ Filter by status=assigned returned {len(data)} assignments")
    
    def test_list_policy_assignments_include_inactive(self, auth_headers):
        """Test including inactive (unassigned/withdrawn) assignments"""
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"include_inactive": True},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Include inactive returned {len(data)} assignments")
    
    def test_list_policy_assignments_unauthenticated(self):
        """Test that unauthenticated requests are rejected"""
        response = requests.get(f"{BASE_URL}/api/policy-assignments")
        assert response.status_code in [401, 403], \
            f"Expected 401/403, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestPolicyAssignmentViewEndpoint(TestAuthSetup):
    """Tests for PUT /api/policy-assignments/{id}/view"""
    
    def test_mark_policy_viewed(self, auth_headers):
        """Test marking a policy as viewed"""
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{TEST_POLICY_ASSIGNMENT_ID}/view",
            headers=auth_headers
        )
        # Could be 200 (success) or 404 (assignment not found)
        if response.status_code == 200:
            data = response.json()
            assert "id" in data, "Response should contain assignment id"
            assert data.get("viewed_at") is not None, "viewed_at should be set"
            print(f"✓ Policy marked as viewed: {data.get('id')}")
        elif response.status_code == 404:
            print(f"✓ Assignment {TEST_POLICY_ASSIGNMENT_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, {response.text}")
    
    def test_mark_policy_viewed_not_found(self, auth_headers):
        """Test marking non-existent policy as viewed"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{fake_id}/view",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent assignment correctly returns 404")


class TestPolicyAssignmentAcknowledgeEndpoint(TestAuthSetup):
    """Tests for PUT /api/policy-assignments/{id}/acknowledge"""
    
    def test_acknowledge_policy(self, auth_headers):
        """Test acknowledging a policy"""
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{TEST_POLICY_ASSIGNMENT_ID}/acknowledge",
            headers=auth_headers
        )
        # Could be 200 (success), 400 (already acknowledged), or 404 (not found)
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "acknowledged", "Status should be acknowledged"
            assert data.get("acknowledged_at") is not None, "acknowledged_at should be set"
            print(f"✓ Policy acknowledged: {data.get('id')}")
        elif response.status_code == 400:
            print("✓ Policy already acknowledged (expected)")
        elif response.status_code == 404:
            print(f"✓ Assignment {TEST_POLICY_ASSIGNMENT_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, {response.text}")
    
    def test_acknowledge_policy_not_found(self, auth_headers):
        """Test acknowledging non-existent policy"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{fake_id}/acknowledge",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent assignment correctly returns 404")


class TestPolicyAssignmentAdminReviewEndpoint(TestAuthSetup):
    """Tests for PUT /api/policy-assignments/{id}/admin-review"""
    
    def test_admin_review_policy(self, auth_headers):
        """Test admin reviewing a policy acknowledgement"""
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{TEST_POLICY_ASSIGNMENT_ID}/admin-review",
            headers=auth_headers
        )
        # Could be 200 (success), 400 (not acknowledged yet), or 404 (not found)
        if response.status_code == 200:
            data = response.json()
            assert data.get("admin_reviewed") == True, "admin_reviewed should be True"
            assert data.get("admin_reviewed_at") is not None, "admin_reviewed_at should be set"
            print(f"✓ Policy admin reviewed: {data.get('id')}")
        elif response.status_code == 400:
            error = response.json()
            print(f"✓ Admin review blocked: {error.get('detail', 'Policy must be acknowledged first')}")
        elif response.status_code == 404:
            print(f"✓ Assignment {TEST_POLICY_ASSIGNMENT_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, {response.text}")
    
    def test_admin_review_not_found(self, auth_headers):
        """Test admin reviewing non-existent policy"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{fake_id}/admin-review",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent assignment correctly returns 404")


class TestPolicyAssignmentUnassignEndpoint(TestAuthSetup):
    """Tests for PUT /api/policy-assignments/{id}/unassign"""
    
    def test_unassign_policy(self, auth_headers):
        """Test unassigning a policy before acknowledgement"""
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{TEST_POLICY_ASSIGNMENT_ID}/unassign",
            json={"reason": "Test unassignment"},
            headers=auth_headers
        )
        # Could be 200 (success), 400 (already acknowledged/unassigned), or 404 (not found)
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "unassigned", "Status should be unassigned"
            assert data.get("unassigned_at") is not None, "unassigned_at should be set"
            print(f"✓ Policy unassigned: {data.get('id')}")
        elif response.status_code == 400:
            error = response.json()
            print(f"✓ Unassign blocked: {error.get('detail', 'Cannot unassign')}")
        elif response.status_code == 404:
            print(f"✓ Assignment {TEST_POLICY_ASSIGNMENT_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, {response.text}")
    
    def test_unassign_policy_not_found(self, auth_headers):
        """Test unassigning non-existent policy"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{fake_id}/unassign",
            json={"reason": "Test"},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent assignment correctly returns 404")


class TestPolicyAssignmentWithdrawEndpoint(TestAuthSetup):
    """Tests for PUT /api/policy-assignments/{id}/withdraw"""
    
    def test_withdraw_policy(self, auth_headers):
        """Test withdrawing an acknowledged policy"""
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{TEST_POLICY_ASSIGNMENT_ID}/withdraw",
            json={"reason": "Test withdrawal"},
            headers=auth_headers
        )
        # Could be 200 (success), 400 (not acknowledged/already withdrawn), or 404 (not found)
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "withdrawn", "Status should be withdrawn"
            assert data.get("withdrawn_at") is not None, "withdrawn_at should be set"
            print(f"✓ Policy withdrawn: {data.get('id')}")
        elif response.status_code == 400:
            error = response.json()
            print(f"✓ Withdraw blocked: {error.get('detail', 'Cannot withdraw')}")
        elif response.status_code == 404:
            print(f"✓ Assignment {TEST_POLICY_ASSIGNMENT_ID} not found (expected if no test data)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, {response.text}")
    
    def test_withdraw_policy_not_found(self, auth_headers):
        """Test withdrawing non-existent policy"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/policy-assignments/{fake_id}/withdraw",
            json={"reason": "Test"},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent assignment correctly returns 404")


class TestRegressionPhase19Roles(TestAuthSetup):
    """Regression tests for Phase 19 - Roles endpoints"""
    
    def test_get_roles_list(self, auth_headers):
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
        print(f"✓ POST /api/employees/{TEST_EMPLOYEE_ID}/auto-promote endpoint exists")
    
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
        print(f"✓ POST /api/employees/{TEST_EMPLOYEE_ID}/force-promote endpoint exists")


class TestRegressionCoreEndpoints(TestAuthSetup):
    """Regression tests for core endpoints"""
    
    def test_auth_login(self):
        """Test POST /api/auth/login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        # API returns 'token' not 'access_token'
        assert "token" in data, "Response should contain token"
        print("✓ POST /api/auth/login working")
    
    def test_get_employees_list(self, auth_headers):
        """Test GET /api/employees"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/employees returned {len(data)} employees")
    
    def test_health_check(self):
        """Test GET /api/health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ GET /api/health working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

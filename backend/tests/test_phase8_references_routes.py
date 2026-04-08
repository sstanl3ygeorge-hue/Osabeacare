"""
Phase 8 References Routes Regression Tests

Tests the extracted references routes module and verifies no regressions
after the server.py refactoring. Focuses on:
- Auth login endpoint
- Employees list
- References routes (CRUD, status, integrity)
- Training routes
- Documents routes
- Worker portal endpoints
- Admin dashboard
- Recruitment routes
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
WORKER_EMAIL = "test.worker@example.com"
WORKER_PASSWORD = "Welcome123!"


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    def test_auth_login_success(self):
        """Test POST /api/auth/login with valid admin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Response missing token"
        assert "user" in data, "Response missing user"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Auth login successful for {ADMIN_EMAIL}")
    
    def test_auth_login_invalid_credentials(self):
        """Test POST /api/auth/login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Auth login correctly rejects invalid credentials")
    
    def test_auth_me(self, admin_token):
        """Test GET /api/auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Auth me failed: {response.text}"
        data = response.json()
        assert "email" in data
        assert data["email"] == ADMIN_EMAIL
        print(f"✓ Auth me returns correct user: {data['email']}")


class TestEmployeesEndpoints:
    """Test employees list endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_employees_list(self, admin_token):
        """Test GET /api/employees"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Employees list failed: {response.text}"
        data = response.json()
        # Response could be a list or dict with employees key
        if isinstance(data, list):
            print(f"✓ Employees list returned {len(data)} employees")
        else:
            employees = data.get("employees", data.get("items", []))
            print(f"✓ Employees list returned {len(employees)} employees")
    
    def test_staff_employees(self, admin_token):
        """Test GET /api/staff/employees"""
        response = requests.get(
            f"{BASE_URL}/api/staff/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Staff employees failed: {response.text}"
        data = response.json()
        if isinstance(data, list):
            print(f"✓ Staff employees returned {len(data)} employees")
        else:
            print(f"✓ Staff employees returned data")


class TestReferencesRoutes:
    """Test references routes - the newly extracted module"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, admin_token):
        """Get a test employee ID"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            employees = data if isinstance(data, list) else data.get("employees", data.get("items", []))
            if employees:
                return employees[0].get("id")
        pytest.skip("No employees found for testing")
    
    def test_get_references_for_employee(self, admin_token, test_employee_id):
        """Test GET /api/references/{employee_id}"""
        response = requests.get(
            f"{BASE_URL}/api/references/{test_employee_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get references failed: {response.text}"
        data = response.json()
        assert "employee_id" in data, "Response missing employee_id"
        assert data["employee_id"] == test_employee_id
        print(f"✓ References for employee {test_employee_id} retrieved successfully")
    
    def test_get_references_status(self, admin_token, test_employee_id):
        """Test GET /api/references/{employee_id}/status"""
        response = requests.get(
            f"{BASE_URL}/api/references/{test_employee_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Get references status failed: {response.text}"
        data = response.json()
        assert "employee_id" in data, "Response missing employee_id"
        assert "references" in data, "Response missing references array"
        assert "overall_status" in data, "Response missing overall_status"
        print(f"✓ References status for employee {test_employee_id}: {data['overall_status']}")
    
    def test_get_references_integrity(self, admin_token, test_employee_id):
        """Test GET /api/references/{employee_id}/1/integrity (server.py version)"""
        response = requests.get(
            f"{BASE_URL}/api/references/{test_employee_id}/1/integrity",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # This endpoint may return 200 or 404 depending on whether reference exists
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Reference integrity check returned data")
        else:
            print(f"✓ Reference integrity check returned 404 (no reference data)")
    
    def test_get_references_nonexistent_employee(self, admin_token):
        """Test GET /api/references/{employee_id} with non-existent employee"""
        fake_id = f"nonexistent-{uuid.uuid4()}"
        response = requests.get(
            f"{BASE_URL}/api/references/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ References endpoint correctly returns 404 for non-existent employee")


class TestTrainingRoutes:
    """Test training routes"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_get_training_records(self, admin_token):
        """Test GET /api/training-records"""
        response = requests.get(
            f"{BASE_URL}/api/training-records",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Training records failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of training records"
        print(f"✓ Training records returned {len(data)} records")
    
    def test_get_training(self, admin_token):
        """Test GET /api/training (if exists)"""
        response = requests.get(
            f"{BASE_URL}/api/training",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # This endpoint may or may not exist
        if response.status_code == 200:
            print("✓ Training endpoint exists and returns data")
        elif response.status_code == 404:
            print("✓ Training endpoint returns 404 (may not be implemented)")
        else:
            print(f"✓ Training endpoint returned {response.status_code}")


class TestDocumentsRoutes:
    """Test documents routes"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_get_document_types(self, admin_token):
        """Test GET /api/document-types"""
        response = requests.get(
            f"{BASE_URL}/api/document-types",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Document types failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of document types"
        print(f"✓ Document types returned {len(data)} types")
    
    def test_get_document_categories(self, admin_token):
        """Test GET /api/document-categories"""
        response = requests.get(
            f"{BASE_URL}/api/document-categories",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Document categories failed: {response.text}"
        data = response.json()
        assert "categories" in data, "Response missing categories"
        print(f"✓ Document categories returned {len(data['categories'])} categories")


class TestWorkerPortalEndpoints:
    """Test worker portal endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_worker_request_login(self):
        """Test POST /api/worker/request-login"""
        response = requests.post(
            f"{BASE_URL}/api/worker/request-login",
            json={"email": WORKER_EMAIL}
        )
        # Should return 200 even if email doesn't exist (security)
        assert response.status_code == 200, f"Worker request login failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Worker request login endpoint works")
    
    def test_worker_login_with_password(self):
        """Test POST /api/worker/login with password"""
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": WORKER_EMAIL, "password": WORKER_PASSWORD}
        )
        # May succeed or fail depending on whether worker exists
        if response.status_code == 200:
            data = response.json()
            assert "token" in data or "access_token" in data
            print("✓ Worker password login successful")
        else:
            print(f"✓ Worker password login returned {response.status_code} (worker may not exist)")
    
    def test_worker_profile_requires_auth(self):
        """Test GET /api/worker/profile-data requires authentication"""
        # Note: The endpoint is /api/worker/profile-data, not /api/worker/profile
        response = requests.get(f"{BASE_URL}/api/worker/profile-data")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Worker profile-data correctly requires authentication")


class TestAdminDashboardEndpoints:
    """Test admin dashboard endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_admin_dashboard(self, admin_token):
        """Test GET /api/admin/dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # May return 200 or 404 depending on implementation
        if response.status_code == 200:
            print("✓ Admin dashboard endpoint returns data")
        elif response.status_code == 404:
            print("✓ Admin dashboard endpoint returns 404 (may use different path)")
        else:
            print(f"✓ Admin dashboard returned {response.status_code}")
    
    def test_dashboard_stats(self, admin_token):
        """Test GET /api/dashboard/stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        print(f"✓ Dashboard stats returned data")
    
    def test_admin_system_health(self, admin_token):
        """Test GET /api/admin/system-health"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"System health failed: {response.text}"
        data = response.json()
        assert "status" in data
        print(f"✓ System health: {data['status']}")
    
    def test_admin_audit_logs(self, admin_token):
        """Test GET /api/admin/audit-logs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Audit logs failed: {response.text}"
        data = response.json()
        assert "logs" in data
        print(f"✓ Audit logs returned {len(data['logs'])} entries")


class TestRecruitmentRoutes:
    """Test recruitment routes"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_get_applicants(self, admin_token):
        """Test GET /api/recruitment/applicants"""
        response = requests.get(
            f"{BASE_URL}/api/recruitment/applicants",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Recruitment applicants failed: {response.text}"
        data = response.json()
        if isinstance(data, list):
            print(f"✓ Recruitment applicants returned {len(data)} applicants")
        else:
            print(f"✓ Recruitment applicants returned data")
    
    def test_get_recruitment_pipeline(self, admin_token):
        """Test GET /api/recruitment/pipeline"""
        response = requests.get(
            f"{BASE_URL}/api/recruitment/pipeline",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Recruitment pipeline failed: {response.text}"
        data = response.json()
        assert "summary" in data or "stages" in data
        print("✓ Recruitment pipeline returned data")
    
    def test_get_recruitment_statistics(self, admin_token):
        """Test GET /api/recruitment/statistics"""
        response = requests.get(
            f"{BASE_URL}/api/recruitment/statistics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Recruitment statistics failed: {response.text}"
        data = response.json()
        print(f"✓ Recruitment statistics returned data")


class TestOrgSettings:
    """Test organization settings endpoints"""
    
    def test_get_org_settings_public(self):
        """Test GET /api/org-settings (public endpoint)"""
        response = requests.get(f"{BASE_URL}/api/org-settings")
        assert response.status_code == 200, f"Org settings failed: {response.text}"
        data = response.json()
        assert "company_name" in data
        print(f"✓ Org settings: {data.get('company_name')}")


class TestNoRouteCollisions:
    """Test that there are no route collisions between modules"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_references_routes_no_collision(self, admin_token):
        """Verify references routes don't collide with server.py routes"""
        # Get an employee ID first
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code != 200:
            pytest.skip("Cannot get employees")
        
        data = response.json()
        employees = data if isinstance(data, list) else data.get("employees", data.get("items", []))
        if not employees:
            pytest.skip("No employees found")
        
        employee_id = employees[0].get("id")
        
        # Test that both references.py and server.py endpoints work
        # references.py: GET /api/references/{employee_id}
        resp1 = requests.get(
            f"{BASE_URL}/api/references/{employee_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp1.status_code == 200, f"references.py endpoint failed: {resp1.text}"
        
        # references.py: GET /api/references/{employee_id}/status
        resp2 = requests.get(
            f"{BASE_URL}/api/references/{employee_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp2.status_code == 200, f"references status endpoint failed: {resp2.text}"
        
        # server.py: GET /api/references/{employee_id}/1/integrity
        resp3 = requests.get(
            f"{BASE_URL}/api/references/{employee_id}/1/integrity",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # This may return 200 or 404 depending on data
        assert resp3.status_code in [200, 404], f"integrity endpoint unexpected: {resp3.status_code}"
        
        print("✓ No route collisions detected between references.py and server.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

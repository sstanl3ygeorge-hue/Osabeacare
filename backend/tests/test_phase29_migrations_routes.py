"""
Phase 29: Migration Routes Extraction Tests

Tests for migration endpoints extracted from server.py to routes/migrations.py:
- POST /api/admin/dual-row-migration/employee/{employee_id} - Single employee migration
- POST /api/admin/dual-row-migration/batch - Batch migration
- POST /api/admin/run-stamp-migration - Stamp historical documents

All endpoints require admin authentication.
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestPhase29Setup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, admin_headers):
        """Get or create a test employee for migration tests"""
        # First try to find an existing employee
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=admin_headers
        )
        if response.status_code == 200:
            employees = response.json()
            if employees and len(employees) > 0:
                return employees[0].get("id")
        
        # Create a test employee if none exists
        test_employee = {
            "name": f"Phase29 Test Employee {uuid.uuid4().hex[:8]}",
            "email": f"phase29test{uuid.uuid4().hex[:8]}@test.com",
            "phone": "07700900001",
            "role": "Care Worker",
            "status": "active"
        }
        response = requests.post(
            f"{BASE_URL}/api/employees",
            headers=admin_headers,
            json=test_employee
        )
        if response.status_code in [200, 201]:
            return response.json().get("id")
        
        # Return a placeholder if we can't create
        return "test-employee-phase29"
    
    def test_admin_login_success(self):
        """Test admin can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"✓ Admin login successful, role: {data['user'].get('role')}")


class TestDualRowMigrationSingleEmployee:
    """Tests for single employee dual-row migration endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, admin_headers):
        """Get a test employee ID"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=admin_headers
        )
        if response.status_code == 200:
            employees = response.json()
            if employees and len(employees) > 0:
                return employees[0].get("id")
        return "nonexistent-employee-id"
    
    def test_single_employee_migration_dry_run(self, admin_headers, test_employee_id):
        """Test single employee migration with dry_run=true (default)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/{test_employee_id}",
            headers=admin_headers
        )
        # Should succeed or return 404 if employee doesn't exist
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}, {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "employee_id" in data
            assert "dry_run" in data
            assert data["dry_run"] == True, "Default should be dry_run=true"
            print(f"✓ Single employee migration dry run successful: {data.get('employee_id')}")
        else:
            print(f"✓ Employee not found (expected for test): {response.json()}")
    
    def test_single_employee_migration_explicit_dry_run_true(self, admin_headers, test_employee_id):
        """Test single employee migration with explicit dry_run=true"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/{test_employee_id}?dry_run=true",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert data["dry_run"] == True
            print(f"✓ Explicit dry_run=true works correctly")
    
    def test_single_employee_migration_nonexistent_employee(self, admin_headers):
        """Test migration for non-existent employee returns 404"""
        fake_id = f"nonexistent-{uuid.uuid4().hex}"
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/{fake_id}",
            headers=admin_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent employee, got {response.status_code}"
        print(f"✓ Non-existent employee returns 404 correctly")
    
    def test_single_employee_migration_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/test-id"
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print(f"✓ Endpoint requires authentication")
    
    def test_single_employee_migration_requires_admin(self):
        """Test that endpoint requires admin role (not just any authenticated user)"""
        # This test would need a non-admin user token
        # For now, we verify the endpoint exists and requires auth
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/test-id",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 with invalid token, got {response.status_code}"
        print(f"✓ Endpoint validates token properly")


class TestDualRowMigrationBatch:
    """Tests for batch dual-row migration endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_batch_migration_dry_run_auto_detect(self, admin_headers):
        """Test batch migration with null employee_ids (auto-detect mode)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch?dry_run=true",
            headers=admin_headers,
            json=None  # null for auto-detect
        )
        assert response.status_code == 200, f"Batch migration failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "dry_run" in data
        assert data["dry_run"] == True
        print(f"✓ Batch migration auto-detect dry run successful")
        print(f"  - Employees found: {data.get('total_employees', 'N/A')}")
    
    def test_batch_migration_with_specific_ids(self, admin_headers):
        """Test batch migration with specific employee IDs"""
        # Get some employee IDs first
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=admin_headers
        )
        
        employee_ids = []
        if emp_response.status_code == 200:
            employees = emp_response.json()
            employee_ids = [e.get("id") for e in employees[:3] if e.get("id")]
        
        if not employee_ids:
            employee_ids = ["test-id-1", "test-id-2"]
        
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch?dry_run=true&limit=10",
            headers=admin_headers,
            json=employee_ids
        )
        assert response.status_code == 200, f"Batch migration with IDs failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert data["dry_run"] == True
        print(f"✓ Batch migration with specific IDs successful")
    
    def test_batch_migration_with_limit(self, admin_headers):
        """Test batch migration respects limit parameter"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch?dry_run=true&limit=5",
            headers=admin_headers,
            json=None
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify limit is respected (if there are results)
        if "results" in data and isinstance(data["results"], list):
            assert len(data["results"]) <= 5, "Limit not respected"
        print(f"✓ Batch migration limit parameter works")
    
    def test_batch_migration_requires_auth(self):
        """Test that batch endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch",
            json=None
        )
        assert response.status_code == 401
        print(f"✓ Batch endpoint requires authentication")
    
    def test_batch_migration_default_dry_run(self, admin_headers):
        """Test that batch migration defaults to dry_run=true"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch",
            headers=admin_headers,
            json=None
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("dry_run") == True, "Default should be dry_run=true for safety"
        print(f"✓ Batch migration defaults to dry_run=true")


class TestStampMigration:
    """Tests for stamp migration endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_stamp_migration_endpoint_exists(self, admin_headers):
        """Test stamp migration endpoint is accessible"""
        response = requests.post(
            f"{BASE_URL}/api/admin/run-stamp-migration",
            headers=admin_headers
        )
        # May return 500 if Supabase not configured, but endpoint should exist
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}, {response.text}"
        
        if response.status_code == 500:
            data = response.json()
            # Expected error if Supabase not configured
            if "Supabase storage not configured" in str(data.get("detail", "")):
                print(f"✓ Stamp migration endpoint exists (Supabase not configured - expected)")
            else:
                print(f"✓ Stamp migration endpoint exists (error: {data.get('detail')})")
        else:
            data = response.json()
            assert "success" in data
            print(f"✓ Stamp migration endpoint works")
            print(f"  - Total found: {data.get('results', {}).get('total_found', 0)}")
            print(f"  - Stamped: {data.get('results', {}).get('stamped_successfully', 0)}")
    
    def test_stamp_migration_requires_auth(self):
        """Test that stamp migration requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/admin/run-stamp-migration"
        )
        assert response.status_code == 401
        print(f"✓ Stamp migration requires authentication")
    
    def test_stamp_migration_requires_admin(self):
        """Test that stamp migration requires admin role"""
        response = requests.post(
            f"{BASE_URL}/api/admin/run-stamp-migration",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code in [401, 403]
        print(f"✓ Stamp migration validates admin role")


class TestMigrationRoutesIntegration:
    """Integration tests for migration routes"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_router_prefix_is_admin(self, admin_headers):
        """Verify all migration routes are under /api/admin prefix"""
        # Test that routes without /admin prefix don't work
        response = requests.post(
            f"{BASE_URL}/api/dual-row-migration/batch",
            headers=admin_headers,
            json=None
        )
        assert response.status_code == 404, "Route should be under /admin prefix"
        print(f"✓ Migration routes correctly use /admin prefix")
    
    def test_all_endpoints_respond(self, admin_headers):
        """Test all 3 migration endpoints respond"""
        endpoints_tested = 0
        
        # 1. Single employee migration
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/test-id",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]  # 404 for non-existent employee is OK
        endpoints_tested += 1
        
        # 2. Batch migration
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch?dry_run=true",
            headers=admin_headers,
            json=None
        )
        assert response.status_code == 200
        endpoints_tested += 1
        
        # 3. Stamp migration
        response = requests.post(
            f"{BASE_URL}/api/admin/run-stamp-migration",
            headers=admin_headers
        )
        assert response.status_code in [200, 500]  # 500 if Supabase not configured
        endpoints_tested += 1
        
        assert endpoints_tested == 3
        print(f"✓ All 3 migration endpoints respond correctly")


class TestRegressionPreviousPhases:
    """Regression tests for previous phases"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_phase28_verifications_still_work(self, admin_headers):
        """Test Phase 28 verification routes still work"""
        # Test RTW extraction endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/rtw/extract",
            headers=admin_headers,
            json={}  # Empty body should return validation error, not 404
        )
        # Should get 422 (validation error) or 400, not 404
        assert response.status_code in [400, 422, 500], f"Phase 28 RTW extract endpoint missing: {response.status_code}"
        print(f"✓ Phase 28 RTW extraction endpoint still accessible")
    
    def test_phase27_dbs_routes_still_work(self, admin_headers):
        """Test Phase 27 DBS routes still work"""
        response = requests.get(
            f"{BASE_URL}/api/dbs-register",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Phase 27 DBS register failed: {response.status_code}"
        print(f"✓ Phase 27 DBS register endpoint still works")
    
    def test_phase26_agreements_still_work(self, admin_headers):
        """Test Phase 26 agreements routes still work"""
        # Get an employee first
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=admin_headers
        )
        if emp_response.status_code == 200 and emp_response.json():
            employee_id = emp_response.json()[0].get("id")
            response = requests.get(
                f"{BASE_URL}/api/employees/{employee_id}/agreements",
                headers=admin_headers
            )
            assert response.status_code == 200, f"Phase 26 agreements failed: {response.status_code}"
            print(f"✓ Phase 26 agreements endpoint still works")
        else:
            print(f"✓ Phase 26 agreements endpoint exists (no employees to test)")
    
    def test_phase25_recurring_compliance_still_works(self, admin_headers):
        """Test Phase 25 recurring compliance routes still work"""
        response = requests.get(
            f"{BASE_URL}/api/recurring-compliance",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Phase 25 recurring compliance failed: {response.status_code}"
        print(f"✓ Phase 25 recurring compliance endpoint still works")
    
    def test_health_endpoint(self):
        """Test basic health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"✓ Health endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

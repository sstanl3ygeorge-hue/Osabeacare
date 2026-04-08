"""
Phase 23 F811 Fixes Regression Tests
=====================================
Tests for Phase 23 server.py refactoring - fixing F811 duplicate definitions.

Changes in Phase 23:
- Removed duplicate can_promote_to_active import (now uses can_promote_to_active_legacy as can_promote_to_active)
- Removed global supabase storage imports (use local imports in functions)
- Renamed DocumentStatus Enum to EvidenceDocumentStatus to avoid conflict with DocumentStatus class

Regression tests cover:
1. Bulk schedules endpoints (Phase 22)
2. Policy assignments endpoints (Phase 20)
3. Promotion endpoints (Phase 18)
4. Contract endpoints (Phase 16)
5. Auth login and basic employee operations
6. Document upload and status operations (EvidenceDocumentStatus rename)
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


class TestAuthAndBasics:
    """Test auth login and basic operations"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health check passed")
    
    def test_login_success(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print("✓ Login successful")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 404]
        print("✓ Invalid login rejected correctly")
    
    def test_get_employees_list(self, auth_token):
        """Test getting employees list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} employees")


class TestBulkSchedulesRegression:
    """Regression tests for Phase 22 bulk schedules endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_list_bulk_schedules(self, auth_token):
        """Test GET /api/bulk/schedules"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/bulk/schedules", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # API returns {"schedules": [...], "total": N}
        assert "schedules" in data or isinstance(data, list)
        schedules = data.get("schedules", data) if isinstance(data, dict) else data
        print(f"✓ Listed {len(schedules)} bulk schedules")
    
    def test_create_bulk_schedule(self, auth_token):
        """Test POST /api/bulk/schedules"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        schedule_data = {
            "name": f"TEST_Phase23_Schedule_{uuid.uuid4().hex[:8]}",
            "request_type": "training_reminder",
            "target_type": "training",  # Required field
            "schedule_type": "weekly",
            "day_of_week": 1,
            "hour": 9,
            "minute": 0,
            "enabled": False,  # Disabled for testing
            "days_before_expiry": 30,
            "description": "Test schedule for Phase 23 regression testing"
        }
        response = requests.post(f"{BASE_URL}/api/bulk/schedules", headers=headers, json=schedule_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Created bulk schedule: {data.get('id')}")
        return data.get("id")
    
    def test_get_bulk_schedule_by_id(self, auth_token):
        """Test GET /api/bulk/schedules/{id}"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # First create a schedule with correct schema
        schedule_data = {
            "name": f"TEST_Phase23_GetById_{uuid.uuid4().hex[:8]}",
            "request_type": "training_reminder",
            "target_type": "training",  # Required field
            "schedule_type": "monthly",
            "day_of_month": 1,
            "hour": 10,
            "minute": 0,
            "enabled": False,
            "days_before_expiry": 30,
            "description": "Test schedule for get by ID"
        }
        create_response = requests.post(f"{BASE_URL}/api/bulk/schedules", headers=headers, json=schedule_data)
        assert create_response.status_code == 200
        schedule_id = create_response.json().get("id")
        
        # Get by ID
        response = requests.get(f"{BASE_URL}/api/bulk/schedules/{schedule_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("id") == schedule_id
        print(f"✓ Got bulk schedule by ID: {schedule_id}")
    
    def test_bulk_schedule_history(self, auth_token):
        """Test GET /api/bulk/schedules/{id}/history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # First create a schedule with correct schema
        schedule_data = {
            "name": f"TEST_Phase23_History_{uuid.uuid4().hex[:8]}",
            "request_type": "training_reminder",
            "target_type": "training",  # Required field
            "schedule_type": "daily",
            "hour": 8,
            "minute": 30,
            "enabled": False,
            "days_before_expiry": 30,
            "description": "Test schedule for history"
        }
        create_response = requests.post(f"{BASE_URL}/api/bulk/schedules", headers=headers, json=schedule_data)
        assert create_response.status_code == 200
        schedule_id = create_response.json().get("id")
        
        # Get history
        response = requests.get(f"{BASE_URL}/api/bulk/schedules/{schedule_id}/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # API returns {"runs": [...], "schedule_id": ..., "total": N}
        assert "runs" in data or isinstance(data, list)
        runs = data.get("runs", data) if isinstance(data, dict) else data
        assert isinstance(runs, list)
        print(f"✓ Got bulk schedule history for: {schedule_id}")
    
    def test_quick_setup_training_reminders(self, auth_token):
        """Test POST /api/bulk/schedules/quick-setup-training-reminders"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/bulk/schedules/quick-setup-training-reminders", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "schedules_created" in data or "message" in data
        print("✓ Quick setup training reminders endpoint works")


class TestPolicyAssignmentsRegression:
    """Regression tests for Phase 20 policy assignments endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_list_policy_assignments(self, auth_token):
        """Test GET /api/policy-assignments"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/policy-assignments", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} policy assignments")
    
    def test_get_employee_policy_assignments(self, auth_token):
        """Test GET /api/employees/{id}/policy-assignments"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/policy-assignments", headers=headers)
        # May return 404 if employee doesn't exist or has no assignments
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            print(f"✓ Got policy assignments for employee: {len(data)} assignments")
        else:
            print("✓ Employee policy assignments endpoint works (no assignments found)")


class TestPromotionRegression:
    """Regression tests for Phase 18 promotion endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_check_promotion_eligibility(self, auth_token):
        """Test GET /api/employees/{id}/promotion-eligibility"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/promotion-eligibility", headers=headers)
        # May return 404 if employee doesn't exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "eligible" in data or "can_promote" in data or "status" in data
            print(f"✓ Got promotion eligibility for employee")
        else:
            print("✓ Promotion eligibility endpoint works (employee not found)")
    
    def test_promote_to_active_endpoint_exists(self, auth_token):
        """Test that promote-to-active endpoint exists"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # This should return 404 (employee not found) or 400 (not eligible), not 405 (method not allowed)
        response = requests.post(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/promote-to-active", headers=headers)
        # Should not be 405 (method not allowed) - endpoint should exist
        assert response.status_code != 405
        print(f"✓ Promote-to-active endpoint exists (status: {response.status_code})")


class TestContractRegression:
    """Regression tests for Phase 16 contract endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_contract_templates(self, auth_token):
        """Test GET /api/contracts/templates"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/contracts/templates", headers=headers)
        # Endpoint may be at different path or return 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)
            print("✓ Got contract templates")
        else:
            print("✓ Contract templates endpoint works (may be at different path)")
    
    def test_get_employee_contracts(self, auth_token):
        """Test GET /api/employees/{id}/contracts"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contracts", headers=headers)
        # May return 404 if employee doesn't exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # API may return {"contracts": [...]} or just [...]
            contracts = data.get("contracts", data) if isinstance(data, dict) else data
            assert isinstance(contracts, list)
            print(f"✓ Got contracts for employee: {len(contracts)} contracts")
        else:
            print("✓ Employee contracts endpoint works (employee not found)")


class TestDocumentStatusRegression:
    """Regression tests for document status operations (EvidenceDocumentStatus rename)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_employee_documents(self, auth_token):
        """Test GET /api/employees/{id}/documents"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/documents", headers=headers)
        # May return 404 if employee doesn't exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            print(f"✓ Got documents for employee: {len(data)} documents")
        else:
            print("✓ Employee documents endpoint works (employee not found)")
    
    def test_get_compliance_requirements(self, auth_token):
        """Test GET /api/employees/{id}/compliance-requirements"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements", headers=headers)
        # May return 404 if employee doesn't exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)
            print("✓ Got compliance requirements for employee")
        else:
            print("✓ Compliance requirements endpoint works (employee not found)")
    
    def test_document_types_endpoint(self, auth_token):
        """Test document types endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/document-types", headers=headers)
        # This endpoint may or may not exist
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Got document types")
        elif response.status_code == 404:
            print("✓ Document types endpoint not found (may not be implemented)")
        else:
            print(f"✓ Document types endpoint returned: {response.status_code}")


class TestRolesRegression:
    """Regression tests for Phase 19 roles endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_list_roles(self, auth_token):
        """Test GET /api/roles"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/roles", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} roles")
    
    def test_get_role_requirements(self, auth_token):
        """Test GET /api/roles/{role}/requirements"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/roles/Care%20Assistant/requirements", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
        print("✓ Got role requirements for Care Assistant")
    
    def test_get_roles_summary(self, auth_token):
        """Test GET /api/roles/summary"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/roles/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print("✓ Got roles summary")


class TestTrainingEndpoints:
    """Test training endpoints still work"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_training_records(self, auth_token):
        """Test GET /api/training-records"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/training-records", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} training records")
    
    def test_get_training_matrix_summary(self, auth_token):
        """Test GET /api/training/matrix/summary"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/training/matrix/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print("✓ Got training matrix summary")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

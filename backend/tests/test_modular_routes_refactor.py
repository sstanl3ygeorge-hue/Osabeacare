"""
Test Suite: Modular Routes Refactoring Verification
====================================================
Tests all endpoints after refactoring server.py into modular routes:
- routes/auth.py - Auth endpoints
- routes/workers.py - Worker portal endpoints
- routes/admin.py - Admin operations
- routes/training.py - Training management

This is a regression test to verify nothing is broken after the refactoring.
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
WORKER_EMAIL = "testworker.pdfimport@example.com"
WORKER_PASSWORD = "Welcome123!"


class TestAuthRoutes:
    """Test auth.py routes - Admin/Staff authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_admin_login_success(self):
        """Test POST /api/auth/login - Admin login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful - role: {data['user'].get('role')}")
    
    def test_admin_login_invalid_credentials(self):
        """Test POST /api/auth/login - Invalid credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_auth_me_endpoint(self):
        """Test GET /api/auth/me - Get current user"""
        # First login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Get current user
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        print(f"✓ Auth/me returned user: {data['email']}")
    
    def test_session_info_endpoint(self):
        """Test GET /api/auth/session-info - Get session info"""
        # First login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Get session info
        response = self.session.get(
            f"{BASE_URL}/api/auth/session-info",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Session info failed: {response.text}"
        data = response.json()
        assert "expires_in_seconds" in data
        assert "email" in data
        print(f"✓ Session info: expires in {data['expires_in_seconds']} seconds")


class TestWorkerAuthRoutes:
    """Test auth.py routes - Worker portal authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_worker_request_login(self):
        """Test POST /api/worker/request-login - Magic link request"""
        response = self.session.post(f"{BASE_URL}/api/worker/request-login", json={
            "email": WORKER_EMAIL
        })
        assert response.status_code == 200, f"Worker request login failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Worker magic link request successful")
    
    def test_worker_password_login(self):
        """Test POST /api/worker/login - Worker password login"""
        response = self.session.post(f"{BASE_URL}/api/worker/login", json={
            "email": WORKER_EMAIL,
            "password": WORKER_PASSWORD
        })
        assert response.status_code == 200, f"Worker login failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        assert "employee" in data
        print(f"✓ Worker login successful - employee: {data['employee'].get('first_name')}")
        return data["token"]


class TestWorkerPortalRoutes:
    """Test workers.py routes - Worker self-service portal"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as worker
        login_resp = self.session.post(f"{BASE_URL}/api/worker/login", json={
            "email": WORKER_EMAIL,
            "password": WORKER_PASSWORD
        })
        if login_resp.status_code == 200:
            self.worker_token = login_resp.json()["token"]
        else:
            self.worker_token = None
    
    def test_worker_notifications(self):
        """Test GET /api/worker/notifications"""
        if not self.worker_token:
            pytest.skip("Worker login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/worker/notifications",
            headers={"Authorization": f"Bearer {self.worker_token}"}
        )
        assert response.status_code == 200, f"Worker notifications failed: {response.text}"
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        print(f"✓ Worker notifications: {len(data['notifications'])} notifications, {data['unread_count']} unread")
    
    def test_worker_profile_data(self):
        """Test GET /api/worker/profile-data"""
        if not self.worker_token:
            pytest.skip("Worker login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/worker/profile-data",
            headers={"Authorization": f"Bearer {self.worker_token}"}
        )
        assert response.status_code == 200, f"Worker profile data failed: {response.text}"
        data = response.json()
        assert "profile_data" in data
        assert "employee_name" in data
        print(f"✓ Worker profile data for: {data['employee_name']}")
    
    def test_worker_profile_completion_status(self):
        """Test GET /api/worker/profile-completion-status"""
        if not self.worker_token:
            pytest.skip("Worker login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/worker/profile-completion-status",
            headers={"Authorization": f"Bearer {self.worker_token}"}
        )
        assert response.status_code == 200, f"Profile completion status failed: {response.text}"
        data = response.json()
        assert "profile_complete" in data
        assert "completion_percentage" in data
        assert "sections" in data
        print(f"✓ Profile completion: {data['completion_percentage']}% complete")


class TestAdminRoutes:
    """Test admin.py routes - Admin operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.admin_token = login_resp.json()["token"]
    
    def test_org_settings_get(self):
        """Test GET /api/org-settings - Public endpoint"""
        response = self.session.get(f"{BASE_URL}/api/org-settings")
        assert response.status_code == 200, f"Org settings failed: {response.text}"
        data = response.json()
        assert "company_name" in data
        print(f"✓ Org settings: {data.get('company_name')}")
    
    def test_document_expiry_alerts(self):
        """Test GET /api/admin/document-expiry-alerts"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/document-expiry-alerts?days=30",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Document expiry alerts failed: {response.text}"
        data = response.json()
        assert "documents" in data
        assert "training" in data
        assert "total_expiring" in data
        print(f"✓ Document expiry alerts: {data['total_expiring']} items expiring in 30 days")
    
    def test_audit_logs(self):
        """Test GET /api/admin/audit-logs"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/audit-logs?limit=10",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Audit logs failed: {response.text}"
        data = response.json()
        assert "logs" in data
        assert "count" in data
        print(f"✓ Audit logs: {data['count']} entries returned")
    
    def test_system_health(self):
        """Test GET /api/admin/system-health"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/system-health",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"System health failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy"
        assert "collections" in data
        print(f"✓ System health: {data['status']} - {data['collections'].get('employees')} employees")


class TestTrainingRoutes:
    """Test training.py routes - Training management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.admin_token = login_resp.json()["token"]
    
    def test_training_records_list(self):
        """Test GET /api/training-records"""
        response = self.session.get(
            f"{BASE_URL}/api/training-records",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Training records list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Training records: {len(data)} records found")
    
    def test_training_expiry_alerts(self):
        """Test GET /api/admin/training-expiry-alerts"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/training-expiry-alerts?days=30",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Training expiry alerts failed: {response.text}"
        data = response.json()
        assert "total" in data
        assert "critical" in data
        assert "warning" in data
        print(f"✓ Training expiry alerts: {data['total']} total, {len(data['critical'])} critical")
    
    def test_training_expiring_summary(self):
        """Test GET /api/training/expiring-summary"""
        response = self.session.get(
            f"{BASE_URL}/api/training/expiring-summary",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Training expiring summary failed: {response.text}"
        data = response.json()
        assert "critical_7_days" in data
        assert "total_expiring_90_days" in data
        print(f"✓ Training expiring summary: {data['total_expiring_90_days']} expiring in 90 days")
    
    def test_training_catalogue(self):
        """Test GET /api/admin/training-catalogue"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/training-catalogue",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Training catalogue failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert "count" in data
        print(f"✓ Training catalogue: {data['count']} items")
    
    def test_training_catalogue_status(self):
        """Test GET /api/admin/training-catalogue/status"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/training-catalogue/status",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Training catalogue status failed: {response.text}"
        data = response.json()
        assert "total_items" in data
        assert "mandatory_count" in data
        print(f"✓ Training catalogue status: {data['total_items']} total, {data['mandatory_count']} mandatory")


class TestDashboardAndEmployees:
    """Test remaining server.py routes - Dashboard and Employees"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.admin_token = login_resp.json()["token"]
    
    def test_dashboard_stats(self):
        """Test GET /api/dashboard/stats"""
        response = self.session.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        # Dashboard stats should have employee counts
        print(f"✓ Dashboard stats loaded successfully")
    
    def test_employees_list(self):
        """Test GET /api/employees"""
        response = self.session.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Employees list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Employees list: {len(data)} employees found")
    
    def test_staff_employees(self):
        """Test GET /api/staff/employees - Scoped employee list"""
        response = self.session.get(
            f"{BASE_URL}/api/staff/employees",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Staff employees failed: {response.text}"
        data = response.json()
        # Response is an array of employees
        assert isinstance(data, list), "Expected list of employees"
        print(f"✓ Staff employees: {len(data)} employees")
    
    def test_recruitment_applicants(self):
        """Test GET /api/recruitment/applicants - Scoped applicant list"""
        response = self.session.get(
            f"{BASE_URL}/api/recruitment/applicants",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Recruitment applicants failed: {response.text}"
        data = response.json()
        # Response is an array of applicants
        assert isinstance(data, list), "Expected list of applicants"
        print(f"✓ Recruitment applicants: {len(data)} applicants")


class TestAdminUserManagement:
    """Test auth.py routes - Admin user management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.admin_token = login_resp.json()["token"]
    
    def test_list_admin_users(self):
        """Test GET /api/admin/users"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"List admin users failed: {response.text}"
        data = response.json()
        assert "users" in data
        assert "count" in data
        print(f"✓ Admin users: {data['count']} users found")


class TestWorkerDashboard:
    """Test worker dashboard endpoint (still in server.py)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as worker
        login_resp = self.session.post(f"{BASE_URL}/api/worker/login", json={
            "email": WORKER_EMAIL,
            "password": WORKER_PASSWORD
        })
        if login_resp.status_code == 200:
            self.worker_token = login_resp.json()["token"]
        else:
            self.worker_token = None
    
    def test_worker_dashboard(self):
        """Test GET /api/worker/dashboard"""
        if not self.worker_token:
            pytest.skip("Worker login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {self.worker_token}"}
        )
        assert response.status_code == 200, f"Worker dashboard failed: {response.text}"
        data = response.json()
        assert "employee" in data
        print(f"✓ Worker dashboard loaded for: {data['employee'].get('first_name')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

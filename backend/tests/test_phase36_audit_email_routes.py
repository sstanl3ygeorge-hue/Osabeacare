"""
Phase 36: Audit & Email Templates Routes Extraction Tests

Tests for 9 endpoints extracted from server.py to routes/audit_email.py:
- GET /email-templates - requires manager/admin auth
- GET /email-templates/{template_key} - requires manager/admin auth
- POST /send-email - requires manager/admin auth
- POST /admin/audit-change - requires admin auth
- GET /admin/audit-trail/{entity_type}/{entity_id} - requires user auth
- GET /audit-logs - requires manager/admin auth
- GET /audit/employee/{employee_id}/training - requires user auth
- GET /audit/training/summary - requires user auth
- GET /audit/training/export - requires manager/admin auth
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPhase36AuditEmailRoutes:
    """Test all 9 audit & email template endpoints from Phase 36 extraction"""
    
    # ==================== EMAIL TEMPLATE ENDPOINTS ====================
    
    def test_get_email_templates_requires_auth(self):
        """GET /api/email-templates - should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/email-templates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: GET /api/email-templates returns 401 without auth")
    
    def test_get_email_template_by_key_requires_auth(self):
        """GET /api/email-templates/{template_key} - should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/email-templates/test-key")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: GET /api/email-templates/test-key returns 401 without auth")
    
    def test_send_email_requires_auth(self):
        """POST /api/send-email - should return 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/send-email",
            json={"template_key": "test", "employee_id": "test-id"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: POST /api/send-email returns 401 without auth")
    
    # ==================== ADMIN AUDIT ENDPOINTS ====================
    
    def test_admin_audit_change_requires_auth(self):
        """POST /api/admin/audit-change - should return 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/admin/audit-change",
            params={
                "entity_type": "employee",
                "entity_id": "test-id",
                "field_name": "test_field",
                "reason": "Test reason for audit change"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: POST /api/admin/audit-change returns 401 without auth")
    
    def test_admin_audit_trail_requires_auth(self):
        """GET /api/admin/audit-trail/{entity_type}/{entity_id} - should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/audit-trail/employee/test-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: GET /api/admin/audit-trail/employee/test-id returns 401 without auth")
    
    def test_audit_logs_requires_auth(self):
        """GET /api/audit-logs - should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/audit-logs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: GET /api/audit-logs returns 401 without auth")
    
    # ==================== TRAINING AUDIT ENDPOINTS ====================
    
    def test_employee_training_audit_requires_auth(self):
        """GET /api/audit/employee/{employee_id}/training - should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/audit/employee/test-id/training")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: GET /api/audit/employee/test-id/training returns 401 without auth")
    
    def test_training_audit_summary_requires_auth(self):
        """GET /api/audit/training/summary - should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: GET /api/audit/training/summary returns 401 without auth")
    
    def test_training_audit_export_requires_auth(self):
        """GET /api/audit/training/export - should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/audit/training/export")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: GET /api/audit/training/export returns 401 without auth")


class TestPhase36AuthenticatedEndpoints:
    """Test endpoints with valid authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for authenticated tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    # ==================== EMAIL TEMPLATE ENDPOINTS WITH AUTH ====================
    
    def test_get_email_templates_with_auth(self):
        """GET /api/email-templates - should return 200 with valid auth"""
        response = requests.get(f"{BASE_URL}/api/email-templates", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, dict), "Expected dict response for email templates"
        print(f"PASS: GET /api/email-templates returns 200 with auth, {len(data)} templates found")
    
    def test_get_email_template_by_key_with_auth(self):
        """GET /api/email-templates/{template_key} - should return 404 for non-existent key"""
        response = requests.get(f"{BASE_URL}/api/email-templates/non-existent-key", headers=self.headers)
        # Should return 404 for non-existent template, not 401
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: GET /api/email-templates/non-existent-key returns 404 with auth")
    
    def test_get_valid_email_template_with_auth(self):
        """GET /api/email-templates - get a valid template key and fetch it"""
        # First get all templates
        response = requests.get(f"{BASE_URL}/api/email-templates", headers=self.headers)
        if response.status_code == 200:
            templates = response.json()
            if templates:
                # Get first template key
                first_key = list(templates.keys())[0]
                response2 = requests.get(f"{BASE_URL}/api/email-templates/{first_key}", headers=self.headers)
                assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
                print(f"PASS: GET /api/email-templates/{first_key} returns 200 with auth")
            else:
                print("SKIP: No email templates found to test")
        else:
            pytest.skip("Could not get email templates list")
    
    # ==================== ADMIN AUDIT ENDPOINTS WITH AUTH ====================
    
    def test_admin_audit_trail_with_auth(self):
        """GET /api/admin/audit-trail/{entity_type}/{entity_id} - should return 200 with auth"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-trail/employee/test-id",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "entity_type" in data, "Expected entity_type in response"
        assert "entity_id" in data, "Expected entity_id in response"
        assert "entries" in data, "Expected entries in response"
        print("PASS: GET /api/admin/audit-trail/employee/test-id returns 200 with auth")
    
    def test_audit_logs_with_auth(self):
        """GET /api/audit-logs - should return 200 with auth"""
        response = requests.get(f"{BASE_URL}/api/audit-logs", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list response for audit logs"
        print(f"PASS: GET /api/audit-logs returns 200 with auth, {len(data)} logs found")
    
    def test_audit_logs_with_filters(self):
        """GET /api/audit-logs - test with query filters"""
        response = requests.get(
            f"{BASE_URL}/api/audit-logs",
            params={"entity_type": "employee", "limit": 10},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: GET /api/audit-logs with filters returns 200")
    
    # ==================== TRAINING AUDIT ENDPOINTS WITH AUTH ====================
    
    def test_employee_training_audit_with_auth(self):
        """GET /api/audit/employee/{employee_id}/training - should return 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/audit/employee/non-existent-id/training",
            headers=self.headers
        )
        # Should return 404 for non-existent employee
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: GET /api/audit/employee/non-existent-id/training returns 404 with auth")
    
    def test_training_audit_summary_with_auth(self):
        """GET /api/audit/training/summary - should return 200 with auth"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total_employees" in data, "Expected total_employees in response"
        assert "fully_compliant" in data, "Expected fully_compliant in response"
        print(f"PASS: GET /api/audit/training/summary returns 200 with auth")
    
    def test_training_audit_export_json_with_auth(self):
        """GET /api/audit/training/export - should return 200 with JSON format"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export",
            params={"format": "json"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "export_date" in data, "Expected export_date in response"
        assert "total_employees" in data, "Expected total_employees in response"
        assert "employees" in data, "Expected employees in response"
        print(f"PASS: GET /api/audit/training/export (JSON) returns 200 with auth")
    
    def test_training_audit_export_csv_with_auth(self):
        """GET /api/audit/training/export - should return CSV with format=csv"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export",
            params={"format": "csv"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "text/csv" in response.headers.get("Content-Type", ""), "Expected CSV content type"
        print("PASS: GET /api/audit/training/export (CSV) returns 200 with auth")


class TestPhase36RegressionTests:
    """Regression tests for previous phases"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for authenticated tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed - skipping regression tests")
    
    def test_phase35_generated_forms_endpoint(self):
        """Regression: GET /api/generated-forms should still work"""
        response = requests.get(f"{BASE_URL}/api/generated-forms", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Phase 35 - GET /api/generated-forms still works")
    
    def test_phase34_pdf_templates_endpoint(self):
        """Regression: GET /api/pdf-templates should still work"""
        response = requests.get(f"{BASE_URL}/api/pdf-templates", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Phase 34 - GET /api/pdf-templates still works")
    
    def test_phase33_worker_dashboard_endpoint(self):
        """Regression: GET /api/worker/dashboard - admin gets 403 (worker-only)"""
        response = requests.get(f"{BASE_URL}/api/worker/dashboard", headers=self.headers)
        # Admin should get 403 as this is worker-only endpoint
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Phase 33 - GET /api/worker/dashboard returns 403 for admin")
    
    def test_phase31_cv_extractions_endpoint(self):
        """Regression: GET /api/extractions/pending-review should still work"""
        response = requests.get(f"{BASE_URL}/api/extractions/pending-review", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Phase 31 - GET /api/extractions/pending-review still works")
    
    def test_phase27_dbs_register_endpoint(self):
        """Regression: GET /api/dbs-register should still work"""
        response = requests.get(f"{BASE_URL}/api/dbs-register", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Phase 27 - GET /api/dbs-register still works")


class TestPhase36RouterRegistration:
    """Verify router is properly registered in server.py"""
    
    def test_router_import_exists(self):
        """Verify router import exists in server.py"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        assert "from routes.audit_email import router as audit_email_router" in content, \
            "Router import not found in server.py"
        print("PASS: Router import found in server.py")
    
    def test_router_inclusion_exists(self):
        """Verify router inclusion exists in server.py"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        assert "api_router.include_router(audit_email_router)" in content, \
            "Router inclusion not found in server.py"
        print("PASS: Router inclusion found in server.py")
    
    def test_audit_email_route_file_exists(self):
        """Verify routes/audit_email.py file exists"""
        import os
        assert os.path.exists("/app/backend/routes/audit_email.py"), \
            "routes/audit_email.py file not found"
        print("PASS: routes/audit_email.py file exists")

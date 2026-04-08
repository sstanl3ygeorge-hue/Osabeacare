"""
Phase 35: Generated Forms Routes Extraction Tests
Tests for 14 endpoints extracted from server.py to routes/generated_forms.py

Endpoints tested:
1. POST /api/generated-forms/{form_id}/regenerate-pdf - manager/admin auth
2. POST /api/generated-forms - manager/admin auth
3. GET /api/generated-forms - user auth
4. GET /api/generated-forms/{form_id} - user auth
5. GET /api/forms/access/{access_token} - public endpoint
6. PUT /api/forms/access/{access_token}/submit - public endpoint
7. PUT /api/generated-forms/{form_id} - manager/admin auth
8. POST /api/generated-forms/{form_id}/send - manager/admin auth
9. POST /api/generated-forms/{form_id}/signoff - admin auth
10. POST /api/generated-forms/{form_id}/save-as-document - manager/admin auth
11. POST /api/generated-forms/{form_id}/archive - admin auth
12. POST /api/generated-forms/bulk - manager/admin auth
13. POST /api/generated-forms/import-application - manager/admin auth
14. POST /api/generated-forms/import-document - manager/admin auth
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPhase35GeneratedFormsRoutes:
    """Test Generated Forms routes extraction - Phase 35"""
    
    # ==================== AUTH TESTS (Without Token) ====================
    
    def test_post_generated_forms_requires_auth(self):
        """POST /api/generated-forms requires manager/admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            json={"template_id": "test", "employee_id": "test", "form_data": {}},
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms returns 401 without auth")
    
    def test_get_generated_forms_requires_auth(self):
        """GET /api/generated-forms requires user auth"""
        response = requests.get(f"{BASE_URL}/api/generated-forms", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: GET /api/generated-forms returns 401 without auth")
    
    def test_get_generated_form_by_id_requires_auth(self):
        """GET /api/generated-forms/{form_id} requires user auth"""
        response = requests.get(f"{BASE_URL}/api/generated-forms/test-id", timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: GET /api/generated-forms/{form_id} returns 401 without auth")
    
    def test_regenerate_pdf_requires_auth(self):
        """POST /api/generated-forms/{form_id}/regenerate-pdf requires manager/admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/test-id/regenerate-pdf",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/regenerate-pdf returns 401 without auth")
    
    def test_update_generated_form_requires_auth(self):
        """PUT /api/generated-forms/{form_id} requires manager/admin auth"""
        response = requests.put(
            f"{BASE_URL}/api/generated-forms/test-id",
            json={"form_data": {}},
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: PUT /api/generated-forms/{form_id} returns 401 without auth")
    
    def test_send_form_requires_auth(self):
        """POST /api/generated-forms/{form_id}/send requires manager/admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/test-id/send",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/send returns 401 without auth")
    
    def test_signoff_form_requires_auth(self):
        """POST /api/generated-forms/{form_id}/signoff requires admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/test-id/signoff",
            params={"admin_signature": "test"},
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/signoff returns 401 without auth")
    
    def test_save_as_document_requires_auth(self):
        """POST /api/generated-forms/{form_id}/save-as-document requires manager/admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/test-id/save-as-document",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/save-as-document returns 401 without auth")
    
    def test_archive_form_requires_auth(self):
        """POST /api/generated-forms/{form_id}/archive requires admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/test-id/archive",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/archive returns 401 without auth")
    
    def test_bulk_generate_requires_auth(self):
        """POST /api/generated-forms/bulk requires manager/admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/bulk",
            params={"employee_id": "test", "template_ids": ["test"]},
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/bulk returns 401 without auth")
    
    def test_import_application_requires_auth(self):
        """POST /api/generated-forms/import-application requires manager/admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-application",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/import-application returns 401 without auth")
    
    def test_import_document_requires_auth(self):
        """POST /api/generated-forms/import-document requires manager/admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-document",
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/generated-forms/import-document returns 401 without auth")
    
    # ==================== PUBLIC ENDPOINT TESTS ====================
    
    def test_get_form_by_token_public_invalid_token(self):
        """GET /api/forms/access/{access_token} - public endpoint returns 404 for invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/forms/access/invalid-token-12345",
            timeout=10
        )
        # Should return 404 for invalid token (not 401 - this is public)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: GET /api/forms/access/{access_token} returns 404 for invalid token (public endpoint)")
    
    def test_submit_form_by_token_public_invalid_token(self):
        """PUT /api/forms/access/{access_token}/submit - public endpoint returns 404 for invalid token"""
        response = requests.put(
            f"{BASE_URL}/api/forms/access/invalid-token-12345/submit",
            json={"form_data": {}},
            timeout=10
        )
        # Should return 404 for invalid token (not 401 - this is public)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: PUT /api/forms/access/{access_token}/submit returns 404 for invalid token (public endpoint)")


class TestPhase35WithAuth:
    """Test Generated Forms routes with authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"},
            timeout=10
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_get_generated_forms_with_auth(self):
        """GET /api/generated-forms returns 200 with auth"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        print(f"PASS: GET /api/generated-forms returns 200 with auth ({len(data)} forms)")
    
    def test_get_generated_form_by_id_not_found(self):
        """GET /api/generated-forms/{form_id} returns 404 for non-existent form"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms/non-existent-form-id",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: GET /api/generated-forms/{form_id} returns 404 for non-existent form")
    
    def test_regenerate_pdf_not_found(self):
        """POST /api/generated-forms/{form_id}/regenerate-pdf returns 404 for non-existent form"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/non-existent-form-id/regenerate-pdf",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/regenerate-pdf returns 404 for non-existent form")
    
    def test_update_generated_form_not_found(self):
        """PUT /api/generated-forms/{form_id} returns 404 for non-existent form"""
        response = requests.put(
            f"{BASE_URL}/api/generated-forms/non-existent-form-id",
            headers=self.headers,
            json={"form_data": {}},
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: PUT /api/generated-forms/{form_id} returns 404 for non-existent form")
    
    def test_send_form_not_found(self):
        """POST /api/generated-forms/{form_id}/send returns 404 for non-existent form"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/non-existent-form-id/send",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/send returns 404 for non-existent form")
    
    def test_signoff_form_not_found(self):
        """POST /api/generated-forms/{form_id}/signoff returns 404 for non-existent form"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/non-existent-form-id/signoff",
            headers=self.headers,
            params={"admin_signature": "test"},
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/signoff returns 404 for non-existent form")
    
    def test_save_as_document_not_found(self):
        """POST /api/generated-forms/{form_id}/save-as-document returns 404 for non-existent form"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/non-existent-form-id/save-as-document",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/save-as-document returns 404 for non-existent form")
    
    def test_archive_form_not_found(self):
        """POST /api/generated-forms/{form_id}/archive returns 404 for non-existent form"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/non-existent-form-id/archive",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POST /api/generated-forms/{form_id}/archive returns 404 for non-existent form")
    
    def test_bulk_generate_employee_not_found(self):
        """POST /api/generated-forms/bulk returns 404 for non-existent employee"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/bulk",
            headers=self.headers,
            params={"employee_id": "non-existent-employee", "template_ids": ["test"]},
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POST /api/generated-forms/bulk returns 404 for non-existent employee")


class TestPhase35RegressionPreviousPhases:
    """Regression tests for previous phases (26-34)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"},
            timeout=10
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed - skipping regression tests")
    
    def test_phase34_pdf_templates_still_works(self):
        """Phase 34: GET /api/pdf-templates still works"""
        response = requests.get(
            f"{BASE_URL}/api/pdf-templates",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Phase 34 - GET /api/pdf-templates still works")
    
    def test_phase33_worker_dashboard_still_works(self):
        """Phase 33: GET /api/worker/dashboard endpoint accessible (403 expected for admin user)"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers=self.headers,
            timeout=10
        )
        # Admin user gets 403 (not authorized as worker) - this is expected behavior
        # The endpoint is accessible, just role-restricted
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"
        print(f"PASS: Phase 33 - GET /api/worker/dashboard endpoint accessible (status: {response.status_code})")
    
    def test_phase31_cv_extractions_still_works(self):
        """Phase 31: GET /api/extractions/pending-review still works"""
        response = requests.get(
            f"{BASE_URL}/api/extractions/pending-review",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Phase 31 - GET /api/extractions/pending-review still works")
    
    def test_phase27_dbs_register_still_works(self):
        """Phase 27: GET /api/dbs-register still works"""
        response = requests.get(
            f"{BASE_URL}/api/dbs-register",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Phase 27 - GET /api/dbs-register still works")
    
    def test_phase26_agreements_endpoint_still_works(self):
        """Phase 26: Agreements endpoint pattern still works"""
        # Get an employee first
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.headers,
            timeout=10
        )
        if emp_response.status_code == 200 and emp_response.json():
            emp_id = emp_response.json()[0].get('id')
            response = requests.get(
                f"{BASE_URL}/api/employees/{emp_id}/agreements",
                headers=self.headers,
                timeout=10
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("PASS: Phase 26 - GET /api/employees/{id}/agreements still works")
        else:
            print("SKIP: No employees found for agreements test")


class TestPhase35RouterRegistration:
    """Verify router registration in server.py"""
    
    def test_router_import_exists(self):
        """Verify router import at line 148"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        assert 'from routes.generated_forms import router as generated_forms_router' in content
        print("PASS: Router import found in server.py")
    
    def test_router_inclusion_exists(self):
        """Verify router inclusion"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        assert 'api_router.include_router(generated_forms_router)' in content
        print("PASS: Router inclusion found in server.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

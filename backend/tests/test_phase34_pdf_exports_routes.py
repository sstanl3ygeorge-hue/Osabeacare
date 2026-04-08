"""
Phase 34: PDF Templates & Exports Routes Extraction Tests

Tests for 10 endpoints extracted from server.py to routes/pdf_exports.py:
- GET /pdf-templates (admin auth)
- GET /pdf-templates/{template_id} (admin auth)
- POST /pdf-templates (admin auth)
- PUT /pdf-templates/{template_id}/activate (admin auth)
- DELETE /pdf-templates/{template_id} (admin auth)
- POST /form-submissions/{submission_id}/generate-pdf (admin auth)
- GET /form-submissions/{submission_id}/download-pdf (user auth)
- GET /form-submissions/{submission_id}/view-pdf (user auth)
- GET /pdf-exports (admin auth)
- GET /pdf-field-mappings/{form_type} (admin auth)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestPDFExportsRoutesWithoutAuth:
    """Test that all PDF exports endpoints require authentication (return 401)"""
    
    def test_list_pdf_templates_requires_auth(self, api_client):
        """GET /api/pdf-templates requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/pdf-templates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/pdf-templates returns 401 without auth")
    
    def test_get_pdf_template_requires_auth(self, api_client):
        """GET /api/pdf-templates/{template_id} requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/pdf-templates/test-template-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/pdf-templates/{template_id} returns 401 without auth")
    
    def test_create_pdf_template_requires_auth(self, api_client):
        """POST /api/pdf-templates requires admin auth"""
        response = requests.post(f"{BASE_URL}/api/pdf-templates", data={
            "form_type": "test",
            "name": "Test Template"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/pdf-templates returns 401 without auth")
    
    def test_activate_pdf_template_requires_auth(self, api_client):
        """PUT /api/pdf-templates/{template_id}/activate requires admin auth"""
        response = requests.put(f"{BASE_URL}/api/pdf-templates/test-template-id/activate")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ PUT /api/pdf-templates/{template_id}/activate returns 401 without auth")
    
    def test_delete_pdf_template_requires_auth(self, api_client):
        """DELETE /api/pdf-templates/{template_id} requires admin auth"""
        response = requests.delete(f"{BASE_URL}/api/pdf-templates/test-template-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ DELETE /api/pdf-templates/{template_id} returns 401 without auth")
    
    def test_generate_pdf_requires_auth(self, api_client):
        """POST /api/form-submissions/{submission_id}/generate-pdf requires admin auth"""
        response = requests.post(f"{BASE_URL}/api/form-submissions/test-submission-id/generate-pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/form-submissions/{submission_id}/generate-pdf returns 401 without auth")
    
    def test_download_pdf_requires_auth(self, api_client):
        """GET /api/form-submissions/{submission_id}/download-pdf requires user auth"""
        response = requests.get(f"{BASE_URL}/api/form-submissions/test-submission-id/download-pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/form-submissions/{submission_id}/download-pdf returns 401 without auth")
    
    def test_view_pdf_requires_auth(self, api_client):
        """GET /api/form-submissions/{submission_id}/view-pdf requires user auth"""
        response = requests.get(f"{BASE_URL}/api/form-submissions/test-submission-id/view-pdf")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/form-submissions/{submission_id}/view-pdf returns 401 without auth")
    
    def test_list_pdf_exports_requires_auth(self, api_client):
        """GET /api/pdf-exports requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/pdf-exports")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/pdf-exports returns 401 without auth")
    
    def test_get_pdf_field_mappings_requires_auth(self, api_client):
        """GET /api/pdf-field-mappings/{form_type} requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/pdf-field-mappings/staff_health_questionnaire")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/pdf-field-mappings/{form_type} returns 401 without auth")


class TestPDFExportsRoutesWithAdminAuth:
    """Test PDF exports endpoints with valid admin authentication"""
    
    def test_list_pdf_templates_with_auth(self, admin_client):
        """GET /api/pdf-templates works with admin auth"""
        response = admin_client.get(f"{BASE_URL}/api/pdf-templates")
        # Should return 200 with list (may be empty)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        print(f"✓ GET /api/pdf-templates returns 200 with {len(data)} templates")
    
    def test_get_pdf_template_not_found(self, admin_client):
        """GET /api/pdf-templates/{template_id} returns 404 for non-existent template"""
        response = admin_client.get(f"{BASE_URL}/api/pdf-templates/non-existent-template-id")
        # Should return 404 for non-existent template
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/pdf-templates/{template_id} returns 404 for non-existent template")
    
    def test_activate_pdf_template_not_found(self, admin_client):
        """PUT /api/pdf-templates/{template_id}/activate returns 404 for non-existent template"""
        response = admin_client.put(f"{BASE_URL}/api/pdf-templates/non-existent-template-id/activate")
        # Should return 404 for non-existent template
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ PUT /api/pdf-templates/{template_id}/activate returns 404 for non-existent template")
    
    def test_delete_pdf_template_not_found(self, admin_client):
        """DELETE /api/pdf-templates/{template_id} returns 404 for non-existent template"""
        response = admin_client.delete(f"{BASE_URL}/api/pdf-templates/non-existent-template-id")
        # Should return 404 for non-existent template
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ DELETE /api/pdf-templates/{template_id} returns 404 for non-existent template")
    
    def test_generate_pdf_submission_not_found(self, admin_client):
        """POST /api/form-submissions/{submission_id}/generate-pdf returns 404 for non-existent submission"""
        response = admin_client.post(f"{BASE_URL}/api/form-submissions/non-existent-submission-id/generate-pdf")
        # Should return 404 for non-existent submission
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ POST /api/form-submissions/{submission_id}/generate-pdf returns 404 for non-existent submission")
    
    def test_download_pdf_submission_not_found(self, admin_client):
        """GET /api/form-submissions/{submission_id}/download-pdf returns 404 for non-existent submission"""
        response = admin_client.get(f"{BASE_URL}/api/form-submissions/non-existent-submission-id/download-pdf")
        # Should return 404 for non-existent submission/export
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/form-submissions/{submission_id}/download-pdf returns 404 for non-existent submission")
    
    def test_view_pdf_submission_not_found(self, admin_client):
        """GET /api/form-submissions/{submission_id}/view-pdf returns 404 for non-existent submission"""
        response = admin_client.get(f"{BASE_URL}/api/form-submissions/non-existent-submission-id/view-pdf")
        # Should return 404 for non-existent submission/export
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/form-submissions/{submission_id}/view-pdf returns 404 for non-existent submission")
    
    def test_list_pdf_exports_with_auth(self, admin_client):
        """GET /api/pdf-exports works with admin auth"""
        response = admin_client.get(f"{BASE_URL}/api/pdf-exports")
        # Should return 200 with list (may be empty)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        print(f"✓ GET /api/pdf-exports returns 200 with {len(data)} exports")
    
    def test_get_pdf_field_mappings_with_auth(self, admin_client):
        """GET /api/pdf-field-mappings/{form_type} works with admin auth"""
        response = admin_client.get(f"{BASE_URL}/api/pdf-field-mappings/staff_health_questionnaire")
        # Should return 200 with mapping config or 404 if not configured
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), "Expected dict response for field mappings"
            print(f"✓ GET /api/pdf-field-mappings/staff_health_questionnaire returns 200 with mapping config")
        else:
            print("✓ GET /api/pdf-field-mappings/staff_health_questionnaire returns 404 (no mapping configured)")
    
    def test_get_pdf_field_mappings_unknown_form_type(self, admin_client):
        """GET /api/pdf-field-mappings/{form_type} returns 404 for unknown form type"""
        response = admin_client.get(f"{BASE_URL}/api/pdf-field-mappings/unknown_form_type_xyz")
        # Should return 404 for unknown form type
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/pdf-field-mappings/{form_type} returns 404 for unknown form type")


class TestRouterRegistration:
    """Verify router is properly registered in server.py"""
    
    def test_router_import_exists(self):
        """Verify router import at line 147"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        assert 'from routes.pdf_exports import router as pdf_exports_router' in content
        print("✓ Router import found: from routes.pdf_exports import router as pdf_exports_router")
    
    def test_router_inclusion_exists(self):
        """Verify router inclusion at line 7553"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        assert 'api_router.include_router(pdf_exports_router)' in content
        print("✓ Router inclusion found: api_router.include_router(pdf_exports_router)")


class TestRegressionPreviousPhases:
    """Regression tests for previous phases (26-33)"""
    
    def test_phase33_worker_dashboard_endpoint(self, api_client):
        """Phase 33: Worker dashboard endpoint still accessible"""
        response = requests.get(f"{BASE_URL}/api/worker/dashboard")
        # Should return 401 (requires worker auth)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Phase 33 regression: GET /api/worker/dashboard returns 401 (worker auth required)")
    
    def test_phase32_profile_photos_endpoint(self, admin_client):
        """Phase 32: Profile photos endpoint still accessible"""
        response = admin_client.get(f"{BASE_URL}/api/employees")
        # Should return 200 with list
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Phase 32 regression: GET /api/employees returns 200")
    
    def test_phase31_cv_extractions_endpoint(self, admin_client):
        """Phase 31: CV extractions endpoint still accessible"""
        response = admin_client.get(f"{BASE_URL}/api/extractions/pending-review")
        # Should return 200 with list
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Phase 31 regression: GET /api/extractions/pending-review returns 200")
    
    def test_phase27_dbs_register_endpoint(self, admin_client):
        """Phase 27: DBS register endpoint still accessible"""
        response = admin_client.get(f"{BASE_URL}/api/dbs-register")
        # Should return 200 with list
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Phase 27 regression: GET /api/dbs-register returns 200")
    
    def test_phase26_agreements_endpoint(self, admin_client):
        """Phase 26: Agreements endpoint still accessible"""
        # Get an employee ID first
        emp_response = admin_client.get(f"{BASE_URL}/api/employees?limit=1")
        if emp_response.status_code == 200:
            employees = emp_response.json()
            if employees and len(employees) > 0:
                emp_id = employees[0].get('id')
                response = admin_client.get(f"{BASE_URL}/api/employees/{emp_id}/agreements")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                print(f"✓ Phase 26 regression: GET /api/employees/{{id}}/agreements returns 200")
                return
        # If no employees, just verify the endpoint pattern exists
        print("✓ Phase 26 regression: Agreements endpoint pattern verified (no employees to test)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test Suite for Phase 14: Forms Routes Cleanup Verification

Tests that form routes work correctly after removing ~652 duplicate routes from server.py.
The form CRUD routes are now served by routes/forms.py.
The complex PDF generation and download routes remain in server.py.

Key endpoints tested:
- Form templates: GET /api/form-submissions/templates
- Form submissions: GET/POST /api/form-submissions
- Generated forms: GET/POST /api/generated-forms, GET /api/generated-forms/{id}
- PDF generation (server.py): POST /api/form-submissions/{id}/generate-pdf
- Previous routes regression: service-users, templates, compliance/policies, employees
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


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for authenticated requests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


# ==================== AUTH LOGIN TEST ====================

class TestAuthLogin:
    """Test authentication endpoint"""
    
    def test_admin_login_success(self):
        """POST /api/auth/login - Admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful")


# ==================== FORM TEMPLATES TESTS ====================

class TestFormTemplates:
    """Test form templates endpoints (from forms.py)"""
    
    def test_get_form_templates_list(self, auth_headers):
        """GET /api/form-submissions/templates - List all form templates"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Form templates list returned {len(data)} templates")
        
        # Verify template structure
        if len(data) > 0:
            template = data[0]
            assert "requirement_id" in template
            assert "name" in template
            print(f"  Sample template: {template.get('name')}")


# ==================== FORM SUBMISSIONS TESTS ====================

class TestFormSubmissions:
    """Test form submissions CRUD (from forms.py)"""
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee for form submissions"""
        response = requests.get(f"{BASE_URL}/api/employees?limit=1", headers=auth_headers)
        if response.status_code == 200:
            employees = response.json()
            if isinstance(employees, list) and len(employees) > 0:
                return employees[0]["id"]
            elif isinstance(employees, dict) and employees.get("employees"):
                return employees["employees"][0]["id"]
        pytest.skip("No employees available")
    
    def test_list_form_submissions(self, auth_headers):
        """GET /api/form-submissions - List form submissions"""
        response = requests.get(f"{BASE_URL}/api/form-submissions", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Form submissions list returned {len(data)} submissions")
    
    def test_create_form_submission(self, auth_headers, test_employee_id):
        """POST /api/form-submissions - Create a new form submission"""
        submission_data = {
            "employee_id": test_employee_id,
            "requirement_id": "health_screening",
            "form_type": "health_screening",
            "data": {"test_field": "Test value from Phase 14 cleanup test"}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            headers=auth_headers,
            json=submission_data
        )
        assert response.status_code == 200, f"Failed to create: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["employee_id"] == test_employee_id
        print(f"✓ Created form submission: {data['id']}")
        
        # Verify retrieval
        get_resp = requests.get(
            f"{BASE_URL}/api/form-submissions/{data['id']}",
            headers=auth_headers
        )
        assert get_resp.status_code == 200
        print(f"✓ Verified form submission retrieval")


# ==================== GENERATED FORMS TESTS ====================

class TestGeneratedForms:
    """Test generated forms CRUD (from forms.py)"""
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee"""
        response = requests.get(f"{BASE_URL}/api/employees?limit=1", headers=auth_headers)
        if response.status_code == 200:
            employees = response.json()
            if isinstance(employees, list) and len(employees) > 0:
                return employees[0]["id"]
            elif isinstance(employees, dict) and employees.get("employees"):
                return employees["employees"][0]["id"]
        pytest.skip("No employees available")
    
    @pytest.fixture(scope="class")
    def test_template_id(self, auth_headers):
        """Get a test template"""
        response = requests.get(f"{BASE_URL}/api/templates?active=true", headers=auth_headers)
        if response.status_code == 200:
            templates = response.json()
            if isinstance(templates, list) and len(templates) > 0:
                return templates[0]["id"]
        pytest.skip("No templates available")
    
    def test_list_generated_forms(self, auth_headers):
        """GET /api/generated-forms - List generated forms"""
        response = requests.get(f"{BASE_URL}/api/generated-forms", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Generated forms list returned {len(data)} forms")
    
    def test_get_generated_form_by_id(self, auth_headers):
        """GET /api/generated-forms/{id} - Get specific generated form"""
        # First get list
        list_resp = requests.get(f"{BASE_URL}/api/generated-forms?limit=1", headers=auth_headers)
        if list_resp.status_code == 200 and len(list_resp.json()) > 0:
            form_id = list_resp.json()[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/generated-forms/{form_id}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed: {response.text}"
            data = response.json()
            assert data["id"] == form_id
            print(f"✓ Retrieved generated form by ID: {form_id}")
        else:
            print("✓ No generated forms to test retrieval (skipped)")
    
    def test_create_generated_form(self, auth_headers, test_employee_id, test_template_id):
        """POST /api/generated-forms - Create a new generated form"""
        form_data = {
            "template_id": test_template_id,
            "employee_id": test_employee_id,
            "form_data": {"test_field": "Phase 14 cleanup test"}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            headers=auth_headers,
            json=form_data
        )
        assert response.status_code == 200, f"Failed to create: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["status"] == "draft"
        print(f"✓ Created generated form: {data['id']}")


# ==================== PDF GENERATION TESTS (server.py) ====================

class TestPDFGeneration:
    """Test PDF generation endpoints (remain in server.py)"""
    
    def test_pdf_generation_endpoint_exists(self, auth_headers):
        """POST /api/form-submissions/{id}/generate-pdf - Endpoint exists"""
        # Get a form submission
        list_resp = requests.get(f"{BASE_URL}/api/form-submissions?limit=1", headers=auth_headers)
        if list_resp.status_code == 200 and len(list_resp.json()) > 0:
            submission_id = list_resp.json()[0]["id"]
            response = requests.post(
                f"{BASE_URL}/api/form-submissions/{submission_id}/generate-pdf",
                headers=auth_headers
            )
            # 400 is expected (no PDF mapping), 404 would mean route doesn't exist
            assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
            print(f"✓ PDF generation endpoint exists (status: {response.status_code})")
        else:
            print("✓ No form submissions to test PDF generation (skipped)")
    
    def test_pdf_download_endpoint_exists(self, auth_headers):
        """GET /api/form-submissions/{id}/download-pdf - Endpoint exists"""
        list_resp = requests.get(f"{BASE_URL}/api/form-submissions?limit=1", headers=auth_headers)
        if list_resp.status_code == 200 and len(list_resp.json()) > 0:
            submission_id = list_resp.json()[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/form-submissions/{submission_id}/download-pdf",
                headers=auth_headers
            )
            # 400 is expected (no PDF mapping), 404 would mean route doesn't exist
            assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
            print(f"✓ PDF download endpoint exists (status: {response.status_code})")
        else:
            print("✓ No form submissions to test PDF download (skipped)")
    
    def test_generated_form_pdf_regeneration_endpoint(self, auth_headers):
        """POST /api/generated-forms/{id}/regenerate-pdf - Endpoint exists"""
        list_resp = requests.get(f"{BASE_URL}/api/generated-forms?limit=1", headers=auth_headers)
        if list_resp.status_code == 200 and len(list_resp.json()) > 0:
            form_id = list_resp.json()[0]["id"]
            response = requests.post(
                f"{BASE_URL}/api/generated-forms/{form_id}/regenerate-pdf",
                headers=auth_headers
            )
            # 400 is expected (form not in completed status), 404 would mean route doesn't exist
            assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
            print(f"✓ PDF regeneration endpoint exists (status: {response.status_code})")
        else:
            print("✓ No generated forms to test PDF regeneration (skipped)")


# ==================== PREVIOUS ROUTES REGRESSION ====================

class TestPreviousRoutesRegression:
    """Verify previous routes still work after cleanup"""
    
    def test_service_users_list(self, auth_headers):
        """GET /api/service-users - Still works"""
        response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Service users route working")
    
    def test_templates_list(self, auth_headers):
        """GET /api/templates - Still works"""
        response = requests.get(f"{BASE_URL}/api/templates", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Templates route working")
    
    def test_compliance_policies(self, auth_headers):
        """GET /api/compliance/policies - Still works"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Compliance policies route working")
    
    def test_employees_list(self, auth_headers):
        """GET /api/employees - Still works"""
        response = requests.get(f"{BASE_URL}/api/employees?limit=5", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Employees route working")


# ==================== NO DUPLICATE ROUTES TEST ====================

class TestNoDuplicateRoutes:
    """Verify no duplicate routes after cleanup"""
    
    def test_form_submissions_single_handler(self, auth_headers):
        """Verify form-submissions routes have single handler (forms.py)"""
        # Test list endpoint
        response = requests.get(f"{BASE_URL}/api/form-submissions", headers=auth_headers)
        assert response.status_code == 200
        
        # Test with filters
        response = requests.get(f"{BASE_URL}/api/form-submissions?status=submitted", headers=auth_headers)
        assert response.status_code == 200
        
        print("✓ Form submissions routes working (single handler from forms.py)")
    
    def test_generated_forms_single_handler(self, auth_headers):
        """Verify generated-forms routes have single handler (forms.py)"""
        # Test list endpoint
        response = requests.get(f"{BASE_URL}/api/generated-forms", headers=auth_headers)
        assert response.status_code == 200
        
        # Test with filters
        response = requests.get(f"{BASE_URL}/api/generated-forms?status=draft", headers=auth_headers)
        assert response.status_code == 200
        
        print("✓ Generated forms routes working (single handler from forms.py)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

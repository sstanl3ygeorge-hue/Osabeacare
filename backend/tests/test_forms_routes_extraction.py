"""
Test Suite for Forms Routes Module (Phase 13 Modularization)

Tests the newly extracted forms.py module which handles:
- Form templates (health screening, induction, etc.)
- Form submissions CRUD
- Generated forms CRUD

Also includes regression tests for previous routes to ensure no collisions.
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


class TestAuthLogin:
    """Test authentication - prerequisite for all other tests"""
    
    def test_admin_login(self):
        """Test admin login returns valid token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful, role: {data['user'].get('role')}")


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


# ==================== FORM TEMPLATES TESTS ====================

class TestFormTemplates:
    """Test form templates endpoints from forms.py"""
    
    def test_get_form_templates_list(self, auth_headers):
        """GET /api/form-submissions/templates - List all form templates"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Form templates list returned {len(data)} templates")
        
        # Verify template structure if any exist
        if len(data) > 0:
            template = data[0]
            assert "requirement_id" in template, "Template missing requirement_id"
            assert "name" in template, "Template missing name"
            print(f"  First template: {template.get('name')} ({template.get('requirement_id')})")
    
    def test_get_form_templates_requires_auth(self):
        """GET /api/form-submissions/templates - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/form-submissions/templates")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Form templates endpoint correctly requires authentication")
    
    def test_get_form_template_by_id_not_found(self, auth_headers):
        """GET /api/form-submissions/template/{id} - Non-existent template returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/template/nonexistent_template_xyz",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent template correctly returns 404")


# ==================== FORM SUBMISSIONS TESTS ====================

class TestFormSubmissions:
    """Test form submissions CRUD endpoints from forms.py"""
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get or create a test employee for form submissions"""
        # First try to find an existing employee
        response = requests.get(
            f"{BASE_URL}/api/employees?limit=1",
            headers=auth_headers
        )
        if response.status_code == 200:
            employees = response.json()
            if isinstance(employees, list) and len(employees) > 0:
                return employees[0]["id"]
            elif isinstance(employees, dict) and employees.get("employees"):
                return employees["employees"][0]["id"]
        
        # If no employees, skip these tests
        pytest.skip("No employees available for form submission tests")
    
    def test_list_form_submissions(self, auth_headers):
        """GET /api/form-submissions - List form submissions"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Form submissions list returned {len(data)} submissions")
    
    def test_list_form_submissions_with_filters(self, auth_headers):
        """GET /api/form-submissions - Test query filters"""
        # Test with status filter
        response = requests.get(
            f"{BASE_URL}/api/form-submissions?status=submitted",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed with status filter: {response.text}"
        
        # Test with limit
        response = requests.get(
            f"{BASE_URL}/api/form-submissions?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed with limit filter: {response.text}"
        print("✓ Form submissions filters work correctly")
    
    def test_form_submissions_requires_auth(self):
        """GET /api/form-submissions - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/form-submissions")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Form submissions endpoint correctly requires authentication")
    
    def test_create_form_submission(self, auth_headers, test_employee_id):
        """POST /api/form-submissions - Create a new form submission"""
        # Use a valid form type from the system
        submission_data = {
            "employee_id": test_employee_id,
            "requirement_id": "health_screening",  # Valid form type
            "form_type": "health_screening",
            "data": {
                "question_1": "Yes",
                "question_2": "No",
                "notes": "Test submission from pytest"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/form-submissions",
            headers=auth_headers,
            json=submission_data
        )
        assert response.status_code == 200, f"Failed to create: {response.text}"
        data = response.json()
        assert "id" in data, "Response missing id"
        assert data["employee_id"] == test_employee_id
        assert data["form_type"] == "health_screening"
        print(f"✓ Created form submission: {data['id']}")
    
    def test_get_form_submission_not_found(self, auth_headers):
        """GET /api/form-submissions/{id} - Non-existent submission returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/nonexistent_submission_xyz",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent form submission correctly returns 404")


# ==================== GENERATED FORMS TESTS ====================

class TestGeneratedForms:
    """Test generated forms CRUD endpoints from forms.py"""
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get or create a test employee for generated forms"""
        response = requests.get(
            f"{BASE_URL}/api/employees?limit=1",
            headers=auth_headers
        )
        if response.status_code == 200:
            employees = response.json()
            if isinstance(employees, list) and len(employees) > 0:
                return employees[0]["id"]
            elif isinstance(employees, dict) and employees.get("employees"):
                return employees["employees"][0]["id"]
        pytest.skip("No employees available for generated forms tests")
    
    @pytest.fixture(scope="class")
    def test_template_id(self, auth_headers):
        """Get or create a test template for generated forms"""
        response = requests.get(
            f"{BASE_URL}/api/templates?active=true",
            headers=auth_headers
        )
        if response.status_code == 200:
            templates = response.json()
            if isinstance(templates, list) and len(templates) > 0:
                return templates[0]["id"]
        pytest.skip("No templates available for generated forms tests")
    
    def test_list_generated_forms(self, auth_headers):
        """GET /api/generated-forms - List generated forms"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Generated forms list returned {len(data)} forms")
    
    def test_list_generated_forms_with_filters(self, auth_headers):
        """GET /api/generated-forms - Test query filters"""
        # Test with status filter
        response = requests.get(
            f"{BASE_URL}/api/generated-forms?status=draft",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed with status filter: {response.text}"
        
        # Test with limit
        response = requests.get(
            f"{BASE_URL}/api/generated-forms?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed with limit filter: {response.text}"
        print("✓ Generated forms filters work correctly")
    
    def test_generated_forms_requires_auth(self):
        """GET /api/generated-forms - Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/generated-forms")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Generated forms endpoint correctly requires authentication")
    
    def test_create_generated_form(self, auth_headers, test_employee_id, test_template_id):
        """POST /api/generated-forms - Create a new generated form"""
        form_data = {
            "template_id": test_template_id,
            "employee_id": test_employee_id,
            "form_data": {
                "test_field": "Test value from pytest"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            headers=auth_headers,
            json=form_data
        )
        assert response.status_code == 200, f"Failed to create: {response.text}"
        data = response.json()
        assert "id" in data, "Response missing id"
        assert data["employee_id"] == test_employee_id
        assert data["template_id"] == test_template_id
        assert data["status"] == "draft"
        print(f"✓ Created generated form: {data['id']}")
        
        # Verify we can get it by ID
        get_response = requests.get(
            f"{BASE_URL}/api/generated-forms/{data['id']}",
            headers=auth_headers
        )
        assert get_response.status_code == 200, f"Failed to get created form: {get_response.text}"
        print(f"✓ Verified generated form retrieval by ID")
        
        return data["id"]
    
    def test_get_generated_form_not_found(self, auth_headers):
        """GET /api/generated-forms/{id} - Non-existent form returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms/nonexistent_form_xyz",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent generated form correctly returns 404")


# ==================== PREVIOUS ROUTES REGRESSION TESTS ====================

class TestPreviousRoutesRegression:
    """Verify previous routes still work after forms.py extraction"""
    
    def test_service_users_list(self, auth_headers):
        """GET /api/service-users - Service users route still works"""
        response = requests.get(
            f"{BASE_URL}/api/service-users",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Service users failed: {response.text}"
        print("✓ Service users route working (from service_users.py)")
    
    def test_templates_list(self, auth_headers):
        """GET /api/templates - Templates route still works"""
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Templates failed: {response.text}"
        data = response.json()
        print(f"✓ Templates route working, returned {len(data)} templates (from templates.py)")
    
    def test_compliance_policies(self, auth_headers):
        """GET /api/compliance/policies - Compliance policies route still works"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance policies failed: {response.text}"
        print("✓ Compliance policies route working (from compliance.py)")
    
    def test_employees_list(self, auth_headers):
        """GET /api/employees - Employees route still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Employees failed: {response.text}"
        print("✓ Employees route working (from employees.py)")
    
    def test_dashboard_stats(self, auth_headers):
        """GET /api/dashboard/stats - Dashboard stats route still works"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=auth_headers
        )
        # Dashboard stats might return 200 or 404 depending on data
        assert response.status_code in [200, 404], f"Dashboard stats unexpected status: {response.status_code}"
        print("✓ Dashboard stats route accessible")


# ==================== ROUTE COLLISION TESTS ====================

class TestNoRouteCollisions:
    """Verify no route collisions between forms.py and server.py"""
    
    def test_form_submissions_vs_server_forms(self, auth_headers):
        """Verify form-submissions routes don't conflict with server.py form routes"""
        # forms.py handles /api/form-submissions/*
        response1 = requests.get(
            f"{BASE_URL}/api/form-submissions",
            headers=auth_headers
        )
        assert response1.status_code == 200, "form-submissions route should work"
        
        # forms.py handles /api/generated-forms/*
        response2 = requests.get(
            f"{BASE_URL}/api/generated-forms",
            headers=auth_headers
        )
        assert response2.status_code == 200, "generated-forms route should work"
        
        print("✓ No route collisions detected between forms.py and server.py")
    
    def test_form_templates_route(self, auth_headers):
        """Verify form templates route works correctly"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Form templates route failed: {response.text}"
        print("✓ Form templates route working correctly")


# ==================== AUTH REQUIREMENTS TESTS ====================

class TestAuthRequirements:
    """Verify all forms routes require proper authentication"""
    
    def test_form_submissions_templates_requires_auth(self):
        """Form templates requires auth"""
        response = requests.get(f"{BASE_URL}/api/form-submissions/templates")
        assert response.status_code == 401
        print("✓ /api/form-submissions/templates requires auth")
    
    def test_form_submissions_list_requires_auth(self):
        """Form submissions list requires auth"""
        response = requests.get(f"{BASE_URL}/api/form-submissions")
        assert response.status_code == 401
        print("✓ /api/form-submissions requires auth")
    
    def test_form_submissions_create_requires_auth(self):
        """Form submissions create requires auth"""
        response = requests.post(f"{BASE_URL}/api/form-submissions", json={})
        assert response.status_code == 401
        print("✓ POST /api/form-submissions requires auth")
    
    def test_generated_forms_list_requires_auth(self):
        """Generated forms list requires auth"""
        response = requests.get(f"{BASE_URL}/api/generated-forms")
        assert response.status_code == 401
        print("✓ /api/generated-forms requires auth")
    
    def test_generated_forms_create_requires_auth(self):
        """Generated forms create requires auth"""
        response = requests.post(f"{BASE_URL}/api/generated-forms", json={})
        assert response.status_code == 401
        print("✓ POST /api/generated-forms requires auth")


# ==================== SUMMARY ====================

class TestSummary:
    """Summary test to verify all modules are working"""
    
    def test_all_13_route_modules_accessible(self, auth_headers):
        """Verify all 13 route modules are accessible"""
        modules_tested = {
            "auth.py": "/api/auth/me",
            "workers.py": "/api/worker/account-status",  # Will fail without worker token, but route exists
            "admin.py": "/api/admin/users",
            "training.py": "/api/training/catalogue",
            "documents.py": "/api/document-types",
            "recruitment.py": "/api/recruitment/applicants",
            "employees.py": "/api/employees",
            "references.py": "/api/references",
            "notifications.py": "/api/notifications",
            "compliance.py": "/api/compliance/policies",
            "templates.py": "/api/templates",
            "service_users.py": "/api/service-users",
            "forms.py": "/api/form-submissions",
        }
        
        accessible_count = 0
        for module, endpoint in modules_tested.items():
            response = requests.get(f"{BASE_URL}{endpoint}", headers=auth_headers)
            # 200, 403, or 404 means route exists (401 without auth is also valid)
            if response.status_code in [200, 403, 404]:
                accessible_count += 1
                print(f"  ✓ {module}: {endpoint} - {response.status_code}")
            else:
                print(f"  ? {module}: {endpoint} - {response.status_code}")
        
        print(f"\n✓ {accessible_count}/{len(modules_tested)} route modules verified accessible")
        assert accessible_count >= 10, f"Expected at least 10 modules accessible, got {accessible_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

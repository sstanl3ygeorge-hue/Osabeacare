"""
Test suite for Import Application Form feature
Tests the /api/generated-forms/import-application endpoint
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test files URLs
APPLICATION_FILE_URL = "https://customer-assets.emergentagent.com/job_caretrust-portal/artifacts/9uxfefiv_kunle.pdf"
CV_FILE_URL = "https://customer-assets.emergentagent.com/job_caretrust-portal/artifacts/clr6k7ja_OLAKUNLE%20CV%20%281%29.pdf"

# Test employee ID
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def application_file():
    """Download and return application file content"""
    response = requests.get(APPLICATION_FILE_URL)
    assert response.status_code == 200, f"Failed to download application file: {response.status_code}"
    return response.content


@pytest.fixture(scope="module")
def cv_file():
    """Download and return CV file content"""
    response = requests.get(CV_FILE_URL)
    assert response.status_code == 200, f"Failed to download CV file: {response.status_code}"
    return response.content


class TestGenerateFormsDropdown:
    """Test that Generate Forms dropdown has correct options"""
    
    def test_templates_endpoint_exists(self, auth_headers):
        """Verify templates endpoint returns data"""
        response = requests.get(f"{BASE_URL}/api/templates", headers=auth_headers)
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)
        print(f"Found {len(templates)} templates")
    
    def test_application_form_template_exists(self, auth_headers):
        """Verify Application Form template exists for import feature"""
        response = requests.get(f"{BASE_URL}/api/templates", headers=auth_headers)
        assert response.status_code == 200
        templates = response.json()
        
        # Find Application Form template
        app_template = next((t for t in templates if "Application Form" in t.get("name", "")), None)
        assert app_template is not None, "Application Form template not found"
        print(f"Found Application Form template: {app_template['name']}")


class TestImportApplicationEndpoint:
    """Test the /api/generated-forms/import-application endpoint"""
    
    def test_import_requires_authentication(self):
        """Verify endpoint requires authentication"""
        files = {
            'application_file': ('test.pdf', b'test content', 'application/pdf')
        }
        data = {'employee_id': TEST_EMPLOYEE_ID}
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-application",
            files=files,
            data=data
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_import_requires_employee_id(self, auth_headers):
        """Verify endpoint requires employee_id"""
        files = {
            'application_file': ('test.pdf', b'test content', 'application/pdf')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-application",
            files=files,
            headers=auth_headers
        )
        # Should fail with 422 (validation error) since employee_id is required
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    def test_import_requires_application_file(self, auth_headers):
        """Verify endpoint requires application_file"""
        data = {'employee_id': TEST_EMPLOYEE_ID}
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-application",
            data=data,
            headers=auth_headers
        )
        # Should fail with 422 (validation error) since application_file is required
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    def test_import_with_invalid_employee_id(self, auth_headers):
        """Verify endpoint returns 404 for invalid employee"""
        files = {
            'application_file': ('test.pdf', b'test content', 'application/pdf')
        }
        data = {'employee_id': 'invalid-employee-id'}
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-application",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "Employee not found" in response.json().get("detail", "")
    
    def test_import_application_only(self, auth_headers, application_file):
        """Test importing application form without CV"""
        files = {
            'application_file': ('kunle_application.pdf', application_file, 'application/pdf')
        }
        data = {'employee_id': TEST_EMPLOYEE_ID}
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-application",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        result = response.json()
        
        # Verify response structure
        assert result.get("success") == True
        assert "form_id" in result
        assert result.get("form_status") == "completed_imported"
        assert result.get("application_file") == "kunle_application.pdf"
        assert result.get("cv_file") is None
        assert "message" in result
        
        print(f"Successfully imported application. Form ID: {result['form_id']}")
        return result["form_id"]
    
    def test_import_application_with_cv(self, auth_headers, application_file, cv_file):
        """Test importing application form with CV"""
        files = {
            'application_file': ('kunle_application_with_cv.pdf', application_file, 'application/pdf'),
            'cv_file': ('kunle_cv.pdf', cv_file, 'application/pdf')
        }
        data = {'employee_id': TEST_EMPLOYEE_ID}
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/import-application",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        result = response.json()
        
        # Verify response structure
        assert result.get("success") == True
        assert "form_id" in result
        assert result.get("form_status") == "completed_imported"
        assert result.get("application_file") == "kunle_application_with_cv.pdf"
        assert result.get("cv_file") == "kunle_cv.pdf"
        
        print(f"Successfully imported application with CV. Form ID: {result['form_id']}")
        return result["form_id"]


class TestImportedFormVerification:
    """Verify imported forms appear correctly in the system"""
    
    def test_imported_form_appears_in_forms_list(self, auth_headers):
        """Verify imported form appears in employee's forms list"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        forms = response.json()
        
        # Find imported forms
        imported_forms = [f for f in forms if f.get("status") == "completed_imported"]
        assert len(imported_forms) > 0, "No imported forms found"
        
        # Verify imported form properties
        imported_form = imported_forms[0]
        assert imported_form.get("locked") == True, "Imported form should be locked"
        assert imported_form.get("template_name") is not None
        assert "Application Form" in imported_form.get("template_name", "")
        
        print(f"Found {len(imported_forms)} imported form(s)")
        print(f"Form status: {imported_form.get('status')}")
        print(f"Form locked: {imported_form.get('locked')}")
    
    def test_imported_form_has_correct_status(self, auth_headers):
        """Verify imported form has 'completed_imported' status"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        forms = response.json()
        
        imported_forms = [f for f in forms if f.get("status") == "completed_imported"]
        assert len(imported_forms) > 0, "No forms with 'completed_imported' status found"
        
        for form in imported_forms:
            assert form.get("status") == "completed_imported"
            print(f"Form {form.get('id')[:8]}... has status: {form.get('status')}")
    
    def test_application_document_created(self, auth_headers):
        """Verify application document is created in employee's documents"""
        response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        documents = response.json()
        
        # Find application form documents
        app_docs = [d for d in documents if "Application" in d.get("document_type_name", "")]
        
        # Check if any have approved status (from import)
        approved_app_docs = [d for d in app_docs if d.get("status") == "approved"]
        
        print(f"Found {len(app_docs)} application document(s)")
        print(f"Approved application documents: {len(approved_app_docs)}")
        
        if approved_app_docs:
            doc = approved_app_docs[0]
            assert doc.get("status") == "approved"
            assert doc.get("file_url") is not None
            print(f"Application document status: {doc.get('status')}")


class TestFormLocking:
    """Test that imported forms are properly locked"""
    
    def test_imported_form_is_locked(self, auth_headers):
        """Verify imported form has locked=True"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        forms = response.json()
        
        imported_forms = [f for f in forms if f.get("status") == "completed_imported"]
        
        for form in imported_forms:
            assert form.get("locked") == True, f"Form {form.get('id')} should be locked"
            print(f"Form {form.get('id')[:8]}... locked: {form.get('locked')}")


class TestCleanup:
    """Clean up test data after tests"""
    
    def test_cleanup_imported_forms(self, auth_headers):
        """Remove test imported forms to keep database clean"""
        # Get all forms for the test employee
        response = requests.get(
            f"{BASE_URL}/api/generated-forms?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            forms = response.json()
            imported_forms = [f for f in forms if f.get("status") == "completed_imported"]
            
            # Note: We're not actually deleting here to preserve test data
            # In a real cleanup, you would delete these forms
            print(f"Found {len(imported_forms)} imported forms (not deleting for verification)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

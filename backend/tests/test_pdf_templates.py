"""
Test PDF Template Management & Generation - Template-Backed Forms Architecture

Tests:
- POST /api/pdf-templates - Create new PDF template
- GET /api/pdf-templates - List all templates
- PUT /api/pdf-templates/{id}/activate - Activate template
- POST /api/form-submissions/{id}/generate-pdf - Generate PDF from submission
- GET /api/form-submissions/{id}/download-pdf - Download PDF
- GET /api/pdf-field-mappings/{form_type} - Get field mapping config
- GET /api/pdf-exports - List PDF exports
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee with staff_health_questionnaire submission
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestPDFTemplateEndpoints:
    """Test PDF Template CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_pdf_templates(self):
        """GET /api/pdf-templates - List all templates"""
        response = requests.get(f"{BASE_URL}/api/pdf-templates", headers=self.headers)
        assert response.status_code == 200, f"Failed to list templates: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ GET /api/pdf-templates returns 200 with {len(data)} templates")
    
    def test_list_pdf_templates_filtered_by_form_type(self):
        """GET /api/pdf-templates?form_type=staff_health_questionnaire"""
        response = requests.get(
            f"{BASE_URL}/api/pdf-templates?form_type=staff_health_questionnaire",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to list templates: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # All returned templates should be for staff_health_questionnaire
        for template in data:
            assert template.get("form_type") == "staff_health_questionnaire"
        print(f"✅ GET /api/pdf-templates?form_type=staff_health_questionnaire returns {len(data)} templates")
    
    def test_create_pdf_template(self):
        """POST /api/pdf-templates - Create new template"""
        # Create a simple PDF file for testing
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        
        files = {
            'file': ('test_template.pdf', io.BytesIO(pdf_content), 'application/pdf')
        }
        data = {
            'form_type': 'staff_health_questionnaire',
            'name': 'TEST_Staff Health Template v1.0',
            'version': '1.0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pdf-templates",
            headers=self.headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Failed to create template: {response.text}"
        
        result = response.json()
        assert "id" in result, "Response should contain template ID"
        assert result.get("form_type") == "staff_health_questionnaire"
        assert result.get("name") == "TEST_Staff Health Template v1.0"
        assert result.get("is_active") == False, "New template should not be active by default"
        
        # Store template ID for cleanup
        self.created_template_id = result["id"]
        print(f"✅ POST /api/pdf-templates creates template with ID: {result['id']}")
        
        # Cleanup - delete the test template
        cleanup_response = requests.delete(
            f"{BASE_URL}/api/pdf-templates/{result['id']}",
            headers=self.headers
        )
        assert cleanup_response.status_code == 200, f"Failed to cleanup template: {cleanup_response.text}"
        print(f"✅ Cleanup: Deleted test template {result['id']}")
    
    def test_create_pdf_template_invalid_form_type(self):
        """POST /api/pdf-templates with invalid form_type should fail"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        
        files = {
            'file': ('test_template.pdf', io.BytesIO(pdf_content), 'application/pdf')
        }
        data = {
            'form_type': 'invalid_form_type_xyz',
            'name': 'Invalid Template',
            'version': '1.0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pdf-templates",
            headers=self.headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 400, f"Should fail with 400 for invalid form_type: {response.text}"
        print("✅ POST /api/pdf-templates rejects invalid form_type with 400")
    
    def test_activate_pdf_template(self):
        """PUT /api/pdf-templates/{id}/activate - Activate template"""
        # First create a template
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        
        files = {
            'file': ('test_activate.pdf', io.BytesIO(pdf_content), 'application/pdf')
        }
        data = {
            'form_type': 'staff_health_questionnaire',
            'name': 'TEST_Activate Template',
            'version': '1.0'
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/pdf-templates",
            headers=self.headers,
            files=files,
            data=data
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        
        # Activate the template
        activate_response = requests.put(
            f"{BASE_URL}/api/pdf-templates/{template_id}/activate",
            headers=self.headers
        )
        
        assert activate_response.status_code == 200, f"Failed to activate template: {activate_response.text}"
        result = activate_response.json()
        assert result.get("success") == True
        print(f"✅ PUT /api/pdf-templates/{template_id}/activate returns 200")
        
        # Verify template is now active
        get_response = requests.get(
            f"{BASE_URL}/api/pdf-templates/{template_id}",
            headers=self.headers
        )
        assert get_response.status_code == 200
        assert get_response.json().get("is_active") == True
        print("✅ Template is_active is True after activation")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pdf-templates/{template_id}", headers=self.headers)
    
    def test_activate_nonexistent_template(self):
        """PUT /api/pdf-templates/{id}/activate with invalid ID should fail"""
        response = requests.put(
            f"{BASE_URL}/api/pdf-templates/nonexistent-id-12345/activate",
            headers=self.headers
        )
        assert response.status_code == 404, f"Should return 404: {response.text}"
        print("✅ PUT /api/pdf-templates/invalid-id/activate returns 404")


class TestPDFFieldMappings:
    """Test PDF field mapping configuration endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_field_mapping_staff_health(self):
        """GET /api/pdf-field-mappings/staff_health_questionnaire"""
        response = requests.get(
            f"{BASE_URL}/api/pdf-field-mappings/staff_health_questionnaire",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get field mapping: {response.text}"
        
        data = response.json()
        assert data.get("form_type") == "staff_health_questionnaire"
        assert "sections" in data, "Mapping should contain sections"
        assert "company_branding" in data, "Mapping should contain company_branding"
        
        # Verify sections
        sections = data.get("sections", [])
        section_ids = [s.get("id") for s in sections]
        assert "personal_info" in section_ids, "Should have personal_info section"
        assert "health_questions" in section_ids, "Should have health_questions section"
        assert "declaration" in section_ids, "Should have declaration section"
        
        # Verify branding
        branding = data.get("company_branding", {})
        assert branding.get("name") == "Osabea Healthcare Solutions Ltd"
        assert branding.get("header_color") == "#2E7D32"
        
        print("✅ GET /api/pdf-field-mappings/staff_health_questionnaire returns correct mapping")
        print(f"   - Sections: {section_ids}")
        print(f"   - Company: {branding.get('name')}")
    
    def test_get_field_mapping_invalid_form_type(self):
        """GET /api/pdf-field-mappings/invalid_form should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/pdf-field-mappings/invalid_form_type",
            headers=self.headers
        )
        
        assert response.status_code == 404, f"Should return 404: {response.text}"
        print("✅ GET /api/pdf-field-mappings/invalid_form_type returns 404")


class TestPDFGeneration:
    """Test PDF generation from form submissions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_form_submission_for_employee(self):
        """Verify test employee has staff_health_questionnaire submission"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions?employee_id={TEST_EMPLOYEE_ID}&requirement_id=staff_health_questionnaire",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get submissions: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, f"Test employee {TEST_EMPLOYEE_ID} should have staff_health_questionnaire submission"
        
        submission = data[0]
        assert submission.get("form_type") == "staff_health_questionnaire"
        assert "data" in submission, "Submission should contain data"
        
        self.submission_id = submission.get("id")
        print(f"✅ Found form submission ID: {self.submission_id}")
        print(f"   - Form type: {submission.get('form_type')}")
        print(f"   - Status: {submission.get('status')}")
        return self.submission_id
    
    def test_generate_pdf_from_submission(self):
        """POST /api/form-submissions/{id}/generate-pdf"""
        # First get the submission ID
        submissions_response = requests.get(
            f"{BASE_URL}/api/form-submissions?employee_id={TEST_EMPLOYEE_ID}&requirement_id=staff_health_questionnaire",
            headers=self.headers
        )
        assert submissions_response.status_code == 200
        submissions = submissions_response.json()
        
        if not submissions:
            pytest.skip("No staff_health_questionnaire submission found for test employee")
        
        submission_id = submissions[0].get("id")
        
        # Generate PDF
        response = requests.post(
            f"{BASE_URL}/api/form-submissions/{submission_id}/generate-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to generate PDF: {response.text}"
        
        result = response.json()
        assert result.get("success") == True, "Response should indicate success"
        assert "export_id" in result, "Response should contain export_id"
        assert "file_url" in result, "Response should contain file_url"
        assert "filename" in result, "Response should contain filename"
        
        # Verify filename format
        filename = result.get("filename", "")
        assert "staff_health_questionnaire" in filename, f"Filename should contain form type: {filename}"
        assert filename.endswith(".pdf"), f"Filename should end with .pdf: {filename}"
        
        print(f"✅ POST /api/form-submissions/{submission_id}/generate-pdf returns 200")
        print(f"   - Export ID: {result.get('export_id')}")
        print(f"   - Filename: {filename}")
        print(f"   - File URL: {result.get('file_url')}")
    
    def test_generate_pdf_invalid_submission(self):
        """POST /api/form-submissions/invalid-id/generate-pdf should fail"""
        response = requests.post(
            f"{BASE_URL}/api/form-submissions/nonexistent-submission-id/generate-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 404, f"Should return 404: {response.text}"
        print("✅ POST /api/form-submissions/invalid-id/generate-pdf returns 404")
    
    def test_download_pdf(self):
        """GET /api/form-submissions/{id}/download-pdf"""
        # First get the submission ID
        submissions_response = requests.get(
            f"{BASE_URL}/api/form-submissions?employee_id={TEST_EMPLOYEE_ID}&requirement_id=staff_health_questionnaire",
            headers=self.headers
        )
        assert submissions_response.status_code == 200
        submissions = submissions_response.json()
        
        if not submissions:
            pytest.skip("No staff_health_questionnaire submission found for test employee")
        
        submission_id = submissions[0].get("id")
        
        # Download PDF (may generate on-the-fly if no export exists)
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{submission_id}/download-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to download PDF: {response.text}"
        
        result = response.json()
        assert "file_url" in result, "Response should contain file_url"
        assert "filename" in result, "Response should contain filename"
        
        print(f"✅ GET /api/form-submissions/{submission_id}/download-pdf returns 200")
        print(f"   - File URL: {result.get('file_url')}")
        print(f"   - Cached: {result.get('cached', 'N/A')}")


class TestPDFExports:
    """Test PDF exports listing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_pdf_exports(self):
        """GET /api/pdf-exports - List all exports"""
        response = requests.get(f"{BASE_URL}/api/pdf-exports", headers=self.headers)
        
        assert response.status_code == 200, f"Failed to list exports: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✅ GET /api/pdf-exports returns 200 with {len(data)} exports")
        
        # If there are exports, verify structure
        if data:
            export = data[0]
            assert "id" in export, "Export should have id"
            assert "submission_id" in export, "Export should have submission_id"
            assert "form_type" in export, "Export should have form_type"
            assert "file_url" in export, "Export should have file_url"
            print(f"   - First export: {export.get('form_type')} for {export.get('employee_name')}")
    
    def test_list_pdf_exports_filtered(self):
        """GET /api/pdf-exports?form_type=staff_health_questionnaire"""
        response = requests.get(
            f"{BASE_URL}/api/pdf-exports?form_type=staff_health_questionnaire",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to list exports: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # All returned exports should be for staff_health_questionnaire
        for export in data:
            assert export.get("form_type") == "staff_health_questionnaire"
        
        print(f"✅ GET /api/pdf-exports?form_type=staff_health_questionnaire returns {len(data)} exports")
    
    def test_list_pdf_exports_by_employee(self):
        """GET /api/pdf-exports?employee_id={id}"""
        response = requests.get(
            f"{BASE_URL}/api/pdf-exports?employee_id={TEST_EMPLOYEE_ID}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to list exports: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # All returned exports should be for the test employee
        for export in data:
            assert export.get("employee_id") == TEST_EMPLOYEE_ID
        
        print(f"✅ GET /api/pdf-exports?employee_id={TEST_EMPLOYEE_ID} returns {len(data)} exports")


class TestExistingFlowsUnchanged:
    """Verify existing View Form/Edit/Verify flows still work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_view_form_submission(self):
        """GET /api/form-submissions - View form still works"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions?employee_id={TEST_EMPLOYEE_ID}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get submissions: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✅ GET /api/form-submissions (View Form) returns 200 with {len(data)} submissions")
    
    def test_compliance_requirements_includes_form_submission(self):
        """GET /api/employees/{id}/compliance-requirements includes form submission data"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get compliance requirements: {response.text}"
        
        data = response.json()
        requirements = data.get("requirements", [])
        
        # Find staff_health_questionnaire requirement
        staff_health_req = None
        for req in requirements:
            if req.get("id") == "staff_health_questionnaire":
                staff_health_req = req
                break
        
        assert staff_health_req is not None, "staff_health_questionnaire should be in requirements"
        
        # Verify form_submission data is included
        form_submission = staff_health_req.get("form_submission")
        if form_submission:
            assert "id" in form_submission, "form_submission should have id"
            assert "data" in form_submission, "form_submission should have data"
            print(f"✅ Compliance requirements includes form_submission for staff_health_questionnaire")
            print(f"   - Submission ID: {form_submission.get('id')}")
            print(f"   - Status: {form_submission.get('status')}")
        else:
            print("⚠️ No form_submission found for staff_health_questionnaire (may not be submitted yet)")
    
    def test_form_template_endpoint(self):
        """GET /api/form-submissions/template/{requirement_id} still works"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get form template: {response.text}"
        
        data = response.json()
        assert data.get("requirement_id") == "staff_health_questionnaire"
        assert "sections" in data, "Template should have sections"
        
        print("✅ GET /api/form-submissions/template/staff_health_questionnaire returns 200")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

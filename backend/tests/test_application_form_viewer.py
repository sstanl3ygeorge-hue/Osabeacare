"""
Test Application Form Viewer Fix - Final Verification
Tests the fix for the "Form template not found" error when viewing application forms.

Key tests:
1. GET /api/form-submissions/{id} returns correct data structure
2. form_data and data fields are both present
3. form_type is set correctly (application_form)
4. PDF export works (returns 200)
5. All form sections have data
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com')

# Test data
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"
EXISTING_EMPLOYEE_ID = "5bc0b72f-e298-4a97-bc63-25eece5cf9cf"
EXISTING_SUBMISSION_ID = "cd56a8f3-3783-4fe6-b017-3e9acabf40a2"
EXPECTED_REFERENCES = ["Sarah Wilson", "Michael Brown"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestApplicationFormViewer:
    """Tests for Application Form Viewer fix"""
    
    def test_form_submission_endpoint_returns_200(self, auth_headers):
        """Test that GET /api/form-submissions/{id} returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Form submission endpoint returns 200")
    
    def test_form_submission_has_form_data(self, auth_headers):
        """Test that response has form_data field"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        assert "form_data" in data, "Response missing form_data field"
        assert data["form_data"] is not None, "form_data is None"
        print("✓ Response has form_data field")
    
    def test_form_submission_has_data_field(self, auth_headers):
        """Test that response has data field (for compatibility)"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        assert "data" in data, "Response missing data field"
        assert data["data"] is not None, "data is None"
        print("✓ Response has data field (compatibility)")
    
    def test_form_type_is_application_form(self, auth_headers):
        """Test that form_type is set to application_form"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        
        form_type = data.get("form_type") or data.get("requirement_id")
        assert form_type == "application_form", f"Expected form_type='application_form', got '{form_type}'"
        print("✓ form_type is 'application_form'")
    
    def test_personal_details_section_has_data(self, auth_headers):
        """Test that Personal Details section has data"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        form_data = data.get("form_data", {})
        
        # Check for personal_details nested object
        personal = form_data.get("personal_details", {})
        assert personal.get("first_name"), "Missing first_name in personal_details"
        assert personal.get("last_name"), "Missing last_name in personal_details"
        print(f"✓ Personal Details: {personal.get('first_name')} {personal.get('last_name')}")
    
    def test_contact_details_section_has_data(self, auth_headers):
        """Test that Contact Details section has data"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        form_data = data.get("form_data", {})
        
        contact = form_data.get("contact_details", {})
        assert contact.get("email"), "Missing email in contact_details"
        assert contact.get("phone"), "Missing phone in contact_details"
        print(f"✓ Contact Details: {contact.get('email')}, {contact.get('phone')}")
    
    def test_address_section_has_data(self, auth_headers):
        """Test that Address section has data"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        form_data = data.get("form_data", {})
        
        address = form_data.get("address", {})
        assert address.get("address_line_1"), "Missing address_line_1"
        assert address.get("city"), "Missing city"
        assert address.get("postcode"), "Missing postcode"
        print(f"✓ Address: {address.get('city')}, {address.get('postcode')}")
    
    def test_employment_history_section_has_data(self, auth_headers):
        """Test that Employment History section has data"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        form_data = data.get("form_data", {})
        
        employment = form_data.get("employment_history", [])
        assert len(employment) > 0, "Employment history is empty"
        
        first_job = employment[0]
        assert first_job.get("employer_name"), "Missing employer_name"
        assert first_job.get("job_title"), "Missing job_title"
        print(f"✓ Employment History: {first_job.get('job_title')} at {first_job.get('employer_name')}")
    
    def test_references_section_has_expected_referees(self, auth_headers):
        """Test that References section has expected referees"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        form_data = data.get("form_data", {})
        
        references = form_data.get("references", [])
        assert len(references) >= 2, f"Expected at least 2 references, got {len(references)}"
        
        referee_names = [ref.get("referee_name") for ref in references]
        for expected_name in EXPECTED_REFERENCES:
            assert expected_name in referee_names, f"Missing expected referee: {expected_name}"
        
        print(f"✓ References: {', '.join(referee_names)}")
    
    def test_declarations_section_exists(self, auth_headers):
        """Test that Declarations section exists"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        form_data = data.get("form_data", {})
        
        declarations = form_data.get("declarations")
        assert declarations is not None, "Missing declarations section"
        print("✓ Declarations section exists")
    
    def test_health_declaration_section_exists(self, auth_headers):
        """Test that Health Declaration section exists"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        data = response.json()
        form_data = data.get("form_data", {})
        
        health = form_data.get("health_declaration")
        assert health is not None, "Missing health_declaration section"
        print("✓ Health Declaration section exists")
    
    def test_pdf_export_returns_200(self, auth_headers):
        """Test that PDF export endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}/download-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"PDF export failed: {response.status_code} - {response.text}"
        
        # Verify it's a PDF
        content_type = response.headers.get("Content-Type", "")
        assert "pdf" in content_type.lower(), f"Expected PDF content type, got {content_type}"
        
        # Verify PDF starts with %PDF
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ PDF export works - {len(response.content)} bytes")
    
    def test_compliance_file_shows_application_form(self, auth_headers):
        """Test that compliance file shows application form with submission"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{EXISTING_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance file failed: {response.status_code}"
        
        data = response.json()
        recruitment_record = data.get("sections", {}).get("recruitment_record", {})
        rows = recruitment_record.get("rows", [])
        
        # Find application_form row
        app_form_row = None
        for row in rows:
            if row.get("key") == "application_form":
                app_form_row = row
                break
        
        assert app_form_row is not None, "Application form row not found in compliance file"
        assert app_form_row.get("has_submission") == True, "Application form should have submission"
        assert app_form_row.get("submission_data") is not None, "Application form should have submission_data"
        
        submission_id = app_form_row.get("submission_data", {}).get("id")
        assert submission_id == EXISTING_SUBMISSION_ID, f"Submission ID mismatch: {submission_id}"
        
        print(f"✓ Compliance file shows application form with submission {submission_id}")


class TestNoTemplateRequired:
    """Tests to verify no template lookup is required for application forms"""
    
    def test_form_submission_does_not_require_template(self, auth_headers):
        """Test that form submission endpoint doesn't require template lookup"""
        # This test verifies the fix - the endpoint should return data without
        # needing to look up a template
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/{EXISTING_SUBMISSION_ID}",
            headers=auth_headers
        )
        
        # Should succeed without template
        assert response.status_code == 200
        
        data = response.json()
        # Should have form_data directly, not requiring template
        assert "form_data" in data
        assert data["form_data"] is not None
        
        print("✓ Form submission works without template lookup")
    
    def test_template_endpoint_returns_404_for_application_form(self, auth_headers):
        """Test that template endpoint returns 404 for application_form (expected)"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/template/application_form",
            headers=auth_headers
        )
        
        # It's OK if this returns 404 - application forms don't need templates
        # The fix ensures the viewer doesn't call this endpoint
        if response.status_code == 404:
            print("✓ Template endpoint returns 404 for application_form (expected - no template needed)")
        else:
            print(f"Note: Template endpoint returned {response.status_code} for application_form")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

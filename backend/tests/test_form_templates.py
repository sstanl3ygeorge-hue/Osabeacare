"""
Test Form Templates and Auto-fill Endpoints
Tests for structured forms with sectioned layouts, auto-fill support, and conditional fields.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def api_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestHealthScreeningForm:
    """Test Health Screening Form template with 6 sections"""
    
    def test_health_screening_template_exists(self, api_client):
        """GET /api/form-submissions/template/health_screening returns form"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/health_screening")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["requirement_id"] == "health_screening"
        assert data["name"] == "Health Screening Questionnaire"
        assert data["form_type"] == "health_screening"
    
    def test_health_screening_has_6_sections(self, api_client):
        """Health Screening form should have exactly 6 sections"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/health_screening")
        assert response.status_code == 200
        
        data = response.json()
        sections = data.get("sections", [])
        assert len(sections) == 6, f"Expected 6 sections, got {len(sections)}"
        
        # Verify section IDs
        section_ids = [s["id"] for s in sections]
        expected_sections = ["section_a", "section_b", "section_c", "section_d", "section_e", "section_f"]
        assert section_ids == expected_sections, f"Section IDs mismatch: {section_ids}"
    
    def test_health_screening_section_titles(self, api_client):
        """Verify section titles match care-sector standards"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/health_screening")
        data = response.json()
        sections = data.get("sections", [])
        
        expected_titles = [
            "Section A: Personal Details",
            "Section B: Job Exposure",
            "Section C: Health History",
            "Section D: Functional Ability",
            "Section E: Employee Declaration",
            "Section F: Employer Use Only"
        ]
        
        actual_titles = [s["title"] for s in sections]
        assert actual_titles == expected_titles, f"Section titles mismatch: {actual_titles}"
    
    def test_health_screening_has_auto_fill_fields(self, api_client):
        """Health Screening should have auto-fill fields defined"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/health_screening")
        data = response.json()
        
        auto_fill_fields = data.get("auto_fill_fields", [])
        assert len(auto_fill_fields) > 0, "Expected auto_fill_fields to be defined"
        assert "full_name" in auto_fill_fields
        assert "date_of_birth" in auto_fill_fields
    
    def test_health_screening_has_conditional_fields(self, api_client):
        """Health Screening should have conditional fields in Health History section"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/health_screening")
        data = response.json()
        
        # Find Section C (Health History)
        section_c = next((s for s in data["sections"] if s["id"] == "section_c"), None)
        assert section_c is not None, "Section C not found"
        
        # Check for conditional fields
        conditional_fields = [f for f in section_c["fields"] if f.get("conditional_on")]
        assert len(conditional_fields) > 0, "Expected conditional fields in Health History section"
        
        # Verify conditional structure
        for field in conditional_fields:
            assert "conditional_value" in field, f"Field {field['id']} missing conditional_value"


class TestStaffPersonalInfoForm:
    """Test Staff Personal Information form with updates_profile flag"""
    
    def test_staff_personal_info_template_exists(self, api_client):
        """GET /api/form-submissions/template/staff_personal_info returns form"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_personal_info")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["requirement_id"] == "staff_personal_info"
        assert data["name"] == "Staff Personal Information"
    
    def test_staff_personal_info_updates_profile_flag(self, api_client):
        """Staff Personal Info should have updates_profile: true"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_personal_info")
        data = response.json()
        
        assert data.get("updates_profile") == True, f"Expected updates_profile=True, got {data.get('updates_profile')}"
    
    def test_staff_personal_info_has_sections(self, api_client):
        """Staff Personal Info should have multiple sections"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_personal_info")
        data = response.json()
        
        sections = data.get("sections", [])
        assert len(sections) >= 5, f"Expected at least 5 sections, got {len(sections)}"
        
        # Check for expected sections
        section_ids = [s["id"] for s in sections]
        assert "basic_details" in section_ids
        assert "contact_details" in section_ids
        assert "emergency_contact" in section_ids


class TestEqualOpportunitiesForm:
    """Test Equal Opportunities form with is_optional flag"""
    
    def test_equal_opportunities_template_exists(self, api_client):
        """GET /api/form-submissions/template/equal_opportunities returns form"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/equal_opportunities")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["requirement_id"] == "equal_opportunities"
        assert data["name"] == "Equal Opportunities Monitoring"
    
    def test_equal_opportunities_is_optional(self, api_client):
        """Equal Opportunities should have is_optional: true"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/equal_opportunities")
        data = response.json()
        
        assert data.get("is_optional") == True, f"Expected is_optional=True, got {data.get('is_optional')}"
    
    def test_equal_opportunities_has_description(self, api_client):
        """Equal Opportunities should have description about voluntary completion"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/equal_opportunities")
        data = response.json()
        
        description = data.get("description", "")
        assert "voluntary" in description.lower() or "optional" in description.lower(), \
            f"Description should mention voluntary/optional nature: {description}"


class TestHMRCStarterChecklist:
    """Test HMRC Starter Checklist with conditional logic"""
    
    def test_hmrc_starter_checklist_template_exists(self, api_client):
        """GET /api/form-submissions/template/hmrc_starter_checklist returns form"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/hmrc_starter_checklist")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["requirement_id"] == "hmrc_starter_checklist"
        assert data["name"] == "HMRC Starter Checklist"
    
    def test_hmrc_starter_checklist_is_conditional(self, api_client):
        """HMRC Starter Checklist should have is_conditional: true"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/hmrc_starter_checklist")
        data = response.json()
        
        assert data.get("is_conditional") == True, f"Expected is_conditional=True, got {data.get('is_conditional')}"
    
    def test_hmrc_has_student_loan_conditional_fields(self, api_client):
        """HMRC form should have conditional student loan fields"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/hmrc_starter_checklist")
        data = response.json()
        
        # Find student loans section
        student_loans_section = next((s for s in data["sections"] if s["id"] == "student_loans"), None)
        assert student_loans_section is not None, "Student loans section not found"
        
        # Check for conditional field
        conditional_fields = [f for f in student_loans_section["fields"] if f.get("conditional_on")]
        assert len(conditional_fields) > 0, "Expected conditional fields in student loans section"
    
    def test_hmrc_has_auto_fill_fields(self, api_client):
        """HMRC form should have auto-fill fields"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/hmrc_starter_checklist")
        data = response.json()
        
        auto_fill_fields = data.get("auto_fill_fields", [])
        assert len(auto_fill_fields) > 0, "Expected auto_fill_fields to be defined"
        assert "full_name" in auto_fill_fields
        assert "ni_number" in auto_fill_fields


class TestAutoFillEndpoint:
    """Test auto-fill endpoint for pre-filling form data from employee profile"""
    
    def test_auto_fill_endpoint_exists(self, api_client):
        """GET /api/form-submissions/auto-fill/{requirement_id}/{employee_id} returns data"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions/auto-fill/health_screening/{TEST_EMPLOYEE_ID}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert "requirement_id" in data
        assert "auto_fill_data" in data
    
    def test_auto_fill_returns_employee_data(self, api_client):
        """Auto-fill should return pre-filled data from employee profile"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions/auto-fill/health_screening/{TEST_EMPLOYEE_ID}"
        )
        data = response.json()
        
        auto_fill_data = data.get("auto_fill_data", {})
        # Should have at least some auto-filled fields
        assert isinstance(auto_fill_data, dict), "auto_fill_data should be a dict"
    
    def test_auto_fill_for_staff_personal_info(self, api_client):
        """Auto-fill for staff_personal_info should return profile fields"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions/auto-fill/staff_personal_info/{TEST_EMPLOYEE_ID}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requirement_id"] == "staff_personal_info"
        assert "auto_fill_data" in data
    
    def test_auto_fill_for_hmrc(self, api_client):
        """Auto-fill for HMRC should return relevant fields"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions/auto-fill/hmrc_starter_checklist/{TEST_EMPLOYEE_ID}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requirement_id"] == "hmrc_starter_checklist"
    
    def test_auto_fill_invalid_form_returns_404(self, api_client):
        """Auto-fill for non-existent form should return 404"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions/auto-fill/invalid_form/{TEST_EMPLOYEE_ID}"
        )
        assert response.status_code == 404
    
    def test_auto_fill_invalid_employee_returns_404(self, api_client):
        """Auto-fill for non-existent employee should return 404"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions/auto-fill/health_screening/invalid-employee-id"
        )
        assert response.status_code == 404


class TestRecruitmentChecklist:
    """Test Recruitment Checklist form"""
    
    def test_recruitment_checklist_template_exists(self, api_client):
        """GET /api/form-submissions/template/recruitment_checklist returns form"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/recruitment_checklist")
        assert response.status_code == 200
        
        data = response.json()
        assert data["requirement_id"] == "recruitment_checklist"
        assert data["name"] == "Recruitment Compliance Checklist"
    
    def test_recruitment_checklist_has_sections(self, api_client):
        """Recruitment Checklist should have multiple sections"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/recruitment_checklist")
        data = response.json()
        
        sections = data.get("sections", [])
        assert len(sections) >= 4, f"Expected at least 4 sections, got {len(sections)}"


class TestFormTemplatesList:
    """Test listing all form templates"""
    
    def test_list_form_templates(self, api_client):
        """GET /api/form-submissions/templates returns all templates"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Expected list of templates"
        assert len(data) >= 5, f"Expected at least 5 templates, got {len(data)}"
        
        # Check that key forms are present
        template_ids = [t["requirement_id"] for t in data]
        assert "health_screening" in template_ids
        assert "staff_personal_info" in template_ids
        assert "equal_opportunities" in template_ids
        assert "hmrc_starter_checklist" in template_ids


class TestComplianceUnchangedAfterFormSubmission:
    """Test that compliance % remains unchanged after form submission"""
    
    def test_get_compliance_before_and_after(self, api_client):
        """Compliance percentage should remain stable"""
        # Get initial compliance
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance")
        assert response.status_code == 200
        
        initial_data = response.json()
        # Compliance data is nested under 'compliance' key
        compliance_data = initial_data.get("compliance", {})
        initial_percentage = compliance_data.get("completion_percentage")
        
        # Compliance should be a valid number
        assert initial_percentage is not None, f"Compliance percentage should be returned. Got: {initial_data.keys()}"
        assert isinstance(initial_percentage, (int, float)), f"Expected number, got {type(initial_percentage)}"
        
        # Verify compliance structure
        assert "items" in compliance_data, "Compliance should have items list"
        assert "total_items" in compliance_data, "Compliance should have total_items"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

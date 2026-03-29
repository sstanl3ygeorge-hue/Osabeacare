"""
Test Suite for Staff Health Questionnaire Feature
Tests the structured form submission system for the Osabea Staff Health Questionnaire
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')

# Test employee ID (Olakunle Alonge)
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")

@pytest.fixture
def api_client(auth_token):
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestStaffHealthQuestionnaireTemplate:
    """Tests for the Staff Health Questionnaire template endpoint"""
    
    def test_template_endpoint_returns_200(self, api_client):
        """Test that the template endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        assert response.status_code == 200
        print("✅ Template endpoint returns 200")
    
    def test_template_has_correct_structure(self, api_client):
        """Test that the template has the correct structure"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        data = response.json()
        
        # Check required fields
        assert data["requirement_id"] == "staff_health_questionnaire"
        assert data["name"] == "Staff Health Questionnaire"
        assert data["form_type"] == "staff_health_questionnaire"
        print("✅ Template has correct basic structure")
    
    def test_template_has_branding(self, api_client):
        """Test that the template includes Osabea branding"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        data = response.json()
        
        # Check branding
        assert "branding" in data
        assert data["branding"]["show_logo"] == True
        assert data["branding"]["header_color"] == "#2E7D32"  # Green
        assert data["branding"]["company_name"] == "Osabea Healthcare Solutions Ltd"
        print("✅ Template has Osabea branding with green header")
    
    def test_template_has_three_sections(self, api_client):
        """Test that the template has 3 sections: Personal Info, Health Questions, Declaration"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        data = response.json()
        
        sections = data.get("sections", [])
        assert len(sections) == 3
        
        section_ids = [s["id"] for s in sections]
        assert "personal_info" in section_ids
        assert "health_questions" in section_ids
        assert "declaration" in section_ids
        print("✅ Template has 3 sections: Personal Info, Health Questions, Declaration")
    
    def test_personal_info_section_has_9_fields(self, api_client):
        """Test that Personal Information section has 9 fields"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        data = response.json()
        
        personal_info = next((s for s in data["sections"] if s["id"] == "personal_info"), None)
        assert personal_info is not None
        
        fields = personal_info.get("fields", [])
        assert len(fields) == 9
        
        # Check expected field IDs
        field_ids = [f["id"] for f in fields]
        expected_fields = [
            "full_name", "date_of_birth", "contact_number",
            "gp_name", "gp_address", "gp_contact_number",
            "nhs_number", "flu_vaccination_date", "covid_vaccination_dates"
        ]
        for expected in expected_fields:
            assert expected in field_ids, f"Missing field: {expected}"
        print("✅ Personal Information section has 9 fields")
    
    def test_health_questions_section_has_yes_no_dropdowns(self, api_client):
        """Test that Health Questions section has Yes/No dropdowns with conditional fields"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        data = response.json()
        
        health_questions = next((s for s in data["sections"] if s["id"] == "health_questions"), None)
        assert health_questions is not None
        
        fields = health_questions.get("fields", [])
        
        # Count Yes/No select fields
        yes_no_fields = [f for f in fields if f.get("type") == "select" and f.get("options") == ["No", "Yes"]]
        assert len(yes_no_fields) == 8, f"Expected 8 Yes/No questions, got {len(yes_no_fields)}"
        
        # Check conditional fields exist
        conditional_fields = [f for f in fields if f.get("conditional_on")]
        assert len(conditional_fields) >= 8, "Expected at least 8 conditional detail fields"
        print("✅ Health Questions section has 8 Yes/No dropdowns with conditional detail fields")
    
    def test_declaration_section_has_3_fields(self, api_client):
        """Test that Declaration section has 3 fields: checkbox, signature, date"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        data = response.json()
        
        declaration = next((s for s in data["sections"] if s["id"] == "declaration"), None)
        assert declaration is not None
        
        fields = declaration.get("fields", [])
        assert len(fields) == 3
        
        field_ids = [f["id"] for f in fields]
        assert "declaration_confirmed" in field_ids
        assert "signature_name" in field_ids
        assert "signature_date" in field_ids
        print("✅ Declaration section has 3 fields: checkbox, signature, date")


class TestStaffHealthQuestionnaireSubmission:
    """Tests for form submission functionality"""
    
    def test_existing_submission_exists(self, api_client):
        """Test that an existing submission exists for the test employee"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions",
            params={"employee_id": TEST_EMPLOYEE_ID, "requirement_id": "staff_health_questionnaire"}
        )
        assert response.status_code == 200
        
        submissions = response.json()
        assert len(submissions) > 0, "No existing submission found"
        print(f"✅ Found {len(submissions)} existing submission(s)")
    
    def test_submission_has_correct_data_structure(self, api_client):
        """Test that the submission has all required data fields"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions",
            params={"employee_id": TEST_EMPLOYEE_ID, "requirement_id": "staff_health_questionnaire"}
        )
        submission = response.json()[0]
        
        # Check submission metadata
        assert submission["requirement_id"] == "staff_health_questionnaire"
        assert submission["form_type"] == "staff_health_questionnaire"
        assert "data" in submission
        
        # Check data fields
        data = submission["data"]
        required_fields = [
            "full_name", "date_of_birth", "contact_number",
            "significant_illness", "ongoing_gp_treatment", "specialist_waiting_list",
            "hospital_admissions_last_5_years", "work_related_condition",
            "medical_problems_affecting_work", "needs_adjustments", "taking_medication",
            "declaration_confirmed", "signature_name", "signature_date"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        print("✅ Submission has correct data structure with all required fields")
    
    def test_submission_appears_in_compliance_requirements(self, api_client):
        """Test that the submission appears in compliance requirements"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get("requirements", [])
        
        staff_health_req = next((r for r in requirements if r["id"] == "staff_health_questionnaire"), None)
        assert staff_health_req is not None, "staff_health_questionnaire not found in requirements"
        
        # Check that it shows as completed with form submission
        assert staff_health_req["status"] == "completed"
        assert staff_health_req["has_evidence"] == True
        assert staff_health_req.get("form_submission") is not None
        print("✅ Submission appears in compliance requirements with 'completed' status")


class TestStaffHealthQuestionnaireVerification:
    """Tests for form verification functionality"""
    
    def test_submission_can_be_verified(self, api_client):
        """Test that the submission can be verified"""
        # Get the submission ID
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions",
            params={"employee_id": TEST_EMPLOYEE_ID, "requirement_id": "staff_health_questionnaire"}
        )
        submission = response.json()[0]
        submission_id = submission["id"]
        
        # Verify the submission
        verify_response = api_client.post(f"{BASE_URL}/api/form-submissions/{submission_id}/verify")
        assert verify_response.status_code == 200
        
        verified_data = verify_response.json()
        assert verified_data["verified"] == True
        assert verified_data["status"] == "verified"
        print("✅ Submission can be verified successfully")
    
    def test_verified_submission_shows_in_compliance(self, api_client):
        """Test that verified submission shows correct status in compliance"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        data = response.json()
        requirements = data.get("requirements", [])
        
        staff_health_req = next((r for r in requirements if r["id"] == "staff_health_questionnaire"), None)
        assert staff_health_req is not None
        
        # Check verification status
        form_submission = staff_health_req.get("form_submission", {})
        assert form_submission.get("verified") == True
        print("✅ Verified submission shows correct status in compliance requirements")


class TestStaffHealthQuestionnaireAutoFill:
    """Tests for auto-fill functionality"""
    
    def test_auto_fill_endpoint_returns_data(self, api_client):
        """Test that auto-fill endpoint returns employee data"""
        response = api_client.get(
            f"{BASE_URL}/api/form-submissions/auto-fill/staff_health_questionnaire/{TEST_EMPLOYEE_ID}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "auto_fill_data" in data
        
        auto_fill = data["auto_fill_data"]
        # Check that employee name is auto-filled
        assert "full_name" in auto_fill or "employee_name" in auto_fill
        print("✅ Auto-fill endpoint returns employee data")


class TestFrontendIntegration:
    """Tests for frontend integration requirements"""
    
    def test_staff_health_questionnaire_in_form_based_requirements(self, api_client):
        """Test that staff_health_questionnaire is recognized as a form-based requirement"""
        # This is verified by the template endpoint returning successfully
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_health_questionnaire")
        assert response.status_code == 200
        print("✅ staff_health_questionnaire is recognized as a form-based requirement")
    
    def test_compliance_requirements_shows_form_submission_data(self, api_client):
        """Test that compliance requirements endpoint includes form submission data"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        data = response.json()
        requirements = data.get("requirements", [])
        
        staff_health_req = next((r for r in requirements if r["id"] == "staff_health_questionnaire"), None)
        assert staff_health_req is not None
        
        # Check form_submission field exists with data
        form_submission = staff_health_req.get("form_submission")
        assert form_submission is not None
        assert "data" in form_submission
        assert "submitted_at" in form_submission
        print("✅ Compliance requirements includes form submission data for viewing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

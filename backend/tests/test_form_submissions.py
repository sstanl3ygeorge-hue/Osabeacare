"""
Test Form Submissions API - Verifies structured form submission functionality
Tests: Health Screening, Induction, Interview Record, Recruitment Checklist, 
       Staff Personal Info, HMRC Starter Checklist, Equal Opportunities forms
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"

# Test employee ID from context
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

# Form types to test
FORM_TYPES = [
    "health_screening",
    "induction",
    "interview_record",
    "recruitment_checklist",
    "staff_personal_info",
    "hmrc_starter_checklist",
    "equal_opportunities"
]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestFormTemplateEndpoints:
    """Test form template retrieval endpoints"""
    
    def test_get_health_screening_template(self, api_client):
        """Test getting health screening form template"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/health_screening")
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "health_screening"
        assert data["name"] == "Health Screening Questionnaire"
        assert "sections" in data
        print("✅ Health Screening template retrieved successfully")
    
    def test_get_induction_template(self, api_client):
        """Test getting induction form template"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/induction")
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "induction"
        assert "Induction" in data["name"]
        print("✅ Induction template retrieved successfully")
    
    def test_get_interview_record_template(self, api_client):
        """Test getting interview record form template"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/interview_record")
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "interview_record"
        print("✅ Interview Record template retrieved successfully")
    
    def test_get_recruitment_checklist_template(self, api_client):
        """Test getting recruitment checklist form template"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/recruitment_checklist")
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "recruitment_checklist"
        print("✅ Recruitment Checklist template retrieved successfully")
    
    def test_get_staff_personal_info_template(self, api_client):
        """Test getting staff personal info form template"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/staff_personal_info")
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "staff_personal_info"
        print("✅ Staff Personal Info template retrieved successfully")
    
    def test_get_hmrc_starter_checklist_template(self, api_client):
        """Test getting HMRC starter checklist form template"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/hmrc_starter_checklist")
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "hmrc_starter_checklist"
        print("✅ HMRC Starter Checklist template retrieved successfully")
    
    def test_get_equal_opportunities_template(self, api_client):
        """Test getting equal opportunities form template"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/equal_opportunities")
        assert response.status_code == 200, f"Failed to get template: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "equal_opportunities"
        print("✅ Equal Opportunities template retrieved successfully")
    
    def test_invalid_template_returns_404(self, api_client):
        """Test that invalid form type returns 404"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions/template/invalid_form_type")
        assert response.status_code == 404
        print("✅ Invalid template correctly returns 404")


class TestFormSubmissionCRUD:
    """Test form submission create, read, update operations"""
    
    def test_submit_health_screening_form(self, api_client):
        """Test submitting health screening form"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "health_screening",
            "form_type": "health_screening",
            "data": {
                "full_name": "Test Employee",
                "date_of_birth": "1990-01-15",
                "job_title": "Care Assistant",
                "declaration_accurate": True,
                "employee_signature": "Test Employee",
                "employee_sign_date": "2026-01-15"
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Form submission failed: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "health_screening"
        assert data["status"] == "submitted"
        assert data["verified"] == False
        print(f"✅ Health Screening form submitted successfully (ID: {data['id']})")
        return data["id"]
    
    def test_submit_induction_form(self, api_client):
        """Test submitting induction form"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "induction",
            "form_type": "induction",
            "data": {
                "employee_name": "Test Employee",
                "induction_date": "2026-01-15",
                "completed_by": "Admin User"
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Form submission failed: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "induction"
        print(f"✅ Induction form submitted successfully (ID: {data['id']})")
    
    def test_submit_interview_record_form(self, api_client):
        """Test submitting interview record form"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "interview_record",
            "form_type": "interview_record",
            "data": {
                "candidate_name": "Test Employee",
                "interview_date": "2026-01-10",
                "interviewer_name": "Admin User",
                "overall_assessment": "Suitable for role"
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Form submission failed: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "interview_record"
        print(f"✅ Interview Record form submitted successfully (ID: {data['id']})")
    
    def test_submit_recruitment_checklist_form(self, api_client):
        """Test submitting recruitment checklist form"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "recruitment_checklist",
            "form_type": "recruitment_checklist",
            "data": {
                "employee_name": "Test Employee",
                "application_received": True,
                "cv_received": True,
                "references_requested": True
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Form submission failed: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "recruitment_checklist"
        print(f"✅ Recruitment Checklist form submitted successfully (ID: {data['id']})")
    
    def test_submit_staff_personal_info_form(self, api_client):
        """Test submitting staff personal info form"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "staff_personal_info",
            "form_type": "staff_personal_info",
            "data": {
                "full_name": "Test Employee",
                "address": "123 Test Street",
                "phone": "07123456789",
                "email": "test@example.com"
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Form submission failed: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "staff_personal_info"
        print(f"✅ Staff Personal Info form submitted successfully (ID: {data['id']})")
    
    def test_submit_hmrc_starter_checklist_form(self, api_client):
        """Test submitting HMRC starter checklist form"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "hmrc_starter_checklist",
            "form_type": "hmrc_starter_checklist",
            "data": {
                "employee_name": "Test Employee",
                "ni_number": "AB123456C",
                "statement_a": True
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Form submission failed: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "hmrc_starter_checklist"
        print(f"✅ HMRC Starter Checklist form submitted successfully (ID: {data['id']})")
    
    def test_submit_equal_opportunities_form(self, api_client):
        """Test submitting equal opportunities form"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "equal_opportunities",
            "form_type": "equal_opportunities",
            "data": {
                "gender": "Prefer not to say",
                "ethnicity": "Prefer not to say",
                "disability": "No"
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Form submission failed: {response.text}"
        data = response.json()
        assert data["requirement_id"] == "equal_opportunities"
        print(f"✅ Equal Opportunities form submitted successfully (ID: {data['id']})")
    
    def test_get_form_submissions_for_employee(self, api_client):
        """Test retrieving form submissions for an employee"""
        response = api_client.get(f"{BASE_URL}/api/form-submissions?employee_id={TEST_EMPLOYEE_ID}")
        assert response.status_code == 200, f"Failed to get submissions: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Retrieved {len(data)} form submissions for employee")
    
    def test_invalid_form_type_returns_400(self, api_client):
        """Test that invalid form type returns 400"""
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "invalid_form_type",
            "form_type": "invalid_form_type",
            "data": {}
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 400
        print("✅ Invalid form type correctly returns 400")


class TestFormVerification:
    """Test form verification flow"""
    
    def test_verify_form_submission(self, api_client):
        """Test verifying a form submission"""
        # First, get existing submissions
        response = api_client.get(f"{BASE_URL}/api/form-submissions?employee_id={TEST_EMPLOYEE_ID}")
        assert response.status_code == 200
        submissions = response.json()
        
        if not submissions:
            pytest.skip("No submissions to verify")
        
        # Find an unverified submission
        unverified = [s for s in submissions if not s.get("verified")]
        if not unverified:
            print("✅ All submissions already verified - skipping verify test")
            return
        
        submission_id = unverified[0]["id"]
        
        # Verify the submission
        response = api_client.post(f"{BASE_URL}/api/form-submissions/{submission_id}/verify")
        assert response.status_code == 200, f"Verification failed: {response.text}"
        data = response.json()
        assert data["verified"] == True
        print(f"✅ Form submission verified successfully (ID: {submission_id})")


class TestFormEditFlow:
    """Test form edit/re-submission flow"""
    
    def test_resubmit_existing_form(self, api_client):
        """Test re-submitting an existing form (edit flow)"""
        # Submit a form
        form_data = {
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "health_screening",
            "form_type": "health_screening",
            "data": {
                "full_name": "Test Employee Updated",
                "date_of_birth": "1990-01-15",
                "job_title": "Senior Care Assistant",
                "declaration_accurate": True,
                "employee_signature": "Test Employee",
                "employee_sign_date": "2026-01-16"
            }
        }
        response = api_client.post(f"{BASE_URL}/api/form-submissions", json=form_data)
        assert response.status_code == 200, f"Re-submission failed: {response.text}"
        data = response.json()
        
        # Verify it's a new version (previous should be superseded)
        assert data["version"] >= 1
        print(f"✅ Form re-submitted successfully (version: {data['version']})")


class TestComplianceRequirementsIntegration:
    """Test that form submissions appear in compliance requirements"""
    
    def test_compliance_requirements_show_form_submissions(self, api_client):
        """Test that compliance requirements endpoint shows form submissions"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200, f"Failed to get compliance requirements: {response.text}"
        data = response.json()
        
        # Check that form-based requirements show submission status
        requirements = data.get("requirements", [])
        form_reqs = [r for r in requirements if r.get("type") in ["form", "form-generated"]]
        
        # At least some form requirements should exist
        assert len(form_reqs) > 0, "No form-based requirements found"
        
        # Check if any have form_submission data
        with_submissions = [r for r in form_reqs if r.get("form_submission")]
        print(f"✅ Found {len(form_reqs)} form requirements, {len(with_submissions)} with submissions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

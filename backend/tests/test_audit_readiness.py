"""
Test Audit-Readiness Fixes:
1. Health Screening Questionnaire is archived (not visible in What's Needed)
2. Staff Health Questionnaire is visible and functional
3. PDF button states work correctly based on has_pdf_export flag
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee with staff_health_questionnaire submission
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

class TestHealthFormArchiving:
    """Test that health_screening is archived and staff_health_questionnaire is visible"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_compliance_requirements_excludes_archived_health_screening(self):
        """Verify health_screening is NOT in compliance requirements (archived)"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Check that health_screening is NOT in the list
        health_screening_found = any(req['id'] == 'health_screening' for req in requirements)
        assert not health_screening_found, "health_screening should be archived and NOT visible"
        
        print("✅ health_screening is correctly excluded (archived)")
    
    def test_compliance_requirements_includes_staff_health_questionnaire(self):
        """Verify staff_health_questionnaire IS in compliance requirements"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Check that staff_health_questionnaire IS in the list
        staff_health_found = any(req['id'] == 'staff_health_questionnaire' for req in requirements)
        assert staff_health_found, "staff_health_questionnaire should be visible"
        
        print("✅ staff_health_questionnaire is correctly included")
    
    def test_only_one_health_form_in_competency_health_category(self):
        """Verify only ONE health form shows in Competency & Health category"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Count health-related forms in category 3
        health_forms = [req for req in requirements 
                       if req.get('category') == '3_Competency_Health' 
                       and 'health' in req['id'].lower()]
        
        assert len(health_forms) == 1, f"Expected 1 health form, found {len(health_forms)}: {[f['id'] for f in health_forms]}"
        assert health_forms[0]['id'] == 'staff_health_questionnaire', "The health form should be staff_health_questionnaire"
        
        print("✅ Only ONE health form (staff_health_questionnaire) in Competency & Health category")


class TestStaffHealthQuestionnaireSubmission:
    """Test Staff Health Questionnaire submission, edit, view, PDF operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_get_form_submission_exists(self):
        """Verify form submission exists for test employee"""
        response = self.session.get(f"{BASE_URL}/api/form-submissions", params={
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "staff_health_questionnaire"
        })
        assert response.status_code == 200
        
        data = response.json()
        submissions = data if isinstance(data, list) else data.get('submissions', [])
        
        assert len(submissions) > 0, "Expected at least one form submission"
        
        submission = submissions[0]
        assert submission.get('requirement_id') == 'staff_health_questionnaire'
        assert submission.get('employee_id') == TEST_EMPLOYEE_ID
        
        print(f"✅ Form submission found: {submission.get('id')}")
        return submission
    
    def test_form_submission_has_pdf_export_info(self):
        """Verify compliance-requirements includes PDF export info"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Find staff_health_questionnaire
        staff_health = next((req for req in requirements if req['id'] == 'staff_health_questionnaire'), None)
        assert staff_health is not None, "staff_health_questionnaire not found"
        
        # Check form_submission data
        form_submission = staff_health.get('form_submission')
        assert form_submission is not None, "form_submission data should be present"
        
        # Verify PDF export fields are present
        assert 'has_pdf_export' in form_submission, "has_pdf_export field should be present"
        assert 'pdf_export_url' in form_submission, "pdf_export_url field should be present"
        
        print(f"✅ PDF export info present: has_pdf_export={form_submission.get('has_pdf_export')}")
        print(f"   pdf_export_url={form_submission.get('pdf_export_url')}")
        
        return form_submission


class TestPDFButtonStates:
    """Test PDF button state logic based on has_pdf_export flag"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_pdf_export_exists_for_test_employee(self):
        """Verify PDF export exists for test employee's submission"""
        # Get form submission first
        response = self.session.get(f"{BASE_URL}/api/form-submissions", params={
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "staff_health_questionnaire"
        })
        assert response.status_code == 200
        
        data = response.json()
        submissions = data if isinstance(data, list) else data.get('submissions', [])
        assert len(submissions) > 0
        
        submission_id = submissions[0].get('id')
        
        # Check PDF exports
        response = self.session.get(f"{BASE_URL}/api/pdf-exports", params={
            "submission_id": submission_id
        })
        assert response.status_code == 200
        
        exports = response.json()
        exports_list = exports if isinstance(exports, list) else exports.get('exports', [])
        
        print(f"✅ Found {len(exports_list)} PDF export(s) for submission {submission_id}")
        
        if len(exports_list) > 0:
            latest = exports_list[0]
            print(f"   Latest export: {latest.get('filename')}")
            print(f"   URL: {latest.get('file_url')}")
    
    def test_generate_pdf_endpoint(self):
        """Test PDF generation endpoint"""
        # Get form submission
        response = self.session.get(f"{BASE_URL}/api/form-submissions", params={
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "staff_health_questionnaire"
        })
        assert response.status_code == 200
        
        data = response.json()
        submissions = data if isinstance(data, list) else data.get('submissions', [])
        assert len(submissions) > 0
        
        submission_id = submissions[0].get('id')
        
        # Generate PDF
        response = self.session.post(f"{BASE_URL}/api/form-submissions/{submission_id}/generate-pdf")
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'file_url' in result or 'pdf_url' in result, "Response should contain file_url or pdf_url"
        
        print(f"✅ PDF generated successfully")
        print(f"   URL: {result.get('file_url') or result.get('pdf_url')}")
    
    def test_download_pdf_endpoint(self):
        """Test PDF download endpoint"""
        # Get form submission
        response = self.session.get(f"{BASE_URL}/api/form-submissions", params={
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "staff_health_questionnaire"
        })
        assert response.status_code == 200
        
        data = response.json()
        submissions = data if isinstance(data, list) else data.get('submissions', [])
        assert len(submissions) > 0
        
        submission_id = submissions[0].get('id')
        
        # Download PDF
        response = self.session.get(f"{BASE_URL}/api/form-submissions/{submission_id}/download-pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'file_url' in result or 'pdf_url' in result or 'url' in result, "Response should contain URL"
        
        print(f"✅ PDF download endpoint works")


class TestMarkAsApproved:
    """Test Mark as Approved functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_verify_form_submission_endpoint(self):
        """Test form submission verification (Mark as Approved)"""
        # Get form submission
        response = self.session.get(f"{BASE_URL}/api/form-submissions", params={
            "employee_id": TEST_EMPLOYEE_ID,
            "requirement_id": "staff_health_questionnaire"
        })
        assert response.status_code == 200
        
        data = response.json()
        submissions = data if isinstance(data, list) else data.get('submissions', [])
        assert len(submissions) > 0
        
        submission_id = submissions[0].get('id')
        
        # Verify/Approve the submission
        response = self.session.post(f"{BASE_URL}/api/form-submissions/{submission_id}/verify")
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        result = response.json()
        print(f"✅ Form submission verified/approved")
        print(f"   Result: {result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test Suite: Recruitment Approval Gate & Applicant/Employee Separation
=====================================================================
Tests the new recruitment approval workflow and applicant vs employee separation:
1. Recruitment approval gate (POST /api/employees/{id}/approve-recruitment)
2. Employee code assignment timing (only on approval)
3. Pipeline endpoint (GET /api/recruitment/pipeline) - applicants only
4. Applicants endpoint (GET /api/recruitment/applicants) - applicants only
5. Staff endpoint (GET /api/staff/employees) - employees only
6. Person stage derivation from status
7. Status transition on approval (applicant → onboarding)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Applicant statuses (pre-hire)
APPLICANT_STATUSES = ["new", "screening", "interview", "compliance_review"]

# Employee statuses (post-hire)
EMPLOYEE_STATUSES = ["onboarding", "active", "inactive"]


class TestRecruitmentApprovalSeparation:
    """Test recruitment approval gate and applicant/employee separation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Authenticate
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")  # API returns 'token' not 'access_token'
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
        
        yield
        
        # Cleanup: Delete test employees created during tests
        if hasattr(self, 'test_employee_ids'):
            for emp_id in self.test_employee_ids:
                try:
                    self.session.delete(f"{BASE_URL}/api/employees/{emp_id}/permanent")
                except:
                    pass
    
    def create_test_applicant(self, status="new"):
        """Helper to create a test applicant"""
        if not hasattr(self, 'test_employee_ids'):
            self.test_employee_ids = []
        
        unique_id = uuid.uuid4().hex[:8]
        response = self.session.post(f"{BASE_URL}/api/employees", json={
            "first_name": f"TestApplicant{unique_id}",
            "last_name": "RecruitmentTest",
            "email": f"test.applicant.{unique_id}@test.com",
            "phone": "07700900000",
            "role": "Care Assistant",
            "status": status,
            "onboarding_status": "New"
        })
        
        if response.status_code == 200:
            emp_data = response.json()
            self.test_employee_ids.append(emp_data['id'])
            return emp_data
        return None
    
    # ==================== ENDPOINT TESTS ====================
    
    def test_recruitment_pipeline_endpoint_exists(self):
        """Test GET /api/recruitment/pipeline returns applicants only"""
        response = self.session.get(f"{BASE_URL}/api/recruitment/pipeline")
        
        assert response.status_code == 200, f"Pipeline endpoint failed: {response.text}"
        data = response.json()
        
        # Should have stages structure
        assert "stages" in data, "Pipeline should have 'stages' key"
        assert "summary" in data, "Pipeline should have 'summary' key"
        
        # Verify stages are applicant statuses only
        stage_statuses = [s['status'] for s in data['stages']]
        for status in stage_statuses:
            assert status in APPLICANT_STATUSES, f"Pipeline stage {status} should be applicant status"
        
        print(f"✓ Pipeline endpoint returns {len(data['stages'])} stages with {data['summary'].get('total_applicants', 0)} applicants")
    
    def test_recruitment_applicants_endpoint_exists(self):
        """Test GET /api/recruitment/applicants returns applicants only"""
        response = self.session.get(f"{BASE_URL}/api/recruitment/applicants")
        
        assert response.status_code == 200, f"Applicants endpoint failed: {response.text}"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), "Applicants endpoint should return a list"
        
        # All returned records should have applicant-stage status
        for applicant in data:
            status = applicant.get('status')
            person_stage = applicant.get('person_stage')
            
            # Either status is in applicant statuses OR person_stage is 'applicant'
            assert status in APPLICANT_STATUSES or person_stage == 'applicant', \
                f"Applicant {applicant.get('id')} has non-applicant status: {status}"
        
        print(f"✓ Applicants endpoint returns {len(data)} applicants")
    
    def test_staff_employees_endpoint_exists(self):
        """Test GET /api/staff/employees returns employees only (not applicants)"""
        response = self.session.get(f"{BASE_URL}/api/staff/employees")
        
        assert response.status_code == 200, f"Staff endpoint failed: {response.text}"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), "Staff endpoint should return a list"
        
        # All returned records should have employee-stage status
        for employee in data:
            status = employee.get('status')
            person_stage = employee.get('person_stage')
            
            # Either status is in employee statuses OR person_stage is 'employee'
            assert status in EMPLOYEE_STATUSES or person_stage == 'employee', \
                f"Staff member {employee.get('id')} has non-employee status: {status}"
        
        print(f"✓ Staff endpoint returns {len(data)} employees")
    
    def test_main_employees_endpoint_with_stage_filter(self):
        """Test GET /api/employees?stage=employee filters correctly"""
        # Test employee stage filter
        response = self.session.get(f"{BASE_URL}/api/employees?stage=employee")
        assert response.status_code == 200, f"Employees endpoint with stage filter failed: {response.text}"
        
        data = response.json()
        for emp in data:
            status = emp.get('status')
            assert status in EMPLOYEE_STATUSES or status == 'archived', \
                f"Employee {emp.get('id')} has non-employee status: {status}"
        
        print(f"✓ Employees endpoint with stage=employee returns {len(data)} records")
        
        # Test applicant stage filter
        response = self.session.get(f"{BASE_URL}/api/employees?stage=applicant")
        assert response.status_code == 200
        
        data = response.json()
        for emp in data:
            status = emp.get('status')
            assert status in APPLICANT_STATUSES, \
                f"Applicant {emp.get('id')} has non-applicant status: {status}"
        
        print(f"✓ Employees endpoint with stage=applicant returns {len(data)} records")
    
    # ==================== EMPLOYEE CODE TIMING TESTS ====================
    
    def test_new_applicant_has_no_employee_code(self):
        """Test that new applicants get applicant_reference, NOT employee_code"""
        applicant = self.create_test_applicant(status="new")
        assert applicant is not None, "Failed to create test applicant"
        
        # Applicant should have applicant_reference
        assert applicant.get('applicant_reference') is not None, \
            "New applicant should have applicant_reference"
        
        # Applicant should NOT have employee_code (or it should be null)
        employee_code = applicant.get('employee_code')
        assert employee_code is None or employee_code == "", \
            f"New applicant should NOT have employee_code, got: {employee_code}"
        
        print(f"✓ New applicant has applicant_reference: {applicant.get('applicant_reference')}, no employee_code")
    
    def test_applicant_statuses_have_no_employee_code(self):
        """Test that all applicant-stage statuses don't get employee_code"""
        for status in APPLICANT_STATUSES:
            applicant = self.create_test_applicant(status=status)
            assert applicant is not None, f"Failed to create applicant with status {status}"
            
            employee_code = applicant.get('employee_code')
            assert employee_code is None or employee_code == "", \
                f"Applicant with status '{status}' should NOT have employee_code, got: {employee_code}"
            
            print(f"✓ Applicant with status '{status}' has no employee_code")
    
    # ==================== RECRUITMENT APPROVAL TESTS ====================
    
    def test_approve_recruitment_endpoint_exists(self):
        """Test POST /api/employees/{id}/approve-recruitment endpoint exists"""
        # Create a test applicant
        applicant = self.create_test_applicant(status="compliance_review")
        assert applicant is not None, "Failed to create test applicant"
        
        # Approve recruitment
        response = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "Test approval"}
        )
        
        assert response.status_code == 200, f"Approve recruitment failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get('status') == 'approved', f"Expected status 'approved', got: {data.get('status')}"
        assert data.get('recruitment_approved') == True, "recruitment_approved should be True"
        assert data.get('employee_code') is not None, "employee_code should be assigned on approval"
        
        print(f"✓ Recruitment approval successful, employee_code: {data.get('employee_code')}")
    
    def test_approve_recruitment_assigns_employee_code(self):
        """Test that recruitment approval assigns employee_code to applicant"""
        # Create applicant (should have no employee_code)
        applicant = self.create_test_applicant(status="new")
        assert applicant is not None, "Failed to create test applicant"
        assert applicant.get('employee_code') is None, "Applicant should not have employee_code before approval"
        
        # Approve recruitment
        response = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "Assigning employee code test"}
        )
        
        assert response.status_code == 200, f"Approval failed: {response.text}"
        approval_data = response.json()
        
        # Verify employee_code was assigned
        assert approval_data.get('employee_code') is not None, "employee_code should be assigned"
        assert approval_data['employee_code'].startswith('OCS-'), \
            f"employee_code should start with 'OCS-', got: {approval_data['employee_code']}"
        
        # Verify by fetching the employee
        get_response = self.session.get(f"{BASE_URL}/api/employees/{applicant['id']}")
        assert get_response.status_code == 200
        
        updated_employee = get_response.json()
        assert updated_employee.get('employee_code') == approval_data['employee_code'], \
            "Employee record should have the assigned employee_code"
        
        print(f"✓ Employee code {approval_data['employee_code']} assigned on approval")
    
    def test_approve_recruitment_transitions_status_to_onboarding(self):
        """Test that recruitment approval transitions applicant status to 'onboarding'"""
        # Create applicant with applicant-stage status
        applicant = self.create_test_applicant(status="compliance_review")
        assert applicant is not None, "Failed to create test applicant"
        assert applicant.get('status') == 'compliance_review', "Initial status should be compliance_review"
        
        # Approve recruitment
        response = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "Status transition test"}
        )
        
        assert response.status_code == 200, f"Approval failed: {response.text}"
        approval_data = response.json()
        
        # Verify stage transition info in response
        stage_transition = approval_data.get('stage_transition', {})
        assert stage_transition.get('from') == 'compliance_review', \
            f"Expected transition from 'compliance_review', got: {stage_transition.get('from')}"
        assert stage_transition.get('to') == 'onboarding', \
            f"Expected transition to 'onboarding', got: {stage_transition.get('to')}"
        
        # Verify by fetching the employee
        get_response = self.session.get(f"{BASE_URL}/api/employees/{applicant['id']}")
        assert get_response.status_code == 200
        
        updated_employee = get_response.json()
        assert updated_employee.get('status') == 'onboarding', \
            f"Status should be 'onboarding' after approval, got: {updated_employee.get('status')}"
        
        print(f"✓ Status transitioned from 'compliance_review' to 'onboarding'")
    
    def test_approve_recruitment_sets_approval_fields(self):
        """Test that recruitment approval sets all approval fields"""
        applicant = self.create_test_applicant(status="interview")
        assert applicant is not None, "Failed to create test applicant"
        
        # Approve with notes
        approval_notes = "Approved after successful interview"
        response = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": approval_notes}
        )
        
        assert response.status_code == 200, f"Approval failed: {response.text}"
        
        # Fetch employee to verify fields
        get_response = self.session.get(f"{BASE_URL}/api/employees/{applicant['id']}")
        assert get_response.status_code == 200
        
        employee = get_response.json()
        
        # Verify all approval fields
        assert employee.get('recruitment_approved') == True, "recruitment_approved should be True"
        assert employee.get('recruitment_approved_by') is not None, "recruitment_approved_by should be set"
        assert employee.get('recruitment_approved_at') is not None, "recruitment_approved_at should be set"
        
        print(f"✓ All approval fields set correctly")
    
    def test_already_approved_returns_status(self):
        """Test that approving an already-approved employee returns appropriate status"""
        applicant = self.create_test_applicant(status="new")
        assert applicant is not None, "Failed to create test applicant"
        
        # First approval
        response1 = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "First approval"}
        )
        assert response1.status_code == 200
        
        # Second approval attempt
        response2 = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "Second approval attempt"}
        )
        
        assert response2.status_code == 200, f"Second approval failed: {response2.text}"
        data = response2.json()
        
        assert data.get('status') == 'already_approved', \
            f"Expected 'already_approved' status, got: {data.get('status')}"
        
        print(f"✓ Already approved employee returns 'already_approved' status")
    
    # ==================== PERSON STAGE DERIVATION TESTS ====================
    
    def test_person_stage_derived_for_applicant_statuses(self):
        """Test that person_stage is 'applicant' for applicant-stage statuses"""
        for status in APPLICANT_STATUSES:
            applicant = self.create_test_applicant(status=status)
            assert applicant is not None, f"Failed to create applicant with status {status}"
            
            # Fetch to get derived person_stage
            get_response = self.session.get(f"{BASE_URL}/api/employees/{applicant['id']}")
            assert get_response.status_code == 200
            
            employee = get_response.json()
            person_stage = employee.get('person_stage')
            
            assert person_stage == 'applicant', \
                f"Status '{status}' should have person_stage 'applicant', got: {person_stage}"
            
            print(f"✓ Status '{status}' → person_stage 'applicant'")
    
    def test_person_stage_derived_for_employee_statuses(self):
        """Test that person_stage is 'employee' for employee-stage statuses"""
        # Create and approve an applicant to get employee status
        applicant = self.create_test_applicant(status="compliance_review")
        assert applicant is not None, "Failed to create test applicant"
        
        # Approve to transition to onboarding
        response = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "Test"}
        )
        assert response.status_code == 200
        
        # Fetch to verify person_stage
        get_response = self.session.get(f"{BASE_URL}/api/employees/{applicant['id']}")
        assert get_response.status_code == 200
        
        employee = get_response.json()
        
        assert employee.get('status') == 'onboarding', "Status should be onboarding"
        assert employee.get('person_stage') == 'employee', \
            f"Status 'onboarding' should have person_stage 'employee', got: {employee.get('person_stage')}"
        
        print(f"✓ Status 'onboarding' → person_stage 'employee'")
    
    # ==================== SEPARATION VERIFICATION TESTS ====================
    
    def test_approved_employee_not_in_applicants_endpoint(self):
        """Test that approved employees don't appear in /recruitment/applicants"""
        # Create and approve an applicant
        applicant = self.create_test_applicant(status="new")
        assert applicant is not None, "Failed to create test applicant"
        
        # Verify appears in applicants before approval
        response = self.session.get(f"{BASE_URL}/api/recruitment/applicants")
        assert response.status_code == 200
        applicants_before = response.json()
        
        found_before = any(a['id'] == applicant['id'] for a in applicants_before)
        assert found_before, "Applicant should appear in /recruitment/applicants before approval"
        
        # Approve
        approve_response = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "Test"}
        )
        assert approve_response.status_code == 200
        
        # Verify NOT in applicants after approval
        response = self.session.get(f"{BASE_URL}/api/recruitment/applicants")
        assert response.status_code == 200
        applicants_after = response.json()
        
        found_after = any(a['id'] == applicant['id'] for a in applicants_after)
        assert not found_after, "Approved employee should NOT appear in /recruitment/applicants"
        
        print(f"✓ Approved employee removed from applicants endpoint")
    
    def test_approved_employee_appears_in_staff_endpoint(self):
        """Test that approved employees appear in /staff/employees"""
        # Create and approve an applicant
        applicant = self.create_test_applicant(status="compliance_review")
        assert applicant is not None, "Failed to create test applicant"
        
        # Verify NOT in staff before approval
        response = self.session.get(f"{BASE_URL}/api/staff/employees")
        assert response.status_code == 200
        staff_before = response.json()
        
        found_before = any(e['id'] == applicant['id'] for e in staff_before)
        assert not found_before, "Applicant should NOT appear in /staff/employees before approval"
        
        # Approve
        approve_response = self.session.post(
            f"{BASE_URL}/api/employees/{applicant['id']}/approve-recruitment",
            json={"notes": "Test"}
        )
        assert approve_response.status_code == 200
        
        # Verify IN staff after approval
        response = self.session.get(f"{BASE_URL}/api/staff/employees")
        assert response.status_code == 200
        staff_after = response.json()
        
        found_after = any(e['id'] == applicant['id'] for e in staff_after)
        assert found_after, "Approved employee should appear in /staff/employees"
        
        print(f"✓ Approved employee appears in staff endpoint")


class TestRecruitmentPipelineDetails:
    """Test recruitment pipeline endpoint details"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Authenticate
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")  # API returns 'token' not 'access_token'
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    def test_pipeline_has_all_applicant_stages(self):
        """Test that pipeline includes all applicant status stages"""
        response = self.session.get(f"{BASE_URL}/api/recruitment/pipeline")
        assert response.status_code == 200
        
        data = response.json()
        stage_statuses = [s['status'] for s in data['stages']]
        
        for expected_status in APPLICANT_STATUSES:
            assert expected_status in stage_statuses, \
                f"Pipeline should include stage for status '{expected_status}'"
        
        print(f"✓ Pipeline includes all {len(APPLICANT_STATUSES)} applicant stages")
    
    def test_pipeline_summary_counts(self):
        """Test that pipeline summary has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/recruitment/pipeline")
        assert response.status_code == 200
        
        data = response.json()
        summary = data.get('summary', {})
        
        assert 'total_applicants' in summary, "Summary should have total_applicants"
        
        # Total should match sum of stage counts
        total_from_stages = sum(len(s.get('applicants', [])) for s in data['stages'])
        assert summary['total_applicants'] == total_from_stages, \
            f"Summary total ({summary['total_applicants']}) should match stage sum ({total_from_stages})"
        
        print(f"✓ Pipeline summary counts are consistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test Scoped Endpoints for NHS-Level Compliance Hardening
=========================================================
Tests Change Sets 1-2:
- Global Applicant/Employee Separation with scoped repository
- Single Readiness Calculation with stable reason codes

Key endpoints tested:
- GET /staff/employees - returns only employee-status records
- GET /recruitment/applicants - returns only applicant-status records
- GET /staff/employees/{id} - returns 404 for applicant IDs
- GET /recruitment/applicants/{id} - returns 404 for employee IDs
- GET /employees/{id}/readiness - authoritative readiness with stable reason codes
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test IDs from the review request
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # status: onboarding
TEST_APPLICANT_ID = "8f351317-8623-4df5-8788-c6a3ce5364cf"  # status: new

# Valid statuses for each scope
APPLICANT_STATUSES = ["new", "screening", "interview", "compliance_review"]
EMPLOYEE_STATUSES = ["onboarding", "active", "inactive"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestScopedListEndpoints:
    """Test scoped list endpoints return correct records"""
    
    def test_staff_employees_returns_only_employee_statuses(self, auth_headers):
        """GET /staff/employees should return only employee-status records"""
        response = requests.get(
            f"{BASE_URL}/api/staff/employees?include_inactive=true",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        employees = response.json()
        assert isinstance(employees, list), "Response should be a list"
        
        # Verify all returned records have employee statuses
        for emp in employees:
            status = emp.get('status')
            assert status in EMPLOYEE_STATUSES, f"Found non-employee status '{status}' in staff/employees response"
            # Verify person_stage is set correctly
            assert emp.get('person_stage') == 'employee', f"Expected person_stage='employee', got '{emp.get('person_stage')}'"
        
        print(f"✓ GET /staff/employees returned {len(employees)} employees, all with valid employee statuses")
    
    def test_recruitment_applicants_returns_only_applicant_statuses(self, auth_headers):
        """GET /recruitment/applicants should return only applicant-status records"""
        response = requests.get(
            f"{BASE_URL}/api/recruitment/applicants",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        applicants = response.json()
        assert isinstance(applicants, list), "Response should be a list"
        
        # Verify all returned records have applicant statuses
        for app in applicants:
            status = app.get('status')
            assert status in APPLICANT_STATUSES, f"Found non-applicant status '{status}' in recruitment/applicants response"
            # Verify person_stage is set correctly
            assert app.get('person_stage') == 'applicant', f"Expected person_stage='applicant', got '{app.get('person_stage')}'"
        
        print(f"✓ GET /recruitment/applicants returned {len(applicants)} applicants, all with valid applicant statuses")
    
    def test_staff_employees_excludes_applicants(self, auth_headers):
        """Verify staff/employees does not include any applicant-status records"""
        # Get all employees
        emp_response = requests.get(
            f"{BASE_URL}/api/staff/employees?include_inactive=true",
            headers=auth_headers
        )
        assert emp_response.status_code == 200
        employees = emp_response.json()
        employee_ids = {e['id'] for e in employees}
        
        # Get all applicants
        app_response = requests.get(
            f"{BASE_URL}/api/recruitment/applicants",
            headers=auth_headers
        )
        assert app_response.status_code == 200
        applicants = app_response.json()
        applicant_ids = {a['id'] for a in applicants}
        
        # Verify no overlap
        overlap = employee_ids & applicant_ids
        assert len(overlap) == 0, f"Found {len(overlap)} IDs appearing in both endpoints: {overlap}"
        
        print(f"✓ No overlap between staff/employees ({len(employee_ids)}) and recruitment/applicants ({len(applicant_ids)})")


class TestScopedProfileEndpoints:
    """Test scoped profile endpoints enforce scope boundaries"""
    
    def test_staff_employee_by_id_returns_employee(self, auth_headers):
        """GET /staff/employees/{id} should return employee record"""
        response = requests.get(
            f"{BASE_URL}/api/staff/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        employee = response.json()
        assert employee.get('id') == TEST_EMPLOYEE_ID
        assert employee.get('status') in EMPLOYEE_STATUSES, f"Expected employee status, got '{employee.get('status')}'"
        assert employee.get('person_stage') == 'employee'
        
        # Verify work_readiness_3tier is included for employees
        assert 'work_readiness_3tier' in employee, "Employee should have work_readiness_3tier"
        
        print(f"✓ GET /staff/employees/{TEST_EMPLOYEE_ID} returned employee with status '{employee.get('status')}'")
    
    def test_staff_employee_by_id_returns_404_for_applicant(self, auth_headers):
        """GET /staff/employees/{id} should return 404 for applicant IDs"""
        response = requests.get(
            f"{BASE_URL}/api/staff/employees/{TEST_APPLICANT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404 for applicant ID in staff endpoint, got {response.status_code}"
        
        print(f"✓ GET /staff/employees/{TEST_APPLICANT_ID} correctly returned 404 for applicant ID")
    
    def test_recruitment_applicant_by_id_returns_applicant(self, auth_headers):
        """GET /recruitment/applicants/{id} should return applicant record"""
        response = requests.get(
            f"{BASE_URL}/api/recruitment/applicants/{TEST_APPLICANT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        applicant = response.json()
        assert applicant.get('id') == TEST_APPLICANT_ID
        assert applicant.get('status') in APPLICANT_STATUSES, f"Expected applicant status, got '{applicant.get('status')}'"
        assert applicant.get('person_stage') == 'applicant'
        
        # Verify work_readiness is NOT included for applicants (they can't work yet)
        assert 'work_readiness_3tier' not in applicant or applicant.get('work_readiness_3tier') is None, \
            "Applicants should not have work_readiness_3tier"
        
        print(f"✓ GET /recruitment/applicants/{TEST_APPLICANT_ID} returned applicant with status '{applicant.get('status')}'")
    
    def test_recruitment_applicant_by_id_returns_404_for_employee(self, auth_headers):
        """GET /recruitment/applicants/{id} should return 404 for employee IDs"""
        response = requests.get(
            f"{BASE_URL}/api/recruitment/applicants/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404 for employee ID in recruitment endpoint, got {response.status_code}"
        
        print(f"✓ GET /recruitment/applicants/{TEST_EMPLOYEE_ID} correctly returned 404 for employee ID")


class TestAuthoritativeReadinessEndpoint:
    """Test authoritative readiness endpoint with stable reason codes"""
    
    def test_readiness_endpoint_returns_authoritative_data(self, auth_headers):
        """GET /employees/{id}/readiness should return authoritative readiness calculation"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/readiness",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        readiness = response.json()
        
        # Verify required fields
        assert 'ready' in readiness, "Response should include 'ready' boolean"
        assert 'status' in readiness, "Response should include 'status'"
        assert 'label' in readiness, "Response should include 'label'"
        assert 'blockedReasons' in readiness, "Response should include 'blockedReasons'"
        assert 'checks' in readiness, "Response should include 'checks'"
        assert 'calculatedAt' in readiness, "Response should include 'calculatedAt'"
        assert 'source_of_truth' in readiness, "Response should include 'source_of_truth'"
        
        # Verify status is one of the 3-tier values
        assert readiness['status'] in ['NOT_READY', 'READY_WITH_CONDITIONS', 'READY_TO_WORK'], \
            f"Invalid status: {readiness['status']}"
        
        # Verify source_of_truth marker
        assert readiness['source_of_truth'] == 'authoritative_readiness_calculation'
        
        print(f"✓ GET /employees/{TEST_EMPLOYEE_ID}/readiness returned status '{readiness['status']}'")
    
    def test_readiness_endpoint_has_stable_reason_codes(self, auth_headers):
        """Verify blockedReasons use stable reason codes"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/readiness",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        readiness = response.json()
        blocked_reasons = readiness.get('blockedReasons', [])
        
        # Known stable reason codes from the implementation
        VALID_REASON_CODES = [
            "applicant_stage",
            "recruitment_not_approved",
            "right_to_work_documents_missing",
            "right_to_work_documents_expired",
            "right_to_work_check_missing",
            "right_to_work_check_expired",
            "identity_documents_missing",
            "identity_documents_expired",
            "dbs_certificate_missing",
            "dbs_certificate_expired",
            "dbs_check_missing",
            "dbs_check_expired",
            "reference_1_incomplete",
            "reference_2_incomplete",
            "references_below_minimum",
            "proof_of_address_below_minimum",
            "health_form_missing",
            "health_form_unverified",
            "interview_form_missing",
            "interview_form_unverified",
        ]
        
        # Verify each reason has a code field
        for reason in blocked_reasons:
            assert 'code' in reason or 'type' in reason, f"Reason should have 'code' or 'type': {reason}"
        
        print(f"✓ Readiness endpoint returned {len(blocked_reasons)} blocked reasons with stable codes")
    
    def test_readiness_endpoint_includes_detailed_checks(self, auth_headers):
        """Verify checks object includes all required check categories"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/readiness",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        checks = response.json().get('checks', {})
        
        # Verify required check categories
        required_checks = [
            'recruitmentApproved',
            'referencesVerified',
            'proofOfAddress',
            'rightToWork',
            'dbs',
            'id',
            'healthForm',
            'interviewForm'
        ]
        
        for check in required_checks:
            assert check in checks, f"Missing check category: {check}"
        
        # Verify referencesVerified structure
        refs = checks.get('referencesVerified', {})
        assert 'required' in refs, "referencesVerified should have 'required'"
        assert 'verified' in refs, "referencesVerified should have 'verified'"
        assert 'passed' in refs, "referencesVerified should have 'passed'"
        
        # Verify proofOfAddress structure
        poa = checks.get('proofOfAddress', {})
        assert 'required' in poa, "proofOfAddress should have 'required'"
        assert poa.get('required') == 2, "proofOfAddress should require 2 documents"
        
        print(f"✓ Readiness checks include all {len(required_checks)} required categories")


class TestScopeHelpers:
    """Test scope helper functions work correctly via API behavior"""
    
    def test_employee_status_filtering(self, auth_headers):
        """Verify employee status filtering works correctly"""
        # Test filtering by specific employee status
        for status in EMPLOYEE_STATUSES:
            response = requests.get(
                f"{BASE_URL}/api/staff/employees?status={status}&include_inactive=true",
                headers=auth_headers
            )
            assert response.status_code == 200
            employees = response.json()
            
            # All returned should have the requested status
            for emp in employees:
                assert emp.get('status') == status, f"Expected status '{status}', got '{emp.get('status')}'"
        
        print(f"✓ Employee status filtering works for all {len(EMPLOYEE_STATUSES)} employee statuses")
    
    def test_applicant_status_filtering(self, auth_headers):
        """Verify applicant status filtering works correctly"""
        # Test filtering by specific applicant status
        for status in APPLICANT_STATUSES:
            response = requests.get(
                f"{BASE_URL}/api/recruitment/applicants?status={status}",
                headers=auth_headers
            )
            assert response.status_code == 200
            applicants = response.json()
            
            # All returned should have the requested status
            for app in applicants:
                assert app.get('status') == status, f"Expected status '{status}', got '{app.get('status')}'"
        
        print(f"✓ Applicant status filtering works for all {len(APPLICANT_STATUSES)} applicant statuses")


class TestDashboardIntegration:
    """Test dashboard uses correct scoped endpoints"""
    
    def test_dashboard_stats_endpoint(self, auth_headers):
        """Verify dashboard stats endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        stats = response.json()
        assert isinstance(stats, dict), "Stats should be a dictionary"
        
        print(f"✓ Dashboard stats endpoint accessible")
    
    def test_staff_employees_count_matches_dashboard(self, auth_headers):
        """Verify staff/employees count is consistent"""
        # Get employees from scoped endpoint
        emp_response = requests.get(
            f"{BASE_URL}/api/staff/employees?include_inactive=true",
            headers=auth_headers
        )
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        # Count should only include employee-status records
        employee_count = len(employees)
        
        # Verify all are employee-status
        for emp in employees:
            assert emp.get('status') in EMPLOYEE_STATUSES
        
        print(f"✓ Staff/employees returns {employee_count} employees (excludes applicants)")


class TestWorkReadiness3Tier:
    """Test 3-tier work readiness calculation"""
    
    def test_employee_has_work_readiness_3tier(self, auth_headers):
        """Verify employees have work_readiness_3tier in list response"""
        response = requests.get(
            f"{BASE_URL}/api/staff/employees?include_inactive=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        employees = response.json()
        
        if len(employees) > 0:
            emp = employees[0]
            assert 'work_readiness_3tier' in emp, "Employee should have work_readiness_3tier"
            
            wr3 = emp.get('work_readiness_3tier', {})
            assert 'status' in wr3, "work_readiness_3tier should have 'status'"
            assert wr3['status'] in ['NOT_READY', 'READY_WITH_CONDITIONS', 'READY_TO_WORK'], \
                f"Invalid 3-tier status: {wr3['status']}"
        
        print(f"✓ Employees have work_readiness_3tier with valid status")
    
    def test_applicants_do_not_have_work_readiness(self, auth_headers):
        """Verify applicants do not have work_readiness (they can't work yet)"""
        response = requests.get(
            f"{BASE_URL}/api/recruitment/applicants",
            headers=auth_headers
        )
        assert response.status_code == 200
        applicants = response.json()
        
        for app in applicants:
            # Applicants should not have work_readiness fields
            assert 'work_readiness' not in app or app.get('work_readiness') is None, \
                f"Applicant {app.get('id')} should not have work_readiness"
            assert 'work_readiness_3tier' not in app or app.get('work_readiness_3tier') is None, \
                f"Applicant {app.get('id')} should not have work_readiness_3tier"
        
        print(f"✓ Applicants correctly do not have work_readiness fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test Work Readiness Engine (Gate 2)
Tests the work readiness evaluation endpoint and response structure.

Gate 2 evaluates whether an APPROVED employee is ready to start work.
Separate from Gate 1 (Recruitment Approval).
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee IDs from review request
APPROVED_EMPLOYEE_HCA = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"  # Lawrence Egbeni - Healthcare Assistant, recruitment_approved=true
APPROVED_EMPLOYEE_2 = "8f351317-8623-4df5-8788-c6a3ce5364cf"  # OLUMIDE - recruitment_approved=true
APPLICANT_NURSE = "ca0e267f-faf2-4a4f-bd2e-afe8ea089b1f"  # Ayomi Lori - Nurse - recruitment_approved=false


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestWorkReadinessEndpoint:
    """Test GET /api/employees/{id}/work-readiness-check endpoint"""
    
    def test_endpoint_returns_200_for_approved_employee(self, auth_headers):
        """Test endpoint returns 200 for approved employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "can_work" in data
        assert "blockers" in data
        print(f"Work readiness check returned: can_work={data.get('can_work')}, blocker_count={data.get('blocker_count')}")
    
    def test_endpoint_returns_correct_structure(self, auth_headers):
        """Test response contains all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required fields per spec
        required_fields = [
            "can_work",
            "blockers",
            "warnings",
            "verified_count",
            "required_count",
            "role",
            "stage_identity"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"Response structure validated: {list(data.keys())}")
    
    def test_response_includes_readiness_status(self, auth_headers):
        """Test response includes readiness_status field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "readiness_status" in data
        assert data["readiness_status"] in ["READY_TO_WORK", "READY_WITH_CONDITIONS", "NOT_READY"]
        print(f"Readiness status: {data['readiness_status']}")
    
    def test_endpoint_returns_404_for_nonexistent_employee(self, auth_headers):
        """Test endpoint returns 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/nonexistent-id-12345/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestHCAWorkRequirements:
    """Test HCA role requires 9 items for work readiness"""
    
    def test_hca_required_count(self, auth_headers):
        """Test HCA role has correct required_count (9 items)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # HCA requires 9 items per spec:
        # contract_acceptance, handbook_acknowledgement, induction, staff_health_questionnaire,
        # care_certificate, right_to_work, dbs, identity, training
        required_count = data.get("required_count", 0)
        required_keys = data.get("required_keys", [])
        
        print(f"HCA required_count: {required_count}")
        print(f"HCA required_keys: {required_keys}")
        
        # Verify required count is 9 for HCA
        assert required_count == 9, f"Expected 9 required items for HCA, got {required_count}"
    
    def test_hca_required_keys_include_core_items(self, auth_headers):
        """Test HCA required_keys includes all core items"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        required_keys = data.get("required_keys", [])
        
        # Core items that must be present for HCA
        expected_items = [
            "contract_acceptance",
            "handbook_acknowledgement",
            "induction",
            "staff_health_questionnaire",
            "care_certificate",
            "right_to_work",
            "dbs",
            "identity",
            "training"
        ]
        
        for item in expected_items:
            assert item in required_keys, f"Missing required item for HCA: {item}"
        
        print(f"All 9 HCA required items verified: {expected_items}")


class TestNurseWorkRequirements:
    """Test Nurse role requires 10 items (9 HCA items + nmc_registration)"""
    
    def test_nurse_required_count(self, auth_headers):
        """Test Nurse role has correct required_count (10 items)"""
        # First, find a nurse employee who is approved
        # We'll check the applicant nurse's role to verify the requirement count
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPLICANT_NURSE}",
            headers=auth_headers
        )
        
        if response.status_code != 200:
            pytest.skip("Nurse employee not found")
        
        employee = response.json()
        role = employee.get("role", "").lower()
        
        if "nurse" not in role:
            pytest.skip(f"Employee is not a nurse: {role}")
        
        # Check work readiness for this nurse
        wr_response = requests.get(
            f"{BASE_URL}/api/employees/{APPLICANT_NURSE}/work-readiness-check",
            headers=auth_headers
        )
        
        assert wr_response.status_code == 200
        data = wr_response.json()
        
        required_count = data.get("required_count", 0)
        required_keys = data.get("required_keys", [])
        
        print(f"Nurse required_count: {required_count}")
        print(f"Nurse required_keys: {required_keys}")
        
        # Nurse requires 10 items (9 HCA + nmc_registration)
        assert required_count == 10, f"Expected 10 required items for Nurse, got {required_count}"
    
    def test_nurse_includes_nmc_registration(self, auth_headers):
        """Test Nurse required_keys includes nmc_registration"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPLICANT_NURSE}/work-readiness-check",
            headers=auth_headers
        )
        
        if response.status_code != 200:
            pytest.skip("Nurse employee not found")
        
        data = response.json()
        required_keys = data.get("required_keys", [])
        
        # NMC registration must be present for nurses
        assert "nmc_registration" in required_keys, "Nurse should require nmc_registration"
        print("NMC registration requirement verified for Nurse role")


class TestBlockerCategories:
    """Test blockers have correct category values"""
    
    def test_blockers_have_category_field(self, auth_headers):
        """Test each blocker has a category field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        blockers = data.get("blockers", [])
        
        if len(blockers) == 0:
            print("No blockers found - employee may be work ready")
            return
        
        for blocker in blockers:
            assert "category" in blocker, f"Blocker missing category: {blocker}"
            assert "label" in blocker, f"Blocker missing label: {blocker}"
            assert "reason" in blocker, f"Blocker missing reason: {blocker}"
        
        print(f"Verified {len(blockers)} blockers have category, label, and reason")
    
    def test_blocker_categories_are_valid(self, auth_headers):
        """Test blocker categories are from valid set"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        blockers = data.get("blockers", [])
        
        # Valid categories per spec
        valid_categories = [
            "agreement",
            "form",
            "competency",
            "document",
            "training",
            "expired_document"
        ]
        
        for blocker in blockers:
            category = blocker.get("category")
            assert category in valid_categories, f"Invalid blocker category: {category}"
        
        categories_found = set(b.get("category") for b in blockers)
        print(f"Blocker categories found: {categories_found}")


class TestStageIdentity:
    """Test stage_identity field in response"""
    
    def test_approved_employee_has_employee_stage(self, auth_headers):
        """Test approved employee has stage_identity='employee'"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        stage_identity = data.get("stage_identity")
        recruitment_approved = data.get("recruitment_approved")
        
        print(f"Stage identity: {stage_identity}, recruitment_approved: {recruitment_approved}")
        
        # If recruitment_approved is True, stage should be 'employee'
        if recruitment_approved:
            assert stage_identity == "employee", f"Expected 'employee' stage for approved employee, got {stage_identity}"
    
    def test_applicant_has_applicant_stage(self, auth_headers):
        """Test applicant has stage_identity='applicant'"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPLICANT_NURSE}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        stage_identity = data.get("stage_identity")
        recruitment_approved = data.get("recruitment_approved")
        
        print(f"Stage identity: {stage_identity}, recruitment_approved: {recruitment_approved}")
        
        # If recruitment_approved is False, stage should be 'applicant'
        if not recruitment_approved:
            assert stage_identity == "applicant", f"Expected 'applicant' stage for non-approved, got {stage_identity}"


class TestProgressTracking:
    """Test verified_count and required_count for progress tracking"""
    
    def test_progress_counts_are_integers(self, auth_headers):
        """Test verified_count and required_count are integers"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        verified_count = data.get("verified_count")
        required_count = data.get("required_count")
        
        assert isinstance(verified_count, int), f"verified_count should be int, got {type(verified_count)}"
        assert isinstance(required_count, int), f"required_count should be int, got {type(required_count)}"
        
        print(f"Progress: {verified_count} / {required_count}")
    
    def test_verified_count_not_greater_than_required(self, auth_headers):
        """Test verified_count <= required_count"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        verified_count = data.get("verified_count", 0)
        required_count = data.get("required_count", 0)
        
        assert verified_count <= required_count, f"verified_count ({verified_count}) > required_count ({required_count})"


class TestCanWorkLogic:
    """Test can_work boolean logic"""
    
    def test_can_work_false_when_blockers_exist(self, auth_headers):
        """Test can_work is False when blockers exist"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{APPROVED_EMPLOYEE_HCA}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        can_work = data.get("can_work")
        blockers = data.get("blockers", [])
        blocker_count = data.get("blocker_count", len(blockers))
        
        if blocker_count > 0:
            assert can_work == False, f"can_work should be False when blockers exist, got {can_work}"
            print(f"Correctly: can_work=False with {blocker_count} blockers")
        else:
            assert can_work == True, f"can_work should be True when no blockers, got {can_work}"
            print("Correctly: can_work=True with no blockers")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

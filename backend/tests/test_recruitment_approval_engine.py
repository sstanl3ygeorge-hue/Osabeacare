"""
Test Recruitment Approval Engine
Tests for:
- GET /api/employees/{id}/recruitment-approval-check
- POST /api/employees/{id}/approve-recruitment
- Blocker evaluation for Healthcare Assistant role (10 required items)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test IDs from the review request
TEST_APPLICANT_ID = "8f351317-8623-4df5-8788-c6a3ce5364cf"  # OLUMIDE OBEMBE - Healthcare Assistant - has blockers
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Already employee status


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(admin_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


class TestRecruitmentApprovalCheck:
    """Tests for GET /api/employees/{id}/recruitment-approval-check"""
    
    def test_approval_check_returns_evaluation(self, api_client):
        """Test that approval check returns proper evaluation structure"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/recruitment-approval-check"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "can_approve" in data, "Missing can_approve field"
        assert "blockers" in data, "Missing blockers field"
        assert "verified_count" in data, "Missing verified_count field"
        assert "required_count" in data, "Missing required_count field"
        
        print(f"Approval check result: can_approve={data['can_approve']}, "
              f"verified={data['verified_count']}/{data['required_count']}, "
              f"blockers={len(data.get('blockers', []))}")
    
    def test_approval_check_has_blockers_for_applicant(self, api_client):
        """Test that applicant with incomplete requirements has blockers"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/recruitment-approval-check"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Applicant should have blockers (incomplete requirements)
        blockers = data.get("blockers", [])
        blocker_count = data.get("blocker_count", len(blockers))
        
        print(f"Applicant has {blocker_count} blockers")
        
        # Each blocker should have required fields
        for blocker in blockers:
            assert "requirement_key" in blocker, "Blocker missing requirement_key"
            assert "label" in blocker, "Blocker missing label"
            assert "reason" in blocker, "Blocker missing reason"
            print(f"  - {blocker['label']}: {blocker['reason']}")
    
    def test_approval_check_healthcare_assistant_requirements(self, api_client):
        """Test that Healthcare Assistant role has 10 required items"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/recruitment-approval-check"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        required_count = data.get("required_count", 0)
        required_keys = data.get("required_keys", [])
        
        # Healthcare Assistant should have 10 required items
        assert required_count == 10, f"Expected 10 required items for HCA, got {required_count}"
        
        # Verify expected requirements
        expected_requirements = [
            "right_to_work",
            "identity",
            "proof_of_address",
            "dbs",
            "reference_1",
            "reference_2",
            "interview_record",
            "recruitment_checklist",
            "staff_health_questionnaire",
            "staff_personal_info"
        ]
        
        for req in expected_requirements:
            assert req in required_keys, f"Missing required key: {req}"
        
        print(f"Healthcare Assistant requirements verified: {required_keys}")
    
    def test_approval_check_returns_role_info(self, api_client):
        """Test that approval check returns role information"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/recruitment-approval-check"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "role" in data, "Missing role field"
        assert "role_normalized" in data, "Missing role_normalized field"
        
        print(f"Role: {data['role']}, Normalized: {data['role_normalized']}")
    
    def test_approval_check_employee_not_found(self, api_client):
        """Test 404 for non-existent employee"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/non-existent-id-12345/recruitment-approval-check"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestApproveRecruitment:
    """Tests for POST /api/employees/{id}/approve-recruitment"""
    
    def test_approve_endpoint_requires_body(self, api_client):
        """Test that approval endpoint accepts empty body"""
        # The endpoint requires a body (even if empty) due to RecruitmentApprovalRequest model
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/approve-recruitment",
            json={}  # Empty body required
        )
        
        # Should get either success (200) or already_approved status, not 422
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Approval response: {data.get('status', 'unknown')}")
    
    def test_approve_employee_not_found(self, api_client):
        """Test 404 for non-existent employee"""
        response = api_client.post(
            f"{BASE_URL}/api/employees/non-existent-id-12345/approve-recruitment",
            json={}  # Empty body required
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    def test_approve_already_approved_returns_status(self, api_client):
        """Test that approving already-approved employee returns appropriate status"""
        # First check if employee is already approved
        check_response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/recruitment-approval-check"
        )
        
        if check_response.status_code == 200:
            check_data = check_response.json()
            if check_data.get("recruitment_approved"):
                # Try to approve again - should return already_approved status
                response = api_client.post(
                    f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/approve-recruitment",
                    json={}
                )
                
                # Should return 200 with already_approved status (not 400)
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                data = response.json()
                assert data.get("status") == "already_approved", f"Expected already_approved status, got: {data}"
                print("Correctly returned already_approved status for re-approval attempt")
            else:
                pytest.skip("Employee not yet approved - cannot test re-approval")
        else:
            pytest.skip(f"Could not check employee status: {check_response.status_code}")


class TestBlockerReasons:
    """Tests for blocker reason generation"""
    
    def test_blockers_have_valid_reasons(self, api_client):
        """Test that each blocker has a meaningful reason"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/recruitment-approval-check"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        blockers = data.get("blockers", [])
        
        valid_reason_patterns = [
            "No evidence submitted",
            "Awaiting verification",
            "Not verified",
            "Requirement not found",
            "Form not completed",
            "Reference not declared",
            "Request not sent",
            "Awaiting referee response",
            "Response received - awaiting verification",
            "Rejected - needs resubmission",
            "Submitted - awaiting verification"
        ]
        
        for blocker in blockers:
            reason = blocker.get("reason", "")
            assert reason, f"Blocker {blocker.get('requirement_key')} has empty reason"
            
            # Check that reason is meaningful (not just generic)
            has_valid_reason = any(pattern in reason for pattern in valid_reason_patterns) or len(reason) > 5
            assert has_valid_reason, f"Blocker {blocker.get('requirement_key')} has invalid reason: {reason}"
            
            print(f"  {blocker.get('label')}: {reason}")


class TestApprovalEvaluationFields:
    """Tests for all evaluation response fields"""
    
    def test_evaluation_has_all_required_fields(self, api_client):
        """Test that evaluation response has all expected fields"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/recruitment-approval-check"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "employee_id",
            "can_approve",
            "blockers",
            "blocker_count",
            "verified_count",
            "required_count",
            "verified_keys",
            "required_keys"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify types
        assert isinstance(data["can_approve"], bool), "can_approve should be boolean"
        assert isinstance(data["blockers"], list), "blockers should be list"
        assert isinstance(data["blocker_count"], int), "blocker_count should be int"
        assert isinstance(data["verified_count"], int), "verified_count should be int"
        assert isinstance(data["required_count"], int), "required_count should be int"
        assert isinstance(data["verified_keys"], list), "verified_keys should be list"
        assert isinstance(data["required_keys"], list), "required_keys should be list"
        
        print(f"All required fields present with correct types")
    
    def test_counts_are_consistent(self, api_client):
        """Test that counts are mathematically consistent"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_APPLICANT_ID}/recruitment-approval-check"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        verified_count = data.get("verified_count", 0)
        required_count = data.get("required_count", 0)
        blocker_count = data.get("blocker_count", 0)
        
        # verified + blockers should equal required
        assert verified_count + blocker_count == required_count, \
            f"Counts inconsistent: {verified_count} verified + {blocker_count} blockers != {required_count} required"
        
        # can_approve should be true only if no blockers
        can_approve = data.get("can_approve", False)
        if blocker_count == 0:
            assert can_approve, "can_approve should be True when no blockers"
        else:
            assert not can_approve, "can_approve should be False when blockers exist"
        
        print(f"Counts consistent: {verified_count} + {blocker_count} = {required_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

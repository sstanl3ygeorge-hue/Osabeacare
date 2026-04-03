"""
Employment Gap 30-Day Threshold Tests

Tests for:
- Gap detection with 30-day threshold (gaps under 30 days should not be flagged)
- Gap detection for gaps over 30 days
- Blocker integration (unexplained gaps block recruitment approval)
- Full workflow: detect -> explain -> verify/reject -> recruitment status update
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

# Test employee with known gaps
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestGapDetectionThreshold:
    """Tests for 30-day gap detection threshold"""
    
    def test_get_gaps_returns_only_gaps_over_30_days(self, admin_headers):
        """Test that only gaps over 30 days are returned"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify gaps exist
        assert data.get("has_gaps") == True
        gaps = data.get("gaps", [])
        
        # All returned gaps should be over 30 days
        for gap in gaps:
            duration_days = gap.get("duration_days", 0)
            assert duration_days > 30, f"Gap {gap.get('gap_id')} has duration {duration_days} days, should be > 30"
            print(f"Gap {gap.get('gap_id')}: {duration_days} days ({gap.get('duration_months')} months)")
    
    def test_gap_1_is_over_30_days(self, admin_headers):
        """Test that gap_1 (2.5 months) is correctly detected"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        gaps = data.get("gaps", [])
        
        gap_1 = next((g for g in gaps if g.get("gap_id") == "gap_1"), None)
        assert gap_1 is not None, "gap_1 not found"
        
        # Verify gap_1 is 2.5 months (76 days)
        assert gap_1.get("duration_days") == 76
        assert gap_1.get("duration_months") == 2.5
        assert gap_1.get("status") == "needs_more_info"
        
        print(f"gap_1: {gap_1.get('duration_days')} days, status={gap_1.get('status')}")
    
    def test_gap_2_is_over_30_days(self, admin_headers):
        """Test that gap_2 (3.1 months) is correctly detected"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        gaps = data.get("gaps", [])
        
        gap_2 = next((g for g in gaps if g.get("gap_id") == "gap_2"), None)
        assert gap_2 is not None, "gap_2 not found"
        
        # Verify gap_2 is 3.1 months (94 days)
        assert gap_2.get("duration_days") == 94
        assert gap_2.get("duration_months") == 3.1
        assert gap_2.get("status") == "rejected"
        
        print(f"gap_2: {gap_2.get('duration_days')} days, status={gap_2.get('status')}")


class TestGapStatusValues:
    """Tests for gap status values and transitions"""
    
    def test_valid_status_values(self, admin_headers):
        """Test that gap statuses are valid"""
        valid_statuses = ["pending", "explained", "verified", "rejected", "needs_more_info"]
        
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        gaps = data.get("gaps", [])
        
        for gap in gaps:
            status = gap.get("status")
            assert status in valid_statuses, f"Invalid status: {status}"
            print(f"Gap {gap.get('gap_id')}: status={status}")
    
    def test_gap_evaluation_counts(self, admin_headers):
        """Test that evaluation counts are correct"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        evaluation = data.get("evaluation", {})
        
        # Verify evaluation structure
        assert "total_gaps" in evaluation
        assert "verified_count" in evaluation
        assert "pending_count" in evaluation
        assert "rejected_count" in evaluation
        assert "needs_info_count" in evaluation
        assert "is_complete" in evaluation
        
        # For test employee: 1 needs_more_info, 1 rejected
        assert evaluation.get("total_gaps") == 2
        assert evaluation.get("rejected_count") == 1
        assert evaluation.get("needs_info_count") == 1
        assert evaluation.get("is_complete") == False
        
        print(f"Evaluation: {evaluation}")


class TestComplianceFileIntegration:
    """Tests for employment_history section in compliance file"""
    
    def test_compliance_file_has_employment_history_section(self, admin_headers):
        """Test that compliance file includes employment_history section"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        sections = data.get("sections", {})
        
        assert "employment_history" in sections, "employment_history section missing"
        
        emp_history = sections["employment_history"]
        assert "rows" in emp_history
        assert len(emp_history["rows"]) > 0
        
        row = emp_history["rows"][0]
        assert row.get("key") == "employment_history_verification"
        assert row.get("row_type") == "employment_gap"
        
        print(f"Employment history section found with {len(emp_history['rows'])} rows")
    
    def test_compliance_file_gap_evaluation(self, admin_headers):
        """Test gap_evaluation in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        sections = data.get("sections", {})
        emp_history = sections.get("employment_history", {})
        rows = emp_history.get("rows", [])
        
        assert len(rows) > 0
        row = rows[0]
        
        # Verify gap_evaluation structure
        gap_evaluation = row.get("gap_evaluation", {})
        assert gap_evaluation.get("has_gaps") == True
        assert gap_evaluation.get("total_gaps") == 2
        assert gap_evaluation.get("is_complete") == False
        
        # Verify blocker_text is set
        assert row.get("blocker_text") is not None
        
        print(f"Gap evaluation: {gap_evaluation}")
        print(f"Blocker text: {row.get('blocker_text')}")
    
    def test_compliance_file_shows_gaps_not_verified(self, admin_headers):
        """Test that compliance file shows gaps are not verified"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        sections = data.get("sections", {})
        emp_history = sections.get("employment_history", {})
        rows = emp_history.get("rows", [])
        
        row = rows[0]
        assert row.get("is_verified") == False
        assert row.get("affects_readiness") == True
        
        print(f"is_verified={row.get('is_verified')}, affects_readiness={row.get('affects_readiness')}")


class TestRecruitmentApprovalBlocker:
    """Tests for employment gap blocking recruitment approval"""
    
    def test_recruitment_approval_check_includes_employment_history(self, admin_headers):
        """Test that recruitment approval check includes employment_history_verification"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/recruitment-approval-check",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required_keys includes employment_history_verification
        required_keys = data.get("required_keys", [])
        assert "employment_history_verification" in required_keys, \
            "employment_history_verification should be in required_keys"
        
        print(f"Required keys: {required_keys}")
    
    def test_unexplained_gaps_block_approval(self, admin_headers):
        """Test that unexplained/rejected gaps block recruitment approval"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/recruitment-approval-check",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should not be able to approve
        assert data.get("can_approve") == False
        
        # Check blockers include employment_history_verification
        blockers = data.get("blockers", [])
        blocker_keys = [b.get("requirement_key") for b in blockers]
        
        assert "employment_history_verification" in blocker_keys, \
            "employment_history_verification should be in blockers"
        
        # Find the employment history blocker
        emp_blocker = next((b for b in blockers if b.get("requirement_key") == "employment_history_verification"), None)
        assert emp_blocker is not None
        assert emp_blocker.get("row_type") == "employment_gap"
        
        print(f"Employment history blocker: {emp_blocker}")


class TestGapExplanationWorkflow:
    """Tests for gap explanation submission"""
    
    def test_explain_gap_endpoint_accepts_explanation(self, admin_headers):
        """Test that explain endpoint accepts explanation"""
        # Submit explanation for gap_2 (rejected status)
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/gap_2/explain",
            params={"explanation": "TEST: I was taking care of a family member during this period"},
            headers=admin_headers
        )
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("new_status") == "explained"
        
        print(f"Explanation submitted: {data}")
    
    def test_gap_status_updated_after_explanation(self, admin_headers):
        """Test that gap status is updated after explanation"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        gaps = data.get("gaps", [])
        
        gap_2 = next((g for g in gaps if g.get("gap_id") == "gap_2"), None)
        assert gap_2 is not None
        
        # Status should now be "explained" (after our test submission)
        assert gap_2.get("status") == "explained", f"Expected 'explained', got '{gap_2.get('status')}'"
        assert gap_2.get("explanation") is not None
        
        print(f"gap_2 status after explanation: {gap_2.get('status')}")


class TestAdminVerificationWorkflow:
    """Tests for admin verification actions"""
    
    def test_verify_gap_requires_admin(self):
        """Test that verify endpoint requires admin role"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/gap_1/verify",
            params={"approved": True}
        )
        
        assert response.status_code in [401, 403]
    
    def test_request_info_requires_admin(self):
        """Test that request-info endpoint requires admin role"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/gap_1/request-info",
            params={"request_message": "Please provide more details"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_verify_gap_approve(self, admin_headers):
        """Test approving a gap explanation"""
        # First ensure gap_2 has an explanation
        requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/gap_2/explain",
            params={"explanation": "TEST: Career break for family care"},
            headers=admin_headers
        )
        
        # Now verify it
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/gap_2/verify",
            params={"approved": True, "notes": "TEST: Verified by automated test"},
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("new_status") == "verified"
        
        print(f"Gap verified: {data}")
    
    def test_gap_status_updated_after_verification(self, admin_headers):
        """Test that gap status is updated after verification"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        gaps = data.get("gaps", [])
        
        gap_2 = next((g for g in gaps if g.get("gap_id") == "gap_2"), None)
        assert gap_2 is not None
        
        # Status should now be "verified"
        assert gap_2.get("status") == "verified", f"Expected 'verified', got '{gap_2.get('status')}'"
        assert gap_2.get("verified_by") is not None
        assert gap_2.get("verified_at") is not None
        
        print(f"gap_2 status after verification: {gap_2.get('status')}")


class TestGapRecordStructure:
    """Tests for gap record structure"""
    
    def test_gap_record_has_required_fields(self, admin_headers):
        """Test that gap records have all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        gaps = data.get("gaps", [])
        
        assert len(gaps) > 0
        
        required_fields = [
            "gap_id",
            "gap_start",
            "gap_end",
            "duration_days",
            "duration_months",
            "status"
        ]
        
        for gap in gaps:
            for field in required_fields:
                assert field in gap, f"Missing required field: {field}"
        
        print(f"All {len(gaps)} gaps have required fields")
    
    def test_gap_record_has_employment_context(self, admin_headers):
        """Test that gap records have previous/next employment context"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        gaps = data.get("gaps", [])
        
        for gap in gaps:
            prev_emp = gap.get("previous_employment")
            next_emp = gap.get("next_employment")
            
            if prev_emp:
                assert "company" in prev_emp
                assert "end_date" in prev_emp
            
            if next_emp:
                assert "company" in next_emp
                assert "start_date" in next_emp
        
        print("Gap records have employment context")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

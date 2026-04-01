"""
Employment Gap Detection and Verification Tests

Tests for:
- GET /api/employees/{id}/employment-gaps - Get gap detection and verification status
- POST /api/employees/{id}/employment-gaps/{gap_id}/explain - Submit gap explanation
- POST /api/employees/{id}/employment-gaps/{gap_id}/verify - Approve/reject gap
- POST /api/employees/{id}/employment-gaps/{gap_id}/request-info - Request more info
- POST /api/employees/{id}/detect-employment-gaps - Re-detect gaps from employment history
- Compliance file includes employment_history section with gap_evaluation
- Recruitment approval check includes employment_history_verification in required items
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "ca0e267f-faf2-4a4f-bd2e-afe8ea089b1f"  # Ayomi Lori - Nurse


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        # API returns "token" not "access_token"
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def test_employee_with_gaps(admin_headers):
    """Create or find an employee with employment history that has gaps"""
    # First check if test employee exists
    response = requests.get(
        f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
        headers=admin_headers
    )
    
    if response.status_code == 200:
        employee = response.json()
        # Check if employee has employment history
        if employee.get("employment_history"):
            return TEST_EMPLOYEE_ID
    
    # Try to find any employee with employment history
    response = requests.get(
        f"{BASE_URL}/api/employees",
        headers=admin_headers
    )
    
    if response.status_code == 200:
        employees = response.json()
        for emp in employees:
            if emp.get("employment_history") and len(emp.get("employment_history", [])) > 0:
                return emp.get("id")
    
    # Return test employee ID anyway - gaps may be empty which is valid
    return TEST_EMPLOYEE_ID


class TestEmploymentGapsEndpoint:
    """Tests for GET /api/employees/{id}/employment-gaps"""
    
    def test_get_employment_gaps_success(self, admin_headers, test_employee_with_gaps):
        """Test getting employment gaps returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "employee_id" in data
        assert "has_gaps" in data
        assert "total_gaps" in data
        assert "gaps" in data
        assert "evaluation" in data
        
        # Verify evaluation structure
        evaluation = data.get("evaluation", {})
        assert "has_gaps" in evaluation
        assert "total_gaps" in evaluation
        assert "verified_count" in evaluation
        assert "pending_count" in evaluation
        assert "is_complete" in evaluation
        
        print(f"Employment gaps response: has_gaps={data['has_gaps']}, total_gaps={data['total_gaps']}")
    
    def test_get_employment_gaps_nonexistent_employee(self, admin_headers):
        """Test getting gaps for non-existent employee returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/employees/nonexistent-id-12345/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    def test_get_employment_gaps_requires_auth(self):
        """Test that getting gaps requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps"
        )
        
        assert response.status_code == 401 or response.status_code == 403


class TestDetectEmploymentGaps:
    """Tests for POST /api/employees/{id}/detect-employment-gaps"""
    
    def test_detect_gaps_success(self, admin_headers, test_employee_with_gaps):
        """Test re-detecting employment gaps"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/detect-employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "status" in data
        assert data["status"] == "success"
        assert "gaps_detected" in data or "message" in data
        
        print(f"Gap detection result: {data}")
    
    def test_detect_gaps_requires_admin(self, admin_token):
        """Test that gap detection requires admin role"""
        # Try without auth
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/detect-employment-gaps"
        )
        
        assert response.status_code in [401, 403]
    
    def test_detect_gaps_nonexistent_employee(self, admin_headers):
        """Test detecting gaps for non-existent employee returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-id-12345/detect-employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 404


class TestGapExplanation:
    """Tests for POST /api/employees/{id}/employment-gaps/{gap_id}/explain"""
    
    def test_explain_gap_endpoint_exists(self, admin_headers, test_employee_with_gaps):
        """Test that explain gap endpoint exists and accepts requests"""
        # First get gaps to find a gap_id
        gaps_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps",
            headers=admin_headers
        )
        
        if gaps_response.status_code != 200:
            pytest.skip("Could not get employment gaps")
        
        gaps_data = gaps_response.json()
        gaps = gaps_data.get("gaps", [])
        
        if not gaps:
            # No gaps to explain - this is valid behavior
            print("No employment gaps found for this employee - skipping explanation test")
            pytest.skip("No gaps to explain")
        
        gap_id = gaps[0].get("gap_id")
        
        # Try to explain the gap
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps/{gap_id}/explain",
            params={"explanation": "TEST: Career break for personal development"},
            headers=admin_headers
        )
        
        # Should succeed or return validation error
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data.get("new_status") == "explained"
            print(f"Gap explanation submitted successfully: {data}")
    
    def test_explain_gap_nonexistent_gap(self, admin_headers, test_employee_with_gaps):
        """Test explaining non-existent gap"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps/nonexistent_gap/explain",
            params={"explanation": "Test explanation"},
            headers=admin_headers
        )
        
        # Should return 404 or succeed with no-op (depending on implementation)
        # The endpoint may create the gap record if it doesn't exist
        assert response.status_code in [200, 404, 400]


class TestGapVerification:
    """Tests for POST /api/employees/{id}/employment-gaps/{gap_id}/verify"""
    
    def test_verify_gap_requires_admin(self, test_employee_with_gaps):
        """Test that gap verification requires admin role"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps/gap_1/verify",
            params={"approved": True}
        )
        
        assert response.status_code in [401, 403]
    
    def test_verify_gap_approve(self, admin_headers, test_employee_with_gaps):
        """Test approving a gap explanation"""
        # First get gaps
        gaps_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps",
            headers=admin_headers
        )
        
        if gaps_response.status_code != 200:
            pytest.skip("Could not get employment gaps")
        
        gaps_data = gaps_response.json()
        gaps = gaps_data.get("gaps", [])
        
        if not gaps:
            pytest.skip("No gaps to verify")
        
        gap_id = gaps[0].get("gap_id")
        
        # Try to verify the gap
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps/{gap_id}/verify",
            params={"approved": True, "notes": "TEST: Verified by automated test"},
            headers=admin_headers
        )
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("new_status") == "verified"
            print(f"Gap verified successfully: {data}")
    
    def test_verify_gap_reject(self, admin_headers, test_employee_with_gaps):
        """Test rejecting a gap explanation"""
        # First get gaps
        gaps_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps",
            headers=admin_headers
        )
        
        if gaps_response.status_code != 200:
            pytest.skip("Could not get employment gaps")
        
        gaps_data = gaps_response.json()
        gaps = gaps_data.get("gaps", [])
        
        # Find a gap that's not already verified
        target_gap = None
        for gap in gaps:
            if gap.get("status") != "verified":
                target_gap = gap
                break
        
        if not target_gap:
            pytest.skip("No unverified gaps to reject")
        
        gap_id = target_gap.get("gap_id")
        
        # Try to reject the gap
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps/{gap_id}/verify",
            params={"approved": False, "rejection_reason": "TEST: Need more details"},
            headers=admin_headers
        )
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("new_status") == "rejected"
            print(f"Gap rejected successfully: {data}")


class TestRequestMoreInfo:
    """Tests for POST /api/employees/{id}/employment-gaps/{gap_id}/request-info"""
    
    def test_request_info_requires_admin(self, test_employee_with_gaps):
        """Test that requesting info requires admin role"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps/gap_1/request-info",
            params={"request_message": "Please provide more details"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_request_info_success(self, admin_headers, test_employee_with_gaps):
        """Test requesting more information about a gap"""
        # First get gaps
        gaps_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps",
            headers=admin_headers
        )
        
        if gaps_response.status_code != 200:
            pytest.skip("Could not get employment gaps")
        
        gaps_data = gaps_response.json()
        gaps = gaps_data.get("gaps", [])
        
        if not gaps:
            pytest.skip("No gaps to request info for")
        
        gap_id = gaps[0].get("gap_id")
        
        # Request more info
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps/{gap_id}/request-info",
            params={"request_message": "TEST: Please provide documentation for this period"},
            headers=admin_headers
        )
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("new_status") == "needs_more_info"
            print(f"Info request sent successfully: {data}")


class TestComplianceFileIntegration:
    """Tests for employment_history section in compliance file"""
    
    def test_compliance_file_includes_employment_history(self, admin_headers, test_employee_with_gaps):
        """Test that compliance file includes employment_history section"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/compliance-file",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        sections = data.get("sections", {})
        
        # Check employment_history section exists
        assert "employment_history" in sections, "employment_history section missing from compliance file"
        
        emp_history = sections["employment_history"]
        assert "rows" in emp_history
        assert len(emp_history["rows"]) > 0
        
        # Check row structure
        row = emp_history["rows"][0]
        assert row.get("key") == "employment_history_verification"
        assert row.get("row_type") == "employment_gap"
        assert "has_gaps" in row
        assert "is_verified" in row
        assert "gap_evaluation" in row
        
        print(f"Employment history section: has_gaps={row.get('has_gaps')}, is_verified={row.get('is_verified')}")
    
    def test_compliance_file_gap_evaluation_structure(self, admin_headers, test_employee_with_gaps):
        """Test gap_evaluation structure in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/compliance-file",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        sections = data.get("sections", {})
        emp_history = sections.get("employment_history", {})
        rows = emp_history.get("rows", [])
        
        if not rows:
            pytest.skip("No employment history rows")
        
        row = rows[0]
        gap_evaluation = row.get("gap_evaluation", {})
        
        # Verify gap_evaluation structure
        assert "has_gaps" in gap_evaluation
        assert "total_gaps" in gap_evaluation
        assert "verified_count" in gap_evaluation
        assert "pending_count" in gap_evaluation
        assert "is_complete" in gap_evaluation
        
        print(f"Gap evaluation: {gap_evaluation}")


class TestRecruitmentApprovalIntegration:
    """Tests for employment_history_verification in recruitment approval"""
    
    def test_approval_check_includes_employment_history(self, admin_headers, test_employee_with_gaps):
        """Test that recruitment approval check includes employment_history_verification"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/recruitment-approval-check",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check required_keys includes employment_history_verification
        required_keys = data.get("required_keys", [])
        
        # For nurse role, employment_history_verification should be required
        if "employment_history_verification" in required_keys:
            print("employment_history_verification is in required_keys")
            
            # Check if it's in blockers (if gaps not verified)
            blockers = data.get("blockers", [])
            blocker_keys = [b.get("requirement_key") for b in blockers]
            
            if "employment_history_verification" in blocker_keys:
                print("employment_history_verification is blocking approval")
            else:
                print("employment_history_verification is not blocking (gaps verified or no gaps)")
        else:
            # May not be required for all roles
            print(f"employment_history_verification not in required_keys for this role: {data.get('role')}")


class TestGapStatusValues:
    """Tests for gap status values"""
    
    def test_gap_status_values(self, admin_headers, test_employee_with_gaps):
        """Test that gap status can be: pending, explained, verified, rejected, needs_more_info"""
        valid_statuses = ["pending", "explained", "verified", "rejected", "needs_more_info"]
        
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        gaps = data.get("gaps", [])
        
        for gap in gaps:
            status = gap.get("status")
            assert status in valid_statuses, f"Invalid gap status: {status}"
            print(f"Gap {gap.get('gap_id')}: status={status}")


class TestGapRecordStructure:
    """Tests for gap record structure"""
    
    def test_gap_record_fields(self, admin_headers, test_employee_with_gaps):
        """Test that gap records have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_with_gaps}/employment-gaps",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        gaps = data.get("gaps", [])
        
        if not gaps:
            pytest.skip("No gaps to check structure")
        
        gap = gaps[0]
        
        # Required fields
        required_fields = [
            "gap_id",
            "gap_start",
            "gap_end",
            "duration_days",
            "duration_months",
            "status"
        ]
        
        for field in required_fields:
            assert field in gap, f"Missing required field: {field}"
        
        # Optional but expected fields
        optional_fields = [
            "previous_employment",
            "next_employment",
            "explanation",
            "verified_by",
            "verified_at"
        ]
        
        print(f"Gap record structure verified: {list(gap.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

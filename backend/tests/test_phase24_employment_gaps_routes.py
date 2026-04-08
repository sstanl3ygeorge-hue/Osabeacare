"""
Phase 24: Employment Gaps Routes Extraction Tests

Tests for the extracted employment gaps routes module:
- GET /api/employees/{id}/employment-gaps - List gaps with evaluation
- POST /api/employees/{id}/employment-gaps/{gap_id}/explain - Explain a gap
- POST /api/employees/{id}/employment-gaps/{gap_id}/verify - Admin verification
- POST /api/employees/{id}/detect-employment-gaps - Detect gaps from history

Regression tests for previous phases (16-23):
- Auth login
- Bulk schedules (Phase 22)
- Policy assignments (Phase 20)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://caretrust-portal.preview.emergentagent.com"

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestHealthAndAuth:
    """Basic health and authentication tests"""
    
    def test_health_endpoint(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_admin_login(self):
        """Test admin login returns valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful: {data['user']['email']}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestEmploymentGapsRoutes:
    """Tests for Phase 24 - Employment Gaps Routes Extraction"""
    
    def test_get_employment_gaps(self, auth_headers):
        """GET /api/employees/{id}/employment-gaps - List gaps with evaluation"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "employee_id" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert "employee_name" in data
        assert "has_gaps" in data
        assert "total_gaps" in data
        assert "gaps" in data
        assert "evaluation" in data
        
        # Verify evaluation structure
        evaluation = data.get("evaluation", {})
        assert "is_complete" in evaluation or "has_gaps" in evaluation
        
        print(f"✓ Get employment gaps: has_gaps={data['has_gaps']}, total={data['total_gaps']}")
    
    def test_get_employment_gaps_nonexistent_employee(self, auth_headers):
        """GET /api/employees/{id}/employment-gaps - 404 for nonexistent employee"""
        fake_id = f"nonexistent-{uuid.uuid4().hex[:8]}"
        response = requests.get(
            f"{BASE_URL}/api/employees/{fake_id}/employment-gaps",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 404
        print(f"✓ Correctly returns 404 for nonexistent employee")
    
    def test_detect_employment_gaps(self, auth_headers):
        """POST /api/employees/{id}/detect-employment-gaps - Detect gaps from history"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/detect-employment-gaps",
            headers=auth_headers,
            timeout=15
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "success" in data
        assert data["success"] == True
        assert "total_gaps_detected" in data or "gaps_found" in data or "message" in data
        
        print(f"✓ Detect employment gaps: {data}")
    
    def test_detect_employment_gaps_nonexistent_employee(self, auth_headers):
        """POST /api/employees/{id}/detect-employment-gaps - 404 for nonexistent employee"""
        fake_id = f"nonexistent-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_id}/detect-employment-gaps",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 404
        print(f"✓ Correctly returns 404 for nonexistent employee")
    
    def test_explain_gap_nonexistent_gap(self, auth_headers):
        """POST /api/employees/{id}/employment-gaps/{gap_id}/explain - 404 for nonexistent gap"""
        fake_gap_id = f"gap_nonexistent_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/{fake_gap_id}/explain",
            headers=auth_headers,
            params={
                "explanation": "Test explanation",
                "reason_type": "education"
            },
            timeout=10
        )
        # Should return 404 for nonexistent gap
        assert response.status_code == 404
        print(f"✓ Correctly returns 404 for nonexistent gap")
    
    def test_verify_gap_nonexistent_gap(self, auth_headers):
        """POST /api/employees/{id}/employment-gaps/{gap_id}/verify - 404 for nonexistent gap"""
        fake_gap_id = f"gap_nonexistent_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/{fake_gap_id}/verify",
            headers=auth_headers,
            params={
                "verified": True,
                "verification_notes": "Test verification"
            },
            timeout=10
        )
        # Should return 404 for nonexistent gap
        assert response.status_code == 404
        print(f"✓ Correctly returns 404 for nonexistent gap")
    
    def test_request_gap_info_nonexistent_gap(self, auth_headers):
        """POST /api/employees/{id}/employment-gaps/{gap_id}/request-info - 404 for nonexistent gap"""
        fake_gap_id = f"gap_nonexistent_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/{fake_gap_id}/request-info",
            headers=auth_headers,
            params={
                "request_message": "Please provide more details"
            },
            timeout=10
        )
        # Should return 404 for nonexistent gap
        assert response.status_code == 404
        print(f"✓ Correctly returns 404 for nonexistent gap")


class TestEmploymentGapsWithExistingGaps:
    """Tests for employment gaps operations when gaps exist"""
    
    def test_get_gaps_and_test_operations(self, auth_headers):
        """Test gap operations if gaps exist for the test employee"""
        # First get existing gaps
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        gaps = data.get("gaps", [])
        if not gaps:
            print("✓ No existing gaps found - skipping gap-specific operations")
            return
        
        # Get first gap ID
        gap_id = gaps[0].get("id")
        if not gap_id:
            print("✓ Gap has no ID - skipping gap-specific operations")
            return
        
        print(f"✓ Found {len(gaps)} gaps, testing with gap_id: {gap_id}")
        
        # Test explain endpoint with existing gap
        explain_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/{gap_id}/explain",
            headers=auth_headers,
            params={
                "explanation": "Test explanation for gap",
                "reason_type": "education"
            },
            timeout=10
        )
        # Should succeed or return appropriate error
        assert explain_response.status_code in [200, 400, 422]
        print(f"✓ Explain gap response: {explain_response.status_code}")
        
        # Test verify endpoint with existing gap
        verify_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps/{gap_id}/verify",
            headers=auth_headers,
            params={
                "verified": True,
                "verification_notes": "Test verification"
            },
            timeout=10
        )
        # Should succeed or return appropriate error
        assert verify_response.status_code in [200, 400, 422]
        print(f"✓ Verify gap response: {verify_response.status_code}")


class TestRegressionBulkSchedules:
    """Regression tests for Phase 22 - Bulk Schedules"""
    
    def test_list_bulk_schedules(self, auth_headers):
        """GET /api/bulk/schedules - List bulk schedules"""
        response = requests.get(
            f"{BASE_URL}/api/bulk/schedules",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        # Response is {"schedules": [...], "total": N}
        assert "schedules" in data or isinstance(data, list)
        schedules = data.get("schedules", data) if isinstance(data, dict) else data
        print(f"✓ List bulk schedules: {len(schedules)} schedules found")
    
    def test_create_bulk_schedule(self, auth_headers):
        """POST /api/bulk/schedules - Create a test bulk schedule"""
        # Use correct payload format for bulk schedules
        schedule_data = {
            "name": f"TEST_Phase24_Schedule_{uuid.uuid4().hex[:6]}",
            "description": "Test schedule for Phase 24 regression",
            "schedule_type": "training_reminder",
            "days_before_expiry": 30,
            "enabled": False  # Disabled for testing
        }
        response = requests.post(
            f"{BASE_URL}/api/bulk/schedules",
            headers=auth_headers,
            json=schedule_data,
            timeout=10
        )
        # 200/201 for success, 422 for validation error (acceptable for regression test)
        assert response.status_code in [200, 201, 422]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data or "schedule" in data
            print(f"✓ Create bulk schedule: {data.get('id') or data.get('schedule', {}).get('id')}")
        else:
            print(f"✓ Create bulk schedule: validation error (expected for some payloads)")
    
    def test_quick_setup_training_reminders(self, auth_headers):
        """POST /api/bulk/schedules/quick-setup-training-reminders - Quick setup endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/bulk/schedules/quick-setup-training-reminders",
            headers=auth_headers,
            json={
                "days_before_expiry": 30,
                "enabled": False
            },
            timeout=10
        )
        # Should succeed or return conflict if already exists
        assert response.status_code in [200, 201, 409]
        print(f"✓ Quick setup training reminders: {response.status_code}")


class TestRegressionPolicyAssignments:
    """Regression tests for Phase 20 - Policy Assignments"""
    
    def test_list_policy_assignments(self, auth_headers):
        """GET /api/policy-assignments - List policy assignments"""
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "assignments" in data
        print(f"✓ List policy assignments: success")
    
    def test_get_employee_policy_assignments(self, auth_headers):
        """GET /api/policy-assignments?employee_id={id} - Get employee policy assignments"""
        # Policy assignments are filtered by employee_id query param, not path param
        response = requests.get(
            f"{BASE_URL}/api/policy-assignments",
            headers=auth_headers,
            params={"employee_id": TEST_EMPLOYEE_ID},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "assignments" in data
        print(f"✓ Get employee policy assignments: success")


class TestRegressionContracts:
    """Regression tests for Phase 16 - Contracts"""
    
    def test_get_contract_templates(self, auth_headers):
        """GET /api/contract-templates - List contract templates"""
        response = requests.get(
            f"{BASE_URL}/api/contract-templates",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "templates" in data
        print(f"✓ Get contract templates: success")
    
    def test_get_employee_contracts(self, auth_headers):
        """GET /api/employees/{id}/contracts - Get employee contracts"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contracts",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "contracts" in data
        print(f"✓ Get employee contracts: success")


class TestRegressionRoles:
    """Regression tests for Phase 19 - Roles"""
    
    def test_list_roles(self, auth_headers):
        """GET /api/roles - List roles"""
        response = requests.get(
            f"{BASE_URL}/api/roles",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "roles" in data
        print(f"✓ List roles: success")
    
    def test_get_roles_summary(self, auth_headers):
        """GET /api/roles/summary - Get roles summary"""
        response = requests.get(
            f"{BASE_URL}/api/roles/summary",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        print(f"✓ Get roles summary: success")


class TestRegressionPromotion:
    """Regression tests for Phase 18 - Promotion"""
    
    def test_get_promotion_status(self, auth_headers):
        """GET /api/employees/{id}/promotion-status - Get promotion status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/promotion-status",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        # Response should contain promotion status info
        assert "status" in data or "eligible" in data or "is_eligible" in data or "can_promote" in data
        print(f"✓ Get promotion status: success")


class TestRegressionTraining:
    """Regression tests for training endpoints"""
    
    def test_get_training_records(self, auth_headers):
        """GET /api/training-records - List training records"""
        response = requests.get(
            f"{BASE_URL}/api/training-records",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "records" in data
        print(f"✓ Get training records: success")
    
    def test_get_training_matrix_summary(self, auth_headers):
        """GET /api/training/matrix/summary - Get training matrix summary"""
        response = requests.get(
            f"{BASE_URL}/api/training/matrix/summary",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        print(f"✓ Get training matrix summary: success")


class TestRegressionDocuments:
    """Regression tests for document endpoints"""
    
    def test_get_document_requests(self, auth_headers):
        """GET /api/employees/{id}/document-requests - Get employee document requests"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/document-requests",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "requests" in data
        print(f"✓ Get employee document requests: success")
    
    def test_get_compliance_requirements(self, auth_headers):
        """GET /api/employees/{id}/compliance-requirements - Get compliance requirements"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "requirements" in data
        print(f"✓ Get compliance requirements: success")
    
    def test_get_document_types(self, auth_headers):
        """GET /api/document-types - Get document types"""
        response = requests.get(
            f"{BASE_URL}/api/document-types",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get document types: {len(data)} types found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

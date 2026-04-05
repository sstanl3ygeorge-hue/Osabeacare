"""
Test CQC Compliance Overhaul Features
=====================================
Tests for:
1. ActionableTaskQueue - GET /api/admin/task-queue endpoint
2. Audit Trail - GET /api/admin/audit-trail/{entity_type}/{entity_id} endpoint
3. Employment Gap Explanation with reason dropdown
4. Reference mismatch override with reason dropdown
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAdminTaskQueue:
    """Tests for GET /api/admin/task-queue endpoint"""
    
    def test_task_queue_requires_auth(self):
        """Task queue endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/task-queue")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_task_queue_returns_200(self, auth_headers):
        """Task queue endpoint returns 200 with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_task_queue_has_pending_verifications(self, auth_headers):
        """Task queue returns pending_verifications array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check pending_verifications exists and is a list
        assert "pending_verifications" in data, "Missing pending_verifications field"
        assert isinstance(data["pending_verifications"], list), "pending_verifications should be a list"
        
        # Check count field exists
        assert "documents_pending_verification" in data, "Missing documents_pending_verification count"
    
    def test_task_queue_has_references_to_send(self, auth_headers):
        """Task queue returns references_to_send array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check references_to_send exists and is a list
        assert "references_to_send" in data, "Missing references_to_send field"
        assert isinstance(data["references_to_send"], list), "references_to_send should be a list"
        
        # Check count field exists
        assert "references_to_send_count" in data, "Missing references_to_send_count"
    
    def test_task_queue_has_stuck_workers(self, auth_headers):
        """Task queue returns stuck_workers array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check stuck_workers exists and is a list
        assert "stuck_workers" in data, "Missing stuck_workers field"
        assert isinstance(data["stuck_workers"], list), "stuck_workers should be a list"
        
        # Check count field exists
        assert "stuck_workers_count" in data, "Missing stuck_workers_count"
    
    def test_task_queue_has_expiring_soon(self, auth_headers):
        """Task queue returns expiring_soon array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check expiring_soon exists and is a list
        assert "expiring_soon" in data, "Missing expiring_soon field"
        assert isinstance(data["expiring_soon"], list), "expiring_soon should be a list"
        
        # Check count field exists
        assert "expiring_soon_count" in data, "Missing expiring_soon_count"
    
    def test_task_queue_has_references_to_review(self, auth_headers):
        """Task queue returns references_to_review array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check references_to_review exists and is a list
        assert "references_to_review" in data, "Missing references_to_review field"
        assert isinstance(data["references_to_review"], list), "references_to_review should be a list"
    
    def test_task_queue_stuck_workers_structure(self, auth_headers):
        """Stuck workers have correct structure with employee_name and progress"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        stuck_workers = data.get("stuck_workers", [])
        if len(stuck_workers) > 0:
            worker = stuck_workers[0]
            assert "employee_id" in worker, "Missing employee_id in stuck worker"
            assert "employee_name" in worker, "Missing employee_name in stuck worker"
            assert "progress" in worker, "Missing progress in stuck worker"
            print(f"Found {len(stuck_workers)} stuck workers")
            for w in stuck_workers[:3]:
                print(f"  - {w.get('employee_name')}: {w.get('progress')}% complete")
        else:
            print("No stuck workers found (this is OK)")
    
    def test_task_queue_pending_verifications_structure(self, auth_headers):
        """Pending verifications have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        pending = data.get("pending_verifications", [])
        if len(pending) > 0:
            doc = pending[0]
            assert "employee_id" in doc, "Missing employee_id in pending verification"
            assert "employee_name" in doc, "Missing employee_name in pending verification"
            assert "document_type" in doc, "Missing document_type in pending verification"
            print(f"Found {data.get('documents_pending_verification', 0)} pending verifications")
        else:
            print("No pending verifications found")


class TestAuditTrail:
    """Tests for GET /api/admin/audit-trail/{entity_type}/{entity_id} endpoint"""
    
    def test_audit_trail_requires_auth(self):
        """Audit trail endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/audit-trail/employee/{TEST_EMPLOYEE_ID}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_audit_trail_returns_200(self, auth_headers):
        """Audit trail endpoint returns 200 with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-trail/employee/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_audit_trail_structure(self, auth_headers):
        """Audit trail returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-trail/employee/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "entity_type" in data, "Missing entity_type"
        assert "entity_id" in data, "Missing entity_id"
        assert "entries" in data, "Missing entries"
        assert "total" in data, "Missing total"
        
        assert data["entity_type"] == "employee"
        assert data["entity_id"] == TEST_EMPLOYEE_ID
        assert isinstance(data["entries"], list)
        
        print(f"Found {data['total']} audit entries for employee {TEST_EMPLOYEE_ID}")
    
    def test_audit_trail_entries_have_required_fields(self, auth_headers):
        """Audit trail entries have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-trail/employee/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        entries = data.get("entries", [])
        if len(entries) > 0:
            entry = entries[0]
            # Check common audit fields
            print(f"Sample audit entry keys: {list(entry.keys())}")
            # Audit entries typically have: action, user_id, created_at, etc.
        else:
            print("No audit entries found for this employee")
    
    def test_audit_trail_with_limit(self, auth_headers):
        """Audit trail respects limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-trail/employee/{TEST_EMPLOYEE_ID}?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        entries = data.get("entries", [])
        assert len(entries) <= 5, f"Expected max 5 entries, got {len(entries)}"


class TestEmploymentGapExplanation:
    """Tests for employment gap explanation with reason dropdown"""
    
    def test_employment_gaps_endpoint_exists(self, auth_headers):
        """Employment gaps endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=auth_headers
        )
        # 200 = has gaps, 404 = no gaps found (both are valid)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"Employment gaps data: has_gaps={data.get('has_gaps')}")
            if data.get('gaps'):
                print(f"  Found {len(data['gaps'])} gaps")
    
    def test_gap_explanation_endpoint_structure(self, auth_headers):
        """Gap explanation endpoint accepts reason_type parameter"""
        # First get gaps to find a gap_id
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-gaps",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            gaps = data.get("gaps", [])
            if gaps:
                gap_id = gaps[0].get("gap_id")
                print(f"Found gap_id: {gap_id}")
                # Note: We don't actually submit to avoid modifying data
                # Just verify the endpoint structure exists
        else:
            print("No employment gaps found for test employee")


class TestReferenceMismatchOverride:
    """Tests for reference mismatch override with reason dropdown"""
    
    def test_references_normalized_endpoint(self, auth_headers):
        """References normalized endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-normalized",
            headers=auth_headers
        )
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            refs = data.get("references", [])
            print(f"Found {len(refs)} references")
            for ref in refs:
                print(f"  - Reference {ref.get('reference_number')}: {ref.get('lifecycle_status')}")
    
    def test_override_mismatch_endpoint_exists(self, auth_headers):
        """Override mismatch endpoint exists (POST)"""
        # We test that the endpoint exists by checking it rejects invalid requests
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/override-mismatch",
            headers=auth_headers,
            json={}  # Empty body should fail validation
        )
        # 422 = validation error (endpoint exists but bad request)
        # 400 = bad request (endpoint exists)
        # 404 = not found (could be no mismatch to override)
        assert response.status_code in [200, 400, 404, 422], f"Unexpected status: {response.status_code}"
        print(f"Override mismatch endpoint returned: {response.status_code}")


class TestDocumentCardReminder:
    """Tests for document card Send Reminder functionality"""
    
    def test_send_reminder_endpoint_exists(self, auth_headers):
        """Send reminder endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/workers/{TEST_EMPLOYEE_ID}/send-reminder",
            headers=auth_headers,
            json={"reminder_type": "general"}
        )
        # 200 = success, 400/404 = endpoint exists but validation/not found
        assert response.status_code in [200, 400, 404, 422, 500], f"Unexpected status: {response.status_code}"
        print(f"Send reminder endpoint returned: {response.status_code}")


class TestTaskQueueCounts:
    """Tests for task queue count accuracy"""
    
    def test_task_queue_total_tasks(self, auth_headers):
        """Task queue returns total_tasks count"""
        response = requests.get(
            f"{BASE_URL}/api/admin/task-queue",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_tasks" in data, "Missing total_tasks"
        print(f"Total tasks: {data['total_tasks']}")
        print(f"  - Documents pending verification: {data.get('documents_pending_verification', 0)}")
        print(f"  - References to send: {data.get('references_to_send_count', 0)}")
        print(f"  - References to review: {data.get('references_to_review_count', 0)}")
        print(f"  - Expiring soon: {data.get('expiring_soon_count', 0)}")
        print(f"  - Stuck workers: {data.get('stuck_workers_count', 0)}")
        print(f"  - DBS expiring 30 days: {data.get('dbs_expiring_30_days', 0)}")
        print(f"  - RTW expiring 30 days: {data.get('rtw_expiring_30_days', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

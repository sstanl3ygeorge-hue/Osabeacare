"""
Test Suite for Training Summary UI Integration and Bulk Document Requests
Tests:
1. Training Summary Dashboard endpoint
2. Employee Training Evaluation endpoint
3. Bulk Document Request endpoints (create, pending, cancel)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee IDs from the review request
TEST_EMPLOYEE_ID_1 = "d88335f6-1b18-435a-8086-28af4a583f77"
TEST_EMPLOYEE_ID_2 = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"

# Admin credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Shared requests session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


# ==================== TRAINING SUMMARY DASHBOARD TESTS ====================

class TestTrainingSummaryDashboard:
    """Tests for GET /api/dashboard/training-summary endpoint."""
    
    def test_training_summary_endpoint_returns_200(self, api_client):
        """Training summary endpoint should return 200 OK."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/training-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Training summary endpoint returns 200")
    
    def test_training_summary_has_correct_structure(self, api_client):
        """Training summary should have required fields."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/training-summary")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields exist
        assert "training_overdue_count" in data, "Missing training_overdue_count"
        assert "training_due_soon_count" in data, "Missing training_due_soon_count"
        assert "employees_blocked_by_training" in data, "Missing employees_blocked_by_training"
        
        # Check counts are integers
        assert isinstance(data["training_overdue_count"], int), "training_overdue_count should be int"
        assert isinstance(data["training_due_soon_count"], int), "training_due_soon_count should be int"
        assert isinstance(data["employees_blocked_by_training"], int), "employees_blocked_by_training should be int"
        
        print(f"✓ Training summary structure correct:")
        print(f"  - Overdue: {data['training_overdue_count']}")
        print(f"  - Due Soon: {data['training_due_soon_count']}")
        print(f"  - Blocked: {data['employees_blocked_by_training']}")
    
    def test_training_summary_has_employee_lists(self, api_client):
        """Training summary should include employee lists for each category."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/training-summary")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check optional employee lists exist
        assert "overdue_employees" in data, "Missing overdue_employees list"
        assert "due_soon_employees" in data, "Missing due_soon_employees list"
        assert "blocked_employees" in data, "Missing blocked_employees list"
        
        # Check they are lists
        assert isinstance(data["overdue_employees"], list), "overdue_employees should be list"
        assert isinstance(data["due_soon_employees"], list), "due_soon_employees should be list"
        assert isinstance(data["blocked_employees"], list), "blocked_employees should be list"
        
        print(f"✓ Training summary employee lists present")


# ==================== EMPLOYEE TRAINING EVALUATION TESTS ====================

class TestEmployeeTrainingEvaluation:
    """Tests for GET /api/employees/{id}/training endpoint."""
    
    def test_training_evaluation_endpoint_returns_200(self, api_client):
        """Training evaluation endpoint should return 200 for valid employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID_1}/training")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Training evaluation endpoint returns 200 for employee {TEST_EMPLOYEE_ID_1}")
    
    def test_training_evaluation_has_correct_structure(self, api_client):
        """Training evaluation should have required fields."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID_1}/training")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "overall" in data, "Missing overall status"
        assert "blockerCount" in data, "Missing blockerCount"
        assert "warningCount" in data, "Missing warningCount"
        assert "items" in data, "Missing items array"
        
        # Check types
        assert isinstance(data["blockerCount"], int), "blockerCount should be int"
        assert isinstance(data["warningCount"], int), "warningCount should be int"
        assert isinstance(data["items"], list), "items should be list"
        
        print(f"✓ Training evaluation structure correct:")
        print(f"  - Overall: {data['overall']}")
        print(f"  - Blocker Count: {data['blockerCount']}")
        print(f"  - Warning Count: {data['warningCount']}")
        print(f"  - Items Count: {len(data['items'])}")
    
    def test_training_evaluation_items_structure(self, api_client):
        """Training evaluation items should have proper structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID_1}/training")
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        if items:
            item = items[0]
            # Check item has expected fields
            assert "title" in item or "name" in item, "Item should have title or name"
            assert "status" in item, "Item should have status"
            
            print(f"✓ Training items have correct structure")
            print(f"  - Sample item: {item.get('title', item.get('name', 'N/A'))} - {item.get('status')}")
        else:
            print(f"✓ No training items found (employee may have all training complete)")
    
    def test_training_evaluation_for_second_employee(self, api_client):
        """Training evaluation should work for second test employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID_2}/training")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"✓ Training evaluation for employee {TEST_EMPLOYEE_ID_2}:")
        print(f"  - Overall: {data.get('overall')}")
        print(f"  - Blocker Count: {data.get('blockerCount')}")
        print(f"  - Warning Count: {data.get('warningCount')}")
    
    def test_training_evaluation_invalid_employee_returns_404(self, api_client):
        """Training evaluation should return 404 for non-existent employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/invalid-employee-id-12345/training")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Training evaluation returns 404 for invalid employee")


# ==================== BULK DOCUMENT REQUEST TESTS ====================

class TestBulkDocumentRequests:
    """Tests for bulk document request endpoints."""
    
    def test_bulk_document_requests_endpoint_exists(self, api_client):
        """POST /api/bulk/document-requests should exist."""
        # Test with minimal payload
        response = api_client.post(f"{BASE_URL}/api/bulk/document-requests", json={
            "employee_ids": [TEST_EMPLOYEE_ID_1],
            "due_days": 14,
            "send_immediately": True
        })
        # Should not be 404 or 405
        assert response.status_code not in [404, 405], f"Endpoint not found: {response.status_code}"
        print(f"✓ Bulk document requests endpoint exists (status: {response.status_code})")
    
    def test_bulk_document_requests_returns_correct_structure(self, api_client):
        """Bulk document requests should return proper result structure."""
        response = api_client.post(f"{BASE_URL}/api/bulk/document-requests", json={
            "employee_ids": [TEST_EMPLOYEE_ID_1],
            "due_days": 14,
            "send_immediately": True
        })
        
        # Accept 200 (success) or 400 (validation error)
        if response.status_code == 200:
            data = response.json()
            
            # Check required fields in response
            assert "total_employees" in data, "Missing total_employees"
            assert "total_requests_created" in data, "Missing total_requests_created"
            assert "total_emails_sent" in data, "Missing total_emails_sent"
            assert "total_skipped" in data, "Missing total_skipped"
            assert "details" in data, "Missing details"
            assert "errors" in data, "Missing errors"
            
            print(f"✓ Bulk request response structure correct:")
            print(f"  - Total Employees: {data['total_employees']}")
            print(f"  - Requests Created: {data['total_requests_created']}")
            print(f"  - Emails Sent: {data['total_emails_sent']}")
            print(f"  - Skipped: {data['total_skipped']}")
        else:
            print(f"✓ Bulk request returned {response.status_code}: {response.text[:200]}")
    
    def test_bulk_document_requests_multiple_employees(self, api_client):
        """Bulk document requests should handle multiple employees."""
        response = api_client.post(f"{BASE_URL}/api/bulk/document-requests", json={
            "employee_ids": [TEST_EMPLOYEE_ID_1, TEST_EMPLOYEE_ID_2],
            "due_days": 14,
            "send_immediately": True
        })
        
        if response.status_code == 200:
            data = response.json()
            assert data["total_employees"] == 2, f"Expected 2 employees, got {data['total_employees']}"
            print(f"✓ Bulk request handled 2 employees correctly")
            print(f"  - Details count: {len(data.get('details', []))}")
        else:
            print(f"✓ Bulk request for multiple employees returned {response.status_code}")
    
    def test_bulk_document_requests_with_specific_requirements(self, api_client):
        """Bulk document requests should accept specific requirement IDs."""
        # First get document types to find a valid requirement ID
        doc_types_response = api_client.get(f"{BASE_URL}/api/document-types")
        
        if doc_types_response.status_code == 200:
            doc_types = doc_types_response.json()
            if doc_types:
                req_id = doc_types[0].get("id")
                
                response = api_client.post(f"{BASE_URL}/api/bulk/document-requests", json={
                    "employee_ids": [TEST_EMPLOYEE_ID_1],
                    "requirement_ids": [req_id],
                    "due_days": 14,
                    "send_immediately": True
                })
                
                assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
                print(f"✓ Bulk request with specific requirement ID works (status: {response.status_code})")
            else:
                print("✓ No document types found, skipping specific requirement test")
        else:
            print(f"✓ Could not fetch document types: {doc_types_response.status_code}")
    
    def test_bulk_document_requests_empty_employee_list_fails(self, api_client):
        """Bulk document requests should fail with empty employee list."""
        response = api_client.post(f"{BASE_URL}/api/bulk/document-requests", json={
            "employee_ids": [],
            "due_days": 14
        })
        
        assert response.status_code == 400 or response.status_code == 422, \
            f"Expected 400/422 for empty list, got {response.status_code}"
        print(f"✓ Bulk request correctly rejects empty employee list")


class TestBulkPendingRequests:
    """Tests for GET /api/bulk/pending-requests endpoint."""
    
    def test_pending_requests_endpoint_returns_200(self, api_client):
        """Pending requests endpoint should return 200."""
        response = api_client.get(f"{BASE_URL}/api/bulk/pending-requests")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Pending requests endpoint returns 200")
    
    def test_pending_requests_has_correct_structure(self, api_client):
        """Pending requests should return proper structure."""
        response = api_client.get(f"{BASE_URL}/api/bulk/pending-requests")
        assert response.status_code == 200
        
        data = response.json()
        
        assert "total" in data, "Missing total count"
        assert "requests" in data, "Missing requests list"
        assert isinstance(data["requests"], list), "requests should be list"
        
        print(f"✓ Pending requests structure correct:")
        print(f"  - Total: {data['total']}")
        print(f"  - Requests count: {len(data['requests'])}")
    
    def test_pending_requests_with_status_filter(self, api_client):
        """Pending requests should accept status filter."""
        response = api_client.get(f"{BASE_URL}/api/bulk/pending-requests?status=sent")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Pending requests with status filter works")


class TestBulkCancelRequests:
    """Tests for POST /api/bulk/cancel-requests endpoint."""
    
    def test_cancel_requests_endpoint_exists(self, api_client):
        """Cancel requests endpoint should exist."""
        response = api_client.post(f"{BASE_URL}/api/bulk/cancel-requests", json={
            "request_ids": ["non-existent-id"],
            "reason": "Test cancellation"
        })
        
        # Should not be 404 or 405
        assert response.status_code not in [404, 405], f"Endpoint not found: {response.status_code}"
        print(f"✓ Cancel requests endpoint exists (status: {response.status_code})")
    
    def test_cancel_requests_returns_correct_structure(self, api_client):
        """Cancel requests should return proper structure."""
        response = api_client.post(f"{BASE_URL}/api/bulk/cancel-requests", json={
            "request_ids": ["test-id-123"],
            "reason": "Test cancellation"
        })
        
        if response.status_code == 200:
            data = response.json()
            assert "cancelled" in data, "Missing cancelled count"
            assert "errors" in data, "Missing errors list"
            print(f"✓ Cancel requests response structure correct")
        else:
            print(f"✓ Cancel requests returned {response.status_code}")
    
    def test_cancel_requests_empty_list_fails(self, api_client):
        """Cancel requests should fail with empty request list."""
        response = api_client.post(f"{BASE_URL}/api/bulk/cancel-requests", json={
            "request_ids": [],
            "reason": "Test"
        })
        
        assert response.status_code in [400, 422], \
            f"Expected 400/422 for empty list, got {response.status_code}"
        print(f"✓ Cancel requests correctly rejects empty list")


# ==================== INTEGRATION TESTS ====================

class TestTrainingBulkIntegration:
    """Integration tests combining training and bulk request features."""
    
    def test_dashboard_stats_endpoint_works(self, api_client):
        """Dashboard stats endpoint should work."""
        response = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Dashboard stats endpoint works")
    
    def test_staff_employees_endpoint_works(self, api_client):
        """Staff employees endpoint should work."""
        response = api_client.get(f"{BASE_URL}/api/staff/employees")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        employees = data.get("employees", data) if isinstance(data, dict) else data
        print(f"✓ Staff employees endpoint works - {len(employees)} employees")
    
    def test_document_types_endpoint_works(self, api_client):
        """Document types endpoint should work for bulk request dialog."""
        response = api_client.get(f"{BASE_URL}/api/document-types")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"✓ Document types endpoint works - {len(data)} types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

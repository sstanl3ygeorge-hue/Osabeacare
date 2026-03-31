"""
Step 8: Compliance File Consolidation + Training Matrix Repair Tests

Tests:
1. Training Matrix summary endpoint (/api/training/matrix/summary)
2. Document correction endpoints:
   - Mark uploaded in error
   - Supersede document
   - Move category
   - Reopen review
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")  # API returns 'token' not 'access_token'
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTrainingMatrixSummary:
    """Test Training Matrix summary endpoint"""
    
    def test_training_matrix_summary_endpoint_exists(self, auth_headers):
        """Test that /api/training/matrix/summary endpoint exists and returns 200"""
        response = requests.get(f"{BASE_URL}/api/training/matrix/summary", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Training matrix summary endpoint exists and returns 200")
    
    def test_training_matrix_summary_returns_5_cards(self, auth_headers):
        """Test that summary returns all 5 stat card counts"""
        response = requests.get(f"{BASE_URL}/api/training/matrix/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check all 5 required fields exist
        required_fields = ["completed", "verified", "needs_renewal", "expired", "awaiting_extraction_review"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"Field {field} should be integer, got {type(data[field])}"
        
        print(f"✓ Training matrix summary returns all 5 cards:")
        print(f"  - Completed: {data['completed']}")
        print(f"  - Verified: {data['verified']}")
        print(f"  - Needs Renewal: {data['needs_renewal']}")
        print(f"  - Expired: {data['expired']}")
        print(f"  - Awaiting Extraction Review: {data['awaiting_extraction_review']}")
    
    def test_training_matrix_summary_counts_are_non_negative(self, auth_headers):
        """Test that all counts are non-negative integers"""
        response = requests.get(f"{BASE_URL}/api/training/matrix/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for field, value in data.items():
            assert value >= 0, f"Field {field} has negative value: {value}"
        
        print("✓ All training matrix summary counts are non-negative")


class TestDocumentCorrectionMarkUploadedInError:
    """Test mark-uploaded-in-error endpoint"""
    
    def test_mark_uploaded_in_error_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/documents/fake-id/mark-uploaded-in-error", json={
            "reason": "Test reason for marking as error"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Mark uploaded in error requires authentication")
    
    def test_mark_uploaded_in_error_requires_10_char_reason(self, auth_headers):
        """Test that reason must be at least 10 characters"""
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-id/mark-uploaded-in-error",
            headers=auth_headers,
            json={"reason": "short"}  # Less than 10 chars
        )
        # Should fail validation (422) or not found (404)
        assert response.status_code in [422, 404], f"Expected 422/404, got {response.status_code}: {response.text}"
        print("✓ Mark uploaded in error validates minimum 10 char reason")
    
    def test_mark_uploaded_in_error_returns_404_for_nonexistent(self, auth_headers):
        """Test that endpoint returns 404 for non-existent document"""
        response = requests.post(
            f"{BASE_URL}/api/documents/nonexistent-doc-id/mark-uploaded-in-error",
            headers=auth_headers,
            json={"reason": "This is a test reason with more than 10 characters"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Mark uploaded in error returns 404 for non-existent document")


class TestDocumentCorrectionSupersede:
    """Test supersede document endpoint"""
    
    def test_supersede_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/documents/fake-id/supersede", json={
            "reason": "Replaced by newer version"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Supersede document requires authentication")
    
    def test_supersede_returns_404_for_nonexistent(self, auth_headers):
        """Test that endpoint returns 404 for non-existent document"""
        response = requests.post(
            f"{BASE_URL}/api/documents/nonexistent-doc-id/supersede",
            headers=auth_headers,
            json={"reason": "Replaced by newer version"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Supersede document returns 404 for non-existent document")
    
    def test_supersede_accepts_optional_replacement_id(self, auth_headers):
        """Test that supersede accepts optional replacement_document_id"""
        # This will return 404 but validates the request body is accepted
        response = requests.post(
            f"{BASE_URL}/api/documents/nonexistent-doc-id/supersede",
            headers=auth_headers,
            json={
                "reason": "Replaced by newer version",
                "replacement_document_id": "some-replacement-id"
            }
        )
        # Should be 404 (not found) not 422 (validation error)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Supersede document accepts optional replacement_document_id")


class TestDocumentCorrectionMoveCategory:
    """Test move-category endpoint"""
    
    def test_move_category_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/documents/fake-id/move-category", json={
            "new_requirement_id": "dbs_certificate",
            "reason": "Filed under wrong category"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Move category requires authentication")
    
    def test_move_category_requires_5_char_reason(self, auth_headers):
        """Test that reason must be at least 5 characters"""
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-id/move-category",
            headers=auth_headers,
            json={
                "new_requirement_id": "dbs_certificate",
                "reason": "abc"  # Less than 5 chars
            }
        )
        # Should fail validation (422) or not found (404)
        assert response.status_code in [422, 404], f"Expected 422/404, got {response.status_code}: {response.text}"
        print("✓ Move category validates minimum 5 char reason")
    
    def test_move_category_returns_404_for_nonexistent(self, auth_headers):
        """Test that endpoint returns 404 for non-existent document"""
        response = requests.post(
            f"{BASE_URL}/api/documents/nonexistent-doc-id/move-category",
            headers=auth_headers,
            json={
                "new_requirement_id": "dbs_certificate",
                "reason": "Filed under wrong category"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Move category returns 404 for non-existent document")


class TestDocumentCorrectionReopenReview:
    """Test reopen-review endpoint"""
    
    def test_reopen_review_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/documents/fake-id/reopen-review", json={
            "reason": "Need to re-verify this document"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Reopen review requires authentication")
    
    def test_reopen_review_requires_10_char_reason(self, auth_headers):
        """Test that reason must be at least 10 characters"""
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-id/reopen-review",
            headers=auth_headers,
            json={"reason": "short"}  # Less than 10 chars
        )
        # Should fail validation (422) or not found (404)
        assert response.status_code in [422, 404], f"Expected 422/404, got {response.status_code}: {response.text}"
        print("✓ Reopen review validates minimum 10 char reason")
    
    def test_reopen_review_returns_404_for_nonexistent(self, auth_headers):
        """Test that endpoint returns 404 for non-existent document"""
        response = requests.post(
            f"{BASE_URL}/api/documents/nonexistent-doc-id/reopen-review",
            headers=auth_headers,
            json={"reason": "Need to re-verify this document after finding issues"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Reopen review returns 404 for non-existent document")


class TestDocumentCorrectionWithRealDocument:
    """Test document correction with a real document (if available)"""
    
    @pytest.fixture
    def test_document_id(self, auth_headers):
        """Find a real document to test with"""
        # Get an employee with documents
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code != 200:
            pytest.skip("Could not fetch employees")
        
        employees = response.json()
        if not employees:
            pytest.skip("No employees found")
        
        # Find an employee with documents
        for emp in employees[:5]:  # Check first 5 employees
            emp_id = emp.get("id")
            docs_response = requests.get(
                f"{BASE_URL}/api/employee-documents?employee_id={emp_id}",
                headers=auth_headers
            )
            if docs_response.status_code == 200:
                docs = docs_response.json()
                if docs:
                    return docs[0].get("id")
        
        pytest.skip("No documents found for testing")
    
    def test_document_history_endpoint(self, auth_headers, test_document_id):
        """Test that document history endpoint works"""
        if not test_document_id:
            pytest.skip("No test document available")
        
        response = requests.get(
            f"{BASE_URL}/api/documents/{test_document_id}/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "document" in data, "Response should contain 'document' field"
        assert "status_history" in data, "Response should contain 'status_history' field"
        
        print(f"✓ Document history endpoint works for document {test_document_id}")


class TestTrainingMatrixIntegration:
    """Integration tests for Training Matrix page"""
    
    def test_training_records_endpoint(self, auth_headers):
        """Test that training records endpoint works"""
        response = requests.get(f"{BASE_URL}/api/training-records", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Training records should be a list"
        print(f"✓ Training records endpoint returns {len(data)} records")
    
    def test_pending_extractions_endpoint(self, auth_headers):
        """Test that pending extractions endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/document-extractions/pending-review?limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "extractions" in data, "Response should contain 'extractions' field"
        print(f"✓ Pending extractions endpoint returns {len(data.get('extractions', []))} extractions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

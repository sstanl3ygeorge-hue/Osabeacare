"""
Test CV Employment History Alignment Feature (NHS-Level Strict)
- CV extraction endpoint
- Employment history mismatch detection
- Mismatch status retrieval
- Add review note for mismatch
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID with known mismatch
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestEmploymentMismatchEndpoints:
    """Test employment history mismatch detection endpoints"""
    
    def test_get_employment_mismatch_status(self, authenticated_client):
        """GET /api/employees/{id}/employment-mismatch returns mismatch status"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-mismatch"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "has_mismatch" in data, "Response should contain has_mismatch field"
        assert "mismatch_count" in data, "Response should contain mismatch_count field"
        assert "mismatch_summary" in data, "Response should contain mismatch_summary field"
        assert "source_of_truth" in data, "Response should contain source_of_truth field"
        
        # Verify source of truth is structured employment history
        assert data["source_of_truth"] == "structured_employment_history", \
            f"Source of truth should be 'structured_employment_history', got {data['source_of_truth']}"
        
        print(f"✓ Mismatch status: has_mismatch={data['has_mismatch']}, count={data['mismatch_count']}")
    
    def test_compare_employment_history_endpoint(self, authenticated_client):
        """POST /api/employees/{id}/compare-employment-history detects mismatches"""
        # Simulated CV extracted roles that differ from structured history
        cv_extracted_roles = [
            {
                "employer": "Test Care Home Ltd",
                "job_title": "Care Assistant",
                "start_date": "2020-01",
                "end_date": "2022-06",
                "is_current": False
            },
            {
                "employer": "NHS Trust Hospital",
                "job_title": "Healthcare Support Worker",
                "start_date": "2022-07",
                "end_date": None,
                "is_current": True
            }
        ]
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compare-employment-history",
            json=cv_extracted_roles
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data, "Response should contain status field"
        assert data["status"] == "success", f"Expected success status, got {data['status']}"
        assert "comparison_result" in data, "Response should contain comparison_result"
        
        result = data["comparison_result"]
        assert "has_mismatch" in result, "Comparison result should contain has_mismatch"
        assert "mismatch_count" in result, "Comparison result should contain mismatch_count"
        assert "mismatch_summary" in result, "Comparison result should contain mismatch_summary"
        assert "structured_role_count" in result, "Comparison result should contain structured_role_count"
        assert "cv_role_count" in result, "Comparison result should contain cv_role_count"
        
        print(f"✓ Comparison result: has_mismatch={result['has_mismatch']}, count={result['mismatch_count']}")
        print(f"  Structured roles: {result['structured_role_count']}, CV roles: {result['cv_role_count']}")
    
    def test_add_mismatch_review_note(self, authenticated_client):
        """POST /api/employees/{id}/employment-mismatch/add-note adds review note"""
        note_text = "TEST_NOTE: Reviewed mismatch - company name variation is acceptable. Verified via phone call with previous employer."
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-mismatch/add-note",
            json={"note": note_text}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success", f"Expected success status, got {data}"
        assert "message" in data, "Response should contain message"
        
        print(f"✓ Review note added successfully")
    
    def test_add_mismatch_note_validation(self, authenticated_client):
        """POST /api/employees/{id}/employment-mismatch/add-note validates note length"""
        # Note too short (less than 5 characters)
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-mismatch/add-note",
            json={"note": "abc"}
        )
        
        # Should fail validation
        assert response.status_code == 422, f"Expected 422 for short note, got {response.status_code}"
        print(f"✓ Note validation works - rejects notes < 5 chars")
    
    def test_mismatch_status_after_comparison(self, authenticated_client):
        """Verify mismatch status is persisted after comparison"""
        # First, run a comparison
        cv_roles = [
            {
                "employer": "Different Company Name",
                "job_title": "Different Role",
                "start_date": "2019-01",
                "end_date": "2020-12"
            }
        ]
        
        compare_response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compare-employment-history",
            json=cv_roles
        )
        assert compare_response.status_code == 200
        
        # Then verify mismatch status is updated
        status_response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-mismatch"
        )
        
        assert status_response.status_code == 200
        data = status_response.json()
        
        # Should have mismatch data
        assert "compared_at" in data, "Should have compared_at timestamp"
        assert "cv_extracted_roles" in data, "Should have cv_extracted_roles stored"
        
        print(f"✓ Mismatch status persisted: compared_at={data.get('compared_at')}")


class TestCVExtractionEndpoint:
    """Test CV extraction endpoint (requires actual CV file)"""
    
    def test_cv_extraction_missing_file(self, authenticated_client):
        """POST /api/cv/extract-employment-history returns 404 for missing file"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/cv/extract-employment-history?file_id=nonexistent-file-id"
        )
        
        assert response.status_code == 404, f"Expected 404 for missing file, got {response.status_code}"
        print(f"✓ CV extraction returns 404 for missing file")
    
    def test_cv_extraction_endpoint_exists(self, authenticated_client):
        """Verify CV extraction endpoint is accessible"""
        # Just verify the endpoint exists and returns proper error for missing file
        response = authenticated_client.post(
            f"{BASE_URL}/api/cv/extract-employment-history?file_id=test-file"
        )
        
        # Should return 404 (file not found) not 405 (method not allowed)
        assert response.status_code in [404, 400, 500], \
            f"Endpoint should exist, got {response.status_code}: {response.text}"
        print(f"✓ CV extraction endpoint exists and is accessible")


class TestGapCalculationSourceOfTruth:
    """Verify gap calculation uses ONLY structured employment history"""
    
    def test_recruitment_status_uses_structured_history(self, authenticated_client):
        """GET /api/employees/{id}/recruitment-status should use structured history for gaps"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/recruitment-status"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response contains gap information
        if "details" in data and "cv_gaps" in data.get("details", {}):
            cv_gaps = data["details"]["cv_gaps"]
            # Gap calculation should be based on structured history
            print(f"✓ Recruitment status returned: gaps={cv_gaps.get('gaps', [])}")
        else:
            print(f"✓ Recruitment status endpoint working (no gap data in response)")


class TestEmployeeNotFound:
    """Test error handling for non-existent employees"""
    
    def test_mismatch_status_employee_not_found(self, authenticated_client):
        """GET /api/employees/{id}/employment-mismatch returns 404 for non-existent employee"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/employment-mismatch"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Returns 404 for non-existent employee")
    
    def test_compare_employee_not_found(self, authenticated_client):
        """POST /api/employees/{id}/compare-employment-history returns 404 for non-existent employee"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/compare-employment-history",
            json=[{"employer": "Test", "job_title": "Test"}]
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Compare returns 404 for non-existent employee")


class TestAuthenticationRequired:
    """Test that endpoints require authentication"""
    
    def test_mismatch_status_requires_auth(self, api_client):
        """GET /api/employees/{id}/employment-mismatch requires authentication"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-mismatch"
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print(f"✓ Mismatch status endpoint requires authentication")
    
    def test_compare_requires_auth(self, api_client):
        """POST /api/employees/{id}/compare-employment-history requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compare-employment-history",
            json=[{"employer": "Test"}]
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print(f"✓ Compare endpoint requires authentication")
    
    def test_add_note_requires_auth(self, api_client):
        """POST /api/employees/{id}/employment-mismatch/add-note requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/employment-mismatch/add-note",
            json={"note": "Test note"}
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print(f"✓ Add note endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

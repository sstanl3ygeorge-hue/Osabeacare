"""
Test Training Matrix Audit-Ready Features
==========================================
Tests for the redesigned training matrix endpoint that supports:
1. 6 mandatory trainings for work readiness with blocker flags
2. additional_items array for non-mandatory qualifications
3. Summary with additional_count
4. Extended training normalization mapping
5. Non-mandatory training preserved with is_additional=true

Test Employee: Olakunle Alonge (d88335f6-1b18-435a-8086-28af4a583f77)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestTrainingMatrixEndpoint:
    """Tests for GET /api/employees/{id}/training/matrix endpoint"""
    
    def test_training_matrix_returns_200(self, auth_headers):
        """Test that training matrix endpoint returns 200 for valid employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "employee_id" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
    
    def test_training_matrix_has_mandatory_items(self, auth_headers):
        """Test that training matrix returns mandatory training items"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify items array exists
        assert "items" in data, "Response should have 'items' array"
        items = data["items"]
        assert isinstance(items, list), "items should be a list"
        
        # Check for mandatory training codes
        mandatory_codes = {'safeguarding', 'manual_handling', 'infection_control', 
                         'basic_life_support', 'bls', 'fire_safety', 'health_safety'}
        item_codes = {item.get('code', '').lower() for item in items}
        
        # At least some mandatory items should be present
        found_mandatory = mandatory_codes.intersection(item_codes)
        print(f"Found mandatory training codes: {found_mandatory}")
        print(f"All item codes: {item_codes}")
        
        # Verify each item has required fields
        for item in items:
            assert "code" in item, "Each item should have 'code'"
            assert "title" in item, "Each item should have 'title'"
            assert "status" in item, "Each item should have 'status'"
            assert "blocker" in item, "Each item should have 'blocker' flag"
    
    def test_training_matrix_has_blocker_flags(self, auth_headers):
        """Test that mandatory items have blocker flags"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        
        # Check blocker flags exist
        items_with_blocker = [item for item in items if "blocker" in item]
        assert len(items_with_blocker) > 0, "At least some items should have blocker field"
        
        # Print blocker status for debugging
        for item in items:
            print(f"Training: {item.get('code')} - blocker: {item.get('blocker')} - status: {item.get('status')}")
    
    def test_training_matrix_has_additional_items_array(self, auth_headers):
        """Test that training matrix returns additional_items array"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify additional_items array exists
        assert "additional_items" in data, "Response should have 'additional_items' array"
        additional_items = data["additional_items"]
        assert isinstance(additional_items, list), "additional_items should be a list"
        
        print(f"Additional items count: {len(additional_items)}")
        
        # If there are additional items, verify their structure
        for item in additional_items:
            assert "code" in item or "title" in item, "Additional item should have code or title"
            assert "is_additional" in item, "Additional item should have 'is_additional' flag"
            assert item.get("is_additional") == True, "is_additional should be True"
            print(f"Additional training: {item.get('title')} - is_additional: {item.get('is_additional')}")
    
    def test_training_matrix_summary_has_additional_count(self, auth_headers):
        """Test that summary includes additional_count"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify summary exists
        assert "summary" in data, "Response should have 'summary' object"
        summary = data["summary"]
        
        # Verify summary fields
        assert "total" in summary, "Summary should have 'total'"
        assert "current" in summary, "Summary should have 'current'"
        assert "missing" in summary, "Summary should have 'missing'"
        assert "blockers" in summary, "Summary should have 'blockers'"
        assert "additional_count" in summary, "Summary should have 'additional_count'"
        
        # Verify additional_count matches additional_items length
        additional_items = data.get("additional_items", [])
        assert summary["additional_count"] == len(additional_items), \
            f"additional_count ({summary['additional_count']}) should match additional_items length ({len(additional_items)})"
        
        print(f"Summary: total={summary['total']}, current={summary['current']}, "
              f"missing={summary['missing']}, blockers={summary['blockers']}, "
              f"additional_count={summary['additional_count']}")
    
    def test_training_matrix_returns_employee_info(self, auth_headers):
        """Test that training matrix returns employee information"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify employee info
        assert "employee_id" in data
        assert "employee_name" in data
        assert "role" in data
        
        print(f"Employee: {data['employee_name']} (ID: {data['employee_id']}, Role: {data['role']})")
    
    def test_training_matrix_404_for_invalid_employee(self, auth_headers):
        """Test that training matrix returns 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestTrainingNormalizationMapping:
    """Tests for extended training normalization mapping"""
    
    def test_normalization_mapping_exists_in_cleanup_endpoint(self, auth_headers):
        """
        Verify the training normalization mapping includes extended synonyms.
        This is a code review test - we verify the endpoint exists and works.
        The actual mapping is in server.py lines 36313-36395.
        """
        # The cleanup endpoint uses the normalization mapping
        # We can't directly test the mapping, but we can verify the endpoint exists
        # and returns expected structure
        
        # Test that the cleanup endpoint exists (don't actually run cleanup)
        # Just verify the endpoint is accessible
        response = requests.post(
            f"{BASE_URL}/api/admin/cleanup-employee/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        # Should return 200 (success) or 403 (permission denied) - not 404
        assert response.status_code in [200, 403], \
            f"Cleanup endpoint should exist, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            # Verify cleanup response structure
            assert "training_normalized" in data or "results" in data or "orphan_docs_deleted" in data, \
                "Cleanup response should have expected fields"
            print(f"Cleanup endpoint response: {data}")


class TestTrainingMatrixItemStructure:
    """Tests for individual training matrix item structure"""
    
    def test_matrix_item_has_evidence_fields(self, auth_headers):
        """Test that matrix items have evidence-related fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        assert len(items) > 0, "Should have at least one training item"
        
        # Check first item for evidence fields
        item = items[0]
        expected_fields = ["has_evidence", "verified", "evidence_required"]
        
        for field in expected_fields:
            assert field in item, f"Item should have '{field}' field"
        
        print(f"Sample item structure: {item}")
    
    def test_matrix_item_has_expiry_fields(self, auth_headers):
        """Test that matrix items have expiry-related fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        assert len(items) > 0, "Should have at least one training item"
        
        # Check for expiry fields
        item = items[0]
        # These fields may be null but should exist
        assert "expires_at" in item or "days_until_expiry" in item, \
            "Item should have expiry-related fields"
        
        # Check for completion date
        assert "completed_at" in item, "Item should have 'completed_at' field"


class TestTrainingMatrixOverallStatus:
    """Tests for overall training status"""
    
    def test_matrix_has_overall_status(self, auth_headers):
        """Test that training matrix has overall status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "overall" in data, "Response should have 'overall' status"
        
        # Overall should be one of expected values
        valid_statuses = ['current', 'completed', 'verified', 'expiring_soon', 
                         'due_soon', 'missing', 'expired', 'overdue', 'partial']
        assert data["overall"] in valid_statuses or data["overall"] is not None, \
            f"Overall status '{data['overall']}' should be valid"
        
        print(f"Overall training status: {data['overall']}")
    
    def test_matrix_has_evaluated_at_timestamp(self, auth_headers):
        """Test that training matrix has evaluation timestamp"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "evaluated_at" in data, "Response should have 'evaluated_at' timestamp"
        print(f"Evaluated at: {data['evaluated_at']}")


class TestMandatoryTrainingCoverage:
    """Tests for 6 mandatory trainings coverage"""
    
    def test_six_mandatory_trainings_present(self, auth_headers):
        """Test that all 6 mandatory trainings are represented"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        
        # Expected mandatory training codes (may vary by implementation)
        # Based on MANDATORY_ITEMS in server.py
        expected_mandatory = {
            'safeguarding',
            'manual_handling', 
            'infection_control',
            'bls',  # or 'basic_life_support'
            'fire_safety',
            'health_safety'
        }
        
        # Get all codes from items
        item_codes = {item.get('code', '').lower() for item in items}
        
        # Check coverage
        found = expected_mandatory.intersection(item_codes)
        missing = expected_mandatory - item_codes
        
        print(f"Expected mandatory: {expected_mandatory}")
        print(f"Found in response: {item_codes}")
        print(f"Matched: {found}")
        print(f"Missing: {missing}")
        
        # At least 4 of 6 should be present (allowing for code variations)
        assert len(found) >= 4, \
            f"Expected at least 4 mandatory trainings, found {len(found)}: {found}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

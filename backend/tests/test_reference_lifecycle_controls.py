"""
Test Reference Lifecycle Controls - Ticket F
Tests for:
- POST /api/references/{id}/{ref_num}/reset - Reset reference to not_started state
- POST /api/references/{id}/{ref_num}/change-referee - Update referee details with history
- POST /api/references/{id}/{ref_num}/set-response-source - Set response source indicator
- GET /api/employees/{id}/references-normalized - allowed_actions and response.source fields
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee with reference data
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestResetReferenceEndpoint:
    """Tests for POST /api/references/{id}/{ref_num}/reset"""
    
    def test_reset_reference_requires_auth(self):
        """Reset endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/reset",
            json={"reset_reason": "Testing reset without auth"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_reset_reference_invalid_ref_num(self, auth_headers):
        """Reset fails for invalid reference number"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/3/reset",
            json={"reset_reason": "Testing invalid ref num"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "ref_num must be 1 or 2" in response.json().get("detail", "")
    
    def test_reset_reference_short_reason(self, auth_headers):
        """Reset fails with reason less than 10 characters"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/reset",
            json={"reset_reason": "short"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "at least 10 characters" in response.json().get("detail", "")
    
    def test_reset_reference_employee_not_found(self, auth_headers):
        """Reset fails for non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/references/{fake_id}/1/reset",
            json={"reset_reason": "Testing with non-existent employee"},
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "Employee not found" in response.json().get("detail", "")
    
    def test_reset_reference_success(self, auth_headers):
        """Reset reference successfully clears response and verification"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/reset",
            json={"reset_reason": "Testing reset functionality for reference lifecycle controls"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("reference_num") == 2
        assert "reset to not_started" in data.get("message", "")
        assert "previous_state" in data


class TestChangeRefereeEndpoint:
    """Tests for POST /api/references/{id}/{ref_num}/change-referee"""
    
    def test_change_referee_requires_auth(self):
        """Change referee endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/change-referee",
            json={"name": "New Name", "change_reason": "Testing without auth"}
        )
        assert response.status_code == 401
    
    def test_change_referee_invalid_ref_num(self, auth_headers):
        """Change referee fails for invalid reference number"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/5/change-referee",
            json={"name": "New Name", "change_reason": "Testing invalid ref num"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "ref_num must be 1 or 2" in response.json().get("detail", "")
    
    def test_change_referee_short_reason(self, auth_headers):
        """Change referee fails with reason less than 10 characters"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/change-referee",
            json={"name": "New Name", "change_reason": "short"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "at least 10 characters" in response.json().get("detail", "")
    
    def test_change_referee_no_fields_provided(self, auth_headers):
        """Change referee fails when no fields to update"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/change-referee",
            json={"change_reason": "Testing with no fields to update provided"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "No fields provided" in response.json().get("detail", "")
    
    def test_change_referee_employee_not_found(self, auth_headers):
        """Change referee fails for non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/references/{fake_id}/1/change-referee",
            json={"name": "New Name", "change_reason": "Testing with non-existent employee"},
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "Employee not found" in response.json().get("detail", "")
    
    def test_change_referee_success(self, auth_headers):
        """Change referee successfully updates details with history"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/change-referee",
            json={
                "name": "Updated Referee Name",
                "email": "updated.referee@test.com",
                "change_reason": "Testing change referee functionality for lifecycle controls"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("reference_num") == 1
        assert "old_referee" in data
        assert "new_referee" in data
        # Verify new values in response
        assert data["new_referee"].get("name") == "Updated Referee Name"
        assert data["new_referee"].get("email") == "updated.referee@test.com"


class TestSetResponseSourceEndpoint:
    """Tests for POST /api/references/{id}/{ref_num}/set-response-source"""
    
    def test_set_response_source_requires_auth(self):
        """Set response source endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/set-response-source",
            json={"source": "external_submission"}
        )
        assert response.status_code == 401
    
    def test_set_response_source_invalid_ref_num(self, auth_headers):
        """Set response source fails for invalid reference number"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/0/set-response-source",
            json={"source": "external_submission"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "ref_num must be 1 or 2" in response.json().get("detail", "")
    
    def test_set_response_source_invalid_source(self, auth_headers):
        """Set response source fails for invalid source value"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/set-response-source",
            json={"source": "invalid_source"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Source must be one of" in response.json().get("detail", "")
    
    def test_set_response_source_employee_not_found(self, auth_headers):
        """Set response source fails for non-existent employee"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/references/{fake_id}/2/set-response-source",
            json={"source": "external_submission"},
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "Employee not found" in response.json().get("detail", "")
    
    def test_set_response_source_external_submission(self, auth_headers):
        """Set response source to external_submission"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/set-response-source",
            json={"source": "external_submission"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("source") == "external_submission"
    
    def test_set_response_source_manual_entry(self, auth_headers):
        """Set response source to manual_entry"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/set-response-source",
            json={"source": "manual_entry"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("source") == "manual_entry"
    
    def test_set_response_source_test_data(self, auth_headers):
        """Set response source to test_data"""
        response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/set-response-source",
            json={"source": "test_data"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("source") == "test_data"


class TestNormalizedReferencesAllowedActions:
    """Tests for GET /api/employees/{id}/references-normalized - allowed_actions and response.source"""
    
    def test_normalized_references_returns_allowed_actions(self, auth_headers):
        """Normalized references endpoint returns allowed_actions array"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-normalized",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "references" in data
        
        for ref in data["references"]:
            assert "allowed_actions" in ref, f"Reference {ref.get('reference_number')} missing allowed_actions"
            assert isinstance(ref["allowed_actions"], list), "allowed_actions should be a list"
    
    def test_normalized_references_includes_reset_and_change_actions(self, auth_headers):
        """Normalized references includes reset_reference and change_referee in allowed_actions"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-normalized",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check that at least one reference has these actions available
        all_actions = []
        for ref in data["references"]:
            all_actions.extend(ref.get("allowed_actions", []))
        
        # These actions should be available for references
        assert "reset_reference" in all_actions or "change_referee" in all_actions, \
            f"Expected reset_reference or change_referee in allowed_actions. Got: {set(all_actions)}"
    
    def test_normalized_references_returns_response_source(self, auth_headers):
        """Normalized references endpoint returns response.source field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-normalized",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for ref in data["references"]:
            if ref.get("response"):
                assert "source" in ref["response"], \
                    f"Reference {ref.get('reference_number')} response missing source field"
    
    def test_normalized_references_response_source_values(self, auth_headers):
        """Response source has valid values"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-normalized",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        valid_sources = ["external_submission", "manual_entry", "test_data", None]
        for ref in data["references"]:
            if ref.get("response"):
                source = ref["response"].get("source")
                assert source in valid_sources, \
                    f"Invalid source '{source}' for reference {ref.get('reference_number')}"


class TestReferenceLifecycleIntegration:
    """Integration tests for reference lifecycle controls"""
    
    def test_reset_then_verify_state_cleared(self, auth_headers):
        """After reset, reference state should be cleared"""
        # First reset the reference
        reset_response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/reset",
            json={"reset_reason": "Integration test - verifying state is cleared after reset"},
            headers=auth_headers
        )
        assert reset_response.status_code == 200
        
        # Then check normalized data
        norm_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/references-normalized",
            headers=auth_headers
        )
        assert norm_response.status_code == 200
        data = norm_response.json()
        
        ref2 = next((r for r in data["references"] if r["reference_number"] == 2), None)
        assert ref2 is not None, "Reference 2 not found"
        
        # After reset, verification should be cleared
        verification = ref2.get("verification", {})
        assert verification.get("verified") != True, "Verification should be cleared after reset"
    
    def test_change_referee_preserves_history(self, auth_headers):
        """Change referee should preserve change history"""
        # Make a change
        change_response = requests.post(
            f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/1/change-referee",
            json={
                "name": f"Test Referee {uuid.uuid4().hex[:8]}",
                "change_reason": "Integration test - verifying change history is preserved"
            },
            headers=auth_headers
        )
        assert change_response.status_code == 200
        data = change_response.json()
        
        # Verify old_referee and new_referee are in response
        assert "old_referee" in data
        assert "new_referee" in data
        assert data["old_referee"] != data["new_referee"]


# Restore test data after tests
@pytest.fixture(scope="module", autouse=True)
def restore_test_data(auth_headers):
    """Restore reference 2 response data after tests"""
    yield
    # Restore response source to external_submission
    requests.post(
        f"{BASE_URL}/api/references/{TEST_EMPLOYEE_ID}/2/set-response-source",
        json={"source": "external_submission"},
        headers=auth_headers
    )

"""
P0 Contract Signing Fixes - Backend Tests
Tests for:
1. Contract Signing - Final Step Only (locked until all checks complete)
2. GET /api/employees/{id}/can-sign-contract endpoint
3. can_sign_contract() function checking 8 requirements
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def test_employee_id(admin_token):
    """Get a test employee ID from the system"""
    response = requests.get(
        f"{BASE_URL}/api/employees",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code == 200:
        employees = response.json()
        if employees and len(employees) > 0:
            return employees[0].get("id")
    pytest.skip("No employees found for testing")


class TestCanSignContractEndpoint:
    """Tests for GET /api/employees/{id}/can-sign-contract endpoint"""
    
    def test_endpoint_exists_and_requires_auth(self):
        """Test that endpoint exists and requires authentication"""
        # Without auth should return 401/403
        response = requests.get(f"{BASE_URL}/api/employees/test-id/can-sign-contract")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
    
    def test_endpoint_returns_eligibility_structure(self, admin_token, test_employee_id):
        """Test that endpoint returns proper eligibility structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "can_sign" in data, "Response should contain 'can_sign' field"
        assert "blockers" in data, "Response should contain 'blockers' field"
        assert "completed" in data, "Response should contain 'completed' field"
        
        # Verify types
        assert isinstance(data["can_sign"], bool), "'can_sign' should be boolean"
        assert isinstance(data["blockers"], list), "'blockers' should be a list"
        assert isinstance(data["completed"], list), "'completed' should be a list"
    
    def test_endpoint_returns_blocker_details(self, admin_token, test_employee_id):
        """Test that blockers list contains meaningful details"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # If there are blockers, they should be strings describing what's missing
        if data["blockers"]:
            for blocker in data["blockers"]:
                assert isinstance(blocker, str), "Each blocker should be a string"
                assert len(blocker) > 0, "Blocker should not be empty"
    
    def test_endpoint_returns_completed_details(self, admin_token, test_employee_id):
        """Test that completed list contains meaningful details"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # If there are completed items, they should be strings
        if data["completed"]:
            for item in data["completed"]:
                assert isinstance(item, str), "Each completed item should be a string"
                assert len(item) > 0, "Completed item should not be empty"
    
    def test_endpoint_returns_total_requirements(self, admin_token, test_employee_id):
        """Test that endpoint returns total requirements count"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should have total_requirements field
        if "total_requirements" in data:
            assert data["total_requirements"] == 8, "Should check 8 requirements"
        
        # Should have completed_count field
        if "completed_count" in data:
            assert isinstance(data["completed_count"], int), "completed_count should be int"
    
    def test_endpoint_handles_invalid_employee_id(self, admin_token):
        """Test that endpoint handles invalid employee ID gracefully"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid-nonexistent-id-12345/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 200 with can_sign=False or 404
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert data["can_sign"] == False, "Invalid employee should not be able to sign"


class TestCanSignContractLogic:
    """Tests for the 8 requirements checked by can_sign_contract()"""
    
    def test_checks_dbs_verification(self, admin_token, test_employee_id):
        """Test that DBS verification is checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Either DBS is in completed or in blockers
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "dbs" in all_items, "DBS should be checked (either completed or blocker)"
    
    def test_checks_right_to_work_verification(self, admin_token, test_employee_id):
        """Test that Right to Work verification is checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "right to work" in all_items or "rtw" in all_items, "Right to Work should be checked"
    
    def test_checks_identity_verification(self, admin_token, test_employee_id):
        """Test that Identity verification is checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "identity" in all_items, "Identity should be checked"
    
    def test_checks_proof_of_address(self, admin_token, test_employee_id):
        """Test that Proof of Address (2 documents) is checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "proof of address" in all_items or "poa" in all_items, "Proof of Address should be checked"
    
    def test_checks_references(self, admin_token, test_employee_id):
        """Test that References (both) are checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "reference" in all_items, "References should be checked"
    
    def test_checks_interview(self, admin_token, test_employee_id):
        """Test that Interview completion is checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "interview" in all_items, "Interview should be checked"
    
    def test_checks_induction(self, admin_token, test_employee_id):
        """Test that Induction completion is checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "induction" in all_items, "Induction should be checked"
    
    def test_checks_mandatory_training(self, admin_token, test_employee_id):
        """Test that Mandatory Training is checked"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/can-sign-contract",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        all_items = " ".join(data["blockers"] + data["completed"]).lower()
        assert "training" in all_items, "Mandatory Training should be checked"


class TestAdminLogin:
    """Test admin login functionality"""
    
    def test_admin_login_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert len(data["token"]) > 0, "Token should not be empty"
    
    def test_admin_login_invalid_credentials(self):
        """Test admin login with wrong credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"


class TestPreEmploymentGates:
    """Test pre-employment gates endpoint for blocker display"""
    
    def test_pre_employment_gates_endpoint(self, admin_token, test_employee_id):
        """Test that pre-employment gates endpoint returns blockers"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/pre-employment-gates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should have blockers list
        assert "blockers" in data, "Response should contain 'blockers' field"
        assert isinstance(data["blockers"], list), "'blockers' should be a list"
    
    def test_blockers_have_gate_and_label(self, admin_token, test_employee_id):
        """Test that blockers have gate and label fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/pre-employment-gates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        if data["blockers"]:
            for blocker in data["blockers"]:
                assert "gate" in blocker or "label" in blocker, "Blocker should have gate or label"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

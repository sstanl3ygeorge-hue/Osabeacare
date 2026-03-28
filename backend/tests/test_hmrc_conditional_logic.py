"""
Test HMRC Starter Checklist Conditional Logic
Tests the conditional requirement logic where HMRC form is only required if no P45 exists.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID from the review request
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@osabea.care", "password": "admin123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestHMRCConditionalLogic:
    """Tests for HMRC Starter Checklist conditional requirement logic"""
    
    def test_compliance_requirements_endpoint_returns_200(self, api_client):
        """Test that compliance requirements endpoint is accessible"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "requirements" in data, "Response missing 'requirements' key"
        print(f"✅ Compliance requirements endpoint returns 200 with {len(data['requirements'])} requirements")
    
    def test_response_includes_conditional_not_required_array(self, api_client):
        """Test that response includes conditional_not_required array"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements"
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify conditional_not_required key exists
        assert "conditional_not_required" in data, "Response missing 'conditional_not_required' key"
        assert isinstance(data["conditional_not_required"], list), "conditional_not_required should be a list"
        print(f"✅ Response includes conditional_not_required array (length: {len(data['conditional_not_required'])})")
    
    def test_hmrc_in_requirements_when_no_p45(self, api_client):
        """Test that HMRC Starter Checklist is in requirements when no P45 exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements"
        )
        assert response.status_code == 200
        data = response.json()
        
        requirements = data.get("requirements", [])
        
        # Check if P45 document exists
        p45_exists = False
        for req in requirements:
            if "p45" in req.get("id", "").lower():
                if req.get("has_evidence") or req.get("status") in ["verified", "pending_review"]:
                    p45_exists = True
                    break
        
        # Find HMRC in requirements
        hmrc_found = False
        hmrc_req = None
        for req in requirements:
            if req.get("id") == "hmrc_starter_checklist":
                hmrc_found = True
                hmrc_req = req
                break
        
        if not p45_exists:
            # When no P45, HMRC should be in requirements
            assert hmrc_found, "HMRC Starter Checklist should be in requirements when no P45 exists"
            assert hmrc_req.get("status") == "missing", f"HMRC status should be 'missing', got '{hmrc_req.get('status')}'"
            print(f"✅ HMRC Starter Checklist is in requirements with status 'missing' (no P45 exists)")
        else:
            # When P45 exists, HMRC should NOT be in requirements
            assert not hmrc_found, "HMRC Starter Checklist should NOT be in requirements when P45 exists"
            print(f"✅ HMRC Starter Checklist correctly excluded (P45 exists)")
    
    def test_conditional_not_required_empty_when_no_p45(self, api_client):
        """Test that conditional_not_required is empty when no P45 exists (HMRC is required)"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements"
        )
        assert response.status_code == 200
        data = response.json()
        
        requirements = data.get("requirements", [])
        conditional_not_required = data.get("conditional_not_required", [])
        
        # Check if P45 document exists
        p45_exists = False
        for req in requirements:
            if "p45" in req.get("id", "").lower():
                if req.get("has_evidence") or req.get("status") in ["verified", "pending_review"]:
                    p45_exists = True
                    break
        
        if not p45_exists:
            # When no P45, HMRC should NOT be in conditional_not_required
            hmrc_excluded = any(item.get("id") == "hmrc_starter_checklist" for item in conditional_not_required)
            assert not hmrc_excluded, "HMRC should NOT be in conditional_not_required when no P45 exists"
            print(f"✅ conditional_not_required does not contain HMRC (correct - no P45 exists)")
        else:
            # When P45 exists, HMRC should be in conditional_not_required
            hmrc_excluded = any(item.get("id") == "hmrc_starter_checklist" for item in conditional_not_required)
            assert hmrc_excluded, "HMRC should be in conditional_not_required when P45 exists"
            print(f"✅ HMRC correctly in conditional_not_required (P45 exists)")
    
    def test_hmrc_requirement_has_correct_category(self, api_client):
        """Test that HMRC Starter Checklist is in Admin/Other category"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements"
        )
        assert response.status_code == 200
        data = response.json()
        
        requirements = data.get("requirements", [])
        
        for req in requirements:
            if req.get("id") == "hmrc_starter_checklist":
                assert req.get("category") == "6_Admin", f"HMRC category should be '6_Admin', got '{req.get('category')}'"
                print(f"✅ HMRC Starter Checklist is in correct category: 6_Admin")
                return
        
        # If HMRC not found, check if it's in conditional_not_required (P45 exists)
        conditional_not_required = data.get("conditional_not_required", [])
        hmrc_excluded = any(item.get("id") == "hmrc_starter_checklist" for item in conditional_not_required)
        if hmrc_excluded:
            print(f"✅ HMRC excluded due to P45 existence (category test skipped)")
        else:
            pytest.fail("HMRC Starter Checklist not found in requirements or conditional_not_required")
    
    def test_hmrc_requirement_structure(self, api_client):
        """Test that HMRC requirement has expected structure"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements"
        )
        assert response.status_code == 200
        data = response.json()
        
        requirements = data.get("requirements", [])
        
        for req in requirements:
            if req.get("id") == "hmrc_starter_checklist":
                # Verify required fields
                assert "id" in req, "HMRC requirement missing 'id'"
                assert "name" in req, "HMRC requirement missing 'name'"
                assert "status" in req, "HMRC requirement missing 'status'"
                assert "category" in req, "HMRC requirement missing 'category'"
                assert "has_evidence" in req, "HMRC requirement missing 'has_evidence'"
                
                # Verify values
                assert req["name"] == "HMRC Starter Checklist", f"Unexpected name: {req['name']}"
                assert req["status"] in ["missing", "pending_review", "verified"], f"Unexpected status: {req['status']}"
                
                print(f"✅ HMRC requirement has correct structure")
                print(f"   - ID: {req['id']}")
                print(f"   - Name: {req['name']}")
                print(f"   - Status: {req['status']}")
                print(f"   - Category: {req['category']}")
                return
        
        # If not found, might be excluded
        conditional_not_required = data.get("conditional_not_required", [])
        if any(item.get("id") == "hmrc_starter_checklist" for item in conditional_not_required):
            print(f"✅ HMRC excluded due to P45 existence (structure test skipped)")
        else:
            pytest.fail("HMRC Starter Checklist not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

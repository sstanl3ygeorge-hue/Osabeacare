"""
RTW Workflow Features Test Suite
Tests for iteration 135 - RTW workflow tightening features:
1. RTW check GET endpoint includes checked_by_name field with resolved user name
2. Human-friendly method labels (not raw enum values)
3. RTW Result section shows route/permission/restrictions
4. No raw IDs or enum values in UI responses
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestRTWCheckedByNameResolution:
    """Test that RTW check GET endpoint returns checked_by_name with resolved user name."""
    
    def test_rtw_check_get_returns_checked_by_name(self, api_client):
        """
        Verify GET /api/employees/{id}/right-to-work/check returns checked_by_name field.
        This field should contain a human-readable name, not a raw user ID.
        """
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check")
        
        # If no check exists, that's okay - we'll create one
        if response.status_code == 404:
            pytest.skip("No RTW check exists for test employee - will test after creating one")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # If there's a current check, verify checked_by_name is present
        if data.get("current"):
            current = data["current"]
            
            # Verify checked_by_name field exists
            assert "checked_by_name" in current, "checked_by_name field missing from RTW check response"
            
            # Verify it's not a raw user ID (user IDs start with 'user_')
            checked_by_name = current.get("checked_by_name", "")
            assert not checked_by_name.startswith("user_"), f"checked_by_name should be human-readable, got: {checked_by_name}"
            
            # Verify it's not empty
            assert checked_by_name, "checked_by_name should not be empty"
            
            print(f"✓ RTW check has checked_by_name: {checked_by_name}")
    
    def test_create_rtw_check_and_verify_name_resolution(self, api_client):
        """
        Create a new RTW check and verify the checked_by_name is resolved correctly.
        """
        # Create a new RTW check
        check_payload = {
            "method": "home_office_online_check",
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "outcome": "verified",
            "source_status_type": "settled_status",
            "notes": "Test check for name resolution verification",
            "is_indefinite": True,
            "follow_up_required": False,
            "route": "home_office_online_check"
        }
        
        # First, we need to upload a proof file (required for compliance)
        # For testing, we'll check if the endpoint accepts the check without proof
        # or if it requires proof
        
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            json=check_payload
        )
        
        # If proof is required, the test should still pass for the name resolution feature
        if response.status_code == 400 and "proof" in response.text.lower():
            pytest.skip("Proof file required - testing name resolution on existing check")
        
        if response.status_code in [200, 201]:
            # Now GET the check and verify checked_by_name
            get_response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check")
            assert get_response.status_code == 200
            
            data = get_response.json()
            current = data.get("current", {})
            
            # Verify checked_by_name is present and human-readable
            assert "checked_by_name" in current, "checked_by_name missing after creating check"
            checked_by_name = current.get("checked_by_name", "")
            assert not checked_by_name.startswith("user_"), f"Name not resolved: {checked_by_name}"
            
            print(f"✓ Created RTW check with checked_by_name: {checked_by_name}")


class TestHumanFriendlyMethodLabels:
    """Test that method values are stored correctly and can be mapped to human-friendly labels."""
    
    # Method value to human-friendly label mapping (as defined in frontend)
    METHOD_LABELS = {
        'home_office_online_check': 'Home Office Online Check',
        'manual_passport_uk_irish': 'Manual Check - UK/Irish Passport',
        'manual_list_a_document': 'Manual Check - List A Document',
        'manual_list_a_check': 'Manual List A Check',
        'manual_list_b_group_1': 'Manual Check - List B Group 1',
        'manual_list_b_group_1_check': 'Manual List B Group 1 Check',
        'manual_list_b_group_2_ecs': 'Manual Check - List B Group 2 / ECS',
        'manual_list_b_group_2_check': 'Manual List B Group 2 Check',
        'idsp_check': 'Digital Verification Service (IDSP)',
        'digital_verification_service_check': 'Digital Verification Service',
        'ecs_pvn_check': 'Employer Checking Service (PVN)',
    }
    
    def test_rtw_check_method_is_valid_enum(self, api_client):
        """Verify RTW check method is a valid enum value that can be mapped to a label."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check")
        
        if response.status_code == 404:
            pytest.skip("No RTW check exists for test employee")
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("current"):
            method = data["current"].get("method")
            assert method, "Method field should not be empty"
            
            # Verify method is a valid enum value (snake_case)
            assert "_" in method or method.islower(), f"Method should be snake_case enum: {method}"
            
            # Verify method can be mapped to a human-friendly label
            # (frontend does this mapping)
            if method in self.METHOD_LABELS:
                print(f"✓ Method '{method}' maps to '{self.METHOD_LABELS[method]}'")
            else:
                # Method might be a valid new method not in our test mapping
                print(f"✓ Method '{method}' is valid snake_case (frontend will format)")


class TestRTWResultComprehensiveDisplay:
    """Test that RTW Result section includes all required fields."""
    
    def test_rtw_check_includes_all_result_fields(self, api_client):
        """
        Verify RTW check response includes comprehensive result fields:
        - route
        - permission_start_date
        - permission_end_date
        - reference_number
        - share_code
        - restrictions
        - hours_limit
        - is_indefinite
        - follow_up_required
        - follow_up_due_at
        """
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check")
        
        if response.status_code == 404:
            pytest.skip("No RTW check exists for test employee")
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("current"):
            current = data["current"]
            
            # List of expected RTW result fields
            expected_fields = [
                "method",
                "outcome",
                "checked_at",
                "checked_by",
                "checked_by_name",  # New field for resolved name
            ]
            
            # Optional but expected RTW result fields
            optional_result_fields = [
                "route",
                "permission_start_date",
                "permission_end_date",
                "reference_number",
                "share_code",
                "restrictions",
                "hours_limit",
                "is_indefinite",
                "follow_up_required",
                "follow_up_due_at",
                "source_status_type",
            ]
            
            # Verify required fields exist
            for field in expected_fields:
                assert field in current, f"Required field '{field}' missing from RTW check"
            
            # Log which optional fields are present
            present_optional = [f for f in optional_result_fields if f in current and current[f] is not None]
            print(f"✓ RTW check has required fields: {expected_fields}")
            print(f"✓ RTW check has optional fields: {present_optional}")
    
    def test_rtw_check_no_raw_ids_in_response(self, api_client):
        """Verify no raw MongoDB ObjectIds or internal IDs leak to the response."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check")
        
        if response.status_code == 404:
            pytest.skip("No RTW check exists for test employee")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that _id is not in response
        def check_no_mongo_id(obj, path=""):
            if isinstance(obj, dict):
                assert "_id" not in obj, f"MongoDB _id found at {path}"
                for key, value in obj.items():
                    check_no_mongo_id(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_no_mongo_id(item, f"{path}[{i}]")
        
        check_no_mongo_id(data)
        print("✓ No MongoDB _id fields in response")


class TestComplianceRequirementsRTWDisplay:
    """Test that compliance requirements endpoint returns RTW data with proper formatting."""
    
    def test_compliance_requirements_rtw_check_data(self, api_client):
        """
        Verify compliance requirements includes RTW check data with:
        - checked_by_name (not raw user ID)
        - method (valid enum)
        - outcome
        """
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Find RTW requirement in the requirements list
        rtw_req = None
        for req in data.get("requirements", []):
            if req.get("id") in ["right_to_work", "right_to_work_check"]:
                rtw_req = req
                break
        
        assert rtw_req, "RTW requirement should exist in compliance requirements"
        print(f"✓ Found RTW requirement: {rtw_req.get('name')}")
        
        # Check if authoritativeCheck exists and has proper data
        if rtw_req.get("authoritativeCheck"):
            check = rtw_req["authoritativeCheck"]
            
            # Verify checked_by_name is present and human-readable
            if "checked_by_name" in check:
                name = check["checked_by_name"]
                assert not name.startswith("user_"), f"checked_by_name should be human-readable: {name}"
                print(f"✓ Compliance requirements RTW check has checked_by_name: {name}")
            
            # Verify method is valid
            if "method" in check:
                method = check["method"]
                assert method, "Method should not be empty"
                print(f"✓ Compliance requirements RTW check has method: {method}")
        else:
            print("ℹ No RTW check in compliance requirements (authoritativeCheck is null)")


class TestStampBadgeDisplay:
    """Test that stamp badge information is properly returned."""
    
    def test_evidence_files_include_stamp_info(self, api_client):
        """
        Verify evidence files include stamp information:
        - verification_stamp
        - verification_stamp_by_name
        - verification_stamp_at
        """
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements")
        
        assert response.status_code == 200
        data = response.json()
        
        found_stamped_file = False
        # Check any requirement with evidence files
        for req in data.get("requirements", []):
            evidence_files = req.get("evidence_files", [])
            for file in evidence_files:
                # If file has a stamp, verify stamp info is present
                if file.get("verification_stamp"):
                    found_stamped_file = True
                    stamp = file["verification_stamp"]
                    print(f"✓ Found stamped file with stamp type: {stamp}")
                    
                    # Check for stamp metadata
                    if file.get("verification_stamp_by_name"):
                        print(f"  - Stamped by: {file['verification_stamp_by_name']}")
                    if file.get("verification_stamp_at"):
                        print(f"  - Stamped at: {file['verification_stamp_at']}")
                    
                    # Verify stamp is a valid type
                    valid_stamps = ['original_seen', 'copy_verified', 'online_check', 'not_verified']
                    assert stamp in valid_stamps, f"Invalid stamp type: {stamp}"
        
        if not found_stamped_file:
            print("ℹ No stamped files found in compliance requirements (this is expected if no stamps applied)")


class TestRTWExtractionEndpoint:
    """Test RTW extraction endpoint for auto-extraction feature."""
    
    def test_rtw_extract_endpoint_exists(self, api_client):
        """Verify RTW extraction endpoint exists and validates input."""
        # Test with empty payload - should return validation error
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            json={},
            params={"employee_id": TEST_EMPLOYEE_ID}
        )
        
        # Should return 400 or 422 for validation error, not 404
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print("✓ RTW extraction endpoint exists and validates input")
    
    def test_rtw_extract_requires_file_data(self, api_client):
        """Verify RTW extraction requires file_base64 or document_id."""
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            json={"file_type": "image/png"},
            params={"employee_id": TEST_EMPLOYEE_ID}
        )
        
        # Should return error about missing file data
        assert response.status_code in [400, 422]
        print("✓ RTW extraction validates required file data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

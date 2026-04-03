"""
RTW System Tests - Right to Work 3-Layer Data Model
Tests for RTW check endpoint storing new fields and RTW extraction endpoint validation.
"""
import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


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


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestRTWCheckEndpoint:
    """Tests for RTW check POST and GET endpoints with new 3-layer fields."""
    
    def test_rtw_check_stores_new_fields(self, api_client):
        """
        Test that RTW check endpoint stores all new fields:
        - permission_start_date
        - permission_end_date
        - reference_number
        - share_code
        - restrictions
        - hours_limit
        - is_indefinite
        - follow_up_required
        - route
        - document_type
        """
        # Create RTW check with all new fields
        payload = {
            "method": "home_office_online_check",
            "checked_at": "2026-01-15",
            "outcome": "verified",
            "source_status_type": "settled_status",
            # New 3-layer fields
            "permission_start_date": "2020-06-01",
            "permission_end_date": "2030-06-01",
            "reference_number": "PVN123456789",
            "share_code": "ABC123DEF",
            "restrictions": "20 hours per week during term time",
            "hours_limit": 20,
            "is_indefinite": False,
            "follow_up_required": True,
            "follow_up_due_at": "2030-05-01",
            "route": "home_office_online_check",
            "document_type": "share_code_result"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            json=payload
        )
        
        print(f"POST RTW Check Response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all new fields are stored
        assert data.get("method") == "home_office_online_check", "Method not stored correctly"
        assert data.get("permission_start_date") == "2020-06-01", "permission_start_date not stored"
        assert data.get("permission_end_date") == "2030-06-01", "permission_end_date not stored"
        assert data.get("reference_number") == "PVN123456789", "reference_number not stored"
        assert data.get("share_code") == "ABC123DEF", "share_code not stored"
        assert data.get("restrictions") == "20 hours per week during term time", "restrictions not stored"
        assert data.get("hours_limit") == 20, "hours_limit not stored"
        assert data.get("follow_up_required") == True, "follow_up_required not stored"
        assert data.get("route") == "home_office_online_check", "route not stored"
        assert data.get("document_type") == "share_code_result", "document_type not stored"
        
        print("✓ All new RTW fields stored correctly")
    
    def test_rtw_check_get_returns_all_fields(self, api_client):
        """Test that GET RTW check returns all stored fields."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check"
        )
        
        print(f"GET RTW Check Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        current = data.get("current")
        
        if current:
            print(f"Current RTW check fields: {list(current.keys())}")
            
            # Verify new fields are returned
            expected_fields = [
                "permission_start_date", "permission_end_date", "reference_number",
                "share_code", "restrictions", "hours_limit", "is_indefinite",
                "follow_up_required", "route", "document_type"
            ]
            
            for field in expected_fields:
                assert field in current, f"Field '{field}' missing from GET response"
            
            print("✓ All new RTW fields returned in GET response")
        else:
            print("No current RTW check found - this is expected if no check recorded yet")
    
    def test_rtw_check_with_indefinite_right(self, api_client):
        """Test RTW check for UK/Irish citizen with indefinite right to work."""
        payload = {
            "method": "manual_passport_uk_irish",
            "checked_at": "2026-01-15",
            "outcome": "verified",
            "source_status_type": "uk_citizen",
            "is_indefinite": True,
            "follow_up_required": False,
            "route": "manual_list_a_check",
            "document_type": "uk_passport"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            json=payload
        )
        
        print(f"POST RTW Check (indefinite) Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("is_indefinite") == True, "is_indefinite should be True for UK citizen"
        assert data.get("follow_up_required") == False, "follow_up_required should be False for indefinite"
        
        print("✓ Indefinite RTW check stored correctly")


class TestRTWExtractionEndpoint:
    """Tests for RTW extraction endpoint validation."""
    
    def test_extraction_requires_input(self, api_client):
        """Test that extraction endpoint returns error when no input provided."""
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            json={}
        )
        
        print(f"RTW Extract (no input) Response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Should return 400 or 422 for missing required data
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        
        print("✓ Extraction endpoint validates missing input")
    
    def test_extraction_with_invalid_document_id(self, api_client):
        """Test extraction with non-existent document ID."""
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            json={"document_id": "nonexistent_doc_123"}
        )
        
        print(f"RTW Extract (invalid doc) Response: {response.status_code}")
        
        # Should return 404 for document not found
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print("✓ Extraction endpoint returns 404 for invalid document")
    
    def test_extraction_with_empty_base64(self, api_client):
        """Test extraction with empty base64 data."""
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            json={"file_base64": ""}
        )
        
        print(f"RTW Extract (empty base64) Response: {response.status_code}")
        
        # Should return error for empty data
        assert response.status_code in [400, 422, 500], f"Expected error status, got {response.status_code}"
        
        print("✓ Extraction endpoint handles empty base64")
    
    def test_extraction_with_valid_base64_image(self, api_client):
        """Test extraction with a valid base64 image (small test image)."""
        # Create a minimal valid PNG image (1x1 pixel)
        # This is a valid PNG but won't contain RTW data
        minimal_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        base64_image = base64.b64encode(minimal_png).decode('utf-8')
        
        response = api_client.post(
            f"{BASE_URL}/api/rtw/extract",
            json={
                "file_base64": base64_image,
                "file_type": "image/png"
            },
            params={"employee_id": TEST_EMPLOYEE_ID}
        )
        
        print(f"RTW Extract (valid image) Response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Should return 200 with extraction result (even if no data extracted)
        # or 400/500 if image processing fails
        assert response.status_code in [200, 400, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response should have 'success' field"
            print(f"✓ Extraction endpoint processed image, success={data.get('success')}")
        else:
            print(f"✓ Extraction endpoint returned error for minimal image (expected)")


class TestRTWCheckHistory:
    """Tests for RTW check history endpoint."""
    
    def test_get_rtw_check_with_history(self, api_client):
        """Test getting RTW check with history included."""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            params={"include_history": True}
        )
        
        print(f"GET RTW Check (with history) Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "current" in data, "Response should have 'current' field"
        assert "history" in data, "Response should have 'history' field when include_history=True"
        
        if data.get("history"):
            print(f"✓ RTW check history returned: {len(data['history'])} records")
        else:
            print("✓ RTW check history endpoint works (no history yet)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

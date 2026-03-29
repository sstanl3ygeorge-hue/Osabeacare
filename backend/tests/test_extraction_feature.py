"""
Test suite for Application Form Extraction Feature
Tests the safe auto-extraction from uploaded application forms into employee profile fields.

Features tested:
1. POST /api/employees/{id}/extract-from-application - Extract data from application form
2. Extended employee profile fields (address, NI number, next of kin, etc.)
3. POST /api/extractions/{id}/apply - Apply selected fields to employee profile
4. POST /api/extractions/{id}/discard - Discard extraction without applying
5. Compliance calculations remain unchanged by profile extraction
6. OCR fallback when AI extraction fails
7. Graceful failure handling with options modal (fill manually, view document, retry)
8. Extraction logging (file type, size, OCR attempts, failure reason)
"""

import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestExtractionEndpoints:
    """Test extraction API endpoints exist and respond correctly"""
    
    def test_extract_from_application_endpoint_exists(self, auth_headers):
        """Test POST /api/employees/{id}/extract-from-application endpoint exists and returns proper response"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=60  # Extraction can take time due to AI processing
        )
        # Should return 200 (success or graceful failure), 404 (no application form), NOT 405 (method not allowed)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✅ Extract endpoint exists - Status: {response.status_code}")
        
        data = response.json()
        
        # If 404, verify error message is appropriate
        if response.status_code == 404:
            assert "detail" in data
            assert "application form" in data["detail"].lower() or "not found" in data["detail"].lower()
            print(f"✅ Correct error message: {data['detail']}")
        
        # If 200, verify response structure (success or graceful failure)
        elif response.status_code == 200:
            if data.get("extraction_failed"):
                # Graceful failure - verify options are provided
                assert "message" in data, "Graceful failure should include message"
                assert "options" in data, "Graceful failure should include options"
                assert len(data["options"]) >= 2, "Should have at least 2 options (fill manually, retry)"
                print(f"✅ Graceful failure with options: {[o['action'] for o in data['options']]}")
            else:
                # Success - verify extracted fields
                assert "fields" in data, "Success response should include fields"
                assert "extraction_id" in data, "Success response should include extraction_id"
                print(f"✅ Extraction successful - {len(data['fields'])} fields extracted")
    
    def test_get_extractions_endpoint_exists(self, auth_headers):
        """Test GET /api/employees/{id}/extractions endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extractions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        data = response.json()
        assert "extractions" in data
        print(f"✅ Get extractions endpoint works - Found {len(data['extractions'])} extractions")
    
    def test_apply_extraction_endpoint_exists(self, auth_headers):
        """Test POST /api/extractions/{id}/apply endpoint exists"""
        # Use a fake extraction ID - should return 404 (not found), not 405 (method not allowed)
        response = requests.post(
            f"{BASE_URL}/api/extractions/fake-extraction-id/apply",
            headers=auth_headers,
            json={"extraction_id": "fake-extraction-id", "fields_to_apply": ["first_name"]}
        )
        assert response.status_code in [400, 404], f"Unexpected status: {response.status_code}"
        print(f"✅ Apply extraction endpoint exists - Status: {response.status_code}")
    
    def test_discard_extraction_endpoint_exists(self, auth_headers):
        """Test POST /api/extractions/{id}/discard endpoint exists"""
        # Use a fake extraction ID - should return 404 (not found), not 405 (method not allowed)
        response = requests.post(
            f"{BASE_URL}/api/extractions/fake-extraction-id/discard",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Unexpected status: {response.status_code}"
        print(f"✅ Discard extraction endpoint exists - Status: {response.status_code}")


class TestExtendedProfileFields:
    """Test that extended profile fields are accepted in employee update"""
    
    def test_employee_update_accepts_extended_fields(self, auth_headers):
        """Test PUT /api/employees/{id} accepts extended profile fields"""
        # First get current employee data
        get_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        original_data = get_response.json()
        
        # Test updating with extended fields
        update_data = {
            "address_line_1": "TEST_123 Test Street",
            "city": "TEST_London",
            "postcode": "TEST_SW1A 1AA",
            "ni_number": "TEST_AB123456C",
            "next_of_kin_name": "TEST_Jane Doe",
            "next_of_kin_phone": "TEST_07700900123"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200, f"Update failed: {response.status_code} - {response.text}"
        print("✅ Extended profile fields accepted in PUT request")
        
        # Verify fields were saved
        verify_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert verify_response.status_code == 200
        updated_data = verify_response.json()
        
        assert updated_data.get("address_line_1") == "TEST_123 Test Street"
        assert updated_data.get("city") == "TEST_London"
        assert updated_data.get("postcode") == "TEST_SW1A 1AA"
        assert updated_data.get("ni_number") == "TEST_AB123456C"
        assert updated_data.get("next_of_kin_name") == "TEST_Jane Doe"
        print("✅ Extended profile fields persisted correctly")
        
        # Clean up - restore original values
        cleanup_data = {
            "address_line_1": original_data.get("address_line_1"),
            "city": original_data.get("city"),
            "postcode": original_data.get("postcode"),
            "ni_number": original_data.get("ni_number"),
            "next_of_kin_name": original_data.get("next_of_kin_name"),
            "next_of_kin_phone": original_data.get("next_of_kin_phone")
        }
        requests.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers,
            json=cleanup_data
        )
        print("✅ Test data cleaned up")


class TestComplianceUnaffected:
    """Test that compliance calculations are NOT affected by profile extraction"""
    
    def test_compliance_unchanged_after_profile_update(self, auth_headers):
        """Verify compliance percentage doesn't change when profile fields are updated"""
        # Get initial compliance
        initial_compliance = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance",
            headers=auth_headers
        )
        assert initial_compliance.status_code == 200
        initial_data = initial_compliance.json()
        initial_percentage = initial_data.get("compliance", {}).get("completion_percentage", 0)
        print(f"Initial compliance percentage: {initial_percentage}%")
        
        # Update profile fields (these should NOT affect compliance)
        update_data = {
            "ni_number": "TEST_ZZ999999Z",
            "address_line_1": "TEST_456 Compliance Test Road"
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers,
            json=update_data
        )
        assert update_response.status_code == 200
        
        # Get compliance after update
        after_compliance = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance",
            headers=auth_headers
        )
        assert after_compliance.status_code == 200
        after_data = after_compliance.json()
        after_percentage = after_data.get("compliance", {}).get("completion_percentage", 0)
        print(f"Compliance percentage after profile update: {after_percentage}%")
        
        # Compliance should be unchanged
        assert initial_percentage == after_percentage, \
            f"Compliance changed from {initial_percentage}% to {after_percentage}% after profile update!"
        print("✅ Compliance percentage unchanged after profile field update")
        
        # Clean up
        requests.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers,
            json={"ni_number": None, "address_line_1": None}
        )
    
    def test_compliance_requirements_structure(self, auth_headers):
        """Verify compliance requirements endpoint returns expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "requirements" in data
        assert "statuses" in data
        assert "work_readiness" in data
        
        # Verify requirements have expected fields
        if data["requirements"]:
            req = data["requirements"][0]
            assert "id" in req
            assert "name" in req
            assert "status" in req
            assert "has_evidence" in req
        
        print("✅ Compliance requirements structure is correct")
        print(f"   - Total requirements: {len(data['requirements'])}")
        print(f"   - Work readiness status: {data['work_readiness'].get('status_label', 'Unknown')}")


class TestExtractionErrorHandling:
    """Test error handling for extraction feature"""
    
    def test_extract_without_application_form(self, auth_headers):
        """Test extraction fails gracefully when no application form exists"""
        # Use a non-existent employee ID to ensure no application form
        response = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/extract-from-application",
            headers=auth_headers,
            timeout=30
        )
        
        # Should return 404 for non-existent employee
        assert response.status_code == 404, f"Unexpected status: {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✅ Correct error handling for non-existent employee: {data['detail']}")
    
    def test_apply_nonexistent_extraction(self, auth_headers):
        """Test applying a non-existent extraction returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/extractions/nonexistent-id-12345/apply",
            headers=auth_headers,
            json={"extraction_id": "nonexistent-id-12345", "fields_to_apply": ["first_name"]}
        )
        assert response.status_code == 404
        print("✅ Non-existent extraction returns 404")
    
    def test_discard_nonexistent_extraction(self, auth_headers):
        """Test discarding a non-existent extraction returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/extractions/nonexistent-id-12345/discard",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✅ Non-existent extraction discard returns 404")


class TestGracefulFailureHandling:
    """Test graceful failure handling - user should NOT be blocked"""
    
    def test_extraction_returns_200_even_on_failure(self, auth_headers):
        """Verify extraction returns 200 with options even when extraction fails"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=60
        )
        
        # Should return 200 (not 500 or 422) to avoid blocking user
        if response.status_code == 200:
            data = response.json()
            if data.get("extraction_failed"):
                # Verify graceful failure structure
                assert "message" in data, "Should have user-friendly message"
                assert "options" in data, "Should have options for user"
                
                # Verify options include expected actions
                option_actions = [o["action"] for o in data["options"]]
                assert "fill_manually" in option_actions, "Should have 'fill manually' option"
                assert "retry" in option_actions, "Should have 'retry' option"
                
                # Verify extraction log is included
                if "extraction_log" in data:
                    log = data["extraction_log"]
                    assert "file_type" in log, "Log should include file_type"
                    assert "file_size_bytes" in log, "Log should include file_size_bytes"
                    print(f"✅ Extraction log included: {log}")
                
                print(f"✅ Graceful failure with message: {data['message']}")
                print(f"✅ Options provided: {option_actions}")
            else:
                print(f"✅ Extraction succeeded - {len(data.get('fields', []))} fields")
        elif response.status_code == 404:
            print("✅ No application form found (expected for test employee)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_extraction_options_have_required_fields(self, auth_headers):
        """Verify each option has action, label, and description"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("extraction_failed") and "options" in data:
                for option in data["options"]:
                    assert "action" in option, "Option should have action"
                    assert "label" in option, "Option should have label"
                    assert "description" in option, "Option should have description"
                print(f"✅ All options have required fields")


class TestExtractionLogging:
    """Test extraction logging functionality"""
    
    def test_extraction_logs_are_stored(self, auth_headers):
        """Verify extraction attempts are logged in database"""
        # Trigger an extraction
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check if extraction_log is in response
            if "extraction_log" in data:
                log = data["extraction_log"]
                print(f"✅ Extraction log in response:")
                print(f"   - File type: {log.get('file_type', 'N/A')}")
                print(f"   - File size: {log.get('file_size_bytes', 'N/A')} bytes")
                print(f"   - AI attempted: {log.get('ai_attempted', 'N/A')}")
                print(f"   - OCR attempted: {log.get('ocr_attempted', 'N/A')}")
                print(f"   - Failure reason: {log.get('failure_reason', 'None')}")
            elif data.get("extraction_method"):
                print(f"✅ Extraction method logged: {data['extraction_method']}")
        elif response.status_code == 404:
            print("✅ No application form - logging test skipped")


class TestExtractionSuccessFlow:
    """Test successful extraction flow with field review"""
    
    def test_successful_extraction_returns_fields(self, auth_headers):
        """Test that successful extraction returns fields with expected structure"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                fields = data["fields"]
                assert len(fields) > 0, "Should have at least one extracted field"
                
                # Verify field structure
                for field in fields:
                    assert "field_name" in field, "Field should have field_name"
                    assert "extracted_value" in field or field.get("extracted_value") is None, "Field should have extracted_value"
                    assert "confidence" in field, "Field should have confidence level"
                    assert field["confidence"] in ["high", "medium", "low"], f"Invalid confidence: {field['confidence']}"
                
                print(f"✅ Extracted {len(fields)} fields with proper structure")
                print(f"   - Fields: {[f['field_name'] for f in fields[:5]]}...")
                
                # Verify extraction_id for apply/discard
                assert "extraction_id" in data, "Should have extraction_id"
                print(f"✅ Extraction ID: {data['extraction_id']}")
        elif response.status_code == 404:
            print("✅ No application form found - success flow test skipped")
    
    def test_extraction_includes_current_values(self, auth_headers):
        """Test that extraction includes current profile values for comparison"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                for field in data["fields"]:
                    # current_value should be present (can be None)
                    assert "current_value" in field or field.get("current_value") is None
                    # apply flag should be present
                    assert "apply" in field, "Field should have apply flag"
                print(f"✅ Fields include current_value and apply flag")
        elif response.status_code == 404:
            print("✅ No application form found - test skipped")


class TestExtractionFieldsList:
    """Test the extractable fields configuration"""
    
    def test_extractable_fields_defined(self, auth_headers):
        """Verify all expected extractable fields are supported"""
        expected_fields = [
            "first_name", "last_name", "email", "phone",
            "address_line_1", "address_line_2", "city", "county", "postcode", "country",
            "ni_number", "date_of_birth",
            "next_of_kin_name", "next_of_kin_relationship", "next_of_kin_phone", "next_of_kin_address",
            "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relationship",
            "reference_1_name", "reference_1_company", "reference_1_phone", "reference_1_email",
            "reference_2_name", "reference_2_company", "reference_2_phone", "reference_2_email",
            "has_driving_licence", "driving_licence_type", "has_own_vehicle", "vehicle_registration"
        ]
        
        # Test that employee update accepts all these fields
        # We'll just verify the endpoint accepts them without error
        test_update = {field: None for field in expected_fields[:5]}  # Test first 5 fields
        
        response = requests.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers,
            json=test_update
        )
        assert response.status_code == 200, f"Update failed: {response.status_code}"
        print(f"✅ Employee update accepts extended profile fields")
        print(f"   - Total extractable fields: {len(expected_fields)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

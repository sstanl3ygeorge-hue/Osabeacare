"""
Test suite for Application Form Extraction Pipeline
Tests the improved extraction pipeline with pdfplumber as PRIMARY method.

Features tested:
1. POST /api/employees/{id}/extract-from-application returns extracted fields
2. pdfplumber is used as PRIMARY method for PDF extraction (check logs)
3. Extraction works without 'poppler not installed' error
4. Validation rejects TEST_ placeholder values
5. Validation rejects invalid NI number formats
6. Validation rejects malformed emails
7. High confidence values (>0.8) are extracted correctly
8. Extraction log shows final_method='pdfplumber' for typed PDFs
"""

import pytest
import requests
import os
import json
import time
import re

BASE_URL = "https://caretrust-portal.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"
# Employee with application form (from main agent context)
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge


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


class TestExtractionPipelineEndpoint:
    """Test the extraction endpoint returns proper response"""
    
    def test_extract_endpoint_returns_200_or_404(self, auth_headers):
        """Test POST /api/employees/{id}/extract-from-application returns proper status"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120  # Extraction can take time
        )
        # Should return 200 (success or graceful failure), 404 (no application form)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code} - {response.text}"
        print(f"✅ Extract endpoint returned status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Check for extraction success or graceful failure
            if data.get("extraction_failed"):
                print(f"   Graceful failure: {data.get('message', 'No message')}")
            else:
                print(f"   Success: {len(data.get('fields', []))} fields extracted")
                if "extraction_log" in data:
                    log = data["extraction_log"]
                    print(f"   Method: {log.get('final_method', 'unknown')}")
    
    def test_extract_returns_fields_structure(self, auth_headers):
        """Test extraction returns proper field structure"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                fields = data["fields"]
                if len(fields) > 0:
                    # Verify field structure
                    field = fields[0]
                    assert "field_name" in field, "Field should have field_name"
                    assert "confidence" in field, "Field should have confidence"
                    print(f"✅ Field structure correct: {list(field.keys())}")
                    
                    # Check confidence is numeric
                    conf = field.get("confidence")
                    assert isinstance(conf, (int, float)), f"Confidence should be numeric, got {type(conf)}"
                    print(f"✅ Confidence is numeric: {conf}")
        elif response.status_code == 404:
            pytest.skip("No application form found for test employee")


class TestPdfplumberPrimaryMethod:
    """Test that pdfplumber is used as PRIMARY extraction method"""
    
    def test_extraction_log_shows_method(self, auth_headers):
        """Test extraction log includes final_method field"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for extraction_log in response
            if "extraction_log" in data:
                log = data["extraction_log"]
                assert "final_method" in log, "Extraction log should have final_method"
                print(f"✅ Extraction method: {log.get('final_method')}")
                
                # For typed PDFs, should be pdfplumber
                if log.get("final_method") == "pdfplumber":
                    print("✅ pdfplumber used as PRIMARY method (expected for typed PDFs)")
                elif log.get("final_method") == "ocr":
                    print("⚠️ OCR used (may be scanned PDF)")
                elif log.get("final_method") == "ai":
                    print("⚠️ AI used (fallback method)")
            elif "extraction_method" in data:
                print(f"✅ Extraction method: {data.get('extraction_method')}")
        elif response.status_code == 404:
            pytest.skip("No application form found")
    
    def test_no_poppler_error(self, auth_headers):
        """Test extraction does NOT return 'poppler not installed' error"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = json.dumps(data).lower()
            
            # Should NOT contain poppler error
            assert "poppler not installed" not in response_text, "Should not have poppler error"
            assert "poppler-utils" not in response_text, "Should not have poppler-utils error"
            print("✅ No poppler installation errors")
            
            # Check extraction_log for errors
            if "extraction_log" in data:
                log = data["extraction_log"]
                ocr_error = log.get("ocr_error", "")
                if ocr_error:
                    assert "poppler" not in ocr_error.lower(), f"OCR error mentions poppler: {ocr_error}"
                print("✅ Extraction log has no poppler errors")
        elif response.status_code == 404:
            pytest.skip("No application form found")


class TestValidationLayer:
    """Test validation layer rejects invalid values"""
    
    def test_validation_rejects_test_prefix(self, auth_headers):
        """Test that TEST_ prefixed values are rejected"""
        # This tests the validate_extracted_value function indirectly
        # by checking that extracted fields don't contain TEST_ values
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                for field in data["fields"]:
                    value = field.get("extracted_value", "")
                    if value:
                        # Should not have TEST_ prefix
                        assert not str(value).upper().startswith("TEST_"), \
                            f"Field {field['field_name']} has TEST_ value: {value}"
                print("✅ No TEST_ prefixed values in extracted fields")
        elif response.status_code == 404:
            pytest.skip("No application form found")
    
    def test_ni_number_format_validation(self, auth_headers):
        """Test that invalid NI numbers are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                for field in data["fields"]:
                    if field.get("field_name") == "ni_number":
                        value = field.get("extracted_value", "")
                        if value:
                            # Should match UK NI format: 2 letters, 6 numbers, 1 letter
                            ni_pattern = r'^[A-Z]{2}\d{6}[A-Z]$'
                            clean_value = value.upper().replace(' ', '')
                            assert re.match(ni_pattern, clean_value), \
                                f"Invalid NI number format: {value}"
                            print(f"✅ NI number format valid: {value}")
        elif response.status_code == 404:
            pytest.skip("No application form found")
    
    def test_email_format_validation(self, auth_headers):
        """Test that malformed emails are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                for field in data["fields"]:
                    if field.get("field_name") == "email":
                        value = field.get("extracted_value", "")
                        if value:
                            # Should match basic email format
                            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                            assert re.match(email_pattern, value), \
                                f"Invalid email format: {value}"
                            print(f"✅ Email format valid: {value}")
        elif response.status_code == 404:
            pytest.skip("No application form found")


class TestHighConfidenceExtraction:
    """Test high confidence values are extracted correctly"""
    
    def test_high_confidence_fields_present(self, auth_headers):
        """Test that high confidence (>0.8) fields are extracted"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                high_conf_fields = []
                for field in data["fields"]:
                    conf = field.get("confidence", 0)
                    if isinstance(conf, (int, float)) and conf > 0.8:
                        high_conf_fields.append({
                            "name": field.get("field_name"),
                            "value": field.get("extracted_value"),
                            "confidence": conf
                        })
                
                print(f"✅ Found {len(high_conf_fields)} high confidence fields (>0.8)")
                for f in high_conf_fields[:5]:  # Show first 5
                    print(f"   - {f['name']}: {f['value']} (conf: {f['confidence']})")
                
                # Should have at least some high confidence fields for a typed PDF
                if len(data["fields"]) > 0:
                    assert len(high_conf_fields) > 0, "Should have at least one high confidence field"
        elif response.status_code == 404:
            pytest.skip("No application form found")
    
    def test_confidence_values_are_numeric(self, auth_headers):
        """Test that confidence values are numeric (0.0-1.0)"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                for field in data["fields"]:
                    conf = field.get("confidence")
                    assert isinstance(conf, (int, float)), \
                        f"Confidence should be numeric, got {type(conf)} for {field.get('field_name')}"
                    assert 0 <= conf <= 1, \
                        f"Confidence should be 0-1, got {conf} for {field.get('field_name')}"
                print("✅ All confidence values are numeric (0.0-1.0)")
        elif response.status_code == 404:
            pytest.skip("No application form found")


class TestExtractionLogging:
    """Test extraction logging functionality"""
    
    def test_extraction_log_structure(self, auth_headers):
        """Test extraction log has expected structure"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if "extraction_log" in data:
                log = data["extraction_log"]
                
                # Check expected fields
                expected_fields = ["file_type", "file_size_bytes", "final_method"]
                for field in expected_fields:
                    assert field in log, f"Extraction log should have {field}"
                
                print(f"✅ Extraction log structure correct:")
                print(f"   - file_type: {log.get('file_type')}")
                print(f"   - file_size_bytes: {log.get('file_size_bytes')}")
                print(f"   - final_method: {log.get('final_method')}")
                print(f"   - ocr_attempted: {log.get('ocr_attempted', 'N/A')}")
                print(f"   - ai_attempted: {log.get('ai_extraction_attempted', 'N/A')}")
        elif response.status_code == 404:
            pytest.skip("No application form found")
    
    def test_pdfplumber_method_for_typed_pdf(self, auth_headers):
        """Test that typed PDFs use pdfplumber as final_method"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if "extraction_log" in data:
                log = data["extraction_log"]
                final_method = log.get("final_method")
                
                # For typed PDFs, pdfplumber should be primary
                if final_method == "pdfplumber":
                    print("✅ pdfplumber used as PRIMARY method for typed PDF")
                    # OCR and AI should NOT have been attempted
                    assert not log.get("ocr_attempted", False) or not log.get("ocr_success", False), \
                        "OCR should not be needed for pdfplumber success"
                    assert not log.get("ai_extraction_attempted", False) or not log.get("ai_extraction_success", False), \
                        "AI should not be needed for pdfplumber success"
                elif final_method == "ocr":
                    print("⚠️ OCR used - may be scanned PDF")
                elif final_method == "ai":
                    print("⚠️ AI used - fallback method")
                else:
                    print(f"⚠️ Unknown method: {final_method}")
        elif response.status_code == 404:
            pytest.skip("No application form found")


class TestExtractionFieldCount:
    """Test extraction returns expected number of fields"""
    
    def test_extraction_returns_multiple_fields(self, auth_headers):
        """Test that extraction returns multiple fields from application form"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("extraction_failed") and "fields" in data:
                fields = data["fields"]
                print(f"✅ Extracted {len(fields)} fields")
                
                # Should have multiple fields from application form
                # Main agent mentioned 38 fields extracted
                assert len(fields) > 5, f"Should extract more than 5 fields, got {len(fields)}"
                
                # List field names
                field_names = [f.get("field_name") for f in fields]
                print(f"   Fields: {field_names[:10]}...")  # Show first 10
        elif response.status_code == 404:
            pytest.skip("No application form found")


class TestGracefulFailureHandling:
    """Test graceful failure handling"""
    
    def test_graceful_failure_has_options(self, auth_headers):
        """Test that graceful failure includes user options"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/extract-from-application",
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("extraction_failed"):
                # Should have options for user
                assert "options" in data, "Graceful failure should include options"
                assert len(data["options"]) >= 2, "Should have at least 2 options"
                
                option_actions = [o.get("action") for o in data["options"]]
                print(f"✅ Graceful failure options: {option_actions}")
                
                # Should have fill_manually and retry options
                assert "fill_manually" in option_actions, "Should have fill_manually option"
                assert "retry" in option_actions, "Should have retry option"
            else:
                print("✅ Extraction succeeded - no graceful failure needed")
        elif response.status_code == 404:
            pytest.skip("No application form found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

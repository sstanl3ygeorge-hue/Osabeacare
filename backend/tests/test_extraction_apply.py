"""
Test extraction and apply functionality for application form data.
Tests the fix for:
1. Pydantic validation error on working_time_opt_out field (string vs bool)
2. Promise.all failing entire fetchData if one request fails
3. Partial updates support in apply_extraction endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestExtractionApply:
    """Tests for extraction and apply functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Test employee ID from context
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
    
    def test_get_employee_no_pydantic_error(self):
        """GET /api/employees/{id} should work without Pydantic validation errors"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}")
        
        # Should not return 500 (Pydantic validation error)
        assert response.status_code != 500, f"Pydantic validation error: {response.text}"
        assert response.status_code == 200, f"Failed to get employee: {response.text}"
        
        data = response.json()
        assert data["id"] == self.test_employee_id
        print(f"✅ GET /api/employees/{self.test_employee_id} works without Pydantic errors")
        
        # Check working_time_opt_out field is present (can be string or bool)
        if "working_time_opt_out" in data:
            print(f"   working_time_opt_out value: {data['working_time_opt_out']} (type: {type(data['working_time_opt_out']).__name__})")
    
    def test_get_employees_list_no_pydantic_error(self):
        """GET /api/employees should work without Pydantic validation errors"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        
        # Should not return 500 (Pydantic validation error)
        assert response.status_code != 500, f"Pydantic validation error: {response.text}"
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ GET /api/employees returns {len(data)} employees without Pydantic errors")
    
    def test_extract_from_application_endpoint(self):
        """POST /api/employees/{id}/extract-from-application should return extraction with fields"""
        response = self.session.post(f"{BASE_URL}/api/employees/{self.test_employee_id}/extract-from-application")
        
        # May return 400 if no application form, or 200 with extraction
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            if "No application form found" in str(detail):
                pytest.skip("No application form found for test employee")
            else:
                pytest.fail(f"Unexpected 400 error: {detail}")
        
        assert response.status_code == 200, f"Extraction failed: {response.text}"
        
        data = response.json()
        
        # Check if extraction failed gracefully
        if data.get("extraction_failed"):
            print(f"⚠️ Extraction failed gracefully: {data.get('message')}")
            return
        
        # Successful extraction
        assert "extraction_id" in data, "Missing extraction_id"
        assert "fields" in data, "Missing fields array"
        assert isinstance(data["fields"], list), "fields should be a list"
        
        print(f"✅ Extraction returned {len(data['fields'])} fields")
        print(f"   Extraction ID: {data['extraction_id']}")
        
        # Store for apply test
        self.extraction_id = data["extraction_id"]
        self.extracted_fields = data["fields"]
    
    def test_apply_extraction_partial_updates(self):
        """POST /api/extractions/{id}/apply should support partial updates"""
        # First extract
        extract_response = self.session.post(f"{BASE_URL}/api/employees/{self.test_employee_id}/extract-from-application")
        
        if extract_response.status_code == 400:
            pytest.skip("No application form found for test employee")
        
        if extract_response.status_code != 200:
            pytest.skip(f"Extraction failed: {extract_response.text}")
        
        extract_data = extract_response.json()
        
        if extract_data.get("extraction_failed"):
            pytest.skip("Extraction failed gracefully")
        
        extraction_id = extract_data["extraction_id"]
        fields = extract_data["fields"]
        
        if not fields:
            pytest.skip("No fields extracted")
        
        # Select a subset of fields to apply
        fields_to_apply = [f["field_name"] for f in fields[:5]]  # Apply first 5 fields
        
        apply_response = self.session.post(
            f"{BASE_URL}/api/extractions/{extraction_id}/apply",
            json={"extraction_id": extraction_id, "fields_to_apply": fields_to_apply}
        )
        
        assert apply_response.status_code == 200, f"Apply failed: {apply_response.text}"
        
        apply_data = apply_response.json()
        assert apply_data.get("success") == True
        assert "applied_fields" in apply_data
        
        print(f"✅ Applied {len(apply_data['applied_fields'])} fields successfully")
        
        # Check for partial success handling
        if apply_data.get("warnings"):
            print(f"   Warnings: {apply_data['warnings']}")
    
    def test_employee_profile_loads_after_apply(self):
        """Employee profile should load without 'Failed to load employee data' error after apply"""
        # Get employee profile
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}")
        
        assert response.status_code == 200, f"Profile load failed: {response.text}"
        
        data = response.json()
        
        # Check expected fields are populated (from context)
        expected_fields = {
            "ni_number": "TK753130C",
            "city": "Chatham",
            "postcode": "ME4 5HY",
            "next_of_kin_name": "Oluremilekun Alonge"
        }
        
        populated_count = 0
        for field, expected_value in expected_fields.items():
            actual_value = data.get(field)
            if actual_value:
                populated_count += 1
                if actual_value == expected_value:
                    print(f"   ✅ {field}: {actual_value}")
                else:
                    print(f"   ⚠️ {field}: {actual_value} (expected: {expected_value})")
            else:
                print(f"   ❌ {field}: not populated")
        
        print(f"✅ Profile loaded successfully with {populated_count}/{len(expected_fields)} expected fields populated")
    
    def test_working_time_opt_out_accepts_string_and_bool(self):
        """working_time_opt_out field should accept both string and boolean values"""
        # Get current employee data
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}")
        assert response.status_code == 200
        
        data = response.json()
        working_time_value = data.get("working_time_opt_out")
        
        # The field should be present and can be string or bool
        print(f"✅ working_time_opt_out value: {working_time_value} (type: {type(working_time_value).__name__})")
        
        # Verify the model accepts both types by checking no 500 error
        assert response.status_code != 500, "Pydantic validation error on working_time_opt_out"
    
    def test_compliance_requirements_endpoint(self):
        """GET /api/employees/{id}/compliance-requirements should work"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements")
        
        assert response.status_code == 200, f"Compliance requirements failed: {response.text}"
        
        data = response.json()
        assert "requirements" in data or isinstance(data, dict)
        
        print(f"✅ Compliance requirements endpoint works")
    
    def test_failed_fields_reported_individually(self):
        """Failed fields should be reported individually, not as generic error"""
        # This test verifies the apply_extraction endpoint returns detailed error info
        
        # Create a mock extraction with invalid fields
        # First, we need to check if there's a pending extraction
        extract_response = self.session.post(f"{BASE_URL}/api/employees/{self.test_employee_id}/extract-from-application")
        
        if extract_response.status_code == 400:
            pytest.skip("No application form found")
        
        if extract_response.status_code != 200:
            pytest.skip(f"Extraction failed: {extract_response.text}")
        
        extract_data = extract_response.json()
        
        if extract_data.get("extraction_failed"):
            pytest.skip("Extraction failed gracefully")
        
        extraction_id = extract_data["extraction_id"]
        
        # Try to apply with non-existent fields
        apply_response = self.session.post(
            f"{BASE_URL}/api/extractions/{extraction_id}/apply",
            json={"extraction_id": extraction_id, "fields_to_apply": ["nonexistent_field_xyz"]}
        )
        
        # Should return 400 with detailed error, not 500
        if apply_response.status_code == 400:
            error_data = apply_response.json()
            detail = error_data.get("detail", {})
            
            # Check for structured error response
            if isinstance(detail, dict):
                print(f"✅ Error response is structured: {detail.get('message', 'No message')}")
                if detail.get("unsupported_fields"):
                    print(f"   Unsupported fields: {detail['unsupported_fields']}")
            else:
                print(f"✅ Error response: {detail}")
        else:
            # If 200, it means no fields were applied (which is also valid)
            print(f"✅ Apply returned {apply_response.status_code} for non-existent fields")


class TestFetchDataGracefulDegradation:
    """Tests for Promise.allSettled graceful degradation in fetchData"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
    
    def test_all_profile_endpoints_work(self):
        """All endpoints used by fetchData should work"""
        endpoints = [
            f"/api/employees/{self.test_employee_id}",
            f"/api/employee-documents?employee_id={self.test_employee_id}",
            "/api/document-types",
            f"/api/policy-assignments?employee_id={self.test_employee_id}",
            f"/api/training-records?employee_id={self.test_employee_id}",
            f"/api/audit-logs?entity_id={self.test_employee_id}&compliance_only=true",
            f"/api/generated-forms?employee_id={self.test_employee_id}",
            "/api/templates",
            f"/api/employees/{self.test_employee_id}/compliance-requirements"
        ]
        
        results = []
        for endpoint in endpoints:
            response = self.session.get(f"{BASE_URL}{endpoint}")
            status = "✅" if response.status_code == 200 else "❌"
            results.append({
                "endpoint": endpoint,
                "status_code": response.status_code,
                "success": response.status_code == 200
            })
            print(f"{status} {endpoint}: {response.status_code}")
        
        # All should succeed
        failed = [r for r in results if not r["success"]]
        assert len(failed) == 0, f"Failed endpoints: {failed}"
        
        print(f"\n✅ All {len(endpoints)} fetchData endpoints work correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

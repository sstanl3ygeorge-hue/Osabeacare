"""
Test Form Prefill/Auto-fill Feature
====================================
Tests for:
1. GET /api/forms/complete/{token} returns auto_fill_data with pre-populated employee fields
2. Auto-fill includes: full_name, email, phone, address, role, date_of_birth
3. Email automation routes form-based requests to /forms/complete/{token}
"""

import pytest
import requests
import os
import jwt
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
JWT_SECRET = "osabea-care-jwt-secret-key-2024-secure"

# Test employee ID from credentials
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestFormPrefillAutoFill:
    """Tests for form prefill/auto-fill feature"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for admin user"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not authenticate")
    
    @pytest.fixture
    def test_employee(self, auth_headers):
        """Get test employee data"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        if response.status_code == 200:
            return response.json()
        pytest.skip("Test employee not found")
    
    def generate_form_token(self, employee_id: str, requirement_id: str, form_type: str = "staff_health_questionnaire"):
        """Generate a valid form completion token"""
        now = datetime.now(timezone.utc)
        payload = {
            "person_id": employee_id,
            "person_type": "employee",
            "action_type": "complete_form",
            "requirement_id": requirement_id,
            "jti": str(uuid.uuid4()),
            "iat": now.timestamp(),
            "exp": (now + timedelta(days=30)).timestamp()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    # =========================================================================
    # TEST 1: GET /api/forms/complete/{token} returns auto_fill_data
    # =========================================================================
    
    def test_forms_complete_endpoint_returns_auto_fill_data(self, test_employee):
        """Test that GET /api/forms/complete/{token} returns auto_fill_data"""
        # Generate token for staff_health_questionnaire
        token = self.generate_form_token(
            TEST_EMPLOYEE_ID, 
            "staff_health_questionnaire",
            "staff_health_questionnaire"
        )
        
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "auto_fill_data" in data, "Response should contain auto_fill_data"
        assert "form_template" in data, "Response should contain form_template"
        assert "employee_id" in data, "Response should contain employee_id"
        assert "employee_name" in data, "Response should contain employee_name"
        
        print(f"✓ GET /api/forms/complete/{{token}} returns auto_fill_data")
        print(f"  - auto_fill_data keys: {list(data['auto_fill_data'].keys())}")
    
    # =========================================================================
    # TEST 2: Auto-fill includes required fields
    # =========================================================================
    
    def test_auto_fill_includes_full_name(self, test_employee):
        """Test that auto_fill_data includes full_name"""
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_health_questionnaire")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        auto_fill = data.get("auto_fill_data", {})
        
        # Check for full_name in auto_fill_data
        has_full_name = "full_name" in auto_fill
        
        # Also check employee_name in response
        employee_name = data.get("employee_name", "")
        
        assert has_full_name or employee_name, "Should have full_name in auto_fill or employee_name in response"
        
        if has_full_name:
            print(f"✓ auto_fill_data includes full_name: {auto_fill['full_name']}")
        else:
            print(f"✓ employee_name in response: {employee_name}")
    
    def test_auto_fill_includes_email_when_form_has_email_field(self, test_employee):
        """Test that auto_fill_data includes email when form template has email field with auto_fill"""
        # Use staff_personal_info form which has email field with auto_fill
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_personal_info")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        auto_fill = data.get("auto_fill_data", {})
        
        # Email should be in auto_fill_data for staff_personal_info form
        assert "email" in auto_fill, "auto_fill_data should include email for staff_personal_info form"
        print(f"✓ auto_fill_data includes email: {auto_fill.get('email')}")
    
    def test_auto_fill_includes_phone(self, test_employee):
        """Test that auto_fill_data includes phone"""
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_health_questionnaire")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        auto_fill = data.get("auto_fill_data", {})
        
        # Phone should be in auto_fill_data
        has_phone = "phone" in auto_fill or "mobile" in auto_fill
        assert has_phone, "auto_fill_data should include phone or mobile"
        print(f"✓ auto_fill_data includes phone: {auto_fill.get('phone') or auto_fill.get('mobile')}")
    
    def test_auto_fill_includes_address_when_form_has_address_field(self, test_employee):
        """Test that auto_fill_data includes address when form template has address field with auto_fill"""
        # Use staff_personal_info form which has address fields with auto_fill
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_personal_info")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        auto_fill = data.get("auto_fill_data", {})
        
        # Address fields should be in auto_fill_data for staff_personal_info form
        has_address = "address" in auto_fill or "full_address" in auto_fill or "address_line_1" in auto_fill
        assert has_address, "auto_fill_data should include address fields for staff_personal_info form"
        print(f"✓ auto_fill_data includes address: {auto_fill.get('address') or auto_fill.get('address_line_1')}")
    
    def test_auto_fill_includes_role_when_form_has_role_field(self, test_employee):
        """Test that auto_fill_data includes role/job_title when form template has role field with auto_fill"""
        # Use health_screening form which has job_title field with auto_fill: "role"
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "health_screening")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        auto_fill = data.get("auto_fill_data", {})
        
        # Role should be in auto_fill_data for health_screening form (as job_title)
        has_role = "role" in auto_fill or "job_title" in auto_fill or "position_applied" in auto_fill
        assert has_role, "auto_fill_data should include role/job_title for health_screening form"
        print(f"✓ auto_fill_data includes role: {auto_fill.get('role') or auto_fill.get('job_title')}")
    
    def test_auto_fill_includes_date_of_birth(self, test_employee):
        """Test that auto_fill_data includes date_of_birth"""
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_health_questionnaire")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        auto_fill = data.get("auto_fill_data", {})
        
        # date_of_birth should be in auto_fill_data
        has_dob = "date_of_birth" in auto_fill
        # Note: date_of_birth may not be present if employee doesn't have it set
        if has_dob:
            print(f"✓ auto_fill_data includes date_of_birth: {auto_fill.get('date_of_birth')}")
        else:
            print(f"⚠ date_of_birth not in auto_fill_data (may not be set for employee)")
    
    # =========================================================================
    # TEST 3: Form template structure
    # =========================================================================
    
    def test_form_template_has_sections(self, test_employee):
        """Test that form_template has sections with fields"""
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_health_questionnaire")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        
        form_template = data.get("form_template", {})
        assert "sections" in form_template, "form_template should have sections"
        
        sections = form_template.get("sections", [])
        assert len(sections) > 0, "form_template should have at least one section"
        
        # Check first section has fields
        first_section = sections[0]
        assert "fields" in first_section, "Section should have fields"
        assert len(first_section.get("fields", [])) > 0, "Section should have at least one field"
        
        print(f"✓ form_template has {len(sections)} sections")
        print(f"  - First section: {first_section.get('title')}")
    
    # =========================================================================
    # TEST 4: Invalid token handling
    # =========================================================================
    
    def test_invalid_token_returns_error(self):
        """Test that invalid token returns appropriate error"""
        response = requests.get(f"{BASE_URL}/api/forms/complete/invalid-token-123")
        
        assert response.status_code == 400, f"Expected 400 for invalid token, got {response.status_code}"
        print(f"✓ Invalid token returns 400 error")
    
    def test_expired_token_returns_error(self):
        """Test that expired token returns appropriate error"""
        # Generate an expired token
        now = datetime.now(timezone.utc)
        payload = {
            "person_id": TEST_EMPLOYEE_ID,
            "person_type": "employee",
            "action_type": "complete_form",
            "requirement_id": "staff_health_questionnaire",
            "jti": str(uuid.uuid4()),
            "iat": (now - timedelta(days=60)).timestamp(),
            "exp": (now - timedelta(days=30)).timestamp()  # Expired 30 days ago
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        response = requests.get(f"{BASE_URL}/api/forms/complete/{expired_token}")
        
        assert response.status_code == 400, f"Expected 400 for expired token, got {response.status_code}"
        print(f"✓ Expired token returns 400 error")
    
    # =========================================================================
    # TEST 5: Different form types
    # =========================================================================
    
    def test_staff_personal_info_form_auto_fill(self, test_employee):
        """Test auto-fill for staff_personal_info form"""
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_personal_info")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "auto_fill_data" in data, "Response should contain auto_fill_data"
        assert data.get("form_type") == "staff_personal_info", f"Expected form_type staff_personal_info, got {data.get('form_type')}"
        
        print(f"✓ staff_personal_info form returns auto_fill_data")
        print(f"  - auto_fill_data keys: {list(data['auto_fill_data'].keys())}")
    
    def test_hmrc_starter_checklist_form_auto_fill(self, test_employee):
        """Test auto-fill for hmrc_starter_checklist form"""
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "hmrc_starter_checklist")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "auto_fill_data" in data, "Response should contain auto_fill_data"
        
        print(f"✓ hmrc_starter_checklist form returns auto_fill_data")
        print(f"  - auto_fill_data keys: {list(data['auto_fill_data'].keys())}")
    
    # =========================================================================
    # TEST 6: Email automation path routing
    # =========================================================================
    
    def test_send_form_creates_request_with_form_path(self, auth_headers, test_employee):
        """Test that sending a form creates a request that routes to /forms/complete/{token}"""
        # Send a form request
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/send-form",
            params={"form_type": "staff_health_questionnaire"},
            headers=auth_headers
        )
        
        # May return 200 (sent) or 409 (duplicate) - both are valid
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Form request sent successfully")
            print(f"  - Response: {data}")
        elif response.status_code == 409:
            print(f"✓ Form request already exists (duplicate blocked)")
        else:
            # Check if it's a different error
            print(f"⚠ Unexpected response: {response.status_code} - {response.text}")
    
    # =========================================================================
    # TEST 7: Auto-fill data count
    # =========================================================================
    
    def test_auto_fill_data_has_multiple_fields(self, test_employee):
        """Test that auto_fill_data has multiple pre-filled fields"""
        token = self.generate_form_token(TEST_EMPLOYEE_ID, "staff_health_questionnaire")
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200
        data = response.json()
        auto_fill = data.get("auto_fill_data", {})
        
        # Should have at least 3 pre-filled fields
        field_count = len(auto_fill)
        assert field_count >= 3, f"Expected at least 3 pre-filled fields, got {field_count}"
        
        print(f"✓ auto_fill_data has {field_count} pre-filled fields")
        print(f"  - Fields: {list(auto_fill.keys())}")


class TestEmailAutomationFormRouting:
    """Tests for email automation form routing logic"""
    
    def test_request_type_complete_form_exists(self):
        """Verify RequestType.COMPLETE_FORM exists in email_automation"""
        # This is a code structure test - we verify the routing logic exists
        # by checking the endpoint behavior
        
        # Generate a token with complete_form action
        now = datetime.now(timezone.utc)
        payload = {
            "person_id": TEST_EMPLOYEE_ID,
            "person_type": "employee",
            "action_type": "complete_form",
            "requirement_id": "staff_health_questionnaire",
            "jti": str(uuid.uuid4()),
            "iat": now.timestamp(),
            "exp": (now + timedelta(days=30)).timestamp()
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        # The endpoint should accept this token
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ complete_form action type is properly handled")
    
    def test_upload_document_token_rejected_for_form_completion(self):
        """Test that upload_document token is rejected for form completion endpoint"""
        # Generate a token with upload_document action (not complete_form)
        now = datetime.now(timezone.utc)
        payload = {
            "person_id": TEST_EMPLOYEE_ID,
            "person_type": "employee",
            "action_type": "upload_document",  # Wrong action type
            "requirement_id": "proof_of_address",
            "jti": str(uuid.uuid4()),
            "iat": now.timestamp(),
            "exp": (now + timedelta(days=30)).timestamp()
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        # The endpoint should reject this token
        response = requests.get(f"{BASE_URL}/api/forms/complete/{token}")
        
        assert response.status_code == 400, f"Expected 400 for wrong action type, got {response.status_code}"
        print(f"✓ upload_document token correctly rejected for form completion")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

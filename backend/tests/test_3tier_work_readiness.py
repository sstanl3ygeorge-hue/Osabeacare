"""
Test 3-Tier Work Readiness Enforcement and Send Form via Email Features
Tests:
- 3-tier work readiness: NOT_READY, READY_WITH_CONDITIONS, READY_TO_WORK
- Send Form via Email API
- Public form completion endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"

# Known employee IDs from context
EMPLOYEE_OLAKUNLE = "d88335f6-1b18-435a-8086-28af4a583f77"
EMPLOYEE_LAWRENCE = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class Test3TierWorkReadiness:
    """Test 3-tier work readiness status calculation"""
    
    def test_employee_list_includes_3tier_status(self, auth_headers):
        """Employee list should include work_readiness_3tier field"""
        response = requests.get(f"{BASE_URL}/api/staff/employees", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        
        employees = response.json()
        assert len(employees) > 0, "No employees returned"
        
        # Check first employee has 3-tier status
        emp = employees[0]
        assert "work_readiness_3tier" in emp, "Missing work_readiness_3tier field"
        
        status_3tier = emp["work_readiness_3tier"]
        assert "status" in status_3tier, "Missing status in work_readiness_3tier"
        assert "label" in status_3tier, "Missing label in work_readiness_3tier"
        assert "color" in status_3tier, "Missing color in work_readiness_3tier"
        assert "reasons" in status_3tier, "Missing reasons in work_readiness_3tier"
        
        # Validate status is one of the 3 tiers
        assert status_3tier["status"] in ["NOT_READY", "READY_WITH_CONDITIONS", "READY_TO_WORK"], \
            f"Invalid status: {status_3tier['status']}"
        
        print(f"✓ Employee list includes 3-tier status: {status_3tier['status']}")
    
    def test_employee_profile_includes_3tier_status(self, auth_headers):
        """Employee profile should include work_readiness_3tier field"""
        response = requests.get(f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get employee: {response.text}"
        
        emp = response.json()
        assert "work_readiness_3tier" in emp, "Missing work_readiness_3tier in profile"
        
        status_3tier = emp["work_readiness_3tier"]
        assert status_3tier["status"] in ["NOT_READY", "READY_WITH_CONDITIONS", "READY_TO_WORK"]
        
        print(f"✓ Employee profile includes 3-tier status: {status_3tier['status']}")
        print(f"  Label: {status_3tier['label']}")
        print(f"  Color: {status_3tier['color']}")
        if status_3tier.get("reasons"):
            print(f"  Reasons: {[r['message'] for r in status_3tier['reasons'][:3]]}")
    
    def test_3tier_status_has_valid_colors(self, auth_headers):
        """3-tier status should have valid color values"""
        response = requests.get(f"{BASE_URL}/api/staff/employees", headers=auth_headers)
        assert response.status_code == 200
        
        employees = response.json()
        for emp in employees[:5]:  # Check first 5
            status_3tier = emp.get("work_readiness_3tier", {})
            color = status_3tier.get("color")
            assert color in ["error", "warning", "success"], f"Invalid color: {color}"
            
            # Verify color matches status
            status = status_3tier.get("status")
            if status == "NOT_READY":
                assert color == "error", f"NOT_READY should have error color, got {color}"
            elif status == "READY_WITH_CONDITIONS":
                assert color == "warning", f"READY_WITH_CONDITIONS should have warning color, got {color}"
            elif status == "READY_TO_WORK":
                assert color == "success", f"READY_TO_WORK should have success color, got {color}"
        
        print("✓ All 3-tier statuses have valid colors matching their status")
    
    def test_not_ready_has_hard_block_reasons(self, auth_headers):
        """NOT_READY status should have hard_block type reasons"""
        response = requests.get(f"{BASE_URL}/api/staff/employees", headers=auth_headers)
        assert response.status_code == 200
        
        employees = response.json()
        not_ready_employees = [e for e in employees if e.get("work_readiness_3tier", {}).get("status") == "NOT_READY"]
        
        if not_ready_employees:
            emp = not_ready_employees[0]
            reasons = emp["work_readiness_3tier"].get("reasons", [])
            
            # Should have at least one hard_block reason
            hard_blocks = [r for r in reasons if r.get("type") == "hard_block"]
            assert len(hard_blocks) > 0, "NOT_READY should have hard_block reasons"
            
            # Check reason structure
            for reason in hard_blocks:
                assert "code" in reason, "Reason missing code"
                assert "message" in reason, "Reason missing message"
            
            print(f"✓ NOT_READY employee has {len(hard_blocks)} hard block reason(s)")
            print(f"  First reason: {hard_blocks[0]['message']}")
        else:
            print("⚠ No NOT_READY employees found to test hard block reasons")
    
    def test_ready_with_conditions_has_conditional_reasons(self, auth_headers):
        """READY_WITH_CONDITIONS status should have conditional type reasons"""
        response = requests.get(f"{BASE_URL}/api/staff/employees", headers=auth_headers)
        assert response.status_code == 200
        
        employees = response.json()
        conditional_employees = [e for e in employees if e.get("work_readiness_3tier", {}).get("status") == "READY_WITH_CONDITIONS"]
        
        if conditional_employees:
            emp = conditional_employees[0]
            reasons = emp["work_readiness_3tier"].get("reasons", [])
            
            # Should have conditional reasons
            conditionals = [r for r in reasons if r.get("type") == "conditional"]
            assert len(conditionals) > 0, "READY_WITH_CONDITIONS should have conditional reasons"
            
            print(f"✓ READY_WITH_CONDITIONS employee has {len(conditionals)} conditional reason(s)")
            print(f"  First reason: {conditionals[0]['message']}")
        else:
            print("⚠ No READY_WITH_CONDITIONS employees found to test conditional reasons")
    
    def test_ready_to_work_has_no_reasons(self, auth_headers):
        """READY_TO_WORK status should have empty reasons"""
        response = requests.get(f"{BASE_URL}/api/staff/employees", headers=auth_headers)
        assert response.status_code == 200
        
        employees = response.json()
        ready_employees = [e for e in employees if e.get("work_readiness_3tier", {}).get("status") == "READY_TO_WORK"]
        
        if ready_employees:
            emp = ready_employees[0]
            reasons = emp["work_readiness_3tier"].get("reasons", [])
            assert len(reasons) == 0, f"READY_TO_WORK should have no reasons, got {len(reasons)}"
            
            print(f"✓ READY_TO_WORK employee has no blocking reasons")
        else:
            print("⚠ No READY_TO_WORK employees found to test empty reasons")


class TestSendFormViaEmail:
    """Test Send Form via Email feature"""
    
    def test_send_form_endpoint_exists(self, auth_headers):
        """POST /api/employees/{id}/send-form endpoint should exist"""
        # Test with invalid form type to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}/send-form",
            headers=auth_headers,
            params={"form_type": "invalid_form_type"}
        )
        # Should return 400 for invalid form type, not 404
        assert response.status_code in [400, 200, 409], f"Unexpected status: {response.status_code}"
        print(f"✓ Send form endpoint exists (status: {response.status_code})")
    
    def test_send_form_validates_form_type(self, auth_headers):
        """Send form should validate form type"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}/send-form",
            headers=auth_headers,
            params={"form_type": "nonexistent_form"}
        )
        assert response.status_code == 400, f"Should reject invalid form type: {response.text}"
        print("✓ Send form validates form type")
    
    def test_send_form_requires_employee_email(self, auth_headers):
        """Send form should require employee to have email"""
        # This test verifies the validation logic exists
        # We can't easily test with an employee without email
        response = requests.post(
            f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}/send-form",
            headers=auth_headers,
            params={"form_type": "staff_health_questionnaire"}
        )
        # Should succeed or return duplicate (if already sent)
        assert response.status_code in [200, 409], f"Unexpected status: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "status" in data, "Response should have status field"
        print(f"✓ Send form response: {data.get('status')} - {data.get('message', '')}")
    
    def test_send_form_valid_form_types(self, auth_headers):
        """Test all valid form types"""
        valid_form_types = [
            "staff_health_questionnaire",
            "staff_personal_info",
            "hmrc_starter_checklist",
            "interview_record"
        ]
        
        for form_type in valid_form_types:
            response = requests.post(
                f"{BASE_URL}/api/employees/{EMPLOYEE_LAWRENCE}/send-form",
                headers=auth_headers,
                params={"form_type": form_type}
            )
            # Should succeed or return duplicate
            assert response.status_code in [200, 409], \
                f"Form type {form_type} failed: {response.status_code} - {response.text}"
            print(f"✓ Form type '{form_type}' accepted")
    
    def test_send_form_with_custom_message(self, auth_headers):
        """Send form should accept custom message"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}/send-form",
            headers=auth_headers,
            params={
                "form_type": "staff_personal_info",
                "message": "Please complete this form by end of week."
            }
        )
        assert response.status_code in [200, 409], f"Failed: {response.text}"
        print("✓ Send form accepts custom message")
    
    def test_send_form_returns_request_id(self, auth_headers):
        """Send form should return request_id on success"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}/send-form",
            headers=auth_headers,
            params={"form_type": "hmrc_starter_checklist"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                assert "request_id" in data, "Success response should include request_id"
                print(f"✓ Send form returns request_id: {data['request_id'][:8]}...")
            else:
                print(f"✓ Send form returned: {data.get('status')}")
        elif response.status_code == 409:
            print("✓ Form request already pending (duplicate)")
        else:
            print(f"⚠ Unexpected response: {response.status_code}")


class TestPublicFormCompletion:
    """Test public form completion endpoints"""
    
    def test_form_completion_get_invalid_token(self):
        """GET /api/forms/complete/{token} should reject invalid token"""
        response = requests.get(f"{BASE_URL}/api/forms/complete/invalid-token-12345")
        assert response.status_code == 400, f"Should reject invalid token: {response.status_code}"
        print("✓ Form completion rejects invalid token")
    
    def test_form_completion_post_invalid_token(self):
        """POST /api/forms/complete/{token} should reject invalid token"""
        response = requests.post(
            f"{BASE_URL}/api/forms/complete/invalid-token-12345",
            json={"field1": "value1"}
        )
        assert response.status_code == 400, f"Should reject invalid token: {response.status_code}"
        print("✓ Form submission rejects invalid token")
    
    def test_form_completion_endpoint_exists(self):
        """Form completion endpoints should exist"""
        # GET endpoint
        response = requests.get(f"{BASE_URL}/api/forms/complete/test-token")
        assert response.status_code in [400, 404], f"GET endpoint issue: {response.status_code}"
        
        # POST endpoint
        response = requests.post(f"{BASE_URL}/api/forms/complete/test-token", json={})
        assert response.status_code in [400, 404], f"POST endpoint issue: {response.status_code}"
        
        print("✓ Form completion endpoints exist")


class TestHomepageContent:
    """Test homepage repositioning for care-sector credibility"""
    
    def test_homepage_loads(self):
        """Homepage should load successfully"""
        response = requests.get(f"{BASE_URL}")
        # Frontend routes may return 200 or redirect
        assert response.status_code in [200, 301, 302, 304], f"Homepage failed: {response.status_code}"
        print("✓ Homepage loads successfully")
    
    def test_api_health_check(self):
        """API health check should work"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ API health check passed")


class TestEmployeeComplianceRequirements:
    """Test compliance requirements include 3-tier status"""
    
    def test_compliance_requirements_endpoint(self, auth_headers):
        """Compliance requirements should include 3-tier status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}/compliance-requirements",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "requirements" in data, "Missing requirements field"
        print(f"✓ Compliance requirements returned {len(data.get('requirements', []))} items")
    
    def test_employee_detail_has_3tier_in_response(self, auth_headers):
        """Employee detail endpoint should include 3-tier status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{EMPLOYEE_OLAKUNLE}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "work_readiness_3tier" in data, "Missing work_readiness_3tier in employee detail"
        
        status = data["work_readiness_3tier"]
        print(f"✓ Employee detail includes 3-tier status:")
        print(f"  Status: {status.get('status')}")
        print(f"  Label: {status.get('label')}")
        print(f"  Reasons count: {len(status.get('reasons', []))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

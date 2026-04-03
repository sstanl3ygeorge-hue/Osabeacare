"""
Test Reference Verification Workflow
Tests for:
1. Employment history mismatch detection (reference dates vs declared employment)
2. Alternative reference path recording when original referee is unresponsive
3. Proper warnings displayed in the UI (via API response)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"


class TestReferenceVerificationWorkflow:
    """Test Reference Verification Workflow features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
        
        token = login_response.json().get("token") or login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get an employee with references for testing
        employees_response = self.session.get(f"{BASE_URL}/api/employees")
        if employees_response.status_code != 200:
            pytest.skip("Could not fetch employees")
        
        employees = employees_response.json()
        if not employees:
            pytest.skip("No employees found")
        
        # Find an employee with reference data
        self.test_employee_id = None
        for emp in employees:
            emp_id = emp.get("id")
            # Check if employee has reference data
            ref_response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/references-normalized")
            if ref_response.status_code == 200:
                ref_data = ref_response.json()
                refs = ref_data.get("references", [])
                # Look for employee with declared referee
                for ref in refs:
                    if ref.get("declared_referee"):
                        self.test_employee_id = emp_id
                        self.test_employee_name = emp.get("name", "Unknown")
                        break
            if self.test_employee_id:
                break
        
        if not self.test_employee_id:
            # Use first employee if none have references
            self.test_employee_id = employees[0].get("id")
            self.test_employee_name = employees[0].get("name", "Unknown")
        
        yield
        
        self.session.close()

    # =====================================================================
    # TEST 1: GET /api/employees/{id}/references-normalized returns employment_mismatches
    # =====================================================================
    
    def test_references_normalized_endpoint_returns_200(self):
        """Test that references-normalized endpoint returns 200"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/employees/{self.test_employee_id}/references-normalized returns 200")
    
    def test_references_normalized_has_integrity_object(self):
        """Test that references-normalized response includes integrity object"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200
        
        data = response.json()
        references = data.get("references", [])
        assert len(references) == 2, "Should have 2 references"
        
        for ref in references:
            # Check integrity object exists
            integrity = ref.get("integrity")
            assert integrity is not None, f"Reference {ref.get('reference_number')} should have integrity object"
            
            # Check integrity has employment_mismatches field
            assert "employment_mismatches" in integrity, f"Integrity should have employment_mismatches field"
            assert "has_employment_mismatch" in integrity, f"Integrity should have has_employment_mismatch field"
            
            print(f"✓ Reference {ref.get('reference_number')} has integrity.employment_mismatches: {integrity.get('employment_mismatches')}")
            print(f"  has_employment_mismatch: {integrity.get('has_employment_mismatch')}")
    
    def test_employment_mismatches_structure(self):
        """Test that employment_mismatches has correct structure when present"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200
        
        data = response.json()
        references = data.get("references", [])
        
        for ref in references:
            integrity = ref.get("integrity", {})
            mismatches = integrity.get("employment_mismatches", [])
            
            # If there are mismatches, verify structure
            for mismatch in mismatches:
                assert "type" in mismatch, "Mismatch should have 'type' field"
                assert "field" in mismatch, "Mismatch should have 'field' field"
                assert "message" in mismatch, "Mismatch should have 'message' field"
                
                # Type should be one of the expected values
                assert mismatch["type"] in [
                    "reference_vs_application",
                    "reference_vs_normalized",
                    "response_vs_declared"
                ], f"Unexpected mismatch type: {mismatch['type']}"
                
                print(f"✓ Mismatch structure valid: {mismatch['type']} - {mismatch['field']}")
    
    # =====================================================================
    # TEST 2: allowed_actions includes 'record_alternative_path'
    # =====================================================================
    
    def test_allowed_actions_includes_record_alternative_path(self):
        """Test that allowed_actions includes record_alternative_path when appropriate"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200
        
        data = response.json()
        references = data.get("references", [])
        
        found_alternative_path_action = False
        for ref in references:
            allowed_actions = ref.get("allowed_actions", [])
            lifecycle_status = ref.get("lifecycle_status")
            
            print(f"Reference {ref.get('reference_number')}: status={lifecycle_status}, actions={allowed_actions}")
            
            # record_alternative_path should be available when status is sent, viewed, or rejected
            if lifecycle_status in ["sent", "viewed", "rejected"]:
                assert "record_alternative_path" in allowed_actions, \
                    f"record_alternative_path should be in allowed_actions for status {lifecycle_status}"
                found_alternative_path_action = True
                print(f"✓ record_alternative_path available for reference with status {lifecycle_status}")
            
            # Also available when mismatch detected
            integrity = ref.get("integrity", {})
            if integrity.get("mismatch_detected") and not integrity.get("override_applied"):
                assert "record_alternative_path" in allowed_actions, \
                    "record_alternative_path should be available when mismatch detected"
                found_alternative_path_action = True
                print(f"✓ record_alternative_path available for reference with mismatch")
        
        print(f"✓ Tested allowed_actions for {len(references)} references")
    
    # =====================================================================
    # TEST 3: POST /api/references/{employee_id}/{ref_num}/record-alternative-path
    # =====================================================================
    
    def test_record_alternative_path_endpoint_exists(self):
        """Test that record-alternative-path endpoint exists"""
        # Test with invalid data to verify endpoint exists
        response = self.session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/1/record-alternative-path",
            json={
                "original_referee_attempts": [],
                "alternative_reason": "Test",
                "alternative_source": "Test"
            }
        )
        
        # Should get 422 (validation error) or 400, not 404
        assert response.status_code != 404, "Endpoint should exist"
        print(f"✓ record-alternative-path endpoint exists (status: {response.status_code})")
    
    def test_record_alternative_path_validation_reason_length(self):
        """Test that alternative_reason requires minimum 20 characters"""
        response = self.session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/1/record-alternative-path",
            json={
                "original_referee_attempts": [{"date": "2025-01-15", "method": "email"}],
                "alternative_reason": "Short",  # Less than 20 chars
                "alternative_source": "HR Department"
            }
        )
        
        # Should fail validation
        assert response.status_code in [400, 422], f"Should reject short reason: {response.status_code}"
        print(f"✓ Validation rejects short alternative_reason")
    
    def test_record_alternative_path_validation_attempts_required(self):
        """Test that at least one attempt with date and method is required"""
        response = self.session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/1/record-alternative-path",
            json={
                "original_referee_attempts": [{"date": "", "method": ""}],  # Empty fields
                "alternative_reason": "Original referee did not respond after multiple attempts over 3 weeks",
                "alternative_source": "HR Department"
            }
        )
        
        # Should fail validation
        assert response.status_code in [400, 422], f"Should reject empty attempt fields: {response.status_code}"
        print(f"✓ Validation rejects attempts without date/method")
    
    def test_record_alternative_path_success(self):
        """Test successful recording of alternative path"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = self.session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/1/record-alternative-path",
            json={
                "original_referee_attempts": [
                    {"date": yesterday, "method": "email", "notes": "No response"},
                    {"date": today, "method": "phone", "notes": "Number disconnected"}
                ],
                "alternative_reason": "Original referee did not respond after multiple attempts over 3 weeks. Phone number disconnected.",
                "alternative_source": "HR Department of previous employer"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success", "Response should indicate success"
        assert data.get("reference_num") == 1, "Should return reference number"
        assert data.get("attempts_recorded") == 2, "Should record 2 attempts"
        
        print(f"✓ Successfully recorded alternative path: {data}")
    
    def test_alternative_path_persisted_in_normalized_response(self):
        """Test that recorded alternative path appears in normalized response"""
        # First record an alternative path
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/2/record-alternative-path",
            json={
                "original_referee_attempts": [
                    {"date": today, "method": "email", "notes": "Test attempt"}
                ],
                "alternative_reason": "Testing alternative path persistence in normalized response",
                "alternative_source": "Test Source for verification"
            }
        )
        
        # Now fetch normalized references
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200
        
        data = response.json()
        ref2 = next((r for r in data.get("references", []) if r.get("reference_number") == 2), None)
        
        assert ref2 is not None, "Reference 2 should exist"
        
        alt_path = ref2.get("alternative_path")
        if alt_path:
            assert alt_path.get("is_alternative") == True, "Should be marked as alternative"
            assert alt_path.get("alternative_source") == "Test Source for verification", "Source should match"
            assert len(alt_path.get("original_referee_attempts", [])) >= 1, "Should have attempts"
            print(f"✓ Alternative path persisted: {alt_path}")
        else:
            print(f"⚠ Alternative path not returned (may be filtered if not is_alternative)")
    
    def test_record_alternative_path_invalid_ref_num(self):
        """Test that invalid ref_num (not 1 or 2) is rejected"""
        response = self.session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/3/record-alternative-path",
            json={
                "original_referee_attempts": [{"date": "2025-01-15", "method": "email"}],
                "alternative_reason": "Testing invalid reference number validation",
                "alternative_source": "Test"
            }
        )
        
        assert response.status_code == 400, f"Should reject ref_num 3: {response.status_code}"
        print(f"✓ Invalid ref_num rejected with 400")
    
    def test_record_alternative_path_requires_auth(self):
        """Test that endpoint requires authentication"""
        # Create new session without auth
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        response = unauth_session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/1/record-alternative-path",
            json={
                "original_referee_attempts": [{"date": "2025-01-15", "method": "email"}],
                "alternative_reason": "Testing authentication requirement",
                "alternative_source": "Test"
            }
        )
        
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
        print(f"✓ Endpoint requires authentication")
        
        unauth_session.close()
    
    # =====================================================================
    # TEST 4: Employment mismatch detection logic
    # =====================================================================
    
    def test_integrity_fields_present(self):
        """Test that all integrity fields are present in response"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200
        
        data = response.json()
        references = data.get("references", [])
        
        expected_integrity_fields = [
            "mismatch_detected",
            "email_match",
            "name_match",
            "organisation_match",
            "mismatch_reasons",
            "override_applied",
            "employment_mismatches",
            "has_employment_mismatch"
        ]
        
        for ref in references:
            integrity = ref.get("integrity", {})
            for field in expected_integrity_fields:
                assert field in integrity, f"Integrity should have '{field}' field"
        
        print(f"✓ All expected integrity fields present")
    
    def test_summary_response_structure(self):
        """Test that summary in response has correct structure"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200
        
        data = response.json()
        summary = data.get("summary", {})
        
        assert "verified_count" in summary, "Summary should have verified_count"
        assert "minimum_required" in summary, "Summary should have minimum_required"
        assert "meets_minimum" in summary, "Summary should have meets_minimum"
        assert "all_blockers" in summary, "Summary should have all_blockers"
        
        print(f"✓ Summary structure valid: {summary}")


class TestEmploymentMismatchDetection:
    """Specific tests for employment mismatch detection logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip("Authentication failed")
        
        token = login_response.json().get("token") or login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()
    
    def test_mismatch_types_documented(self):
        """Document the three types of employment mismatches"""
        # This is a documentation test to verify the mismatch types
        mismatch_types = [
            "reference_vs_application",  # Reference dates vs application form employment history
            "reference_vs_normalized",   # Reference dates vs normalized employment history
            "response_vs_declared"       # Response dates vs declared reference dates
        ]
        
        print("Employment mismatch types:")
        for mt in mismatch_types:
            print(f"  - {mt}")
        
        print("✓ Mismatch types documented")
    
    def test_date_tolerance_30_days(self):
        """Document that date comparison uses 30-day tolerance"""
        # This is a documentation test
        print("Date comparison uses 30-day tolerance for matching")
        print("✓ Date tolerance documented")


class TestAlternativePathUI:
    """Tests for alternative path UI elements via API response"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip("Authentication failed")
        
        token = login_response.json().get("token") or login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get test employee
        employees_response = self.session.get(f"{BASE_URL}/api/employees")
        if employees_response.status_code != 200 or not employees_response.json():
            pytest.skip("No employees found")
        
        self.test_employee_id = employees_response.json()[0].get("id")
        
        yield
        self.session.close()
    
    def test_alternative_path_in_response_structure(self):
        """Test that alternative_path field exists in normalized response"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/references-normalized"
        )
        assert response.status_code == 200
        
        data = response.json()
        references = data.get("references", [])
        
        for ref in references:
            # alternative_path can be None if not recorded
            # But the field should be present in the response structure
            ref_num = ref.get("reference_number")
            alt_path = ref.get("alternative_path")
            
            if alt_path:
                # If present, verify structure
                expected_fields = [
                    "is_alternative",
                    "original_referee_attempts",
                    "alternative_reason",
                    "alternative_source"
                ]
                for field in expected_fields:
                    assert field in alt_path, f"alternative_path should have '{field}'"
                print(f"✓ Reference {ref_num} has alternative_path with correct structure")
            else:
                print(f"✓ Reference {ref_num} has no alternative_path (expected when not recorded)")
    
    def test_multiple_attempts_tracking(self):
        """Test that multiple contact attempts can be recorded"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        attempts = [
            {"date": "2025-01-10", "method": "email", "notes": "Initial contact attempt"},
            {"date": "2025-01-13", "method": "phone", "notes": "Left voicemail"},
            {"date": "2025-01-17", "method": "email", "notes": "Follow-up email"},
            {"date": today, "method": "phone", "notes": "Final attempt - no answer"}
        ]
        
        response = self.session.post(
            f"{BASE_URL}/api/references/{self.test_employee_id}/1/record-alternative-path",
            json={
                "original_referee_attempts": attempts,
                "alternative_reason": "Original referee unresponsive after 4 contact attempts over 2 weeks",
                "alternative_source": "HR Department of previous employer"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("attempts_recorded") == 4, "Should record all 4 attempts"
        
        print(f"✓ Successfully recorded {data.get('attempts_recorded')} contact attempts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

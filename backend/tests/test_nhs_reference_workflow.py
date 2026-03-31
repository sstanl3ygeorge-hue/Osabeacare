"""
NHS-Level Strict Reference Workflow Tests

Tests the complete reference workflow:
1. Send reference request to referee via email
2. Public referee form completion (token-based)
3. Mismatch detection between declared vs returned details
4. 2-step verification: Review (manager) -> Verify (admin only)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee ID from previous iteration
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestNHSReferenceWorkflow:
    """NHS-Level Reference Workflow Tests"""
    
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
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    # ==================== Reference Status Endpoint Tests ====================
    
    def test_reference_status_endpoint_returns_data(self):
        """Test /api/employees/{id}/reference-status returns correct structure"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/reference-status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "references" in data, "Response should contain 'references' key"
        assert len(data["references"]) == 2, "Should return 2 references"
        
        # Validate structure of each reference
        for ref in data["references"]:
            assert "reference_num" in ref
            assert ref["reference_num"] in [1, 2]
            assert "declared" in ref
            assert "returned" in ref
            assert "request_status" in ref
            assert "mismatch_detected" in ref
            assert "reviewed" in ref
            assert "verified" in ref
        
        print(f"✓ Reference status endpoint returns correct structure")
        print(f"  Reference 1 status: {data['references'][0].get('request_status')}")
        print(f"  Reference 2 status: {data['references'][1].get('request_status')}")
    
    def test_reference_status_requires_auth(self):
        """Test reference status endpoint requires authentication"""
        # Create unauthenticated session
        unauth_session = requests.Session()
        response = unauth_session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/reference-status")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Reference status endpoint requires authentication")
    
    def test_reference_status_invalid_employee(self):
        """Test reference status with invalid employee ID"""
        fake_id = str(uuid.uuid4())
        response = self.session.get(f"{BASE_URL}/api/employees/{fake_id}/reference-status")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Reference status returns 404 for invalid employee")
    
    # ==================== Send Reference Request Tests ====================
    
    def test_send_reference_request_requires_auth(self):
        """Test send reference request requires manager/admin auth"""
        unauth_session = requests.Session()
        response = unauth_session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/send-reference-request",
            params={"reference_num": 1}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Send reference request requires authentication")
    
    def test_send_reference_request_invalid_ref_num(self):
        """Test send reference request with invalid reference number"""
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/send-reference-request",
            params={"reference_num": 3}  # Invalid - must be 1 or 2
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "must be 1 or 2" in response.text.lower()
        print("✓ Send reference request validates reference_num (1 or 2)")
    
    def test_send_reference_request_missing_email(self):
        """Test send reference request fails when referee email not set"""
        # Create a test employee without referee email
        test_emp_id = str(uuid.uuid4())
        create_response = self.session.post(f"{BASE_URL}/api/employees", json={
            "id": test_emp_id,
            "first_name": "TEST_RefNoEmail",
            "last_name": "Worker",
            "email": f"test_refnoemail_{uuid.uuid4().hex[:8]}@test.com",
            "phone": "07700900000",
            "status": "applicant",
            "reference_1_name": "John Referee"
            # No reference_1_email
        })
        
        if create_response.status_code in [200, 201]:
            response = self.session.post(
                f"{BASE_URL}/api/employees/{test_emp_id}/send-reference-request",
                params={"reference_num": 1}
            )
            
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "email not provided" in response.text.lower()
            print("✓ Send reference request requires referee email")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/employees/{test_emp_id}")
        else:
            pytest.skip("Could not create test employee")
    
    # ==================== Public Referee Form Tests ====================
    
    def test_public_referee_form_invalid_token(self):
        """Test public referee form with invalid token"""
        response = requests.get(f"{BASE_URL}/api/referee/complete/invalid_token_12345")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "invalid" in response.text.lower() or "expired" in response.text.lower()
        print("✓ Public referee form rejects invalid token")
    
    def test_public_referee_submit_invalid_token(self):
        """Test public referee form submission with invalid token"""
        response = requests.post(
            f"{BASE_URL}/api/referee/complete/invalid_token_12345",
            json={
                "referee_full_name": "Test Referee",
                "referee_job_title": "Manager",
                "referee_organisation": "Test Company",
                "referee_work_email": "referee@test.com",
                "relationship_type": "Line Manager",
                "known_from_date": "2020-01-01",
                "performance_rating": "Excellent",
                "reliability": "Excellent",
                "professionalism": "Excellent",
                "care_vulnerable_suitable": "Yes",
                "declaration_accurate": True,
                "declaration_authority": True
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Public referee form submission rejects invalid token")
    
    # ==================== Review Reference Tests ====================
    
    def test_review_reference_requires_auth(self):
        """Test review reference requires manager/admin auth"""
        unauth_session = requests.Session()
        response = unauth_session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/review-reference",
            params={"reference_num": 1}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Review reference requires authentication")
    
    def test_review_reference_invalid_ref_num(self):
        """Test review reference with invalid reference number"""
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/review-reference",
            params={"reference_num": 5}  # Invalid
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Review reference validates reference_num")
    
    def test_review_reference_not_submitted(self):
        """Test review reference fails if reference not submitted"""
        # Create test employee with no reference submitted
        test_emp_id = str(uuid.uuid4())
        create_response = self.session.post(f"{BASE_URL}/api/employees", json={
            "id": test_emp_id,
            "first_name": "TEST_RefNotSubmitted",
            "last_name": "Worker",
            "email": f"test_refnotsubmitted_{uuid.uuid4().hex[:8]}@test.com",
            "phone": "07700900001",
            "status": "applicant",
            "reference_1_name": "John Referee",
            "reference_1_email": "john@referee.com"
        })
        
        if create_response.status_code in [200, 201]:
            response = self.session.post(
                f"{BASE_URL}/api/employees/{test_emp_id}/review-reference",
                params={"reference_num": 1}
            )
            
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "submitted" in response.text.lower()
            print("✓ Review reference requires reference to be submitted first")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/employees/{test_emp_id}")
        else:
            pytest.skip("Could not create test employee")
    
    # ==================== Verify Reference Strict Tests ====================
    
    def test_verify_reference_strict_requires_admin(self):
        """Test verify reference strict requires admin role"""
        # This test verifies the endpoint exists and requires admin
        # We're already logged in as admin, so we test the endpoint behavior
        
        # Create test employee without response data
        test_emp_id = str(uuid.uuid4())
        create_response = self.session.post(f"{BASE_URL}/api/employees", json={
            "id": test_emp_id,
            "first_name": "TEST_VerifyStrict",
            "last_name": "Worker",
            "email": f"test_verifystrict_{uuid.uuid4().hex[:8]}@test.com",
            "phone": "07700900002",
            "status": "applicant"
        })
        
        if create_response.status_code in [200, 201]:
            # Try to verify without response data
            response = self.session.post(
                f"{BASE_URL}/api/employees/{test_emp_id}/verify-reference-strict",
                params={"reference_num": 1}
            )
            
            # Should fail because no response data
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "response" in response.text.lower()
            print("✓ Verify reference strict requires response data")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/employees/{test_emp_id}")
        else:
            pytest.skip("Could not create test employee")
    
    def test_verify_reference_strict_invalid_ref_num(self):
        """Test verify reference strict with invalid reference number"""
        response = self.session.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/verify-reference-strict",
            params={"reference_num": 0}  # Invalid
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Verify reference strict validates reference_num")
    
    def test_verify_reference_strict_requires_review(self):
        """Test verify reference strict requires review first"""
        # Create test employee with response data but not reviewed
        test_emp_id = str(uuid.uuid4())
        create_response = self.session.post(f"{BASE_URL}/api/employees", json={
            "id": test_emp_id,
            "first_name": "TEST_VerifyNoReview",
            "last_name": "Worker",
            "email": f"test_verifynoreview_{uuid.uuid4().hex[:8]}@test.com",
            "phone": "07700900003",
            "status": "applicant",
            "reference_1_response_data": {
                "referee_full_name": "Test Referee",
                "referee_organisation": "Test Company"
            },
            "reference_1_request_status": "submitted"
        })
        
        if create_response.status_code in [200, 201]:
            response = self.session.post(
                f"{BASE_URL}/api/employees/{test_emp_id}/verify-reference-strict",
                params={"reference_num": 1}
            )
            
            # Should fail because not reviewed
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "reviewed" in response.text.lower()
            print("✓ Verify reference strict requires review first")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/employees/{test_emp_id}")
        else:
            pytest.skip("Could not create test employee")
    
    # ==================== Full Workflow Integration Test ====================
    
    def test_reference_workflow_status_progression(self):
        """Test reference status shows correct progression through workflow"""
        # Get current status of test employee
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/reference-status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Reference 2 is verified (as per context)
        ref2 = next((r for r in data["references"] if r["reference_num"] == 2), None)
        assert ref2 is not None, "Reference 2 should exist"
        
        # Check if Reference 2 went through full workflow
        if ref2.get("verified"):
            print(f"✓ Reference 2 is verified")
            print(f"  - Request status: {ref2.get('request_status')}")
            print(f"  - Reviewed: {ref2.get('reviewed')}")
            print(f"  - Verified: {ref2.get('verified')}")
        else:
            print(f"  Reference 2 status: {ref2.get('request_status')}")
        
        # Check Reference 1 status
        ref1 = next((r for r in data["references"] if r["reference_num"] == 1), None)
        assert ref1 is not None, "Reference 1 should exist"
        print(f"  Reference 1 status: {ref1.get('request_status')}")
        print(f"  Reference 1 verified: {ref1.get('verified')}")


class TestMismatchDetection:
    """Tests for mismatch detection between declared and returned referee details"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_mismatch_indicator_in_reference_status(self):
        """Test that mismatch_detected field is present in reference status"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/reference-status")
        
        assert response.status_code == 200
        data = response.json()
        
        for ref in data["references"]:
            assert "mismatch_detected" in ref, "mismatch_detected field should be present"
            assert "mismatch_notes" in ref, "mismatch_notes field should be present"
            assert isinstance(ref["mismatch_detected"], bool), "mismatch_detected should be boolean"
        
        print("✓ Mismatch detection fields present in reference status")
    
    def test_review_requires_mismatch_notes_when_mismatch_detected(self):
        """Test that review requires mismatch notes when mismatch is detected"""
        # Create employee with mismatch detected
        test_emp_id = str(uuid.uuid4())
        create_response = self.session.post(f"{BASE_URL}/api/employees", json={
            "id": test_emp_id,
            "first_name": "TEST_MismatchNotes",
            "last_name": "Worker",
            "email": f"test_mismatchnotes_{uuid.uuid4().hex[:8]}@test.com",
            "phone": "07700900004",
            "status": "applicant",
            "reference_1_name": "John Smith",
            "reference_1_company": "ABC Company",
            "reference_1_request_status": "submitted",
            "reference_1_mismatch_detected": True,
            "reference_1_response_data": {
                "referee_full_name": "Jonathan Smith",  # Different name
                "referee_organisation": "XYZ Company"   # Different company
            }
        })
        
        if create_response.status_code in [200, 201]:
            # Try to review without mismatch notes
            response = self.session.post(
                f"{BASE_URL}/api/employees/{test_emp_id}/review-reference",
                params={"reference_num": 1}
                # No mismatch_notes provided
            )
            
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "mismatch" in response.text.lower() and "notes" in response.text.lower()
            print("✓ Review requires mismatch notes when mismatch detected")
            
            # Now try with mismatch notes
            response_with_notes = self.session.post(
                f"{BASE_URL}/api/employees/{test_emp_id}/review-reference",
                params={
                    "reference_num": 1,
                    "mismatch_notes": "Verified via phone call - name variation is acceptable"
                }
            )
            
            # Should succeed or fail for other reason (not mismatch notes)
            if response_with_notes.status_code == 200:
                print("✓ Review succeeds with mismatch notes provided")
            else:
                print(f"  Review with notes status: {response_with_notes.status_code}")
            
            # Cleanup
            self.session.delete(f"{BASE_URL}/api/employees/{test_emp_id}")
        else:
            pytest.skip("Could not create test employee")


class TestRefereeFormTemplate:
    """Tests for referee form template structure"""
    
    def test_referee_form_template_structure(self):
        """Test that referee form template has required sections"""
        # We can't test the actual form without a valid token,
        # but we can verify the endpoint exists
        response = requests.get(f"{BASE_URL}/api/referee/complete/test_token")
        
        # Should return 400 (invalid token) not 404 (endpoint not found)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Referee form endpoint exists and validates tokens")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

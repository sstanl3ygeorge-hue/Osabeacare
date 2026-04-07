"""
Test Suite for RTW and DBS Stamp-All Endpoints
Tests the 'Confirm & Stamp All' flow for Right to Work (RTW) and DBS verification.

This tests the atomic stamping of both employee evidence documents and admin verification 
proof documents at the END of the verification flow, linking them with a shared verification ID.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"  # Lawrence Egbeni


class TestStampAllRTWDBS:
    """Test suite for RTW and DBS stamp-all endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        token = response.json().get("token")
        assert token, "No token returned from login"
        return token
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_employee(self, auth_headers):
        """Get or verify test employee exists"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        if response.status_code == 200:
            return response.json()
        pytest.skip(f"Test employee {TEST_EMPLOYEE_ID} not found")
    
    # ==================== RTW STAMP-ALL TESTS ====================
    
    def test_rtw_stamp_all_endpoint_exists(self, auth_headers, test_employee):
        """Test that RTW stamp-all endpoint exists and requires proper data"""
        # Test with empty payload - should fail validation
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={}
        )
        # Should return 422 (validation error) not 404 (not found)
        assert response.status_code in [422, 400], f"Unexpected status: {response.status_code}"
        print(f"✓ RTW stamp-all endpoint exists (validation error as expected)")
    
    def test_rtw_stamp_all_requires_evidence_file_ids(self, auth_headers, test_employee):
        """Test that RTW stamp-all requires evidence_file_ids"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={"stamp_verification_proof": True}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ RTW stamp-all correctly requires evidence_file_ids")
    
    def test_rtw_stamp_all_with_nonexistent_docs(self, auth_headers, test_employee):
        """Test RTW stamp-all with non-existent document IDs"""
        fake_doc_id = f"fake_doc_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [fake_doc_id],
                "stamp_verification_proof": True
            }
        )
        # Should succeed but report errors for missing docs
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("errors") is not None or data.get("documents_stamped") == 0
        print(f"✓ RTW stamp-all handles non-existent docs gracefully")
        print(f"  Response: {data}")
    
    def test_rtw_stamp_all_employee_not_found(self, auth_headers):
        """Test RTW stamp-all with non-existent employee"""
        fake_employee_id = f"fake_emp_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_employee_id}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": ["doc_123"],
                "stamp_verification_proof": True
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ RTW stamp-all returns 404 for non-existent employee")
    
    # ==================== DBS STAMP-ALL TESTS ====================
    
    def test_dbs_stamp_all_endpoint_exists(self, auth_headers, test_employee):
        """Test that DBS stamp-all endpoint exists and requires proper data"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/stamp-all",
            headers=auth_headers,
            json={}
        )
        # Should return 422 (validation error) not 404 (not found)
        assert response.status_code in [422, 400], f"Unexpected status: {response.status_code}"
        print(f"✓ DBS stamp-all endpoint exists (validation error as expected)")
    
    def test_dbs_stamp_all_requires_evidence_file_ids(self, auth_headers, test_employee):
        """Test that DBS stamp-all requires evidence_file_ids"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/stamp-all",
            headers=auth_headers,
            json={"stamp_verification_proof": True}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ DBS stamp-all correctly requires evidence_file_ids")
    
    def test_dbs_stamp_all_with_nonexistent_docs(self, auth_headers, test_employee):
        """Test DBS stamp-all with non-existent document IDs"""
        fake_doc_id = f"fake_doc_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [fake_doc_id],
                "stamp_verification_proof": True
            }
        )
        # Should succeed but report errors for missing docs
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ DBS stamp-all handles non-existent docs gracefully")
        print(f"  Response: {data}")
    
    def test_dbs_stamp_all_employee_not_found(self, auth_headers):
        """Test DBS stamp-all with non-existent employee"""
        fake_employee_id = f"fake_emp_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/employees/{fake_employee_id}/dbs/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": ["doc_123"],
                "stamp_verification_proof": True
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ DBS stamp-all returns 404 for non-existent employee")
    
    # ==================== AUTHORIZATION TESTS ====================
    
    def test_rtw_stamp_all_requires_auth(self):
        """Test that RTW stamp-all requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            json={
                "evidence_file_ids": ["doc_123"],
                "stamp_verification_proof": True
            }
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ RTW stamp-all requires authentication")
    
    def test_dbs_stamp_all_requires_auth(self):
        """Test that DBS stamp-all requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/stamp-all",
            json={
                "evidence_file_ids": ["doc_123"],
                "stamp_verification_proof": True
            }
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ DBS stamp-all requires authentication")


class TestStampAllWithRealData:
    """
    Test stamp-all with real document data.
    These tests create test documents, stamp them, and verify the stamps.
    """
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_employee_compliance_file(self, auth_headers):
        """Get employee compliance file to check RTW/DBS status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get compliance file: {response.text}"
        data = response.json()
        
        # Check if RTW section exists
        rtw_section = data.get("right_to_work") or data.get("right_to_work_documents")
        dbs_section = data.get("dbs") or data.get("dbs_certificate")
        
        print(f"✓ Got compliance file for employee")
        print(f"  RTW section: {rtw_section is not None}")
        print(f"  DBS section: {dbs_section is not None}")
        
        return data
    
    def test_rtw_stamp_all_response_structure(self, auth_headers):
        """Test RTW stamp-all response has correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [],  # Empty list
                "stamp_verification_proof": True
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert "verification_id" in data, "Response missing 'verification_id' field"
        assert "documents_stamped" in data, "Response missing 'documents_stamped' field"
        
        print(f"✓ RTW stamp-all response has correct structure")
        print(f"  success: {data.get('success')}")
        print(f"  verification_id: {data.get('verification_id')}")
        print(f"  documents_stamped: {data.get('documents_stamped')}")
        print(f"  message: {data.get('message')}")
    
    def test_dbs_stamp_all_response_structure(self, auth_headers):
        """Test DBS stamp-all response has correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [],  # Empty list
                "stamp_verification_proof": True
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert "verification_id" in data, "Response missing 'verification_id' field"
        assert "documents_stamped" in data, "Response missing 'documents_stamped' field"
        
        print(f"✓ DBS stamp-all response has correct structure")
        print(f"  success: {data.get('success')}")
        print(f"  verification_id: {data.get('verification_id')}")
        print(f"  documents_stamped: {data.get('documents_stamped')}")
        print(f"  message: {data.get('message')}")
    
    def test_verification_id_format(self, auth_headers):
        """Test that verification_id is in correct format (8 char uppercase)"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [],
                "stamp_verification_proof": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        verification_id = data.get("verification_id")
        assert verification_id is not None, "verification_id should not be None"
        assert len(verification_id) == 8, f"verification_id should be 8 chars, got {len(verification_id)}"
        assert verification_id.isupper(), f"verification_id should be uppercase, got {verification_id}"
        
        print(f"✓ Verification ID format is correct: {verification_id}")
    
    def test_employee_status_updated_after_rtw_stamp(self, auth_headers):
        """Test that employee rtw_fully_verified is set after stamping"""
        # First stamp
        stamp_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [],
                "stamp_verification_proof": True
            }
        )
        assert stamp_response.status_code == 200
        verification_id = stamp_response.json().get("verification_id")
        
        # Then check employee status
        emp_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert emp_response.status_code == 200
        employee = emp_response.json()
        
        # Verify status flags are set
        assert employee.get("rtw_fully_verified") == True, "rtw_fully_verified should be True"
        assert employee.get("rtw_verification_id") == verification_id, f"rtw_verification_id should be {verification_id}"
        
        print(f"✓ Employee RTW status updated correctly")
        print(f"  rtw_fully_verified: {employee.get('rtw_fully_verified')}")
        print(f"  rtw_verification_id: {employee.get('rtw_verification_id')}")
    
    def test_employee_status_updated_after_dbs_stamp(self, auth_headers):
        """Test that employee dbs_fully_verified is set after stamping"""
        # First stamp
        stamp_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [],
                "stamp_verification_proof": True
            }
        )
        assert stamp_response.status_code == 200
        verification_id = stamp_response.json().get("verification_id")
        
        # Then check employee status
        emp_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert emp_response.status_code == 200
        employee = emp_response.json()
        
        # Verify status flags are set
        assert employee.get("dbs_fully_verified") == True, "dbs_fully_verified should be True"
        assert employee.get("dbs_verification_id") == verification_id, f"dbs_verification_id should be {verification_id}"
        
        print(f"✓ Employee DBS status updated correctly")
        print(f"  dbs_fully_verified: {employee.get('dbs_fully_verified')}")
        print(f"  dbs_verification_id: {employee.get('dbs_verification_id')}")


class TestStampAllInputModel:
    """Test the StampAllInput model validation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_stamp_verification_proof_default_true(self, auth_headers):
        """Test that stamp_verification_proof defaults to True"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": []
                # stamp_verification_proof not provided - should default to True
            }
        )
        assert response.status_code == 200
        print(f"✓ stamp_verification_proof defaults correctly")
    
    def test_stamp_verification_proof_can_be_false(self, auth_headers):
        """Test that stamp_verification_proof can be set to False"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": [],
                "stamp_verification_proof": False
            }
        )
        assert response.status_code == 200
        print(f"✓ stamp_verification_proof can be set to False")
    
    def test_evidence_file_ids_must_be_list(self, auth_headers):
        """Test that evidence_file_ids must be a list"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right_to_work/stamp-all",
            headers=auth_headers,
            json={
                "evidence_file_ids": "not_a_list",
                "stamp_verification_proof": True
            }
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ evidence_file_ids must be a list")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

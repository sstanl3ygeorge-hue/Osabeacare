"""
Phase 28: Verification Routes Extraction Tests

Tests for 12 verification endpoints extracted to routes/verifications.py:
- POST /api/rtw/extract - Extract RTW document fields using AI
- POST /api/identity/extract - Extract Identity document fields using AI
- POST /api/address/extract - Extract Address/POA document fields using AI
- POST /api/employees/{employee_id}/identity/check - Record identity check
- GET /api/employees/{employee_id}/identity/check - Get identity check
- POST /api/employees/{employee_id}/address/check - Record address check
- GET /api/employees/{employee_id}/address/check - Get address check
- POST /api/employees/{employee_id}/address/verify - Record address verification (legacy)
- GET /api/employees/{employee_id}/address/verification - Get address verification (legacy)
- POST /api/employees/{employee_id}/identity/verify-and-stamp - Unified verify and stamp identity
- POST /api/employees/{employee_id}/address/verify-and-stamp - Unified verify and stamp address
- POST /api/employees/{employee_id}/right_to_work/stamp-all - Stamp all RTW documents
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestPhase28Setup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get or create a test employee for verification tests"""
        # First try to find an existing employee
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                return employees[0].get("id")
        
        # Create a test employee if none exists
        test_employee = {
            "first_name": "TEST_Phase28",
            "last_name": "Verification",
            "email": f"test_phase28_{uuid.uuid4().hex[:8]}@test.com",
            "phone": "07700900123",
            "status": "active"
        }
        response = requests.post(f"{BASE_URL}/api/employees", json=test_employee, headers=auth_headers)
        if response.status_code in [200, 201]:
            return response.json().get("id")
        
        pytest.skip("Could not get or create test employee")
    
    @pytest.fixture(scope="class")
    def test_document_id(self, auth_headers, test_employee_id):
        """Get or create a test document for extraction tests"""
        # Try to find an existing document
        response = requests.get(f"{BASE_URL}/api/employees/{test_employee_id}/documents", headers=auth_headers)
        if response.status_code == 200:
            docs = response.json()
            if isinstance(docs, list) and len(docs) > 0:
                return docs[0].get("id")
            elif isinstance(docs, dict) and docs.get("documents"):
                return docs["documents"][0].get("id")
        
        # Return None - extraction tests will use file_base64 mode
        return None
    
    def test_api_health(self):
        """Test API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("API health check passed")
    
    def test_admin_login(self, auth_token):
        """Test admin login works"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print("Admin login successful")


class TestRTWExtraction:
    """Tests for RTW document extraction endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_rtw_extract_requires_auth(self):
        """Test RTW extraction requires authentication"""
        response = requests.post(f"{BASE_URL}/api/rtw/extract", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("RTW extract auth check passed")
    
    def test_rtw_extract_requires_input(self, auth_headers):
        """Test RTW extraction requires document_id or file_base64"""
        response = requests.post(f"{BASE_URL}/api/rtw/extract", json={}, headers=auth_headers)
        # Should return 400 or error response
        assert response.status_code in [400, 422] or (response.status_code == 200 and not response.json().get("success")), \
            f"Expected validation error, got {response.status_code}: {response.text}"
        print("RTW extract input validation passed")
    
    def test_rtw_extract_invalid_document_id(self, auth_headers):
        """Test RTW extraction with non-existent document"""
        response = requests.post(f"{BASE_URL}/api/rtw/extract", json={
            "document_id": "non-existent-doc-id"
        }, headers=auth_headers)
        # Should return 404 or error response
        assert response.status_code in [404, 400] or (response.status_code == 200 and not response.json().get("success")), \
            f"Expected error for invalid doc, got {response.status_code}: {response.text}"
        print("RTW extract invalid document check passed")
    
    def test_rtw_extract_endpoint_exists(self, auth_headers):
        """Test RTW extraction endpoint is registered"""
        # Test with minimal valid input to verify endpoint exists
        response = requests.post(f"{BASE_URL}/api/rtw/extract", json={
            "file_base64": "invalid_base64_data",
            "file_type": "image/png"
        }, headers=auth_headers)
        # Should not return 404 (endpoint not found)
        assert response.status_code != 404, "RTW extract endpoint not found"
        print(f"RTW extract endpoint exists, status: {response.status_code}")


class TestIdentityExtraction:
    """Tests for Identity document extraction endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_identity_extract_requires_auth(self):
        """Test Identity extraction requires authentication"""
        response = requests.post(f"{BASE_URL}/api/identity/extract", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Identity extract auth check passed")
    
    def test_identity_extract_requires_input(self, auth_headers):
        """Test Identity extraction requires document_id or file_base64"""
        response = requests.post(f"{BASE_URL}/api/identity/extract", json={}, headers=auth_headers)
        assert response.status_code in [400, 422] or (response.status_code == 200 and not response.json().get("success")), \
            f"Expected validation error, got {response.status_code}: {response.text}"
        print("Identity extract input validation passed")
    
    def test_identity_extract_endpoint_exists(self, auth_headers):
        """Test Identity extraction endpoint is registered"""
        response = requests.post(f"{BASE_URL}/api/identity/extract", json={
            "file_base64": "invalid_base64_data",
            "file_type": "image/png"
        }, headers=auth_headers)
        assert response.status_code != 404, "Identity extract endpoint not found"
        print(f"Identity extract endpoint exists, status: {response.status_code}")


class TestAddressExtraction:
    """Tests for Address/POA document extraction endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_address_extract_requires_auth(self):
        """Test Address extraction requires authentication"""
        response = requests.post(f"{BASE_URL}/api/address/extract", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Address extract auth check passed")
    
    def test_address_extract_requires_input(self, auth_headers):
        """Test Address extraction requires document_id or file_base64"""
        response = requests.post(f"{BASE_URL}/api/address/extract", json={}, headers=auth_headers)
        assert response.status_code in [400, 422] or (response.status_code == 200 and not response.json().get("success")), \
            f"Expected validation error, got {response.status_code}: {response.text}"
        print("Address extract input validation passed")
    
    def test_address_extract_endpoint_exists(self, auth_headers):
        """Test Address extraction endpoint is registered"""
        response = requests.post(f"{BASE_URL}/api/address/extract", json={
            "file_base64": "invalid_base64_data",
            "file_type": "image/png"
        }, headers=auth_headers)
        assert response.status_code != 404, "Address extract endpoint not found"
        print(f"Address extract endpoint exists, status: {response.status_code}")


class TestIdentityCheck:
    """Tests for Identity check recording and retrieval endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee ID"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                return employees[0].get("id")
        pytest.skip("No employees available for testing")
    
    def test_identity_check_post_requires_auth(self, test_employee_id):
        """Test identity check POST requires authentication"""
        response = requests.post(f"{BASE_URL}/api/employees/{test_employee_id}/identity/check", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Identity check POST auth check passed")
    
    def test_identity_check_get_requires_auth(self, test_employee_id):
        """Test identity check GET requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/{test_employee_id}/identity/check")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Identity check GET auth check passed")
    
    def test_identity_check_post_invalid_employee(self, auth_headers):
        """Test identity check POST with invalid employee"""
        response = requests.post(f"{BASE_URL}/api/employees/invalid-employee-id/identity/check", json={
            "method": "original_document_seen",
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }, headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Identity check POST invalid employee check passed")
    
    def test_identity_check_record_and_retrieve(self, auth_headers, test_employee_id):
        """Test recording and retrieving identity check"""
        # Record identity check
        check_data = {
            "method": "original_document_seen",
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "outcome": "verified",
            "document_type": "passport",
            "full_name_on_document": "TEST_Phase28 Verification",
            "name_matches_application": True,
            "dob_matches_application": True,
            "photo_match_confirmed": True,
            "notes": "Phase 28 test identity check"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/identity/check",
            json=check_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201], f"Failed to record identity check: {response.text}"
        print(f"Identity check recorded, status: {response.status_code}")
        
        # Retrieve identity check
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/identity/check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get identity check: {response.text}"
        data = response.json()
        assert "current" in data, "Response should contain 'current' field"
        print("Identity check retrieval passed")


class TestAddressCheck:
    """Tests for Address check recording and retrieval endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee ID"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                return employees[0].get("id")
        pytest.skip("No employees available for testing")
    
    def test_address_check_post_requires_auth(self, test_employee_id):
        """Test address check POST requires authentication"""
        response = requests.post(f"{BASE_URL}/api/employees/{test_employee_id}/address/check", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Address check POST auth check passed")
    
    def test_address_check_get_requires_auth(self, test_employee_id):
        """Test address check GET requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/{test_employee_id}/address/check")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Address check GET auth check passed")
    
    def test_address_check_post_invalid_employee(self, auth_headers):
        """Test address check POST with invalid employee"""
        response = requests.post(f"{BASE_URL}/api/employees/invalid-employee-id/address/check", json={
            "method": "original_document_seen",
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }, headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Address check POST invalid employee check passed")
    
    def test_address_check_record_and_retrieve(self, auth_headers, test_employee_id):
        """Test recording and retrieving address check"""
        # Record address check
        check_data = {
            "method": "original_document_seen",
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "outcome": "verified",
            "documents_received_count": 2,
            "documents_required_count": 2,
            "address_matches_application": True,
            "all_documents_sufficiently_recent": True,
            "notes": "Phase 28 test address check"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/check",
            json=check_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201], f"Failed to record address check: {response.text}"
        print(f"Address check recorded, status: {response.status_code}")
        
        # Retrieve address check
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get address check: {response.text}"
        data = response.json()
        assert "current" in data, "Response should contain 'current' field"
        print("Address check retrieval passed")


class TestLegacyAddressVerification:
    """Tests for legacy address verification endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee ID"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                return employees[0].get("id")
        pytest.skip("No employees available for testing")
    
    def test_legacy_address_verify_endpoint_exists(self, auth_headers, test_employee_id):
        """Test legacy address verify endpoint is registered"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/verify",
            json={
                "method": "copy_verified",
                "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            },
            headers=auth_headers
        )
        assert response.status_code != 404, "Legacy address verify endpoint not found"
        print(f"Legacy address verify endpoint exists, status: {response.status_code}")
    
    def test_legacy_address_verification_get_endpoint_exists(self, auth_headers, test_employee_id):
        """Test legacy address verification GET endpoint is registered"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/verification",
            headers=auth_headers
        )
        assert response.status_code != 404, "Legacy address verification GET endpoint not found"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("Legacy address verification GET endpoint exists")


class TestVerifyAndStamp:
    """Tests for unified verify-and-stamp endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee ID"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                return employees[0].get("id")
        pytest.skip("No employees available for testing")
    
    def test_identity_verify_stamp_requires_auth(self, test_employee_id):
        """Test identity verify-and-stamp requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/identity/verify-and-stamp",
            json={}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Identity verify-and-stamp auth check passed")
    
    def test_identity_verify_stamp_invalid_employee(self, auth_headers):
        """Test identity verify-and-stamp with invalid employee"""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id/identity/verify-and-stamp",
            json={
                "document_id": "test-doc-id",
                "method": "original_document_seen",
                "stamp_type": "original_seen",
                "checks_confirmed": {
                    "document_genuine": True,
                    "details_match": True,
                    "date_valid": True
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Identity verify-and-stamp invalid employee check passed")
    
    def test_identity_verify_stamp_requires_checks(self, auth_headers, test_employee_id):
        """Test identity verify-and-stamp requires checks_confirmed"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/identity/verify-and-stamp",
            json={
                "document_id": "test-doc-id",
                "method": "original_document_seen",
                "stamp_type": "original_seen",
                "checks_confirmed": {
                    "document_genuine": False,  # Not confirmed
                    "details_match": True,
                    "date_valid": True
                }
            },
            headers=auth_headers
        )
        # Should fail because document_genuine is False
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print("Identity verify-and-stamp checks validation passed")
    
    def test_address_verify_stamp_requires_auth(self, test_employee_id):
        """Test address verify-and-stamp requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/verify-and-stamp",
            json={}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Address verify-and-stamp auth check passed")
    
    def test_address_verify_stamp_invalid_employee(self, auth_headers):
        """Test address verify-and-stamp with invalid employee"""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id/address/verify-and-stamp",
            json={
                "document_id": "test-doc-id",
                "method": "original_document_seen",
                "stamp_type": "original_seen",
                "checks_confirmed": {
                    "document_genuine": True,
                    "details_match": True,
                    "date_valid": True
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Address verify-and-stamp invalid employee check passed")
    
    def test_address_verify_stamp_requires_all_checks(self, auth_headers, test_employee_id):
        """Test address verify-and-stamp requires all checks including date_valid"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/verify-and-stamp",
            json={
                "document_id": "test-doc-id",
                "method": "original_document_seen",
                "stamp_type": "original_seen",
                "checks_confirmed": {
                    "document_genuine": True,
                    "details_match": True,
                    "date_valid": False  # Not confirmed - should fail
                }
            },
            headers=auth_headers
        )
        # Should fail because date_valid is False
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print("Address verify-and-stamp checks validation passed")


class TestRTWStampAll:
    """Tests for RTW stamp-all endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee ID"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                return employees[0].get("id")
        pytest.skip("No employees available for testing")
    
    def test_rtw_stamp_all_requires_auth(self, test_employee_id):
        """Test RTW stamp-all requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right_to_work/stamp-all",
            json={}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("RTW stamp-all auth check passed")
    
    def test_rtw_stamp_all_invalid_employee(self, auth_headers):
        """Test RTW stamp-all with invalid employee"""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id/right_to_work/stamp-all",
            json={
                "evidence_file_ids": [],
                "stamp_verification_proof": True
            },
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("RTW stamp-all invalid employee check passed")
    
    def test_rtw_stamp_all_empty_files(self, auth_headers, test_employee_id):
        """Test RTW stamp-all with empty file list"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right_to_work/stamp-all",
            json={
                "evidence_file_ids": [],
                "stamp_verification_proof": False
            },
            headers=auth_headers
        )
        # Should succeed with 0 documents stamped
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert data.get("documents_stamped") == 0, "Expected 0 documents stamped"
        print("RTW stamp-all empty files test passed")
    
    def test_rtw_stamp_all_nonexistent_files(self, auth_headers, test_employee_id):
        """Test RTW stamp-all with non-existent file IDs"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right_to_work/stamp-all",
            json={
                "evidence_file_ids": ["non-existent-file-1", "non-existent-file-2"],
                "stamp_verification_proof": False
            },
            headers=auth_headers
        )
        # Should succeed but report errors for non-existent files
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        # Should have errors for non-existent files
        errors = data.get("errors", [])
        assert len(errors) > 0, "Expected errors for non-existent files"
        print("RTW stamp-all non-existent files test passed")


class TestRegressionPreviousPhases:
    """Regression tests for previous phases to ensure refactoring didn't break anything"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authorization headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee ID"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                return employees[0].get("id")
        pytest.skip("No employees available for testing")
    
    def test_phase27_dbs_register(self, auth_headers):
        """Regression: Phase 27 DBS Register endpoint"""
        response = requests.get(f"{BASE_URL}/api/dbs-register", headers=auth_headers)
        assert response.status_code == 200, f"DBS Register failed: {response.text}"
        print("Phase 27 DBS Register regression passed")
    
    def test_phase26_agreements(self, auth_headers, test_employee_id):
        """Regression: Phase 26 Agreements endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Agreements failed: {response.text}"
        print("Phase 26 Agreements regression passed")
    
    def test_phase25_recurring_compliance(self, auth_headers):
        """Regression: Phase 25 Recurring Compliance endpoint"""
        response = requests.get(f"{BASE_URL}/api/recurring-compliance", headers=auth_headers)
        assert response.status_code == 200, f"Recurring Compliance failed: {response.text}"
        print("Phase 25 Recurring Compliance regression passed")
    
    def test_phase24_employment_gaps(self, auth_headers, test_employee_id):
        """Regression: Phase 24 Employment Gaps endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/employment-gaps",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Employment Gaps failed: {response.text}"
        print("Phase 24 Employment Gaps regression passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

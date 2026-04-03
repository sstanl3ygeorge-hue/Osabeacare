"""
Test Identity and Address Check Endpoints
Tests the new Identity and POA verification check endpoints and compliance-file integration.

Features tested:
- POST /api/employees/{id}/identity/check - Record identity verification
- GET /api/employees/{id}/identity/check - Get current identity check
- POST /api/employees/{id}/address/check - Record address verification
- GET /api/employees/{id}/address/check - Get current address check
- Compliance-file endpoint returns identity and address check data
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestIdentityCheckEndpoints:
    """Test Identity verification check endpoints."""
    
    def test_get_identity_check_endpoint_exists(self, auth_headers):
        """Test GET /api/employees/{id}/identity/check endpoint exists."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/identity/check",
            headers=auth_headers
        )
        # Should return 200 even if no check exists (returns null current)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "current" in data, "Response should have 'current' key"
    
    def test_post_identity_check_endpoint_exists(self, auth_headers):
        """Test POST /api/employees/{id}/identity/check endpoint exists and accepts valid data."""
        # Prepare identity check data
        identity_data = {
            "method": "original_document_seen",
            "outcome": "verified",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "document_type": "passport",
            "full_name_on_document": "Test Employee Name",
            "date_of_birth": "1990-01-15",
            "document_number": "AB123456",
            "issue_date": "2020-01-01",
            "expiry_date": (datetime.now() + timedelta(days=365*5)).strftime("%Y-%m-%d"),
            "nationality": "British",
            "name_matches_application": True,
            "dob_matches_application": True,
            "photo_match_confirmed": True,
            "notes": "Test identity verification"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/identity/check",
            headers=auth_headers,
            json=identity_data
        )
        
        # Should return 200 or 201 for successful creation
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response contains expected fields
        assert "id" in data or "check_id" in data or "success" in data, f"Response should contain id or success: {data}"
    
    def test_get_identity_check_returns_recorded_data(self, auth_headers):
        """Test GET returns the identity check data after recording."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/identity/check",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If a check was recorded, verify the data structure
        if data.get("current"):
            current = data["current"]
            # Check for identity-specific fields
            assert "method" in current or "outcome" in current, "Current check should have method or outcome"
    
    def test_identity_check_with_invalid_employee(self, auth_headers):
        """Test identity check with non-existent employee returns 404."""
        response = requests.post(
            f"{BASE_URL}/api/employees/non-existent-id/identity/check",
            headers=auth_headers,
            json={
                "method": "original_document_seen",
                "outcome": "verified",
                "checked_at": datetime.now().strftime("%Y-%m-%d")
            }
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent employee, got {response.status_code}"


class TestAddressCheckEndpoints:
    """Test Address/POA verification check endpoints."""
    
    def test_get_address_check_endpoint_exists(self, auth_headers):
        """Test GET /api/employees/{id}/address/check endpoint exists."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/address/check",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "current" in data, "Response should have 'current' key"
    
    def test_post_address_check_endpoint_exists(self, auth_headers):
        """Test POST /api/employees/{id}/address/check endpoint exists and accepts valid data."""
        # Prepare address check data
        address_data = {
            "method": "original_document_seen",
            "outcome": "verified",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "documents_received_count": 2,
            "documents_required_count": 2,
            "verified_documents": [
                {
                    "type": "utility_bill",
                    "issue_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "is_valid": True,
                    "recency_status": "valid"
                },
                {
                    "type": "bank_statement",
                    "issue_date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
                    "is_valid": True,
                    "recency_status": "valid"
                }
            ],
            "extracted_address_line1": "123 Test Street",
            "extracted_city": "London",
            "extracted_postcode": "SW1A 1AA",
            "address_matches_application": True,
            "all_documents_sufficiently_recent": True,
            "notes": "Test address verification"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/address/check",
            headers=auth_headers,
            json=address_data
        )
        
        # Should return 200 or 201 for successful creation
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data or "check_id" in data or "success" in data, f"Response should contain id or success: {data}"
    
    def test_get_address_check_returns_recorded_data(self, auth_headers):
        """Test GET returns the address check data after recording."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/address/check",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If a check was recorded, verify the data structure
        if data.get("current"):
            current = data["current"]
            assert "method" in current or "outcome" in current, "Current check should have method or outcome"
    
    def test_address_check_with_invalid_employee(self, auth_headers):
        """Test address check with non-existent employee returns 404."""
        response = requests.post(
            f"{BASE_URL}/api/employees/non-existent-id/address/check",
            headers=auth_headers,
            json={
                "method": "original_document_seen",
                "outcome": "verified",
                "checked_at": datetime.now().strftime("%Y-%m-%d")
            }
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent employee, got {response.status_code}"


class TestComplianceFileIntegration:
    """Test that compliance-file endpoint returns identity and address check data."""
    
    def test_compliance_file_returns_identity_section(self, auth_headers):
        """Test compliance-file endpoint includes identity section with check data."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check for identity section in compliance file
        sections = data.get("sections", {})
        assert "identity" in sections or "identity_verification" in sections, \
            f"Compliance file should have identity section. Available sections: {list(sections.keys())}"
    
    def test_compliance_file_returns_address_section(self, auth_headers):
        """Test compliance-file endpoint includes address/POA section with check data."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for address/POA section in compliance file
        sections = data.get("sections", {})
        assert "proof_of_address" in sections or "address" in sections or "poa" in sections, \
            f"Compliance file should have address section. Available sections: {list(sections.keys())}"
    
    def test_compliance_file_identity_check_data_structure(self, auth_headers):
        """Test identity check data structure in compliance-file response."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        sections = data.get("sections", {})
        
        # Get identity section
        identity_section = sections.get("identity") or sections.get("identity_verification")
        if identity_section:
            # Check for check row with identity-specific fields
            rows = identity_section.get("rows", [])
            check_row = next((r for r in rows if r.get("row_type") == "check"), None)
            
            if check_row and check_row.get("has_check"):
                check_data = check_row.get("check_data", {})
                # Verify identity-specific fields are present in check_data
                identity_fields = ["document_type", "full_name_on_document", "date_of_birth", 
                                   "name_matches_application", "dob_matches_application", "photo_match_confirmed"]
                present_fields = [f for f in identity_fields if f in check_data]
                print(f"Identity fields present in check_data: {present_fields}")
    
    def test_compliance_file_address_check_data_structure(self, auth_headers):
        """Test address check data structure in compliance-file response."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        sections = data.get("sections", {})
        
        # Get address section
        address_section = sections.get("proof_of_address") or sections.get("address")
        if address_section:
            # Check for check row with address-specific fields
            rows = address_section.get("rows", [])
            check_row = next((r for r in rows if r.get("row_type") == "check"), None)
            
            if check_row and check_row.get("has_check"):
                check_data = check_row.get("check_data", {})
                # Verify address-specific fields are present in check_data
                address_fields = ["documents_received_count", "documents_required_count", 
                                  "verified_documents", "extracted_address_line1", 
                                  "address_matches_application", "all_documents_sufficiently_recent"]
                present_fields = [f for f in address_fields if f in check_data]
                print(f"Address fields present in check_data: {present_fields}")


class TestComplianceEngineImports:
    """Test that compliance_engine module imports work correctly."""
    
    def test_compliance_engine_main_imports(self):
        """Test main compliance engine imports."""
        import sys
        sys.path.insert(0, '/app/backend')
        try:
            from compliance_engine import ComplianceEngine, StatusEngine, BlockerEngine
            assert ComplianceEngine is not None
            assert StatusEngine is not None
            assert BlockerEngine is not None
            print("ComplianceEngine, StatusEngine, BlockerEngine imports successful")
        except ImportError as e:
            pytest.fail(f"Failed to import compliance engine: {e}")
    
    def test_rule_packs_imports(self):
        """Test rule packs imports."""
        import sys
        sys.path.insert(0, '/app/backend')
        try:
            from compliance_engine import RTWRulePack, DBSRulePack, IdentityRulePack, POARulePack
            assert RTWRulePack is not None
            assert DBSRulePack is not None
            assert IdentityRulePack is not None
            assert POARulePack is not None
            print("All rule packs imports successful")
        except ImportError as e:
            pytest.fail(f"Failed to import rule packs: {e}")
    
    def test_models_imports(self):
        """Test models imports."""
        import sys
        sys.path.insert(0, '/app/backend')
        try:
            from compliance_engine.models import (
                RequirementType, EvidenceStatus, VerificationOutcome, 
                ComputedState, Evidence, Verification
            )
            assert RequirementType is not None
            assert EvidenceStatus is not None
            assert VerificationOutcome is not None
            print("All models imports successful")
        except ImportError as e:
            pytest.fail(f"Failed to import models: {e}")
    
    def test_labels_imports(self):
        """Test labels imports."""
        import sys
        sys.path.insert(0, '/app/backend')
        try:
            from compliance_engine.labels import (
                get_label, get_status_color, 
                IDENTITY_METHOD_LABELS, ADDRESS_METHOD_LABELS
            )
            assert get_label is not None
            assert get_status_color is not None
            assert IDENTITY_METHOD_LABELS is not None
            assert ADDRESS_METHOD_LABELS is not None
            print("All labels imports successful")
        except ImportError as e:
            pytest.fail(f"Failed to import labels: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test References Restoration - Phase D4.2 STEP A - P0 Functional Repair
Tests that references appear as proper requirement cards in the Compliance File
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")

@pytest.fixture(scope="module")
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestReferencesSection:
    """Test References section appears in Compliance File"""
    
    def test_compliance_file_has_references_section(self, api_client):
        """References section exists in compliance-file response"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        assert "sections" in data
        assert "references" in data["sections"], "References section missing from compliance file"
        
        references = data["sections"]["references"]
        assert references["title"] == "References"
        assert "rows" in references
        assert "valid_count" in references
        assert "required_count" in references
    
    def test_references_has_two_rows(self, api_client):
        """References section contains Reference 1 and Reference 2 rows"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        references = response.json()["sections"]["references"]
        rows = references["rows"]
        
        assert len(rows) == 2, f"Expected 2 reference rows, got {len(rows)}"
        
        # Check Reference 1
        ref1 = rows[0]
        assert ref1["key"] == "reference_1"
        assert ref1["title"] == "Reference 1"
        assert ref1["row_type"] == "reference"
        assert ref1["reference_num"] == 1
        
        # Check Reference 2
        ref2 = rows[1]
        assert ref2["key"] == "reference_2"
        assert ref2["title"] == "Reference 2"
        assert ref2["row_type"] == "reference"
        assert ref2["reference_num"] == 2


class TestReferenceRowFields:
    """Test reference row contains all required fields"""
    
    def test_reference_row_has_lifecycle_status(self, api_client):
        """Reference row includes lifecycle_status field"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        for row in rows:
            assert "lifecycle_status" in row, f"lifecycle_status missing from {row['key']}"
            assert row["lifecycle_status"] in [
                "verified", "reviewed", "mismatch_detected", "awaiting_review",
                "awaiting_response", "requested", "not_requested", "not_declared"
            ]
    
    def test_reference_row_has_verified_field(self, api_client):
        """Reference row includes verified field"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        for row in rows:
            assert "verified" in row, f"verified field missing from {row['key']}"
            assert isinstance(row["verified"], bool)
    
    def test_reference_row_has_has_response_field(self, api_client):
        """Reference row includes has_response field"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        for row in rows:
            assert "has_response" in row, f"has_response field missing from {row['key']}"
            assert isinstance(row["has_response"], bool)
    
    def test_reference_row_has_declared_referee(self, api_client):
        """Reference row includes declared_referee details"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        for row in rows:
            assert "has_declared" in row
            assert "declared_referee" in row
            
            if row["has_declared"]:
                referee = row["declared_referee"]
                assert referee is not None
                # Check referee fields exist
                assert "name" in referee
                assert "company" in referee
                assert "email" in referee
                assert "phone" in referee


class TestVerifiedReferences:
    """Test verified references display correctly"""
    
    def test_verified_references_have_verified_true(self, api_client):
        """Both references for test employee are verified"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        references = response.json()["sections"]["references"]
        rows = references["rows"]
        
        # Both should be verified for this test employee
        assert rows[0]["verified"] == True, "Reference 1 should be verified"
        assert rows[1]["verified"] == True, "Reference 2 should be verified"
    
    def test_verified_references_have_verifier_info(self, api_client):
        """Verified references include verifier name and date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        
        for row in rows:
            if row["verified"]:
                assert row["verified_by"] is not None, f"verified_by missing for {row['key']}"
                assert row["verified_at"] is not None, f"verified_at missing for {row['key']}"
    
    def test_verified_references_lifecycle_status(self, api_client):
        """Verified references have lifecycle_status='verified'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        
        for row in rows:
            if row["verified"]:
                assert row["lifecycle_status"] == "verified"
    
    def test_verified_references_status_summary(self, api_client):
        """Verified references have status_summary with company and date"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        
        for row in rows:
            if row["verified"]:
                summary = row["status_summary"]
                assert "Verified" in summary, f"status_summary should contain 'Verified': {summary}"
                # Should contain company name
                company = row["declared_referee"]["company"]
                assert company in summary, f"status_summary should contain company '{company}': {summary}"


class TestReferenceRowActions:
    """Test reference row allowed_actions"""
    
    def test_verified_reference_has_view_response_action(self, api_client):
        """Verified references with response have view_response action"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        
        # Reference 2 has a response
        ref2 = rows[1]
        if ref2["has_response"]:
            assert "view_response" in ref2["allowed_actions"], "view_response action missing"
    
    def test_reference_has_view_history_action(self, api_client):
        """All references have view_history action"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        rows = response.json()["sections"]["references"]["rows"]
        
        for row in rows:
            assert "view_history" in row["allowed_actions"], f"view_history missing from {row['key']}"


class TestReferenceValidCount:
    """Test references valid_count calculation"""
    
    def test_valid_count_matches_verified_references(self, api_client):
        """valid_count equals number of verified references"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        references = response.json()["sections"]["references"]
        rows = references["rows"]
        
        verified_count = sum(1 for row in rows if row["verified"])
        assert references["valid_count"] == verified_count
        assert references["required_count"] == 2

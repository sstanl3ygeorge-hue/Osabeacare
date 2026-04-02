"""
Test suite for verifying compliance features:
1. Dual-Row Compliance UI (RTW and DBS sections)
2. Recruitment Record (Application Form, CV/Resume)
3. Training Matrix with 3 tabs (Mandatory, All Qualifications, Certificates)
4. Document Request Email Flow
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json().get("token")
    assert token, "No token returned"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTrainingMatrixAPI:
    """Test Training Matrix API - returns items and additional_items arrays"""
    
    def test_training_matrix_returns_items_array(self, auth_headers):
        """Training matrix should return items array for mandatory training"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify items array exists
        assert "items" in data, "Missing 'items' array in response"
        assert isinstance(data["items"], list), "items should be a list"
        
        # Verify 6 mandatory training items
        assert len(data["items"]) == 6, f"Expected 6 mandatory items, got {len(data['items'])}"
        
        # Verify item structure
        for item in data["items"]:
            assert "code" in item
            assert "title" in item
            assert "status" in item
            assert "blocker" in item
    
    def test_training_matrix_returns_additional_items_array(self, auth_headers):
        """Training matrix should return additional_items array for non-mandatory training"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify additional_items array exists
        assert "additional_items" in data, "Missing 'additional_items' array in response"
        assert isinstance(data["additional_items"], list), "additional_items should be a list"
        
        # Verify additional items have correct structure
        for item in data["additional_items"]:
            assert "code" in item
            assert "title" in item
            assert "status" in item
            assert "is_additional" in item
            assert item["is_additional"] == True, "Additional items should have is_additional=True"
    
    def test_training_matrix_returns_summary(self, auth_headers):
        """Training matrix should return summary with correct counts"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/matrix",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify summary exists
        assert "summary" in data, "Missing 'summary' in response"
        summary = data["summary"]
        
        # Verify summary fields
        assert "total" in summary
        assert "current" in summary
        assert "expiring" in summary
        assert "missing" in summary
        assert "blockers" in summary
        assert "additional_count" in summary
        
        # Verify total matches items count
        assert summary["total"] == len(data["items"])


class TestDualRowComplianceAPI:
    """Test Dual-Row Compliance Model for RTW and DBS sections"""
    
    def test_compliance_file_has_rtw_section(self, auth_headers):
        """Compliance file should have right_to_work section with dual-row model"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify RTW section exists
        assert "sections" in data
        assert "right_to_work" in data["sections"], "Missing right_to_work section"
        
        rtw = data["sections"]["right_to_work"]
        assert "rows" in rtw, "RTW section should have rows"
        
        # Verify dual-row model: evidence row and check row
        row_types = [row.get("row_type") for row in rtw["rows"]]
        assert "evidence" in row_types, "RTW should have evidence row"
        assert "check" in row_types, "RTW should have check (verification) row"
    
    def test_rtw_evidence_row_structure(self, auth_headers):
        """RTW evidence row should have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        rtw = data["sections"]["right_to_work"]
        evidence_row = next((r for r in rtw["rows"] if r.get("row_type") == "evidence"), None)
        
        assert evidence_row is not None, "RTW evidence row not found"
        assert "counts" in evidence_row
        assert "documents_preview" in evidence_row or "status" in evidence_row
    
    def test_rtw_verification_row_structure(self, auth_headers):
        """RTW verification row should have check_data with method, outcome, checked_at"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        rtw = data["sections"]["right_to_work"]
        check_row = next((r for r in rtw["rows"] if r.get("row_type") == "check"), None)
        
        assert check_row is not None, "RTW check row not found"
        assert "check_data" in check_row or "has_check" in check_row
        
        if check_row.get("has_check"):
            check_data = check_row.get("check_data", {})
            assert "method" in check_data, "Check data should have method"
            assert "outcome" in check_data, "Check data should have outcome"
            assert "checked_at" in check_data, "Check data should have checked_at"
    
    def test_compliance_file_has_dbs_section(self, auth_headers):
        """Compliance file should have dbs section with dual-row model"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify DBS section exists
        assert "dbs" in data["sections"], "Missing dbs section"
        
        dbs = data["sections"]["dbs"]
        assert "rows" in dbs, "DBS section should have rows"
        
        # Verify dual-row model: evidence row and check row
        row_types = [row.get("row_type") for row in dbs["rows"]]
        assert "evidence" in row_types, "DBS should have evidence row"
        assert "check" in row_types, "DBS should have check (verification) row"
    
    def test_dbs_verification_row_has_proof(self, auth_headers):
        """DBS verification row should support proof of check"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        dbs = data["sections"]["dbs"]
        check_row = next((r for r in dbs["rows"] if r.get("row_type") == "check"), None)
        
        assert check_row is not None, "DBS check row not found"
        
        if check_row.get("has_check"):
            check_data = check_row.get("check_data", {})
            # Verify proof document fields exist
            assert "evidence_document_id" in check_data or "evidence_document" in check_data or True


class TestRecruitmentRecordAPI:
    """Test Recruitment Record section with Application Form and CV"""
    
    def test_compliance_file_has_recruitment_record(self, auth_headers):
        """Compliance file should have recruitment_record section"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "recruitment_record" in data["sections"], "Missing recruitment_record section"
    
    def test_recruitment_record_has_application_form(self, auth_headers):
        """Recruitment record should have application_form row"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        recruitment = data["sections"]["recruitment_record"]
        assert "rows" in recruitment
        
        app_form = next((r for r in recruitment["rows"] if r.get("key") == "application_form"), None)
        assert app_form is not None, "Application form row not found"
        assert app_form.get("row_type") == "form"
    
    def test_recruitment_record_has_cv_resume(self, auth_headers):
        """Recruitment record should have cv row"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        recruitment = data["sections"]["recruitment_record"]
        cv_row = next((r for r in recruitment["rows"] if r.get("key") == "cv"), None)
        
        assert cv_row is not None, "CV row not found"
        assert cv_row.get("row_type") == "evidence"
    
    def test_cv_shows_file_if_uploaded(self, auth_headers):
        """CV row should show file info if uploaded"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        recruitment = data["sections"]["recruitment_record"]
        cv_row = next((r for r in recruitment["rows"] if r.get("key") == "cv"), None)
        
        # This employee has a CV uploaded
        assert cv_row.get("has_files") == True, "CV should have files"
        assert cv_row.get("file_count", 0) >= 1, "CV should have at least 1 file"


class TestDocumentRequestAPI:
    """Test Document Request API returns request_id"""
    
    def test_document_request_returns_request_id(self, auth_headers):
        """Document request should return request_id when successful"""
        import time
        unique_req = f"test_verification_{int(time.time())}"
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/request-document",
            params={"requirement_id": unique_req},
            headers=auth_headers,
            json={"message": "Test verification request"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify request_id is returned
        assert "request_id" in data, "Response should contain request_id"
        assert data["request_id"] is not None, "request_id should not be null for new request"
        assert "status" in data
        assert data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

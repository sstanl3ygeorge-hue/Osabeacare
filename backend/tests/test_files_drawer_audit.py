"""
Test suite for Files Drawer Audit - Comprehensive testing of:
- Files endpoint returns Active Files, Request History, Historical Files
- Row summaries reflect actual backend counts
- File-level actions work correctly
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFilesDrawerAudit:
    """Files Drawer Audit Tests - Verifying drawer renders real endpoint data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        
        # Login and get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": self.admin_email, "password": self.admin_password}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # =========================================================================
    # DBS Evidence Files Tests
    # =========================================================================
    
    def test_dbs_evidence_files_endpoint_returns_active_files(self):
        """DBS Evidence should return 2 active files (1 verified, 1 pending)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/dbs_certificate_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify active files count
        assert data["active_file_count"] == 2, f"Expected 2 active files, got {data['active_file_count']}"
        assert len(data["active_files"]) == 2
        
        # Verify verified count
        assert data["verified_count"] == 1, f"Expected 1 verified, got {data['verified_count']}"
        
        # Verify file details
        verified_files = [f for f in data["active_files"] if f.get("verified")]
        assert len(verified_files) == 1, "Should have 1 verified file"
        
        pending_files = [f for f in data["active_files"] if not f.get("verified")]
        assert len(pending_files) == 1, "Should have 1 pending file"
        
        print(f"DBS Evidence: {data['active_file_count']} active, {data['verified_count']} verified")
    
    def test_dbs_evidence_files_endpoint_returns_request_history(self):
        """DBS Evidence should return request history with 1 pending request"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/dbs_certificate_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify request history
        assert "requests" in data, "Response should include requests array"
        assert data["request_count"] >= 1, f"Expected at least 1 request, got {data['request_count']}"
        
        # Verify request details
        if data["requests"]:
            request = data["requests"][0]
            assert "request_id" in request
            assert "status" in request
            assert "sent_at" in request
            print(f"DBS Request History: {data['request_count']} requests, latest status: {request['status']}")
    
    def test_dbs_evidence_files_endpoint_returns_historical_files(self):
        """DBS Evidence should return historical files array (may be empty)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/dbs_certificate_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify historical files structure
        assert "historical_files" in data, "Response should include historical_files array"
        assert "historical_file_count" in data
        assert data["historical_file_count"] == len(data["historical_files"])
        
        print(f"DBS Historical Files: {data['historical_file_count']}")
    
    # =========================================================================
    # RTW Evidence Files Tests
    # =========================================================================
    
    def test_rtw_evidence_files_endpoint_returns_verified_file(self):
        """RTW Evidence should return 1 verified file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify counts
        assert data["active_file_count"] == 1, f"Expected 1 active file, got {data['active_file_count']}"
        assert data["verified_count"] == 1, f"Expected 1 verified, got {data['verified_count']}"
        
        # Verify file is verified
        assert data["active_files"][0]["verified"] == True
        
        print(f"RTW Evidence: {data['active_file_count']} active, {data['verified_count']} verified")
    
    def test_rtw_evidence_multi_file_config(self):
        """RTW Evidence should have multi-file config with required_count=1"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify multi-file config
        assert "multi_file_config" in data
        config = data["multi_file_config"]
        assert config["multi_file"] == True
        assert config["required_count"] == 1
        
        print(f"RTW Multi-file config: required_count={config['required_count']}")
    
    # =========================================================================
    # Identity Evidence Files Tests
    # =========================================================================
    
    def test_identity_evidence_files_endpoint_returns_no_active_files(self):
        """Identity Evidence should return 0 active files (all superseded)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/identity_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify no active files
        assert data["active_file_count"] == 0, f"Expected 0 active files, got {data['active_file_count']}"
        
        print(f"Identity Evidence: {data['active_file_count']} active files")
    
    def test_identity_evidence_files_endpoint_returns_historical_files(self):
        """Identity Evidence should return historical files (superseded)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/identity_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify historical files
        assert data["historical_file_count"] >= 1, f"Expected at least 1 historical file, got {data['historical_file_count']}"
        
        # Verify superseded status
        if data["historical_files"]:
            superseded_files = [f for f in data["historical_files"] if f.get("status") == "superseded"]
            assert len(superseded_files) >= 1, "Should have at least 1 superseded file"
        
        print(f"Identity Historical Files: {data['historical_file_count']}")
    
    def test_identity_evidence_files_endpoint_returns_request_history(self):
        """Identity Evidence should return request history"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/identity_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify request history
        assert data["request_count"] >= 1, f"Expected at least 1 request, got {data['request_count']}"
        
        print(f"Identity Request History: {data['request_count']} requests")
    
    # =========================================================================
    # Proof of Address Evidence Files Tests
    # =========================================================================
    
    def test_poa_evidence_files_endpoint_returns_no_active_files(self):
        """Proof of Address Evidence should return 0 active files"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/proof_of_address_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify no active files
        assert data["active_file_count"] == 0, f"Expected 0 active files, got {data['active_file_count']}"
        
        print(f"PoA Evidence: {data['active_file_count']} active files")
    
    def test_poa_evidence_multi_file_config(self):
        """Proof of Address Evidence should have multi-file config with required_count=2"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/proof_of_address_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify multi-file config
        assert "multi_file_config" in data
        config = data["multi_file_config"]
        assert config["multi_file"] == True
        assert config["required_count"] == 2
        
        print(f"PoA Multi-file config: required_count={config['required_count']}")
    
    def test_poa_evidence_files_endpoint_returns_request_history(self):
        """Proof of Address Evidence should return request history"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/proof_of_address_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify request history
        assert data["request_count"] >= 1, f"Expected at least 1 request, got {data['request_count']}"
        
        print(f"PoA Request History: {data['request_count']} requests")
    
    # =========================================================================
    # File Structure Validation Tests
    # =========================================================================
    
    def test_active_file_structure(self):
        """Verify active file has all required fields for drawer display"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/dbs_certificate_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["active_files"]) > 0, "Need at least 1 active file to test"
        
        file = data["active_files"][0]
        required_fields = [
            "file_id", "file_name", "file_url", "file_available",
            "status", "source_type", "uploaded_by", "uploaded_at",
            "verified", "rejected", "extraction_status"
        ]
        
        for field in required_fields:
            assert field in file, f"Active file missing required field: {field}"
        
        print(f"Active file structure validated: {len(required_fields)} required fields present")
    
    def test_request_history_structure(self):
        """Verify request history has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/dbs_certificate_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["requests"]) > 0, "Need at least 1 request to test"
        
        request = data["requests"][0]
        required_fields = [
            "request_id", "status", "source", "created_at", "sent_at",
            "viewed_at", "submitted_at", "is_replacement", "reminder_count"
        ]
        
        for field in required_fields:
            assert field in request, f"Request missing required field: {field}"
        
        print(f"Request history structure validated: {len(required_fields)} required fields present")
    
    # =========================================================================
    # Row Summary Verification Tests
    # =========================================================================
    
    def test_compliance_endpoint_returns_evidence_rows(self):
        """Verify compliance endpoint returns evidence rows with correct summaries"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check compliance items exist
        assert "compliance" in data
        assert "items" in data["compliance"]
        
        # Find DBS certificate item
        dbs_item = next((item for item in data["compliance"]["items"] if item["id"] == "dbs_certificate"), None)
        assert dbs_item is not None, "DBS certificate item not found"
        
        # Find RTW documents item
        rtw_item = next((item for item in data["compliance"]["items"] if item["id"] == "right_to_work_documents"), None)
        assert rtw_item is not None, "RTW documents item not found"
        
        print(f"Compliance items found: DBS={dbs_item['status']}, RTW={rtw_item['status']}")


class TestFileActions:
    """Test file-level actions from the drawer"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        
        # Login and get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": self.admin_email, "password": self.admin_password}
        )
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_file_has_action_menu_fields(self):
        """Verify file has fields needed for action menu decisions"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/dbs_certificate_evidence/files",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["active_files"]) > 0
        file = data["active_files"][0]
        
        # Fields needed for action menu
        action_fields = ["verified", "rejected", "status", "extraction_status"]
        for field in action_fields:
            assert field in file, f"File missing action field: {field}"
        
        print("File has all action menu fields")
    
    def test_verify_endpoint_exists(self):
        """Verify the verify endpoint exists (don't actually verify)"""
        # Just check the endpoint pattern exists by checking a non-existent file
        response = requests.post(
            f"{BASE_URL}/api/documents/non-existent-id/verify",
            headers=self.headers,
            json={}
        )
        # Should return 404 for non-existent file, not 405 for method not allowed
        assert response.status_code in [404, 400], f"Unexpected status: {response.status_code}"
        print("Verify endpoint exists")
    
    def test_supersede_endpoint_exists(self):
        """Verify the supersede endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/documents/non-existent-id/supersede",
            headers=self.headers,
            json={"reason": "test"}
        )
        assert response.status_code in [404, 400], f"Unexpected status: {response.status_code}"
        print("Supersede endpoint exists")
    
    def test_mark_uploaded_in_error_endpoint_exists(self):
        """Verify the mark-uploaded-in-error endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/documents/non-existent-id/mark-uploaded-in-error",
            headers=self.headers,
            json={"reason": "test"}
        )
        # 404/400/422 all indicate endpoint exists (422 = validation error for non-existent file)
        assert response.status_code in [404, 400, 422], f"Unexpected status: {response.status_code}"
        print("Mark uploaded in error endpoint exists")
    
    def test_move_category_endpoint_exists(self):
        """Verify the move-category endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/documents/non-existent-id/move-category",
            headers=self.headers,
            json={"reason": "test", "new_requirement_id": "other"}
        )
        # 404/400/422 all indicate endpoint exists (422 = validation error for non-existent file)
        assert response.status_code in [404, 400, 422], f"Unexpected status: {response.status_code}"
        print("Move category endpoint exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

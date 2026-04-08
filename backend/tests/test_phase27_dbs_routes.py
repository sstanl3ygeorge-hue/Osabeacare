"""
Phase 27: DBS Routes Extraction Tests
Tests for DBS endpoints extracted from server.py to routes/dbs.py

Endpoints tested:
1. GET /api/dbs-register - DBS Register with status filters
2. POST /api/dbs/extract - Extract DBS certificate fields using AI Vision
3. POST /api/employees/{employee_id}/dbs/check - Record DBS check
4. GET /api/employees/{employee_id}/dbs/check - Get DBS check with optional history
5. POST /api/employees/{employee_id}/dbs/stamp-all - Stamp all DBS documents
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestPhase27DBSRoutes:
    """Test suite for Phase 27 DBS routes extraction"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.auth_token = None
        self.test_employee_id = None
        
    def get_auth_token(self):
        """Get authentication token"""
        if self.auth_token:
            return self.auth_token
            
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            self.auth_token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            return self.auth_token
        pytest.skip(f"Authentication failed: {response.status_code}")
        
    def get_test_employee_id(self):
        """Get a test employee ID"""
        if self.test_employee_id:
            return self.test_employee_id
            
        self.get_auth_token()
        # Get any employee from the system
        response = self.session.get(f"{BASE_URL}/api/employees?limit=1")
        if response.status_code == 200:
            data = response.json()
            employees = data.get("employees", data) if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                self.test_employee_id = employees[0].get("id")
                return self.test_employee_id
        pytest.skip("No employees found for testing")

    # ==================== DBS REGISTER TESTS ====================
    
    def test_dbs_register_basic(self):
        """Test GET /api/dbs-register - basic request"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/dbs-register")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "register" in data, "Response should contain 'register' field"
        assert "stats" in data, "Response should contain 'stats' field"
        
        # Verify stats structure
        stats = data["stats"]
        assert "total" in stats, "Stats should contain 'total'"
        assert "current" in stats, "Stats should contain 'current'"
        assert "missing" in stats, "Stats should contain 'missing'"
        assert "needs_attention" in stats, "Stats should contain 'needs_attention'"
        
        print(f"DBS Register: {stats['total']} employees, {stats['needs_attention']} need attention")
        
    def test_dbs_register_with_status_filter(self):
        """Test GET /api/dbs-register with status_filter parameter"""
        self.get_auth_token()
        
        # Test with 'missing' status filter
        response = self.session.get(f"{BASE_URL}/api/dbs-register?status_filter=missing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # All returned records should have dbs_status = 'missing'
        for record in data.get("register", []):
            assert record.get("dbs_status") == "missing", f"Expected dbs_status='missing', got {record.get('dbs_status')}"
            
        print(f"DBS Register (missing filter): {len(data.get('register', []))} records")
        
    def test_dbs_register_with_needs_attention_filter(self):
        """Test GET /api/dbs-register with needs_attention=true"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/dbs-register?needs_attention=true")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # All returned records should have needs_attention = True
        for record in data.get("register", []):
            assert record.get("needs_attention") == True, f"Expected needs_attention=True"
            
        print(f"DBS Register (needs_attention): {len(data.get('register', []))} records")
        
    def test_dbs_register_unauthorized(self):
        """Test GET /api/dbs-register without auth"""
        # Don't set auth token
        response = requests.get(f"{BASE_URL}/api/dbs-register")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    # ==================== DBS EXTRACTION TESTS ====================
    
    def test_dbs_extract_no_input(self):
        """Test POST /api/dbs/extract with no input - should return 400"""
        self.get_auth_token()
        
        response = self.session.post(
            f"{BASE_URL}/api/dbs/extract",
            json={}
        )
        
        # Should return 400 because neither document_id nor file_base64 provided
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
    def test_dbs_extract_invalid_document_id(self):
        """Test POST /api/dbs/extract with invalid document_id"""
        self.get_auth_token()
        
        response = self.session.post(
            f"{BASE_URL}/api/dbs/extract",
            json={"document_id": "nonexistent-doc-id-12345"}
        )
        
        # Should return 404 for non-existent document
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
    def test_dbs_extract_unauthorized(self):
        """Test POST /api/dbs/extract without auth - requires manager/admin"""
        response = requests.post(
            f"{BASE_URL}/api/dbs/extract",
            json={"document_id": "test"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_dbs_extract_with_base64_image(self):
        """Test POST /api/dbs/extract with base64 image - tests endpoint structure"""
        self.get_auth_token()
        
        # Small test image (1x1 white pixel PNG)
        test_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = self.session.post(
            f"{BASE_URL}/api/dbs/extract",
            json={
                "file_base64": test_base64,
                "file_type": "image/png"
            }
        )
        
        # Should return 200 with extraction result (may have empty fields for tiny image)
        # Or 500 if LLM key not configured
        assert response.status_code in [200, 500], f"Expected 200 or 500, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response should contain 'success' field"
            assert "extraction" in data or "error" in data, "Response should contain 'extraction' or 'error'"
            print(f"DBS Extract response: success={data.get('success')}")
            
    # ==================== DBS CHECK RECORD TESTS ====================
    
    def test_record_dbs_check(self):
        """Test POST /api/employees/{employee_id}/dbs/check - record DBS check"""
        self.get_auth_token()
        employee_id = self.get_test_employee_id()
        
        check_data = {
            "method": "dbs_certificate_review",
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "outcome": "verified",
            "dbs_level": "enhanced",
            "certificate_number": "123456789012",
            "certificate_issue_date": "2025-01-15",
            "name_on_certificate": "Test Employee",
            "workforce": "adult_and_child",
            "update_service_registered": True,
            "update_service_status": "active",
            "recheck_required": True,
            "next_recheck_date": "2027-01-15",
            "result_status": "clear",
            "information_present": False,
            "result_summary": "Clear - no information disclosed",
            "notes": "TEST_Phase27 - DBS check recorded via API test"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{employee_id}/dbs/check",
            json=check_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response contains expected fields
        assert "success" in data or "id" in data or "check_id" in data, f"Response should indicate success: {data}"
        print(f"DBS Check recorded for employee {employee_id}")
        
    def test_record_dbs_check_invalid_employee(self):
        """Test POST /api/employees/{employee_id}/dbs/check with invalid employee"""
        self.get_auth_token()
        
        check_data = {
            "method": "dbs_certificate_review",
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "outcome": "verified"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/dbs/check",
            json=check_data
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
    def test_record_dbs_check_unauthorized(self):
        """Test POST /api/employees/{employee_id}/dbs/check without auth"""
        response = requests.post(
            f"{BASE_URL}/api/employees/test-id/dbs/check",
            json={"method": "dbs_certificate_review", "checked_at": "2026-01-01", "outcome": "verified"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    # ==================== GET DBS CHECK TESTS ====================
    
    def test_get_dbs_check(self):
        """Test GET /api/employees/{employee_id}/dbs/check - get current DBS check"""
        self.get_auth_token()
        employee_id = self.get_test_employee_id()
        
        response = self.session.get(f"{BASE_URL}/api/employees/{employee_id}/dbs/check")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Response should contain 'current' field
        assert "current" in data, "Response should contain 'current' field"
        print(f"DBS Check for {employee_id}: current={data.get('current') is not None}")
        
    def test_get_dbs_check_with_history(self):
        """Test GET /api/employees/{employee_id}/dbs/check?include_history=true"""
        self.get_auth_token()
        employee_id = self.get_test_employee_id()
        
        response = self.session.get(f"{BASE_URL}/api/employees/{employee_id}/dbs/check?include_history=true")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Response should contain both 'current' and 'history' fields
        assert "current" in data, "Response should contain 'current' field"
        assert "history" in data, "Response should contain 'history' field when include_history=true"
        
        print(f"DBS Check history for {employee_id}: {len(data.get('history', []))} records")
        
    def test_get_dbs_check_unauthorized(self):
        """Test GET /api/employees/{employee_id}/dbs/check without auth"""
        response = requests.get(f"{BASE_URL}/api/employees/test-id/dbs/check")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    # ==================== DBS STAMP ALL TESTS ====================
    
    def test_stamp_all_dbs_invalid_employee(self):
        """Test POST /api/employees/{employee_id}/dbs/stamp-all with invalid employee"""
        self.get_auth_token()
        
        stamp_data = {
            "evidence_file_ids": ["test-file-id"],
            "stamp_verification_proof": True
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/dbs/stamp-all",
            json=stamp_data
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
    def test_stamp_all_dbs_empty_files(self):
        """Test POST /api/employees/{employee_id}/dbs/stamp-all with empty file list"""
        self.get_auth_token()
        employee_id = self.get_test_employee_id()
        
        stamp_data = {
            "evidence_file_ids": [],
            "stamp_verification_proof": True
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{employee_id}/dbs/stamp-all",
            json=stamp_data
        )
        
        # Should succeed with 0 documents stamped
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Should succeed even with empty file list"
        assert data.get("documents_stamped") == 0, "Should stamp 0 documents"
        print(f"Stamp all DBS (empty): verification_id={data.get('verification_id')}")
        
    def test_stamp_all_dbs_unauthorized(self):
        """Test POST /api/employees/{employee_id}/dbs/stamp-all without auth"""
        response = requests.post(
            f"{BASE_URL}/api/employees/test-id/dbs/stamp-all",
            json={"evidence_file_ids": [], "stamp_verification_proof": True},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_stamp_all_dbs_with_nonexistent_files(self):
        """Test POST /api/employees/{employee_id}/dbs/stamp-all with non-existent file IDs"""
        self.get_auth_token()
        employee_id = self.get_test_employee_id()
        
        stamp_data = {
            "evidence_file_ids": ["nonexistent-file-1", "nonexistent-file-2"],
            "stamp_verification_proof": True
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/employees/{employee_id}/dbs/stamp-all",
            json=stamp_data
        )
        
        # Should succeed but with errors for non-existent files
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Should succeed overall"
        assert data.get("errors") is not None, "Should have errors for non-existent files"
        print(f"Stamp all DBS (nonexistent files): errors={data.get('errors')}")
        
    # ==================== REGRESSION TESTS ====================
    
    def test_regression_agreements_endpoint(self):
        """Regression: Phase 26 agreements endpoint still works"""
        self.get_auth_token()
        employee_id = self.get_test_employee_id()
        
        response = self.session.get(f"{BASE_URL}/api/employees/{employee_id}/agreements")
        
        assert response.status_code == 200, f"Phase 26 agreements endpoint failed: {response.status_code}"
        print("Regression: Phase 26 agreements endpoint OK")
        
    def test_regression_recurring_compliance_endpoint(self):
        """Regression: Phase 25 recurring compliance endpoint still works"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/recurring-compliance")
        
        assert response.status_code == 200, f"Phase 25 recurring compliance endpoint failed: {response.status_code}"
        print("Regression: Phase 25 recurring compliance endpoint OK")
        
    def test_regression_employment_gaps_endpoint(self):
        """Regression: Phase 24 employment gaps endpoint still works"""
        self.get_auth_token()
        employee_id = self.get_test_employee_id()
        
        response = self.session.get(f"{BASE_URL}/api/employees/{employee_id}/employment-gaps")
        
        assert response.status_code == 200, f"Phase 24 employment gaps endpoint failed: {response.status_code}"
        print("Regression: Phase 24 employment gaps endpoint OK")
        
    def test_regression_bulk_schedules_endpoint(self):
        """Regression: Phase 22 bulk schedules endpoint still works"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/bulk/schedules")
        
        assert response.status_code == 200, f"Phase 22 bulk schedules endpoint failed: {response.status_code}"
        print("Regression: Phase 22 bulk schedules endpoint OK")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

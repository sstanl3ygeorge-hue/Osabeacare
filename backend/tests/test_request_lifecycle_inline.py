"""
Phase D4 - Request Lifecycle Inline Display Tests

Tests for:
- request_lifecycle object in compliance-file endpoint
- Status values (not_requested, sent, viewed, submitted)
- Timestamps (last_requested_at, last_viewed_at, last_submitted_at)
- Source (manual/scheduled)
- Stale request detection (7+ days old, not submitted)
- Multi-file awareness (files_needed, files_submitted)
- Action flags (can_resend, can_request_replacement)
- Resend request endpoint
- Request replacement endpoint
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRequestLifecycleInline:
    """Tests for Phase D4 - Request Lifecycle Inline Display"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        self.employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def _get_all_rows(self, data):
        """Helper to iterate through all rows in sections (object format)"""
        sections = data.get("sections", {})
        for section_key, section_data in sections.items():
            if isinstance(section_data, dict):
                for row in section_data.get("rows", []):
                    yield row
    
    # =========================================================================
    # Test: compliance-file endpoint returns request_lifecycle
    # =========================================================================
    def test_compliance_file_returns_request_lifecycle(self):
        """Verify compliance-file endpoint returns request_lifecycle in evidence rows"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "sections" in data, "Response should have sections"
        
        # Find an evidence row
        evidence_row_found = False
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence":
                evidence_row_found = True
                assert "request_lifecycle" in row, f"Evidence row {row.get('key')} should have request_lifecycle"
                
                lifecycle = row["request_lifecycle"]
                # Verify structure
                assert "status" in lifecycle, "request_lifecycle should have status"
                assert "current_request" in lifecycle, "request_lifecycle should have current_request"
                assert "last_requested_at" in lifecycle, "request_lifecycle should have last_requested_at"
                assert "last_viewed_at" in lifecycle, "request_lifecycle should have last_viewed_at"
                assert "last_submitted_at" in lifecycle, "request_lifecycle should have last_submitted_at"
                assert "source" in lifecycle, "request_lifecycle should have source"
                assert "is_stale" in lifecycle, "request_lifecycle should have is_stale"
                assert "stale_days" in lifecycle, "request_lifecycle should have stale_days"
                assert "files_submitted" in lifecycle, "request_lifecycle should have files_submitted"
                assert "files_needed" in lifecycle, "request_lifecycle should have files_needed"
                assert "can_resend" in lifecycle, "request_lifecycle should have can_resend"
                assert "can_request_replacement" in lifecycle, "request_lifecycle should have can_request_replacement"
                assert "is_replacement_request" in lifecycle, "request_lifecycle should have is_replacement_request"
                break
        
        assert evidence_row_found, "Should find at least one evidence row"
        print("✓ compliance-file endpoint returns request_lifecycle in evidence rows")
    
    # =========================================================================
    # Test: request_lifecycle status values
    # =========================================================================
    def test_request_lifecycle_status_values(self):
        """Verify request_lifecycle status is one of valid values"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        valid_statuses = ["not_requested", "pending", "sent", "viewed", "submitted", "awaiting_review", "verified", "rejected", "expired"]
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                status = row["request_lifecycle"]["status"]
                assert status in valid_statuses, f"Invalid status '{status}' for {row.get('key')}"
        
        print("✓ All request_lifecycle status values are valid")
    
    # =========================================================================
    # Test: DBS Certificate Evidence has 'sent' status (per test context)
    # =========================================================================
    def test_dbs_evidence_has_sent_status(self):
        """Verify DBS Certificate Evidence has request status 'sent'"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        dbs_evidence_found = False
        
        for row in self._get_all_rows(data):
            if row.get("key") in ["dbs_certificate_evidence", "dbs_evidence"]:
                dbs_evidence_found = True
                lifecycle = row.get("request_lifecycle", {})
                status = lifecycle.get("status")
                print(f"DBS Evidence status: {status}")
                # Status should be 'sent' per test context
                assert status == "sent", f"DBS Evidence status should be 'sent', got {status}"
                break
        
        assert dbs_evidence_found, "DBS Evidence row should exist"
        print("✓ DBS Evidence has 'sent' status")
    
    # =========================================================================
    # Test: RTW Evidence status
    # =========================================================================
    def test_rtw_evidence_status(self):
        """Verify RTW Evidence request_lifecycle status"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_evidence_found = False
        
        for row in self._get_all_rows(data):
            if row.get("key") in ["right_to_work_evidence", "rtw_evidence"]:
                rtw_evidence_found = True
                lifecycle = row.get("request_lifecycle", {})
                status = lifecycle.get("status")
                print(f"RTW Evidence status: {status}")
                # Verify status is valid
                assert status is not None, "RTW Evidence should have a status"
                break
        
        assert rtw_evidence_found, "RTW Evidence row should exist"
        print(f"✓ RTW Evidence status: {status}")
    
    # =========================================================================
    # Test: can_resend flag logic
    # =========================================================================
    def test_can_resend_flag(self):
        """Verify can_resend flag is set correctly based on status"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                status = lifecycle["status"]
                can_resend = lifecycle["can_resend"]
                
                # can_resend should be True for sent/viewed status or stale requests
                if status in ["sent", "viewed"]:
                    assert can_resend == True, f"can_resend should be True for status '{status}'"
                elif status == "not_requested":
                    assert can_resend == False, f"can_resend should be False for status 'not_requested'"
        
        print("✓ can_resend flag logic is correct")
    
    # =========================================================================
    # Test: can_request_replacement flag logic
    # =========================================================================
    def test_can_request_replacement_flag(self):
        """Verify can_request_replacement flag is set when files are verified"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                can_replace = lifecycle["can_request_replacement"]
                verified_count = row.get("counts", {}).get("verified", 0)
                
                # can_request_replacement should be True if verified_count > 0
                if verified_count > 0:
                    assert can_replace == True, f"can_request_replacement should be True when verified_count={verified_count}"
        
        print("✓ can_request_replacement flag logic is correct")
    
    # =========================================================================
    # Test: Multi-file awareness (files_needed, files_submitted)
    # =========================================================================
    def test_multi_file_awareness(self):
        """Verify multi-file requirements have files_needed and files_submitted"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        for row in self._get_all_rows(data):
            if row.get("key") in ["proof_of_address_evidence", "proof_of_address"]:
                lifecycle = row.get("request_lifecycle", {})
                files_needed = lifecycle.get("files_needed")
                files_submitted = lifecycle.get("files_submitted")
                
                assert files_needed is not None, "Proof of Address should have files_needed"
                assert files_submitted is not None, "Proof of Address should have files_submitted"
                assert isinstance(files_needed, int), "files_needed should be an integer"
                assert isinstance(files_submitted, int), "files_submitted should be an integer"
                
                print(f"✓ Proof of Address: files_needed={files_needed}, files_submitted={files_submitted}")
                return
        
        print("✓ Multi-file awareness test completed (proof_of_address row may not exist)")
    
    # =========================================================================
    # Test: Stale request detection
    # =========================================================================
    def test_stale_request_detection(self):
        """Verify stale request detection (is_stale, stale_days)"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                is_stale = lifecycle.get("is_stale")
                stale_days = lifecycle.get("stale_days")
                
                assert isinstance(is_stale, bool), "is_stale should be a boolean"
                assert isinstance(stale_days, int), "stale_days should be an integer"
                
                # If stale, stale_days should be >= 7
                if is_stale:
                    assert stale_days >= 7, f"stale_days should be >= 7 when is_stale=True, got {stale_days}"
                    print(f"Found stale request: {row.get('key')} - {stale_days} days old")
        
        print("✓ Stale request detection fields are correct")
    
    # =========================================================================
    # Test: current_request structure
    # =========================================================================
    def test_current_request_structure(self):
        """Verify current_request has correct structure when present"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                current_request = lifecycle.get("current_request")
                
                if current_request is not None:
                    # Verify structure
                    assert "id" in current_request, "current_request should have id"
                    assert "status" in current_request, "current_request should have status"
                    assert "source" in current_request, "current_request should have source"
                    assert "sent_at" in current_request, "current_request should have sent_at"
                    assert "viewed_at" in current_request, "current_request should have viewed_at"
                    assert "submitted_at" in current_request, "current_request should have submitted_at"
                    assert "due_date" in current_request, "current_request should have due_date"
                    assert "reminder_count" in current_request, "current_request should have reminder_count"
                    assert "is_replacement" in current_request, "current_request should have is_replacement"
                    
                    print(f"✓ current_request structure verified for {row.get('key')}")
                    return
        
        print("✓ current_request structure test completed (no active requests found)")
    
    # =========================================================================
    # Test: Resend request endpoint
    # =========================================================================
    def test_resend_request_endpoint(self):
        """Test resend-request endpoint"""
        # First, find a requirement with a sent request
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        requirement_key = None
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                if lifecycle.get("can_resend"):
                    requirement_key = row.get("key")
                    break
        
        if not requirement_key:
            # Use a default requirement key for testing
            requirement_key = "dbs_certificate_evidence"
        
        # Test the resend endpoint
        resend_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{requirement_key}/resend-request",
            json={"message": "Test resend request"}
        )
        
        # Should succeed or fail with expected error
        assert resend_response.status_code in [200, 400, 404, 422], f"Unexpected status: {resend_response.status_code}"
        
        if resend_response.status_code == 200:
            result = resend_response.json()
            assert "success" in result, "Response should have success field"
            assert "request_id" in result, "Response should have request_id"
            print(f"✓ Resend request successful: {result.get('message')}")
        else:
            print(f"✓ Resend request returned expected error: {resend_response.json()}")
    
    # =========================================================================
    # Test: Request replacement endpoint
    # =========================================================================
    def test_request_replacement_endpoint(self):
        """Test request-replacement endpoint"""
        # Find a requirement with verified files
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        requirement_key = None
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                if lifecycle.get("can_request_replacement"):
                    requirement_key = row.get("key")
                    break
        
        if not requirement_key:
            # Use a default requirement key for testing
            requirement_key = "right_to_work_evidence"
        
        # Test the replacement endpoint
        replacement_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{requirement_key}/request-replacement",
            json={"reason": "Test replacement request"}
        )
        
        # Should succeed or fail with expected error
        assert replacement_response.status_code in [200, 400, 404, 422], f"Unexpected status: {replacement_response.status_code}"
        
        if replacement_response.status_code == 200:
            result = replacement_response.json()
            assert "success" in result, "Response should have success field"
            assert "request_id" in result, "Response should have request_id"
            print(f"✓ Request replacement successful: {result.get('message')}")
        else:
            print(f"✓ Request replacement returned expected error: {replacement_response.json()}")
    
    # =========================================================================
    # Test: Source field (manual/scheduled)
    # =========================================================================
    def test_source_field(self):
        """Verify source field is present and valid"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        valid_sources = ["manual", "scheduled", None]
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                source = lifecycle.get("source")
                
                assert source in valid_sources, f"Invalid source '{source}' for {row.get('key')}"
        
        print("✓ Source field values are valid")
    
    # =========================================================================
    # Test: Timestamps format
    # =========================================================================
    def test_timestamps_format(self):
        """Verify timestamps are in ISO format or null"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        for row in self._get_all_rows(data):
            if row.get("row_type") == "evidence" and row.get("request_lifecycle"):
                lifecycle = row["request_lifecycle"]
                
                for ts_field in ["last_requested_at", "last_viewed_at", "last_submitted_at"]:
                    ts_value = lifecycle.get(ts_field)
                    if ts_value is not None:
                        # Should be ISO format string
                        assert isinstance(ts_value, str), f"{ts_field} should be a string"
                        # Try to parse it
                        try:
                            datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
                        except ValueError:
                            pytest.fail(f"Invalid timestamp format for {ts_field}: {ts_value}")
        
        print("✓ Timestamp formats are valid")
    
    # =========================================================================
    # Test: DBS Evidence current_request details
    # =========================================================================
    def test_dbs_evidence_current_request_details(self):
        """Verify DBS Evidence has current_request with correct details"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        for row in self._get_all_rows(data):
            if row.get("key") == "dbs_certificate_evidence":
                lifecycle = row.get("request_lifecycle", {})
                current_request = lifecycle.get("current_request")
                
                assert current_request is not None, "DBS Evidence should have current_request"
                assert current_request.get("status") == "sent", "current_request status should be 'sent'"
                assert current_request.get("source") == "manual", "current_request source should be 'manual'"
                assert current_request.get("is_replacement") == False, "current_request is_replacement should be False"
                
                print(f"✓ DBS Evidence current_request verified: id={current_request.get('id')}")
                return
        
        pytest.fail("DBS Evidence row not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

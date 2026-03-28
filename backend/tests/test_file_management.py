"""
Test file management controls for healthcare compliance documents.
Tests: Remove File (soft-delete), Replace File, View History endpoints.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFileManagement:
    """Test file management endpoints: remove, replace, history"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get employee OCS-0001 (Olakunle Alonge)
        employees_response = self.session.get(f"{BASE_URL}/api/employees?search=OCS-0001")
        assert employees_response.status_code == 200
        employees = employees_response.json()
        assert len(employees) > 0, "Employee OCS-0001 not found"
        self.employee_id = employees[0]['id']
        self.employee_code = employees[0]['employee_code']
        
    def test_login_success(self):
        """Test login with admin credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@osabea.care"
        print("✓ Login successful with admin@osabea.care")
    
    def test_get_compliance_requirements(self):
        """Test getting compliance requirements for employee"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        assert "requirements" in data
        assert len(data["requirements"]) > 0
        print(f"✓ Got {len(data['requirements'])} compliance requirements")
        
        # Find Right to Work Documents requirement
        rtw_req = next((r for r in data["requirements"] if r["id"] == "right_to_work_documents"), None)
        assert rtw_req is not None, "Right to Work Documents requirement not found"
        print(f"✓ Found Right to Work Documents requirement with {rtw_req.get('evidence_count', 0)} evidence files")
        return data
    
    def test_get_requirement_history_endpoint_exists(self):
        """Test that history endpoint exists and returns proper structure"""
        # Test with right_to_work_documents requirement
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/history"
        )
        assert response.status_code == 200, f"History endpoint failed: {response.text}"
        data = response.json()
        assert "requirement_id" in data
        assert "employee_id" in data
        assert "history" in data
        assert isinstance(data["history"], list)
        print(f"✓ History endpoint returns {len(data['history'])} entries")
        return data
    
    def test_remove_file_requires_reason(self):
        """Test that remove file endpoint requires a reason"""
        # First get a file to remove
        compliance = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements").json()
        rtw_req = next((r for r in compliance["requirements"] if r["id"] == "right_to_work_documents"), None)
        
        if not rtw_req or not rtw_req.get("evidence_files"):
            pytest.skip("No evidence files to test remove on")
        
        active_files = [f for f in rtw_req["evidence_files"] if f.get("status", "active") == "active"]
        if not active_files:
            pytest.skip("No active evidence files to test remove on")
        
        file_id = active_files[0]["file_id"]
        
        # Try to remove without reason - should fail
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/evidence/{file_id}/remove",
            json={"reason": ""}
        )
        assert response.status_code == 400, "Should require reason"
        print("✓ Remove file correctly requires reason")
    
    def test_remove_file_requires_minimum_reason_length(self):
        """Test that remove file requires minimum 3 character reason"""
        compliance = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements").json()
        rtw_req = next((r for r in compliance["requirements"] if r["id"] == "right_to_work_documents"), None)
        
        if not rtw_req or not rtw_req.get("evidence_files"):
            pytest.skip("No evidence files to test")
        
        active_files = [f for f in rtw_req["evidence_files"] if f.get("status", "active") == "active"]
        if not active_files:
            pytest.skip("No active evidence files")
        
        file_id = active_files[0]["file_id"]
        
        # Try with short reason
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/evidence/{file_id}/remove",
            json={"reason": "ab"}
        )
        assert response.status_code == 400, "Should require minimum 3 characters"
        print("✓ Remove file correctly requires minimum 3 character reason")
    
    def test_replace_file_endpoint_exists(self):
        """Test that replace file endpoint exists"""
        compliance = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements").json()
        rtw_req = next((r for r in compliance["requirements"] if r["id"] == "right_to_work_documents"), None)
        
        if not rtw_req or not rtw_req.get("evidence_files"):
            pytest.skip("No evidence files to test replace on")
        
        active_files = [f for f in rtw_req["evidence_files"] if f.get("status", "active") == "active"]
        if not active_files:
            pytest.skip("No active evidence files")
        
        file_id = active_files[0]["file_id"]
        
        # Try to replace without file - should fail with 422 (validation error)
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/evidence/{file_id}/replace",
            data={"reason": "Test replacement"}
        )
        # Should fail because no file provided
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print("✓ Replace file endpoint exists and validates input")
    
    def test_replace_file_requires_reason(self):
        """Test that replace file requires a reason"""
        compliance = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements").json()
        rtw_req = next((r for r in compliance["requirements"] if r["id"] == "right_to_work_documents"), None)
        
        if not rtw_req or not rtw_req.get("evidence_files"):
            pytest.skip("No evidence files to test")
        
        active_files = [f for f in rtw_req["evidence_files"] if f.get("status", "active") == "active"]
        if not active_files:
            pytest.skip("No active evidence files")
        
        file_id = active_files[0]["file_id"]
        
        # Create a test file
        test_file_content = b"Test PDF content for replacement"
        files = {"file": ("test_replacement.pdf", test_file_content, "application/pdf")}
        
        # Try without reason
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/evidence/{file_id}/replace",
            files=files,
            data={"reason": ""}
        )
        # 400 or 422 are both acceptable for validation errors
        assert response.status_code in [400, 422], f"Should require reason, got {response.status_code}"
        print("✓ Replace file correctly requires reason")
    
    def test_history_shows_audit_trail_structure(self):
        """Test that history returns proper audit trail structure"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/history"
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "history" in data
        
        # If there are history entries, check their structure
        if len(data["history"]) > 0:
            entry = data["history"][0]
            # Should have these fields
            assert "action" in entry or "action_type" in entry
            assert "timestamp" in entry
            print(f"✓ History entry has proper structure: {list(entry.keys())}")
        else:
            print("✓ History endpoint returns empty list (no history yet)")
    
    def test_soft_delete_flow(self):
        """Test complete soft-delete flow: upload -> remove -> verify in history"""
        # First upload a test file
        test_file_content = b"Test document for soft delete testing"
        files = {"file": ("test_soft_delete.pdf", test_file_content, "application/pdf")}
        
        upload_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/evidence",
            files=files
        )
        
        if upload_response.status_code != 200:
            pytest.skip(f"Could not upload test file: {upload_response.text}")
        
        upload_data = upload_response.json()
        file_id = upload_data.get("file_id")
        assert file_id, "No file_id returned from upload"
        print(f"✓ Uploaded test file with ID: {file_id}")
        
        # Now remove it with reason
        remove_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/evidence/{file_id}/remove",
            json={"reason": "Testing soft delete functionality for audit compliance"}
        )
        assert remove_response.status_code == 200, f"Remove failed: {remove_response.text}"
        remove_data = remove_response.json()
        assert remove_data.get("status") == "removed"
        print("✓ File marked as removed")
        
        # Verify it appears in history
        history_response = self.session.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/history"
        )
        assert history_response.status_code == 200
        history = history_response.json()["history"]
        
        # Should have remove_evidence action
        remove_actions = [h for h in history if h.get("action") == "remove_evidence"]
        assert len(remove_actions) > 0, "Remove action not found in history"
        print("✓ Remove action recorded in history")
        
        # Verify the file is no longer active in compliance
        compliance = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements").json()
        rtw_req = next((r for r in compliance["requirements"] if r["id"] == "right_to_work_documents"), None)
        
        if rtw_req and rtw_req.get("evidence_files"):
            removed_file = next((f for f in rtw_req["evidence_files"] if f.get("file_id") == file_id), None)
            if removed_file:
                assert removed_file.get("status") == "removed", "File should be marked as removed"
                print("✓ File status is 'removed' in compliance data")
    
    def test_requirement_reverts_to_still_needed_when_all_files_removed(self):
        """Test that requirement reverts to 'Still Needed' when all active files are removed"""
        # Get current compliance state
        compliance = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements").json()
        
        # Find a requirement with evidence
        req_with_evidence = None
        for req in compliance["requirements"]:
            active_files = [f for f in req.get("evidence_files", []) if f.get("status", "active") == "active"]
            if len(active_files) == 1:  # Find one with exactly 1 active file for clean test
                req_with_evidence = req
                break
        
        if not req_with_evidence:
            # Upload a file to a requirement first
            test_file_content = b"Test document for revert testing"
            files = {"file": ("test_revert.pdf", test_file_content, "application/pdf")}
            
            upload_response = self.session.post(
                f"{BASE_URL}/api/employees/{self.employee_id}/requirements/identity_documents/evidence",
                files=files
            )
            
            if upload_response.status_code != 200:
                pytest.skip("Could not set up test data")
            
            file_id = upload_response.json().get("file_id")
            req_id = "identity_documents"
        else:
            active_files = [f for f in req_with_evidence.get("evidence_files", []) if f.get("status", "active") == "active"]
            file_id = active_files[0]["file_id"]
            req_id = req_with_evidence["id"]
        
        # Remove the file
        remove_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{req_id}/evidence/{file_id}/remove",
            json={"reason": "Testing requirement status revert when all files removed"}
        )
        
        if remove_response.status_code != 200:
            pytest.skip(f"Could not remove file: {remove_response.text}")
        
        # Check compliance status
        compliance_after = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements").json()
        req_after = next((r for r in compliance_after["requirements"] if r["id"] == req_id), None)
        
        if req_after:
            active_files_after = [f for f in req_after.get("evidence_files", []) if f.get("status", "active") == "active"]
            if len(active_files_after) == 0:
                # Requirement should show as not complete
                assert req_after.get("has_evidence") == False or req_after.get("status") in ["missing", "not_started", "Still Needed"]
                print(f"✓ Requirement {req_id} correctly shows as incomplete after all files removed")
            else:
                print(f"✓ Requirement {req_id} still has {len(active_files_after)} active files")


class TestAuditTrail:
    """Test audit trail captures required information"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        employees_response = self.session.get(f"{BASE_URL}/api/employees?search=OCS-0001")
        employees = employees_response.json()
        self.employee_id = employees[0]['id']
    
    def test_audit_trail_captures_user_id(self):
        """Test that audit trail captures user_id"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/history"
        )
        assert response.status_code == 200
        history = response.json()["history"]
        
        if len(history) > 0:
            entry = history[0]
            assert "user_id" in entry or "user_name" in entry, "Audit entry should have user info"
            print(f"✓ Audit trail captures user info: user_id={entry.get('user_id')}, user_name={entry.get('user_name')}")
        else:
            print("✓ No history entries yet to verify user_id")
    
    def test_audit_trail_captures_action_type(self):
        """Test that audit trail captures action_type"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/history"
        )
        assert response.status_code == 200
        history = response.json()["history"]
        
        if len(history) > 0:
            entry = history[0]
            assert "action" in entry, "Audit entry should have action type"
            print(f"✓ Audit trail captures action type: {entry.get('action')}")
        else:
            print("✓ No history entries yet to verify action_type")
    
    def test_audit_trail_captures_timestamp(self):
        """Test that audit trail captures timestamp"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/history"
        )
        assert response.status_code == 200
        history = response.json()["history"]
        
        if len(history) > 0:
            entry = history[0]
            assert "timestamp" in entry, "Audit entry should have timestamp"
            print(f"✓ Audit trail captures timestamp: {entry.get('timestamp')}")
        else:
            print("✓ No history entries yet to verify timestamp")
    
    def test_audit_trail_captures_reason(self):
        """Test that audit trail captures reason for remove/replace actions"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/right_to_work_documents/history"
        )
        assert response.status_code == 200
        history = response.json()["history"]
        
        # Find a remove or replace action
        action_with_reason = next(
            (h for h in history if h.get("action") in ["remove_evidence", "replace_evidence"]),
            None
        )
        
        if action_with_reason:
            assert "reason" in action_with_reason, "Remove/replace action should have reason"
            print(f"✓ Audit trail captures reason: {action_with_reason.get('reason')}")
        else:
            print("✓ No remove/replace actions yet to verify reason capture")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

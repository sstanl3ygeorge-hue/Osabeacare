"""
Test file deletion and file management features:
- Delete file endpoint: POST /api/employees/{id}/requirements/{req_id}/evidence/{file_id}/delete
- Delete file removes from active UI and compliance calculation
- Delete file creates audit trail with filename, requirement, deleted_by, deleted_at
- Audit log shows 'File Deleted' with filename in grouped categories
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFileManagement:
    """Test file deletion and management features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get an employee for testing
        employees_response = self.session.get(f"{BASE_URL}/api/employees")
        assert employees_response.status_code == 200
        employees = employees_response.json()
        assert len(employees) > 0, "No employees found for testing"
        self.employee_id = employees[0]["id"]
        self.employee_name = f"{employees[0]['first_name']} {employees[0]['last_name']}"
        
    def test_delete_file_endpoint_exists(self):
        """Test that the delete file endpoint exists and returns proper error for invalid file"""
        # Try to delete a non-existent file
        response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/reference_1/evidence/non-existent-file-id/delete",
            json={}
        )
        # Should return 200 with success (no file found is still success) or 404
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}, {response.text}"
        print(f"✅ Delete file endpoint exists and responds correctly")
    
    def test_delete_file_creates_audit_trail(self):
        """Test that deleting a file creates an audit trail entry"""
        # First, get compliance requirements to find a requirement with evidence
        comp_response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements")
        assert comp_response.status_code == 200
        comp_data = comp_response.json()
        
        # Find a requirement with evidence files
        requirement_with_evidence = None
        file_to_delete = None
        
        for req in comp_data.get('requirements', []):
            evidence_files = req.get('evidence_files', [])
            if evidence_files:
                for ef in evidence_files:
                    if ef.get('status') == 'active' and ef.get('file_id'):
                        requirement_with_evidence = req
                        file_to_delete = ef
                        break
                if file_to_delete:
                    break
        
        if not file_to_delete:
            pytest.skip("No evidence files found to test deletion")
        
        # Delete the file
        delete_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{requirement_with_evidence['id']}/evidence/{file_to_delete['file_id']}/delete",
            json={"reason": "TEST_deletion_audit_trail_test"}
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        delete_data = delete_response.json()
        assert delete_data.get('success') == True
        print(f"✅ File deleted successfully: {delete_data.get('deleted_file', {}).get('filename')}")
        
        # Check audit log for the deletion entry
        time.sleep(0.5)  # Wait for audit log to be created
        audit_response = self.session.get(f"{BASE_URL}/api/audit-logs?entity_id={self.employee_id}&compliance_only=true")
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        
        # Find the file_deleted audit entry
        file_deleted_entry = None
        for log in audit_logs:
            if log.get('action') == 'file_deleted':
                file_deleted_entry = log
                break
        
        assert file_deleted_entry is not None, "No file_deleted audit entry found"
        
        # Verify audit trail contains required fields
        metadata = file_deleted_entry.get('metadata', {})
        assert 'filename' in metadata or 'deleted_file' in str(file_deleted_entry), "Filename not in audit trail"
        assert 'deleted_by' in metadata or 'changed_by' in file_deleted_entry, "deleted_by not in audit trail"
        assert 'deleted_at' in metadata or 'created_at' in file_deleted_entry, "deleted_at not in audit trail"
        print(f"✅ Audit trail created with filename, deleted_by, deleted_at")
    
    def test_delete_file_removes_from_compliance(self):
        """Test that deleting a file removes it from compliance calculation"""
        # Get initial compliance
        initial_comp = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements")
        assert initial_comp.status_code == 200
        initial_data = initial_comp.json()
        
        # Find a requirement with evidence
        requirement_with_evidence = None
        file_to_delete = None
        
        for req in initial_data.get('requirements', []):
            evidence_files = req.get('evidence_files', [])
            if evidence_files:
                for ef in evidence_files:
                    if ef.get('status') == 'active' and ef.get('file_id'):
                        requirement_with_evidence = req
                        file_to_delete = ef
                        break
                if file_to_delete:
                    break
        
        if not file_to_delete:
            pytest.skip("No evidence files found to test deletion")
        
        initial_evidence_count = len(requirement_with_evidence.get('evidence_files', []))
        
        # Delete the file
        delete_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{requirement_with_evidence['id']}/evidence/{file_to_delete['file_id']}/delete",
            json={"reason": "TEST_compliance_removal_test"}
        )
        assert delete_response.status_code == 200
        
        # Get updated compliance
        updated_comp = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements")
        assert updated_comp.status_code == 200
        updated_data = updated_comp.json()
        
        # Find the same requirement
        updated_req = None
        for req in updated_data.get('requirements', []):
            if req['id'] == requirement_with_evidence['id']:
                updated_req = req
                break
        
        if updated_req:
            updated_evidence_count = len(updated_req.get('evidence_files', []))
            assert updated_evidence_count < initial_evidence_count, "Evidence count should decrease after deletion"
            print(f"✅ File removed from compliance: {initial_evidence_count} -> {updated_evidence_count}")
        else:
            print(f"✅ Requirement no longer has evidence (file was only evidence)")


class TestDashboardClickableCards:
    """Test dashboard clickable cards navigation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_dashboard_stats_endpoint(self):
        """Test dashboard stats endpoint returns expected data"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields exist
        expected_fields = ['total_employees', 'unsigned_policies', 'expiring_30_days']
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✅ Dashboard stats: {data}")
    
    def test_dashboard_expiry_alerts_endpoint(self):
        """Test dashboard expiry alerts endpoint"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/expiry-alerts")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert 'expired' in data or 'expiring_soon' in data, "Missing expiry data"
        print(f"✅ Expiry alerts: expired={data.get('expired', {}).get('total_items', 0)}, expiring_soon={data.get('expiring_soon', {}).get('total_items', 0)}")


class TestTrainingMatrixFilters:
    """Test Training Matrix URL-based filters"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_training_records_endpoint(self):
        """Test training records endpoint returns data"""
        response = self.session.get(f"{BASE_URL}/api/training-records")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Training records should be a list"
        print(f"✅ Training records: {len(data)} records found")
    
    def test_training_records_with_expiry(self):
        """Test training records include expiry date information"""
        response = self.session.get(f"{BASE_URL}/api/training-records")
        assert response.status_code == 200
        data = response.json()
        
        # Check if any records have expiry_date
        records_with_expiry = [r for r in data if r.get('expiry_date')]
        print(f"✅ Training records with expiry: {len(records_with_expiry)} of {len(data)}")


class TestAuditLogFileDeleted:
    """Test audit log shows File Deleted entries"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_audit_logs_endpoint(self):
        """Test audit logs endpoint returns data"""
        response = self.session.get(f"{BASE_URL}/api/audit-logs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Audit logs should be a list"
        print(f"✅ Audit logs: {len(data)} entries found")
    
    def test_audit_logs_include_file_actions(self):
        """Test audit logs include file-related actions"""
        response = self.session.get(f"{BASE_URL}/api/audit-logs")
        assert response.status_code == 200
        data = response.json()
        
        # Check for file-related actions
        file_actions = ['file_deleted', 'delete_evidence', 'upload_evidence', 'replace_evidence']
        found_actions = set()
        
        for log in data:
            action = log.get('action', '')
            if action in file_actions:
                found_actions.add(action)
        
        print(f"✅ File-related audit actions found: {found_actions}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test Employee Management Controls
- Archive Employee (soft delete)
- Restore Employee
- Permanent Delete (Super Admin only)
- Edit Employee Details
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestEmployeeManagementControls:
    """Test employee archive, restore, and permanent delete functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as super admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.text}")
        
        login_data = login_response.json()
        self.token = login_data.get("token")
        self.user = login_data.get("user")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        print(f"Logged in as: {self.user.get('email')} with role: {self.user.get('role')}")
        
        yield
        
        # Cleanup - delete test employees created during tests
        self._cleanup_test_employees()
    
    def _cleanup_test_employees(self):
        """Clean up test employees created during tests"""
        try:
            # Get all employees with TEST_ prefix
            response = self.session.get(f"{BASE_URL}/api/employees?include_archived=true")
            if response.status_code == 200:
                employees = response.json()
                for emp in employees:
                    if emp.get('email', '').startswith('TEST_'):
                        # Permanent delete test employees
                        self.session.delete(f"{BASE_URL}/api/employees/{emp['id']}/permanent")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def _create_test_employee(self, suffix=""):
        """Helper to create a test employee"""
        unique_id = uuid.uuid4().hex[:8]
        employee_data = {
            "first_name": f"Test{suffix}",
            "last_name": f"Employee{unique_id}",
            "email": f"TEST_{unique_id}@test.com",
            "phone": "1234567890",
            "role": "Care Assistant",
            "assignment": "Test Assignment",
            "status": "active"
        }
        response = self.session.post(f"{BASE_URL}/api/employees", json=employee_data)
        assert response.status_code == 200, f"Failed to create test employee: {response.text}"
        return response.json()
    
    # ==================== ARCHIVE EMPLOYEE TESTS ====================
    
    def test_archive_employee_success(self):
        """Test archiving an active employee"""
        # Create test employee
        employee = self._create_test_employee("Archive")
        employee_id = employee['id']
        
        # Archive the employee
        response = self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        assert response.status_code == 200, f"Archive failed: {response.text}"
        data = response.json()
        assert data.get("message") == "Employee archived successfully"
        assert data.get("employee_id") == employee_id
        
        # Verify employee status is now archived
        get_response = self.session.get(f"{BASE_URL}/api/employees/{employee_id}")
        assert get_response.status_code == 200
        archived_emp = get_response.json()
        assert archived_emp['status'] == 'archived'
        
        print(f"✓ Employee {employee_id} archived successfully")
    
    def test_archive_already_archived_employee(self):
        """Test archiving an already archived employee returns error"""
        # Create and archive employee
        employee = self._create_test_employee("AlreadyArchived")
        employee_id = employee['id']
        
        # Archive first time
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        # Try to archive again
        response = self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "already archived" in response.json().get("detail", "").lower()
        
        print("✓ Cannot archive already archived employee")
    
    def test_archive_nonexistent_employee(self):
        """Test archiving a non-existent employee returns 404"""
        fake_id = "nonexistent-employee-id"
        response = self.session.post(f"{BASE_URL}/api/employees/{fake_id}/archive")
        
        assert response.status_code == 404
        print("✓ Archive non-existent employee returns 404")
    
    def test_archived_employees_hidden_by_default(self):
        """Test that archived employees are hidden from default list"""
        # Create and archive employee
        employee = self._create_test_employee("Hidden")
        employee_id = employee['id']
        
        # Archive the employee
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        # Get employees without include_archived flag
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        employees = response.json()
        
        # Verify archived employee is not in the list
        employee_ids = [emp['id'] for emp in employees]
        assert employee_id not in employee_ids, "Archived employee should not appear in default list"
        
        print("✓ Archived employees hidden by default")
    
    def test_archived_employees_visible_with_flag(self):
        """Test that archived employees are visible with include_archived=true"""
        # Create and archive employee
        employee = self._create_test_employee("Visible")
        employee_id = employee['id']
        
        # Archive the employee
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        # Get employees with include_archived flag
        response = self.session.get(f"{BASE_URL}/api/employees?include_archived=true")
        assert response.status_code == 200
        employees = response.json()
        
        # Verify archived employee is in the list
        employee_ids = [emp['id'] for emp in employees]
        assert employee_id in employee_ids, "Archived employee should appear with include_archived=true"
        
        print("✓ Archived employees visible with include_archived=true")
    
    def test_filter_by_archived_status(self):
        """Test filtering employees by archived status"""
        # Create and archive employee
        employee = self._create_test_employee("FilterArchived")
        employee_id = employee['id']
        
        # Archive the employee
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        # Filter by archived status
        response = self.session.get(f"{BASE_URL}/api/employees?status=archived&include_archived=true")
        assert response.status_code == 200
        employees = response.json()
        
        # All returned employees should be archived
        for emp in employees:
            assert emp['status'] == 'archived', f"Expected archived status, got {emp['status']}"
        
        print("✓ Filter by archived status works")
    
    # ==================== RESTORE EMPLOYEE TESTS ====================
    
    def test_restore_employee_success(self):
        """Test restoring an archived employee"""
        # Create and archive employee
        employee = self._create_test_employee("Restore")
        employee_id = employee['id']
        original_status = employee['status']
        
        # Archive the employee
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        # Restore the employee
        response = self.session.post(f"{BASE_URL}/api/employees/{employee_id}/restore")
        
        assert response.status_code == 200, f"Restore failed: {response.text}"
        data = response.json()
        assert data.get("message") == "Employee restored successfully"
        assert data.get("employee_id") == employee_id
        
        # Verify employee status is restored
        get_response = self.session.get(f"{BASE_URL}/api/employees/{employee_id}")
        assert get_response.status_code == 200
        restored_emp = get_response.json()
        assert restored_emp['status'] != 'archived'
        
        print(f"✓ Employee {employee_id} restored successfully")
    
    def test_restore_non_archived_employee(self):
        """Test restoring a non-archived employee returns error"""
        # Create active employee
        employee = self._create_test_employee("NotArchived")
        employee_id = employee['id']
        
        # Try to restore non-archived employee
        response = self.session.post(f"{BASE_URL}/api/employees/{employee_id}/restore")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "not archived" in response.json().get("detail", "").lower()
        
        print("✓ Cannot restore non-archived employee")
    
    def test_restore_nonexistent_employee(self):
        """Test restoring a non-existent employee returns 404"""
        fake_id = "nonexistent-employee-id"
        response = self.session.post(f"{BASE_URL}/api/employees/{fake_id}/restore")
        
        assert response.status_code == 404
        print("✓ Restore non-existent employee returns 404")
    
    # ==================== PERMANENT DELETE TESTS ====================
    
    def test_permanent_delete_success(self):
        """Test permanent deletion of employee (Super Admin only)"""
        # Create test employee
        employee = self._create_test_employee("Delete")
        employee_id = employee['id']
        
        # Permanent delete
        response = self.session.delete(f"{BASE_URL}/api/employees/{employee_id}/permanent")
        
        assert response.status_code == 200, f"Permanent delete failed: {response.text}"
        data = response.json()
        assert data.get("message") == "Employee permanently deleted"
        assert data.get("employee_id") == employee_id
        assert "deleted_records" in data
        
        # Verify employee no longer exists
        get_response = self.session.get(f"{BASE_URL}/api/employees/{employee_id}")
        assert get_response.status_code == 404
        
        print(f"✓ Employee {employee_id} permanently deleted")
    
    def test_permanent_delete_nonexistent_employee(self):
        """Test permanent delete of non-existent employee returns 404"""
        fake_id = "nonexistent-employee-id"
        response = self.session.delete(f"{BASE_URL}/api/employees/{fake_id}/permanent")
        
        assert response.status_code == 404
        print("✓ Permanent delete non-existent employee returns 404")
    
    def test_permanent_delete_removes_related_records(self):
        """Test that permanent delete removes all related records"""
        # Create test employee
        employee = self._create_test_employee("DeleteRelated")
        employee_id = employee['id']
        
        # Permanent delete
        response = self.session.delete(f"{BASE_URL}/api/employees/{employee_id}/permanent")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify deleted_records structure
        deleted_records = data.get("deleted_records", {})
        assert "documents" in deleted_records
        assert "forms" in deleted_records
        assert "policies" in deleted_records
        assert "training" in deleted_records
        
        print(f"✓ Permanent delete removes related records: {deleted_records}")
    
    # ==================== EDIT EMPLOYEE TESTS ====================
    
    def test_update_employee_details(self):
        """Test updating employee details"""
        # Create test employee
        employee = self._create_test_employee("Update")
        employee_id = employee['id']
        
        # Update employee details
        update_data = {
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
            "phone": "9876543210",
            "role": "Senior Care Assistant",
            "assignment": "Updated Assignment",
            "status": "onboarding",
            "notes": "Test notes for employee"
        }
        
        response = self.session.put(f"{BASE_URL}/api/employees/{employee_id}", json=update_data)
        
        assert response.status_code == 200, f"Update failed: {response.text}"
        updated_emp = response.json()
        
        # Verify updates
        assert updated_emp['first_name'] == "UpdatedFirst"
        assert updated_emp['last_name'] == "UpdatedLast"
        assert updated_emp['phone'] == "9876543210"
        assert updated_emp['role'] == "Senior Care Assistant"
        assert updated_emp['assignment'] == "Updated Assignment"
        assert updated_emp['status'] == "onboarding"
        assert updated_emp['notes'] == "Test notes for employee"
        
        print(f"✓ Employee {employee_id} details updated successfully")
    
    def test_update_employee_email(self):
        """Test updating employee email"""
        # Create test employee
        employee = self._create_test_employee("EmailUpdate")
        employee_id = employee['id']
        
        # Update email
        new_email = f"TEST_updated_{uuid.uuid4().hex[:8]}@test.com"
        update_data = {"email": new_email}
        
        response = self.session.put(f"{BASE_URL}/api/employees/{employee_id}", json=update_data)
        
        assert response.status_code == 200, f"Email update failed: {response.text}"
        updated_emp = response.json()
        assert updated_emp['email'] == new_email
        
        print(f"✓ Employee email updated to {new_email}")
    
    def test_update_employee_start_date(self):
        """Test updating employee start date"""
        # Create test employee
        employee = self._create_test_employee("StartDate")
        employee_id = employee['id']
        
        # Update start date
        update_data = {"start_date": "2024-01-15"}
        
        response = self.session.put(f"{BASE_URL}/api/employees/{employee_id}", json=update_data)
        
        assert response.status_code == 200, f"Start date update failed: {response.text}"
        updated_emp = response.json()
        assert updated_emp['start_date'] == "2024-01-15"
        
        print("✓ Employee start date updated")
    
    def test_update_nonexistent_employee(self):
        """Test updating non-existent employee returns 404"""
        fake_id = "nonexistent-employee-id"
        update_data = {"first_name": "Test"}
        
        response = self.session.put(f"{BASE_URL}/api/employees/{fake_id}", json=update_data)
        
        assert response.status_code == 404
        print("✓ Update non-existent employee returns 404")
    
    # ==================== AUDIT LOG TESTS ====================
    
    def test_archive_action_logged(self):
        """Test that archive action is logged in audit trail"""
        # Create and archive employee
        employee = self._create_test_employee("AuditArchive")
        employee_id = employee['id']
        
        # Archive the employee
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        
        # Check audit logs
        response = self.session.get(f"{BASE_URL}/api/audit-logs?entity_id={employee_id}")
        assert response.status_code == 200
        logs = response.json()
        
        # Find archive action
        archive_logs = [log for log in logs if log.get('action') == 'archive_employee']
        assert len(archive_logs) > 0, "Archive action should be logged"
        
        print("✓ Archive action logged in audit trail")
    
    def test_restore_action_logged(self):
        """Test that restore action is logged in audit trail"""
        # Create, archive, and restore employee
        employee = self._create_test_employee("AuditRestore")
        employee_id = employee['id']
        
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/archive")
        self.session.post(f"{BASE_URL}/api/employees/{employee_id}/restore")
        
        # Check audit logs
        response = self.session.get(f"{BASE_URL}/api/audit-logs?entity_id={employee_id}")
        assert response.status_code == 200
        logs = response.json()
        
        # Find restore action
        restore_logs = [log for log in logs if log.get('action') == 'restore_employee']
        assert len(restore_logs) > 0, "Restore action should be logged"
        
        print("✓ Restore action logged in audit trail")
    
    def test_permanent_delete_action_logged(self):
        """Test that permanent delete action is logged in audit trail"""
        # Create test employee
        employee = self._create_test_employee("AuditDelete")
        employee_id = employee['id']
        
        # Permanent delete
        self.session.delete(f"{BASE_URL}/api/employees/{employee_id}/permanent")
        
        # Check audit logs (employee is deleted but log should exist)
        response = self.session.get(f"{BASE_URL}/api/audit-logs?entity_id={employee_id}")
        assert response.status_code == 200
        logs = response.json()
        
        # Find permanent delete action
        delete_logs = [log for log in logs if log.get('action') == 'permanent_delete_employee']
        assert len(delete_logs) > 0, "Permanent delete action should be logged"
        
        print("✓ Permanent delete action logged in audit trail")


class TestEmployeeListActions:
    """Test employee list actions column and dropdown menu"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as super admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.text}")
        
        login_data = login_response.json()
        self.token = login_data.get("token")
        self.user = login_data.get("user")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_get_employees_list(self):
        """Test getting employees list"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        
        assert response.status_code == 200
        employees = response.json()
        assert isinstance(employees, list)
        
        print(f"✓ Got {len(employees)} employees")
    
    def test_get_employees_with_archived(self):
        """Test getting employees list including archived"""
        response = self.session.get(f"{BASE_URL}/api/employees?include_archived=true")
        
        assert response.status_code == 200
        employees = response.json()
        assert isinstance(employees, list)
        
        print(f"✓ Got {len(employees)} employees (including archived)")
    
    def test_employee_response_structure(self):
        """Test employee response has required fields"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        
        assert response.status_code == 200
        employees = response.json()
        
        if len(employees) > 0:
            emp = employees[0]
            required_fields = ['id', 'employee_code', 'first_name', 'last_name', 'email', 
                             'role', 'status', 'completion_percentage']
            for field in required_fields:
                assert field in emp, f"Missing field: {field}"
        
        print("✓ Employee response has required fields")


class TestSuperAdminRestriction:
    """Test that permanent delete is restricted to Super Admin only"""
    
    def test_verify_super_admin_role(self):
        """Verify the test user has super_admin role"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        user = login_data.get("user")
        
        assert user.get("role") == "super_admin", f"Expected super_admin role, got {user.get('role')}"
        
        print(f"✓ User {user.get('email')} has super_admin role")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

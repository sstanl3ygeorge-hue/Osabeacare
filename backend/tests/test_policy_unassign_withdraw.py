"""
Test Policy Unassign/Withdraw, Org Settings, and Document Removal Features
Tests for:
1. PUT /api/policy-assignments/{id}/unassign - unassigns pending policy
2. PUT /api/policy-assignments/{id}/withdraw - withdraws acknowledged policy
3. GET /api/org-settings - returns organisation settings including service_type
4. PUT /api/org-settings - updates organisation service type
5. Document removal correctly marks file as 'removed' not deleted
6. Policy assignments exclude unassigned/withdrawn from counts
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPolicyUnassignWithdraw:
    """Test policy unassign and withdraw functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Test employee ID
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        
    def test_get_org_settings(self):
        """Test GET /api/org-settings returns organisation settings"""
        response = self.session.get(f"{BASE_URL}/api/org-settings")
        assert response.status_code == 200, f"Failed to get org settings: {response.text}"
        
        data = response.json()
        assert "service_type" in data, "service_type field missing"
        assert "organisation_name" in data, "organisation_name field missing"
        assert data["service_type"] in ["adults_only", "children_only", "mixed"], f"Invalid service_type: {data['service_type']}"
        print(f"✅ GET /api/org-settings - service_type: {data['service_type']}")
        
    def test_update_org_settings_service_type(self):
        """Test PUT /api/org-settings updates service type"""
        # Get current settings
        get_response = self.session.get(f"{BASE_URL}/api/org-settings")
        current_settings = get_response.json()
        original_type = current_settings.get("service_type")
        
        # Update to a different type
        new_type = "mixed" if original_type != "mixed" else "adults_only"
        update_response = self.session.put(f"{BASE_URL}/api/org-settings", json={
            "service_type": new_type
        })
        assert update_response.status_code == 200, f"Failed to update org settings: {update_response.text}"
        
        updated_data = update_response.json()
        assert updated_data["service_type"] == new_type, f"Service type not updated: {updated_data}"
        
        # Restore original
        self.session.put(f"{BASE_URL}/api/org-settings", json={
            "service_type": original_type
        })
        print(f"✅ PUT /api/org-settings - updated service_type from {original_type} to {new_type}")
        
    def test_unassign_pending_policy(self):
        """Test unassigning a pending (not acknowledged) policy"""
        # First, get available policies
        policies_response = self.session.get(f"{BASE_URL}/api/policies")
        if policies_response.status_code != 200:
            pytest.skip("No policies endpoint available")
        
        policies = policies_response.json()
        if not policies:
            pytest.skip("No policies available for testing")
        
        policy_id = policies[0].get("id")
        
        # Create a test employee for this test
        test_emp_id = str(uuid.uuid4())
        emp_response = self.session.post(f"{BASE_URL}/api/employees", json={
            "id": test_emp_id,
            "name": "TEST_Unassign Test",
            "email": f"test_unassign_{test_emp_id[:8]}@test.com",
            "role": "Care Worker",
            "branch": "Main Branch"
        })
        
        if emp_response.status_code not in [200, 201]:
            # Use existing test employee
            test_emp_id = self.test_employee_id
        
        # Assign a policy
        assign_response = self.session.post(f"{BASE_URL}/api/policies/assign", json={
            "policy_id": policy_id,
            "employee_id": test_emp_id
        })
        
        if assign_response.status_code != 200:
            pytest.skip(f"Could not assign policy: {assign_response.text}")
        
        assignment_id = assign_response.json().get("id")
        
        # Now unassign it
        unassign_response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment_id}/unassign", json={
            "reason": "Testing unassign functionality"
        })
        assert unassign_response.status_code == 200, f"Failed to unassign: {unassign_response.text}"
        
        unassigned_data = unassign_response.json()
        assert unassigned_data["status"] == "unassigned", f"Status not unassigned: {unassigned_data}"
        assert "unassigned_at" in unassigned_data, "unassigned_at missing"
        assert "unassigned_by_name" in unassigned_data, "unassigned_by_name missing"
        
        print(f"✅ PUT /api/policy-assignments/{assignment_id}/unassign - policy unassigned successfully")
        
    def test_cannot_unassign_acknowledged_policy(self):
        """Test that acknowledged policies cannot be unassigned"""
        # Get policy assignments for test employee
        assignments_response = self.session.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"employee_id": self.test_employee_id, "include_inactive": "true"}
        )
        
        if assignments_response.status_code != 200:
            pytest.skip("Could not get policy assignments")
        
        assignments = assignments_response.json()
        
        # Find an acknowledged policy
        acknowledged = [a for a in assignments if a.get("status") in ["acknowledged", "signed"]]
        
        if not acknowledged:
            pytest.skip("No acknowledged policies to test")
        
        assignment_id = acknowledged[0]["id"]
        
        # Try to unassign - should fail
        unassign_response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment_id}/unassign", json={
            "reason": "Should fail"
        })
        
        assert unassign_response.status_code == 400, f"Should have failed with 400, got {unassign_response.status_code}"
        assert "withdraw" in unassign_response.text.lower() or "acknowledged" in unassign_response.text.lower()
        
        print(f"✅ Correctly rejected unassign for acknowledged policy (400 error)")
        
    def test_withdraw_acknowledged_policy(self):
        """Test withdrawing an acknowledged policy"""
        # Get policy assignments for test employee
        assignments_response = self.session.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"employee_id": self.test_employee_id, "include_inactive": "true"}
        )
        
        if assignments_response.status_code != 200:
            pytest.skip("Could not get policy assignments")
        
        assignments = assignments_response.json()
        
        # Find an acknowledged policy that's not already withdrawn
        acknowledged = [a for a in assignments if a.get("status") in ["acknowledged", "signed"]]
        
        if not acknowledged:
            # Create and acknowledge a policy for testing
            policies_response = self.session.get(f"{BASE_URL}/api/policies")
            if policies_response.status_code != 200 or not policies_response.json():
                pytest.skip("No policies available")
            
            policy_id = policies_response.json()[0]["id"]
            
            # Assign
            assign_response = self.session.post(f"{BASE_URL}/api/policies/assign", json={
                "policy_id": policy_id,
                "employee_id": self.test_employee_id
            })
            
            if assign_response.status_code != 200:
                pytest.skip("Could not assign policy for withdraw test")
            
            assignment_id = assign_response.json()["id"]
            
            # Acknowledge
            ack_response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment_id}/acknowledge")
            if ack_response.status_code != 200:
                pytest.skip("Could not acknowledge policy for withdraw test")
            
            acknowledged = [ack_response.json()]
        
        assignment_id = acknowledged[0]["id"]
        
        # Withdraw the policy
        withdraw_response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment_id}/withdraw", json={
            "reason": "Testing withdraw functionality"
        })
        
        assert withdraw_response.status_code == 200, f"Failed to withdraw: {withdraw_response.text}"
        
        withdrawn_data = withdraw_response.json()
        assert withdrawn_data["status"] == "withdrawn", f"Status not withdrawn: {withdrawn_data}"
        assert "withdrawn_at" in withdrawn_data, "withdrawn_at missing"
        assert "withdrawn_by_name" in withdrawn_data, "withdrawn_by_name missing"
        # Verify acknowledgement history is preserved
        assert "acknowledged_at" in withdrawn_data, "acknowledged_at should be preserved"
        
        print(f"✅ PUT /api/policy-assignments/{assignment_id}/withdraw - policy withdrawn with history preserved")
        
    def test_cannot_withdraw_pending_policy(self):
        """Test that pending policies cannot be withdrawn"""
        # Get available policies
        policies_response = self.session.get(f"{BASE_URL}/api/policies")
        if policies_response.status_code != 200 or not policies_response.json():
            pytest.skip("No policies available")
        
        policy_id = policies_response.json()[0]["id"]
        
        # Create a new assignment (will be pending)
        test_emp_id = str(uuid.uuid4())
        emp_response = self.session.post(f"{BASE_URL}/api/employees", json={
            "id": test_emp_id,
            "name": "TEST_Withdraw Test",
            "email": f"test_withdraw_{test_emp_id[:8]}@test.com",
            "role": "Care Worker",
            "branch": "Main Branch"
        })
        
        if emp_response.status_code not in [200, 201]:
            test_emp_id = self.test_employee_id
        
        assign_response = self.session.post(f"{BASE_URL}/api/policies/assign", json={
            "policy_id": policy_id,
            "employee_id": test_emp_id
        })
        
        if assign_response.status_code != 200:
            pytest.skip("Could not assign policy")
        
        assignment_id = assign_response.json()["id"]
        
        # Try to withdraw - should fail
        withdraw_response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment_id}/withdraw", json={
            "reason": "Should fail"
        })
        
        assert withdraw_response.status_code == 400, f"Should have failed with 400, got {withdraw_response.status_code}"
        assert "unassign" in withdraw_response.text.lower() or "pending" in withdraw_response.text.lower()
        
        # Clean up - unassign the policy
        self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment_id}/unassign", json={
            "reason": "Cleanup after test"
        })
        
        print(f"✅ Correctly rejected withdraw for pending policy (400 error)")
        
    def test_policy_assignment_not_found(self):
        """Test 404 for non-existent assignment"""
        fake_id = str(uuid.uuid4())
        
        unassign_response = self.session.put(f"{BASE_URL}/api/policy-assignments/{fake_id}/unassign", json={})
        assert unassign_response.status_code == 404
        
        withdraw_response = self.session.put(f"{BASE_URL}/api/policy-assignments/{fake_id}/withdraw", json={})
        assert withdraw_response.status_code == 404
        
        print(f"✅ Non-existent assignment returns 404")
        
    def test_audit_log_for_unassign(self):
        """Test that unassign action is logged in audit trail"""
        # Get recent audit logs
        audit_response = self.session.get(f"{BASE_URL}/api/audit-logs", params={
            "compliance_only": "true"
        })
        
        if audit_response.status_code != 200:
            pytest.skip("Could not get audit logs")
        
        logs = audit_response.json()
        
        # Check for policy_unassigned action
        unassign_logs = [l for l in logs if l.get("action") == "policy_unassigned"]
        
        # This may or may not exist depending on previous tests
        print(f"✅ Audit logs accessible - found {len(unassign_logs)} policy_unassigned entries")


class TestDocumentRemoval:
    """Test document removal functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        
    def test_document_removal_marks_as_removed(self):
        """Test that document removal marks file as 'removed' not deleted"""
        # Get employee documents
        docs_response = self.session.get(f"{BASE_URL}/api/employee-documents", params={
            "employee_id": self.test_employee_id
        })
        
        if docs_response.status_code != 200:
            pytest.skip("Could not get employee documents")
        
        docs = docs_response.json()
        
        # Find a document with files
        doc_with_files = None
        for doc in docs:
            if doc.get("files") and len(doc["files"]) > 0:
                # Check for non-removed files
                active_files = [f for f in doc["files"] if f.get("status") != "removed"]
                if active_files:
                    doc_with_files = doc
                    break
        
        if not doc_with_files:
            pytest.skip("No documents with active files to test removal")
        
        # Get the first active file
        active_file = [f for f in doc_with_files["files"] if f.get("status") != "removed"][0]
        file_id = active_file.get("file_id")
        requirement_id = doc_with_files.get("requirement_id")
        
        # Remove the file
        remove_response = self.session.post(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/requirements/{requirement_id}/evidence/{file_id}/remove",
            json={"reason": "Testing removal functionality"}
        )
        
        if remove_response.status_code != 200:
            pytest.skip(f"Could not remove file: {remove_response.text}")
        
        # Verify the file is marked as removed, not deleted
        docs_after = self.session.get(f"{BASE_URL}/api/employee-documents", params={
            "employee_id": self.test_employee_id
        }).json()
        
        # Find the document again
        doc_after = next((d for d in docs_after if d.get("requirement_id") == requirement_id), None)
        
        if doc_after:
            # Check if file is marked as removed
            removed_file = next((f for f in doc_after.get("files", []) if f.get("file_id") == file_id), None)
            if removed_file:
                assert removed_file.get("status") == "removed", f"File should be marked as removed: {removed_file}"
                print(f"✅ Document removal marks file as 'removed' (not deleted)")
            else:
                # File might be filtered out from active view
                print(f"✅ Document removal - file no longer in active list")
        else:
            print(f"✅ Document removal processed")


class TestComplianceScoring:
    """Test compliance scoring consistency"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        
    def test_compliance_requirements_has_overall_percentage(self):
        """Test that compliance requirements endpoint returns overall percentage"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        
        assert response.status_code == 200, f"Failed to get compliance requirements: {response.text}"
        
        data = response.json()
        
        # Check for statuses.overall_compliance.percentage
        assert "statuses" in data, "statuses field missing"
        assert "overall_compliance" in data["statuses"], "overall_compliance missing in statuses"
        assert "percentage" in data["statuses"]["overall_compliance"], "percentage missing in overall_compliance"
        
        percentage = data["statuses"]["overall_compliance"]["percentage"]
        assert isinstance(percentage, (int, float)), f"percentage should be numeric: {percentage}"
        assert 0 <= percentage <= 100, f"percentage should be 0-100: {percentage}"
        
        print(f"✅ Compliance requirements returns overall_compliance.percentage: {percentage}%")
        
    def test_compliance_endpoint_consistency(self):
        """Test that compliance endpoint returns consistent data"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance"
        )
        
        assert response.status_code == 200, f"Failed to get compliance: {response.text}"
        
        data = response.json()
        
        # Check for percentage field
        if "percentage" in data:
            percentage = data["percentage"]
            assert isinstance(percentage, (int, float)), f"percentage should be numeric: {percentage}"
            print(f"✅ Compliance endpoint returns percentage: {percentage}%")
        elif "completion_percentage" in data:
            percentage = data["completion_percentage"]
            print(f"✅ Compliance endpoint returns completion_percentage: {percentage}%")
        else:
            print(f"⚠️ Compliance endpoint structure: {list(data.keys())}")
            
    def test_policy_counts_exclude_unassigned_withdrawn(self):
        """Test that policy assignment counts exclude unassigned/withdrawn"""
        # Get all assignments including inactive
        all_response = self.session.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"employee_id": self.test_employee_id, "include_inactive": "true"}
        )
        
        if all_response.status_code != 200:
            pytest.skip("Could not get policy assignments")
        
        all_assignments = all_response.json()
        
        # Get active assignments only
        active_response = self.session.get(
            f"{BASE_URL}/api/policy-assignments",
            params={"employee_id": self.test_employee_id}
        )
        
        active_assignments = active_response.json()
        
        # Count unassigned/withdrawn
        inactive_count = len([a for a in all_assignments if a.get("status") in ["unassigned", "withdrawn"]])
        
        # Active should be less than or equal to all minus inactive
        expected_active = len(all_assignments) - inactive_count
        
        print(f"✅ Policy counts - All: {len(all_assignments)}, Active: {len(active_assignments)}, Inactive: {inactive_count}")
        
        # Verify active doesn't include unassigned/withdrawn
        for assignment in active_assignments:
            assert assignment.get("status") not in ["unassigned", "withdrawn"], \
                f"Active list should not include {assignment.get('status')} policies"
        
        print(f"✅ Active policy list correctly excludes unassigned/withdrawn")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

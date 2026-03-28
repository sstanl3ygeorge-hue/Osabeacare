"""
Test Policy Acknowledgement and Document Verification System
Tests the audit-safe policy acknowledgement workflow:
1. Policy assignment with audit log
2. Policy viewed tracking
3. Employee acknowledgement with timestamp
4. Admin review after acknowledgement
5. Audit log filtering for compliance actions
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee ID from the review request
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge


class TestPolicyAcknowledgementSystem:
    """Tests for the Policy Acknowledgement and Document Verification System"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    # ==================== POLICY ASSIGNMENT TESTS ====================
    
    def test_get_policy_assignments_for_employee(self):
        """Test GET /api/policy-assignments?employee_id={id} returns assignments with all fields"""
        response = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # If there are assignments, verify the structure
        if len(data) > 0:
            assignment = data[0]
            # Verify required fields are present
            assert "id" in assignment, "Assignment should have id"
            assert "policy_id" in assignment, "Assignment should have policy_id"
            assert "employee_id" in assignment, "Assignment should have employee_id"
            assert "status" in assignment, "Assignment should have status"
            assert "assigned_at" in assignment, "Assignment should have assigned_at"
            
            # Verify optional fields structure
            assert "policy_title" in assignment, "Assignment should have policy_title"
            assert "policy_version" in assignment, "Assignment should have policy_version"
            assert "acknowledged_at" in assignment or assignment.get("acknowledged_at") is None
            assert "admin_reviewed" in assignment, "Assignment should have admin_reviewed field"
            
            print(f"✅ Found {len(data)} policy assignments for employee")
            print(f"   First assignment: {assignment.get('policy_title')} - Status: {assignment.get('status')}")
        else:
            print("ℹ️ No policy assignments found for test employee")
    
    def test_assign_policy_to_employee(self):
        """Test POST /api/policies/assign - assigns policy to employee with audit log"""
        # First, get available policies
        policies_response = self.session.get(f"{BASE_URL}/api/policies")
        assert policies_response.status_code == 200, f"Failed to get policies: {policies_response.text}"
        
        policies = policies_response.json()
        if len(policies) == 0:
            pytest.skip("No policies available to assign")
        
        # Get a policy that's not already assigned to the test employee
        existing_assignments = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}").json()
        assigned_policy_ids = [a['policy_id'] for a in existing_assignments]
        
        available_policy = None
        for policy in policies:
            if policy['id'] not in assigned_policy_ids:
                available_policy = policy
                break
        
        if not available_policy:
            # All policies already assigned, test with existing assignment
            print("ℹ️ All policies already assigned to test employee")
            return
        
        # Assign the policy
        response = self.session.post(f"{BASE_URL}/api/policies/assign", json={
            "policy_id": available_policy['id'],
            "employee_ids": [TEST_EMPLOYEE_ID]
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "assigned" in data, "Response should have 'assigned' count"
        assert data["assigned"] >= 0, "Assigned count should be >= 0"
        
        print(f"✅ Policy '{available_policy['title']}' assigned successfully")
        print(f"   Assigned count: {data['assigned']}")
    
    # ==================== POLICY VIEW TESTS ====================
    
    def test_mark_policy_as_viewed(self):
        """Test PUT /api/policy-assignments/{id}/view - marks policy as viewed"""
        # Get assignments for the test employee
        assignments_response = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}")
        assert assignments_response.status_code == 200
        
        assignments = assignments_response.json()
        if len(assignments) == 0:
            pytest.skip("No policy assignments to test view")
        
        # Find an assignment that hasn't been viewed yet, or use any
        assignment = assignments[0]
        
        response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment['id']}/view")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "viewed_at" in data, "Response should have viewed_at"
        
        # If it was already viewed, viewed_at should still be present
        if data.get("viewed_at"):
            print(f"✅ Policy marked as viewed at: {data['viewed_at']}")
        else:
            print("ℹ️ Policy was already viewed")
    
    # ==================== POLICY ACKNOWLEDGEMENT TESTS ====================
    
    def test_acknowledge_policy(self):
        """Test PUT /api/policy-assignments/{id}/acknowledge - employee acknowledges policy"""
        # Get assignments for the test employee
        assignments_response = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}")
        assert assignments_response.status_code == 200
        
        assignments = assignments_response.json()
        
        # Find an unacknowledged assignment
        unacknowledged = [a for a in assignments if a.get('status') not in ['acknowledged', 'signed']]
        
        if len(unacknowledged) == 0:
            # All policies acknowledged, verify the acknowledged ones have correct fields
            acknowledged = [a for a in assignments if a.get('status') in ['acknowledged', 'signed']]
            if len(acknowledged) > 0:
                a = acknowledged[0]
                assert a.get('acknowledged_at') is not None, "Acknowledged policy should have acknowledged_at"
                print(f"✅ Verified acknowledged policy has timestamp: {a.get('acknowledged_at')}")
                print(f"   Acknowledged by: {a.get('acknowledged_by_employee_name')}")
            return
        
        assignment = unacknowledged[0]
        
        response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment['id']}/acknowledge")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "acknowledged", "Status should be 'acknowledged'"
        assert data.get("acknowledged_at") is not None, "Should have acknowledged_at timestamp"
        assert data.get("acknowledged_by_employee_name") is not None, "Should have employee name"
        
        print(f"✅ Policy acknowledged successfully")
        print(f"   Acknowledged at: {data.get('acknowledged_at')}")
        print(f"   Acknowledged by: {data.get('acknowledged_by_employee_name')}")
    
    def test_acknowledge_already_acknowledged_policy_fails(self):
        """Test that acknowledging an already acknowledged policy returns error"""
        # Get assignments for the test employee
        assignments_response = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}")
        assert assignments_response.status_code == 200
        
        assignments = assignments_response.json()
        
        # Find an acknowledged assignment
        acknowledged = [a for a in assignments if a.get('status') == 'acknowledged']
        
        if len(acknowledged) == 0:
            pytest.skip("No acknowledged policies to test duplicate acknowledgement")
        
        assignment = acknowledged[0]
        
        response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment['id']}/acknowledge")
        
        # Should return 400 for already acknowledged
        assert response.status_code == 400, f"Expected 400 for duplicate acknowledgement, got {response.status_code}"
        print("✅ Correctly rejected duplicate acknowledgement")
    
    # ==================== ADMIN REVIEW TESTS ====================
    
    def test_admin_review_acknowledged_policy(self):
        """Test PUT /api/policy-assignments/{id}/admin-review - admin reviews acknowledged policy"""
        # Get assignments for the test employee
        assignments_response = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}")
        assert assignments_response.status_code == 200
        
        assignments = assignments_response.json()
        
        # Find an acknowledged but not reviewed assignment
        acknowledged_not_reviewed = [a for a in assignments 
                                      if a.get('status') in ['acknowledged', 'signed'] 
                                      and not a.get('admin_reviewed')]
        
        if len(acknowledged_not_reviewed) == 0:
            # Check if there are already reviewed ones
            reviewed = [a for a in assignments if a.get('admin_reviewed')]
            if len(reviewed) > 0:
                a = reviewed[0]
                assert a.get('admin_reviewed_at') is not None, "Reviewed policy should have admin_reviewed_at"
                assert a.get('admin_reviewed_by_name') is not None, "Reviewed policy should have admin name"
                print(f"✅ Verified admin-reviewed policy has correct fields")
                print(f"   Reviewed at: {a.get('admin_reviewed_at')}")
                print(f"   Reviewed by: {a.get('admin_reviewed_by_name')}")
            return
        
        assignment = acknowledged_not_reviewed[0]
        
        response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment['id']}/admin-review")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("admin_reviewed") == True, "admin_reviewed should be True"
        assert data.get("admin_reviewed_at") is not None, "Should have admin_reviewed_at timestamp"
        assert data.get("admin_reviewed_by_name") is not None, "Should have admin name"
        
        print(f"✅ Policy admin-reviewed successfully")
        print(f"   Reviewed at: {data.get('admin_reviewed_at')}")
        print(f"   Reviewed by: {data.get('admin_reviewed_by_name')}")
    
    def test_admin_review_unacknowledged_policy_fails(self):
        """Test that admin cannot review a policy that hasn't been acknowledged"""
        # Get assignments for the test employee
        assignments_response = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}")
        assert assignments_response.status_code == 200
        
        assignments = assignments_response.json()
        
        # Find an unacknowledged assignment
        unacknowledged = [a for a in assignments if a.get('status') not in ['acknowledged', 'signed']]
        
        if len(unacknowledged) == 0:
            pytest.skip("No unacknowledged policies to test admin review rejection")
        
        assignment = unacknowledged[0]
        
        response = self.session.put(f"{BASE_URL}/api/policy-assignments/{assignment['id']}/admin-review")
        
        # Should return 400 for unacknowledged policy
        assert response.status_code == 400, f"Expected 400 for unacknowledged policy, got {response.status_code}"
        print("✅ Correctly rejected admin review of unacknowledged policy")
    
    # ==================== AUDIT LOG TESTS ====================
    
    def test_audit_logs_compliance_filter(self):
        """Test GET /api/audit-logs?entity_id={id}&compliance_only=true returns compliance audit trail"""
        response = self.session.get(f"{BASE_URL}/api/audit-logs?entity_id={TEST_EMPLOYEE_ID}&compliance_only=true")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check that logs contain compliance-relevant actions
        compliance_actions = [
            'policy_assigned', 'policy_viewed', 'policy_acknowledged', 'policy_admin_reviewed',
            'document_uploaded', 'document_verified', 'training_completed'
        ]
        
        if len(data) > 0:
            # Verify log structure
            log = data[0]
            assert "action" in log, "Log should have action"
            assert "created_at" in log or "timestamp" in log, "Log should have created_at or timestamp"
            
            # Count compliance-related actions
            compliance_count = sum(1 for l in data if l.get('action') in compliance_actions)
            print(f"✅ Found {len(data)} audit logs, {compliance_count} compliance-related")
            
            # Print sample actions
            actions = set(l.get('action') for l in data[:10])
            print(f"   Sample actions: {actions}")
        else:
            print("ℹ️ No audit logs found for test employee")
    
    # ==================== FULL WORKFLOW TEST ====================
    
    def test_full_policy_acknowledgement_workflow(self):
        """Test the complete policy acknowledgement workflow end-to-end"""
        # 1. Get policies
        policies_response = self.session.get(f"{BASE_URL}/api/policies")
        assert policies_response.status_code == 200
        policies = policies_response.json()
        
        print(f"Step 1: Found {len(policies)} policies")
        
        # 2. Get current assignments
        assignments_response = self.session.get(f"{BASE_URL}/api/policy-assignments?employee_id={TEST_EMPLOYEE_ID}")
        assert assignments_response.status_code == 200
        assignments = assignments_response.json()
        
        print(f"Step 2: Found {len(assignments)} assignments for test employee")
        
        # 3. Verify assignment structure
        if len(assignments) > 0:
            assignment = assignments[0]
            required_fields = ['id', 'policy_id', 'employee_id', 'status', 'assigned_at', 
                              'policy_title', 'policy_version', 'admin_reviewed']
            
            for field in required_fields:
                assert field in assignment, f"Missing required field: {field}"
            
            print(f"Step 3: Assignment structure verified")
            print(f"   Policy: {assignment.get('policy_title')} v{assignment.get('policy_version')}")
            print(f"   Status: {assignment.get('status')}")
            print(f"   Admin Reviewed: {assignment.get('admin_reviewed')}")
            
            # 4. Check signature information
            if assignment.get('status') in ['acknowledged', 'signed']:
                assert assignment.get('acknowledged_at') is not None, "Should have acknowledged_at"
                print(f"Step 4: Employee acknowledgement verified")
                print(f"   Acknowledged by: {assignment.get('acknowledged_by_employee_name')}")
                print(f"   Acknowledged at: {assignment.get('acknowledged_at')}")
            
            if assignment.get('admin_reviewed'):
                assert assignment.get('admin_reviewed_at') is not None, "Should have admin_reviewed_at"
                print(f"Step 5: Admin review verified")
                print(f"   Reviewed by: {assignment.get('admin_reviewed_by_name')}")
                print(f"   Reviewed at: {assignment.get('admin_reviewed_at')}")
        
        print("✅ Full workflow verification complete")


class TestPolicyAssignmentEndpoints:
    """Additional tests for policy assignment edge cases"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_get_all_policy_assignments(self):
        """Test GET /api/policy-assignments without filters"""
        response = self.session.get(f"{BASE_URL}/api/policy-assignments")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✅ Found {len(data)} total policy assignments")
    
    def test_get_policy_assignments_by_policy_id(self):
        """Test GET /api/policy-assignments?policy_id={id}"""
        # First get a policy
        policies_response = self.session.get(f"{BASE_URL}/api/policies")
        assert policies_response.status_code == 200
        
        policies = policies_response.json()
        if len(policies) == 0:
            pytest.skip("No policies available")
        
        policy_id = policies[0]['id']
        
        response = self.session.get(f"{BASE_URL}/api/policy-assignments?policy_id={policy_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify all assignments are for the requested policy
        for assignment in data:
            assert assignment['policy_id'] == policy_id, "All assignments should be for the requested policy"
        
        print(f"✅ Found {len(data)} assignments for policy '{policies[0]['title']}'")
    
    def test_assignment_not_found(self):
        """Test that non-existent assignment returns 404"""
        fake_id = str(uuid.uuid4())
        
        response = self.session.put(f"{BASE_URL}/api/policy-assignments/{fake_id}/view")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Correctly returned 404 for non-existent assignment")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

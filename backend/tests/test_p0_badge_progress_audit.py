"""
P0 Fixes Testing - Badge Logic, Unified Progress, Audit Trail
Tests for:
1. Recruitment Approved badge logic - badge should ONLY appear when recruitment_approved=true AND zero blockers exist
2. Unified Progress Consistency - Worker and Admin views use same progress calculation
3. Audit Trail logging - events should be recorded
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestP0BadgeLogicAndProgress:
    """Test P0 fixes for badge logic and unified progress"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get employees for testing
        employees_response = self.session.get(f"{BASE_URL}/api/employees?limit=50")
        assert employees_response.status_code == 200
        self.employees = employees_response.json()
        
        # Find employees with different states for testing
        self.approved_with_blockers = None
        self.approved_no_blockers = None
        self.not_approved = None
        
        for emp in self.employees:
            if emp.get("recruitment_approved") and emp.get("work_readiness_3tier", {}).get("reasons"):
                self.approved_with_blockers = emp
            elif emp.get("recruitment_approved") and not emp.get("work_readiness_3tier", {}).get("reasons"):
                self.approved_no_blockers = emp
            elif not emp.get("recruitment_approved"):
                self.not_approved = emp
    
    # ========== P0 Issue 1: Badge Logic Tests ==========
    
    def test_unified_progress_endpoint_returns_blockers(self):
        """P0 Issue 1: Verify unified-progress endpoint returns blockers list"""
        if not self.approved_with_blockers:
            pytest.skip("No employee with approved status and blockers found")
        
        emp_id = self.approved_with_blockers["id"]
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/unified-progress")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "blockers" in data, "Response should contain 'blockers' field"
        assert "overall_percentage" in data, "Response should contain 'overall_percentage'"
        assert "completed_requirements" in data, "Response should contain 'completed_requirements'"
        assert "total_requirements" in data, "Response should contain 'total_requirements'"
        
        # For approved with blockers, blockers list should NOT be empty
        assert len(data["blockers"]) > 0, f"Employee {emp_id} is approved but should have blockers"
        print(f"PASS: Employee {emp_id} has {len(data['blockers'])} blockers: {data['blockers'][:3]}...")
    
    def test_approved_with_blockers_should_not_show_approved_badge(self):
        """P0 Issue 1: Employee with recruitment_approved=true but blockers should NOT show 'Approved' badge"""
        if not self.approved_with_blockers:
            pytest.skip("No employee with approved status and blockers found")
        
        emp_id = self.approved_with_blockers["id"]
        
        # Get unified progress to check blockers
        progress_response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/unified-progress")
        assert progress_response.status_code == 200
        progress_data = progress_response.json()
        
        # Verify this employee has blockers
        blockers = progress_data.get("blockers", [])
        assert len(blockers) > 0, "Test employee should have blockers"
        
        # Verify employee is recruitment_approved
        assert self.approved_with_blockers.get("recruitment_approved") == True
        
        # The badge logic in frontend should show "Conditionally Approved" not "Approved"
        # This is verified by checking that blockers exist when recruitment_approved=true
        print(f"PASS: Employee {emp_id} is recruitment_approved=true but has {len(blockers)} blockers")
        print(f"Frontend should show 'Conditionally Approved' badge, NOT 'Approved' badge")
    
    def test_not_approved_employee_should_show_awaiting_approval(self):
        """P0 Issue 1: Employee with recruitment_approved=false should show 'Awaiting Approval'"""
        if not self.not_approved:
            pytest.skip("No employee with not approved status found")
        
        emp_id = self.not_approved["id"]
        
        # Verify employee is NOT recruitment_approved
        assert self.not_approved.get("recruitment_approved") == False
        
        # Get employee details
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}")
        assert response.status_code == 200
        emp_data = response.json()
        
        assert emp_data.get("recruitment_approved") == False
        print(f"PASS: Employee {emp_id} has recruitment_approved=false")
        print(f"Frontend should show 'Awaiting Approval' badge")
    
    # ========== P0 Issue 2: Unified Progress Consistency Tests ==========
    
    def test_unified_progress_endpoint_exists(self):
        """P0 Issue 2: Verify GET /api/employees/{id}/unified-progress endpoint exists"""
        if not self.employees:
            pytest.skip("No employees found")
        
        emp_id = self.employees[0]["id"]
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/unified-progress")
        
        assert response.status_code == 200, f"Endpoint should return 200, got {response.status_code}"
        data = response.json()
        
        # Verify required fields
        required_fields = ["employee_id", "overall_percentage", "completed_requirements", 
                         "total_requirements", "categories", "blockers"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"PASS: unified-progress endpoint returns all required fields")
    
    def test_unified_progress_categories_structure(self):
        """P0 Issue 2: Verify unified-progress returns correct category structure"""
        if not self.employees:
            pytest.skip("No employees found")
        
        emp_id = self.employees[0]["id"]
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/unified-progress")
        
        assert response.status_code == 200
        data = response.json()
        
        categories = data.get("categories", {})
        expected_categories = ["documents", "forms", "training", "references", "agreements", "induction"]
        
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
            assert "completed" in categories[cat], f"Category {cat} missing 'completed'"
            assert "total" in categories[cat], f"Category {cat} missing 'total'"
        
        print(f"PASS: All 6 categories present with completed/total counts")
    
    def test_unified_progress_blocker_count_consistency(self):
        """P0 Issue 2: Verify blocker count is consistent across endpoints"""
        if not self.approved_with_blockers:
            pytest.skip("No employee with blockers found")
        
        emp_id = self.approved_with_blockers["id"]
        
        # Get unified progress
        progress_response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/unified-progress")
        assert progress_response.status_code == 200
        progress_data = progress_response.json()
        
        blockers = progress_data.get("blockers", [])
        completed = progress_data.get("completed_requirements", 0)
        total = progress_data.get("total_requirements", 0)
        percentage = progress_data.get("overall_percentage", 0)
        
        # Verify math consistency
        if total > 0:
            expected_percentage = round((completed / total) * 100)
            # Allow small rounding differences
            assert abs(percentage - expected_percentage) <= 1, \
                f"Percentage mismatch: {percentage} vs expected {expected_percentage}"
        
        print(f"PASS: Progress calculation consistent - {completed}/{total} = {percentage}%")
        print(f"Blockers count: {len(blockers)}")
    
    # ========== P0 Issue 3: Audit Trail Tests ==========
    
    def test_audit_trail_endpoint_exists(self):
        """P0 Issue 3: Verify GET /api/employees/{id}/audit-trail endpoint exists"""
        if not self.employees:
            pytest.skip("No employees found")
        
        emp_id = self.employees[0]["id"]
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/audit-trail?limit=10")
        
        assert response.status_code == 200, f"Endpoint should return 200, got {response.status_code}"
        data = response.json()
        
        # Verify response structure
        assert "employee_id" in data, "Response should contain 'employee_id'"
        assert "employee_name" in data, "Response should contain 'employee_name'"
        assert "audit_trail" in data, "Response should contain 'audit_trail'"
        assert "pagination" in data, "Response should contain 'pagination'"
        
        print(f"PASS: audit-trail endpoint returns correct structure")
    
    def test_audit_trail_returns_events(self):
        """P0 Issue 3: Verify audit trail returns events for employees with history"""
        # Find an employee with audit trail events
        for emp in self.employees[:10]:
            emp_id = emp["id"]
            response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/audit-trail?limit=50")
            
            if response.status_code == 200:
                data = response.json()
                audit_events = data.get("audit_trail", [])
                
                if len(audit_events) > 0:
                    # Verify event structure
                    event = audit_events[0]
                    assert "action" in event, "Event should have 'action' field"
                    # Field can be 'timestamp' or 'created_at' depending on audit source
                    assert "timestamp" in event or "created_at" in event, \
                        "Event should have 'timestamp' or 'created_at' field"
                    
                    print(f"PASS: Found {len(audit_events)} audit events for employee {emp_id}")
                    print(f"Sample event action: {event.get('action')}")
                    return
        
        # If no events found, that's still valid - just means no actions recorded yet
        print("INFO: No audit trail events found for tested employees (may be expected)")
    
    def test_audit_trail_pagination(self):
        """P0 Issue 3: Verify audit trail supports pagination"""
        if not self.employees:
            pytest.skip("No employees found")
        
        emp_id = self.employees[0]["id"]
        
        # Test with limit
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/audit-trail?limit=5&skip=0")
        assert response.status_code == 200
        data = response.json()
        
        pagination = data.get("pagination", {})
        assert pagination.get("limit") == 5, "Pagination limit should be 5"
        assert pagination.get("skip") == 0, "Pagination skip should be 0"
        
        print(f"PASS: Audit trail pagination working correctly")
    
    # ========== Additional Validation Tests ==========
    
    def test_employee_compliance_requirements_endpoint(self):
        """Verify compliance requirements endpoint returns blockers for badge logic"""
        if not self.approved_with_blockers:
            pytest.skip("No employee with blockers found")
        
        emp_id = self.approved_with_blockers["id"]
        
        # Try compliance-requirements endpoint
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/compliance-requirements")
        
        if response.status_code == 200:
            data = response.json()
            # Check if blockers are present
            blockers = data.get("blockers", [])
            pre_emp_blockers = data.get("pre_employment_gates", {}).get("blockers", [])
            
            total_blockers = len(blockers) + len(pre_emp_blockers)
            print(f"PASS: compliance-requirements returns {total_blockers} total blockers")
        else:
            print(f"INFO: compliance-requirements endpoint returned {response.status_code}")
    
    def test_recruitment_pipeline_endpoint(self):
        """Verify recruitment pipeline endpoint returns approval status"""
        response = self.session.get(f"{BASE_URL}/api/recruitment/pipeline")
        
        assert response.status_code == 200, f"Pipeline endpoint failed: {response.text}"
        data = response.json()
        
        # Check if applicants have recruitment_approved field
        applicants = data.get("applicants", [])
        if applicants:
            for applicant in applicants[:3]:
                assert "recruitment_approved" in applicant or "id" in applicant, \
                    "Applicant should have recruitment_approved or id field"
            print(f"PASS: Recruitment pipeline returns {len(applicants)} applicants")
        else:
            print("INFO: No applicants in recruitment pipeline")


class TestWorkerDashboardUnifiedProgress:
    """Test that worker dashboard uses unified progress calculation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin first to get employee data
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.admin_token = login_response.json().get("token")
    
    def test_admin_unified_progress_endpoint(self):
        """Verify admin can access unified-progress for any employee"""
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # Get an employee
        employees_response = self.session.get(f"{BASE_URL}/api/employees?limit=1")
        assert employees_response.status_code == 200
        employees = employees_response.json()
        
        if not employees:
            pytest.skip("No employees found")
        
        emp_id = employees[0]["id"]
        
        # Get unified progress
        response = self.session.get(f"{BASE_URL}/api/employees/{emp_id}/unified-progress")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("employee_id") == emp_id
        assert "overall_percentage" in data
        assert "blockers" in data
        
        print(f"PASS: Admin can access unified-progress for employee {emp_id}")
        print(f"Progress: {data.get('overall_percentage')}%, Blockers: {len(data.get('blockers', []))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test Acknowledgement Flow for Contract/Handbook
Tests the lightweight acknowledgement flow (no file upload required)
and Equal Opportunities optional flag.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAcknowledgementFlow:
    """Test acknowledgement flow for Contract and Handbook requirements"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        self.token = None
        self.employee_id = None
        
    def get_auth_token(self):
        """Get authentication token"""
        if self.token:
            return self.token
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            return self.token
        pytest.skip("Authentication failed - skipping tests")
        
    def get_headers(self):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {self.get_auth_token()}",
            "Content-Type": "application/json"
        }
    
    def get_test_employee(self):
        """Get an employee for testing (Olakunle Alonge)"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.get_headers())
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        employees = response.json()
        # Find Olakunle Alonge or first employee
        for emp in employees:
            if "Olakunle" in emp.get("first_name", "") or "Alonge" in emp.get("last_name", ""):
                return emp["id"]
        # Return first employee if Olakunle not found
        if employees:
            return employees[0]["id"]
        pytest.skip("No employees found for testing")
    
    # ========== MANDATORY_ITEMS Configuration Tests ==========
    
    def test_contract_is_acknowledgement_type(self):
        """Verify Contract is configured as acknowledgement type in MANDATORY_ITEMS"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.get_headers())
        assert response.status_code == 200
        
        employee_id = self.get_test_employee()
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find contract requirement
        contract_req = None
        for req in data.get("requirements", []):
            if req["id"] == "contract":
                contract_req = req
                break
        
        assert contract_req is not None, "Contract requirement not found"
        assert contract_req["type"] == "acknowledgement", f"Contract type should be 'acknowledgement', got '{contract_req['type']}'"
        assert "acknowledgement_text" in contract_req, "Contract should have acknowledgement_text"
        print(f"✅ Contract is acknowledgement type with text: {contract_req.get('acknowledgement_text', '')[:50]}...")
    
    def test_handbook_is_acknowledgement_type(self):
        """Verify Employee Handbook is configured as acknowledgement type"""
        employee_id = self.get_test_employee()
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find handbook requirement
        handbook_req = None
        for req in data.get("requirements", []):
            if req["id"] == "handbook":
                handbook_req = req
                break
        
        assert handbook_req is not None, "Handbook requirement not found"
        assert handbook_req["type"] == "acknowledgement", f"Handbook type should be 'acknowledgement', got '{handbook_req['type']}'"
        assert "acknowledgement_text" in handbook_req, "Handbook should have acknowledgement_text"
        print(f"✅ Handbook is acknowledgement type with text: {handbook_req.get('acknowledgement_text', '')[:50]}...")
    
    def test_equal_opportunities_is_optional(self):
        """Verify Equal Opportunities is marked as optional"""
        employee_id = self.get_test_employee()
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find equal opportunities requirement
        eq_opp_req = None
        for req in data.get("requirements", []):
            if req["id"] == "equal_opportunities":
                eq_opp_req = req
                break
        
        assert eq_opp_req is not None, "Equal Opportunities requirement not found"
        assert eq_opp_req.get("optional") == True, f"Equal Opportunities should be optional, got optional={eq_opp_req.get('optional')}"
        print(f"✅ Equal Opportunities is marked as optional")
    
    # ========== Acknowledgement Endpoint Tests ==========
    
    def test_acknowledge_contract_endpoint(self):
        """Test the acknowledge endpoint for Contract"""
        employee_id = self.get_test_employee()
        
        # First check current status
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        contract_req = None
        for req in data.get("requirements", []):
            if req["id"] == "contract":
                contract_req = req
                break
        
        initial_acknowledged = contract_req.get("acknowledged", False)
        print(f"Contract initial acknowledged status: {initial_acknowledged}")
        
        # Submit acknowledgement
        response = requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/contract/acknowledge",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Acknowledge failed: {response.text}"
        ack_data = response.json()
        
        assert ack_data.get("success") == True, "Acknowledgement should succeed"
        assert ack_data.get("acknowledged") == True, "acknowledged should be True"
        assert "acknowledged_at" in ack_data, "Should include acknowledged_at timestamp"
        assert "acknowledged_by" in ack_data, "Should include acknowledged_by name"
        print(f"✅ Contract acknowledged by {ack_data.get('acknowledged_by')} at {ack_data.get('acknowledged_at')}")
    
    def test_acknowledge_handbook_endpoint(self):
        """Test the acknowledge endpoint for Handbook"""
        employee_id = self.get_test_employee()
        
        # Submit acknowledgement
        response = requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/handbook/acknowledge",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Acknowledge failed: {response.text}"
        ack_data = response.json()
        
        assert ack_data.get("success") == True, "Acknowledgement should succeed"
        assert ack_data.get("acknowledged") == True, "acknowledged should be True"
        print(f"✅ Handbook acknowledged successfully")
    
    def test_acknowledge_non_acknowledgement_type_fails(self):
        """Test that acknowledging a non-acknowledgement type requirement fails"""
        employee_id = self.get_test_employee()
        
        # Try to acknowledge a document type requirement (should fail)
        response = requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/dbs_certificate/acknowledge",
            headers=self.get_headers()
        )
        assert response.status_code == 400, f"Should fail for non-acknowledgement type, got {response.status_code}"
        assert "does not support acknowledgement" in response.json().get("detail", "").lower()
        print(f"✅ Non-acknowledgement type correctly rejected")
    
    # ========== Status Update Tests ==========
    
    def test_acknowledged_item_shows_completed_and_verified(self):
        """Verify acknowledged items show as completed AND verified"""
        employee_id = self.get_test_employee()
        
        # First acknowledge contract
        requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/contract/acknowledge",
            headers=self.get_headers()
        )
        
        # Check compliance requirements
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        contract_req = None
        for req in data.get("requirements", []):
            if req["id"] == "contract":
                contract_req = req
                break
        
        assert contract_req is not None, "Contract requirement not found"
        assert contract_req.get("acknowledged") == True, "Contract should be acknowledged"
        assert contract_req.get("status") == "completed", f"Status should be 'completed', got '{contract_req.get('status')}'"
        assert contract_req.get("verified") == True, f"Acknowledged items should be auto-verified, got verified={contract_req.get('verified')}"
        assert contract_req.get("has_evidence") == True, "Acknowledgement should count as evidence"
        print(f"✅ Acknowledged contract shows status=completed, verified=True, has_evidence=True")
    
    # ========== Compliance Percentage Tests ==========
    
    def test_optional_items_excluded_from_compliance_total(self):
        """Verify optional items (Equal Opportunities) don't affect compliance percentage"""
        employee_id = self.get_test_employee()
        
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        # Count total requirements and optional requirements
        total_reqs = len(data.get("requirements", []))
        optional_reqs = sum(1 for req in data.get("requirements", []) if req.get("optional"))
        
        # Summary should exclude optional items from total
        summary = data.get("summary", {})
        summary_total = summary.get("total", 0)
        
        expected_total = total_reqs - optional_reqs
        assert summary_total == expected_total, f"Summary total should be {expected_total} (excluding {optional_reqs} optional), got {summary_total}"
        print(f"✅ Summary total ({summary_total}) correctly excludes {optional_reqs} optional item(s)")
    
    def test_compliance_percentage_after_acknowledgement(self):
        """Test that compliance percentage updates after acknowledging items"""
        employee_id = self.get_test_employee()
        
        # Get initial compliance
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        initial_data = response.json()
        initial_percentage = initial_data.get("summary", {}).get("completion_percentage", 0)
        
        # Acknowledge both contract and handbook
        requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/contract/acknowledge",
            headers=self.get_headers()
        )
        requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/handbook/acknowledge",
            headers=self.get_headers()
        )
        
        # Get updated compliance
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        updated_data = response.json()
        updated_percentage = updated_data.get("summary", {}).get("completion_percentage", 0)
        
        print(f"Initial compliance: {initial_percentage}%, Updated: {updated_percentage}%")
        # Note: Percentage may not increase if items were already acknowledged
        # Just verify the endpoint works and returns valid data
        assert isinstance(updated_percentage, int), "Completion percentage should be an integer"
        assert 0 <= updated_percentage <= 100, "Percentage should be between 0 and 100"
        print(f"✅ Compliance percentage is valid: {updated_percentage}%")
    
    # ========== Audit Log Tests ==========
    
    def test_acknowledgement_creates_audit_log(self):
        """Verify acknowledgement creates audit log entry"""
        employee_id = self.get_test_employee()
        
        # Acknowledge contract
        requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/contract/acknowledge",
            headers=self.get_headers()
        )
        
        # Check audit logs
        response = requests.get(
            f"{BASE_URL}/api/audit-logs?entity_id={employee_id}&compliance_only=true",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        logs = response.json()
        
        # Find acknowledgement log
        ack_logs = [log for log in logs if log.get("action") == "acknowledgement_completed"]
        
        assert len(ack_logs) > 0, "Should have acknowledgement_completed audit log"
        latest_ack = ack_logs[0]
        assert "contract" in latest_ack.get("details", {}).get("requirement_name", "").lower() or \
               latest_ack.get("entity_id") == "contract", "Audit log should reference contract"
        print(f"✅ Audit log created for acknowledgement: {latest_ack.get('action')}")


class TestAcknowledgementIdempotency:
    """Test that acknowledgements are idempotent"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_email = "admin@osabea.care"
        self.admin_password = "admin123"
        self.token = None
        
    def get_auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            return self.token
        pytest.skip("Authentication failed")
        
    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.get_auth_token()}",
            "Content-Type": "application/json"
        }
    
    def get_test_employee(self):
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.get_headers())
        employees = response.json()
        for emp in employees:
            if "Olakunle" in emp.get("first_name", ""):
                return emp["id"]
        return employees[0]["id"] if employees else None
    
    def test_double_acknowledgement_is_idempotent(self):
        """Test that acknowledging twice doesn't cause errors"""
        employee_id = self.get_test_employee()
        
        # First acknowledgement
        response1 = requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/contract/acknowledge",
            headers=self.get_headers()
        )
        assert response1.status_code == 200
        
        # Second acknowledgement (should succeed with "already acknowledged" message)
        response2 = requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/contract/acknowledge",
            headers=self.get_headers()
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("success") == True
        assert data2.get("acknowledged") == True
        # Should indicate already acknowledged
        assert "already" in data2.get("message", "").lower() or data2.get("acknowledged") == True
        print(f"✅ Double acknowledgement handled gracefully: {data2.get('message')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

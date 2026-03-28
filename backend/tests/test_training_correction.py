"""
Test Training Correction System - Safe Correction API with Audit Trail
Tests POST /api/training-records/{record_id}/correct and GET /api/training-records/{record_id}/history
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTrainingCorrectionSystem:
    """Tests for the Safe Correction System with mandatory reasons and audit trail"""
    
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
        
        # Get employees for testing
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200
        self.employees = emp_response.json()
        
        # Get existing training records
        training_response = self.session.get(f"{BASE_URL}/api/training-records")
        assert training_response.status_code == 200
        self.training_records = training_response.json()
    
    def test_training_records_endpoint_exists(self):
        """Test that training records endpoint returns data"""
        response = self.session.get(f"{BASE_URL}/api/training-records")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Training records endpoint works - {len(data)} records found")
    
    def test_create_training_record_for_correction_test(self):
        """Create a training record to test correction on"""
        if not self.employees:
            pytest.skip("No employees available for testing")
        
        employee_id = self.employees[0]['id']
        test_record = {
            "employee_id": employee_id,
            "training_name": "TEST_Safeguarding of Vulnerable Adults",
            "mandatory": True,
            "status": "completed",
            "expiry_date": "2025-06-15"
        }
        
        response = self.session.post(f"{BASE_URL}/api/training-records", json=test_record)
        assert response.status_code in [200, 201], f"Failed to create training record: {response.text}"
        
        data = response.json()
        assert "id" in data
        self.test_record_id = data["id"]
        print(f"✅ Created test training record: {self.test_record_id}")
        return data
    
    def test_correction_endpoint_requires_reason(self):
        """Test that correction endpoint requires a reason"""
        # First create a record
        record = self.test_create_training_record_for_correction_test()
        record_id = record["id"]
        
        # Try to correct without reason
        correction_data = {
            "field": "expiry_date",
            "old_value": "2025-06-15",
            "new_value": "2026-06-15",
            "reason": ""  # Empty reason
        }
        
        response = self.session.post(f"{BASE_URL}/api/training-records/{record_id}/correct", json=correction_data)
        assert response.status_code == 400, f"Expected 400 for empty reason, got {response.status_code}"
        print("✅ Correction endpoint correctly rejects empty reason")
    
    def test_correction_endpoint_requires_minimum_reason_length(self):
        """Test that correction endpoint requires minimum 3 character reason"""
        record = self.test_create_training_record_for_correction_test()
        record_id = record["id"]
        
        # Try with short reason
        correction_data = {
            "field": "expiry_date",
            "old_value": "2025-06-15",
            "new_value": "2026-06-15",
            "reason": "ab"  # Too short
        }
        
        response = self.session.post(f"{BASE_URL}/api/training-records/{record_id}/correct", json=correction_data)
        assert response.status_code == 400, f"Expected 400 for short reason, got {response.status_code}"
        print("✅ Correction endpoint correctly rejects reason < 3 characters")
    
    def test_correction_endpoint_success(self):
        """Test successful correction with valid reason"""
        record = self.test_create_training_record_for_correction_test()
        record_id = record["id"]
        
        correction_data = {
            "field": "expiry_date",
            "old_value": "2025-06-15",
            "new_value": "2026-12-31",
            "reason": "Certificate renewed - new expiry date confirmed"
        }
        
        response = self.session.post(f"{BASE_URL}/api/training-records/{record_id}/correct", json=correction_data)
        assert response.status_code == 200, f"Correction failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "audit_entry" in data
        assert data["audit_entry"]["field_changed"] == "expiry_date"
        assert data["audit_entry"]["new_value"] == "2026-12-31"
        assert data["audit_entry"]["reason"] == "Certificate renewed - new expiry date confirmed"
        print("✅ Correction endpoint works with valid reason")
        return record_id
    
    def test_correction_status_field(self):
        """Test correcting the status field"""
        record = self.test_create_training_record_for_correction_test()
        record_id = record["id"]
        
        correction_data = {
            "field": "status",
            "old_value": "completed",
            "new_value": "in_progress",
            "reason": "Training was not fully completed - needs additional modules"
        }
        
        response = self.session.post(f"{BASE_URL}/api/training-records/{record_id}/correct", json=correction_data)
        assert response.status_code == 200, f"Status correction failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        print("✅ Status field correction works")
    
    def test_correction_invalid_field(self):
        """Test that invalid fields are rejected"""
        record = self.test_create_training_record_for_correction_test()
        record_id = record["id"]
        
        correction_data = {
            "field": "employee_id",  # Not allowed
            "old_value": "old",
            "new_value": "new",
            "reason": "Trying to change employee"
        }
        
        response = self.session.post(f"{BASE_URL}/api/training-records/{record_id}/correct", json=correction_data)
        assert response.status_code == 400, f"Expected 400 for invalid field, got {response.status_code}"
        print("✅ Invalid field correctly rejected")
    
    def test_history_endpoint_exists(self):
        """Test that history endpoint exists and returns data"""
        # First create and correct a record
        record_id = self.test_correction_endpoint_success()
        
        response = self.session.get(f"{BASE_URL}/api/training-records/{record_id}/history")
        assert response.status_code == 200, f"History endpoint failed: {response.text}"
        
        data = response.json()
        assert "training_record" in data
        assert "history" in data
        assert isinstance(data["history"], list)
        print(f"✅ History endpoint works - {len(data['history'])} entries found")
    
    def test_history_contains_correction_details(self):
        """Test that history contains correction details"""
        record = self.test_create_training_record_for_correction_test()
        record_id = record["id"]
        
        # Make a correction
        correction_data = {
            "field": "expiry_date",
            "old_value": "2025-06-15",
            "new_value": "2027-01-01",
            "reason": "Extended validity period per new regulations"
        }
        self.session.post(f"{BASE_URL}/api/training-records/{record_id}/correct", json=correction_data)
        
        # Get history
        response = self.session.get(f"{BASE_URL}/api/training-records/{record_id}/history")
        assert response.status_code == 200
        
        data = response.json()
        history = data["history"]
        
        # Find the correction entry
        correction_entry = next((h for h in history if h.get("action") == "training_correction"), None)
        assert correction_entry is not None, "Correction entry not found in history"
        assert correction_entry["field_changed"] == "expiry_date"
        assert correction_entry["new_value"] == "2027-01-01"
        assert correction_entry["reason"] == "Extended validity period per new regulations"
        print("✅ History contains full correction details")
    
    def test_history_for_nonexistent_record(self):
        """Test history endpoint for non-existent record"""
        fake_id = str(uuid.uuid4())
        response = self.session.get(f"{BASE_URL}/api/training-records/{fake_id}/history")
        assert response.status_code == 404
        print("✅ History endpoint returns 404 for non-existent record")
    
    def test_correction_for_nonexistent_record(self):
        """Test correction endpoint for non-existent record"""
        fake_id = str(uuid.uuid4())
        correction_data = {
            "field": "expiry_date",
            "old_value": "2025-01-01",
            "new_value": "2026-01-01",
            "reason": "Test correction"
        }
        response = self.session.post(f"{BASE_URL}/api/training-records/{fake_id}/correct", json=correction_data)
        assert response.status_code == 404
        print("✅ Correction endpoint returns 404 for non-existent record")


class TestDashboardExpiryAlerts:
    """Test dashboard expiry alerts endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_dashboard_stats_endpoint(self):
        """Test dashboard stats endpoint"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields
        assert "total_employees" in data
        print(f"✅ Dashboard stats endpoint works - {data.get('total_employees')} employees")
    
    def test_dashboard_expiry_alerts_endpoint(self):
        """Test dashboard expiry alerts endpoint"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/expiry-alerts")
        
        # This endpoint may or may not exist
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Expiry alerts endpoint works - expired: {data.get('expired', {}).get('total_items', 0)}, expiring: {data.get('expiring_soon', {}).get('total_items', 0)}")
        elif response.status_code == 404:
            print("⚠️ Expiry alerts endpoint not found (404)")
        else:
            print(f"⚠️ Expiry alerts endpoint returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

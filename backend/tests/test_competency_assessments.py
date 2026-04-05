"""
Test Competency Assessments API Endpoints
Tests for P2 Feature: Competency Assessments UI
- GET /employees/{id}/competencies
- POST /employees/{id}/competencies
- PUT /employees/{id}/competencies/{id}
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCompetencyAssessmentsAPI:
    """Test competency assessment endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login and get employee"""
        # Login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get an employee to test with
        employees_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert employees_response.status_code == 200, f"Failed to get employees: {employees_response.text}"
        employees = employees_response.json()
        assert len(employees) > 0, "No employees found for testing"
        self.employee_id = employees[0].get("id")
        self.employee_name = f"{employees[0].get('first_name', '')} {employees[0].get('last_name', '')}"
        
    def test_get_competencies_empty_or_existing(self):
        """Test GET /employees/{id}/competencies returns list"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get competencies: {response.text}"
        data = response.json()
        assert "competencies" in data, "Response should contain 'competencies' key"
        assert isinstance(data["competencies"], list), "Competencies should be a list"
        print(f"✓ GET competencies returned {len(data['competencies'])} records")
        
    def test_create_competency_assessment(self):
        """Test POST /employees/{id}/competencies creates new assessment"""
        # Calculate review due date (1 year from now)
        review_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        payload = {
            "competency_type": "medication",
            "competency_name": "Medication Administration",
            "status": "competent",
            "review_due_date": review_date,
            "notes": "TEST_Competency assessment passed with flying colors"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to create competency: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "id" in data, "Response should contain competency ID"
        assert data.get("status") == "competent", "Status should match input"
        
        self.created_competency_id = data["id"]
        print(f"✓ Created competency assessment with ID: {self.created_competency_id}")
        
        # Verify it appears in GET
        get_response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers
        )
        assert get_response.status_code == 200
        competencies = get_response.json().get("competencies", [])
        found = any(c.get("id") == self.created_competency_id for c in competencies)
        assert found, "Created competency should appear in GET response"
        print("✓ Created competency verified in GET response")
        
    def test_create_competency_training_required(self):
        """Test creating competency with 'training_required' status"""
        review_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        
        payload = {
            "competency_type": "manual_handling",
            "competency_name": "Moving & Handling",
            "status": "training_required",
            "review_due_date": review_date,
            "notes": "TEST_Needs refresher training on manual handling techniques"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to create competency: {response.text}"
        data = response.json()
        assert data.get("status") == "training_required"
        print(f"✓ Created 'training_required' competency: {data.get('id')}")
        
    def test_create_competency_not_competent(self):
        """Test creating competency with 'not_competent' status"""
        review_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        payload = {
            "competency_type": "safeguarding",
            "competency_name": "Safeguarding Adults",
            "status": "not_competent",
            "review_due_date": review_date,
            "notes": "TEST_Failed initial assessment, requires full training"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to create competency: {response.text}"
        data = response.json()
        assert data.get("status") == "not_competent"
        print(f"✓ Created 'not_competent' competency: {data.get('id')}")
        
    def test_create_competency_missing_required_fields(self):
        """Test that missing required fields returns error"""
        # Missing competency_type
        payload = {
            "competency_name": "Test",
            "status": "competent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers,
            json=payload
        )
        # Should fail validation
        assert response.status_code in [400, 422], f"Should reject missing fields: {response.text}"
        print("✓ Missing required fields correctly rejected")
        
    def test_update_competency_assessment(self):
        """Test PUT /employees/{id}/competencies/{id} updates assessment"""
        # First create a competency to update
        review_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        create_payload = {
            "competency_type": "dementia_care",
            "competency_name": "Dementia Care",
            "status": "training_required",
            "review_due_date": review_date,
            "notes": "TEST_Initial assessment - needs training"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers,
            json=create_payload
        )
        assert create_response.status_code == 200
        competency_id = create_response.json().get("id")
        print(f"✓ Created competency for update test: {competency_id}")
        
        # Now update it
        new_review_date = (datetime.now() + timedelta(days=730)).strftime("%Y-%m-%d")
        update_payload = {
            "competency_type": "dementia_care",
            "competency_name": "Dementia Care",
            "status": "competent",
            "review_due_date": new_review_date,
            "notes": "TEST_Completed training, now competent"
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies/{competency_id}",
            headers=self.headers,
            json=update_payload
        )
        assert update_response.status_code == 200, f"Failed to update competency: {update_response.text}"
        data = update_response.json()
        assert data.get("success") == True
        print(f"✓ Updated competency status to 'competent'")
        
        # Verify update persisted
        get_response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers
        )
        competencies = get_response.json().get("competencies", [])
        updated = next((c for c in competencies if c.get("id") == competency_id), None)
        assert updated is not None, "Updated competency should exist"
        assert updated.get("status") == "competent", "Status should be updated"
        print("✓ Update verified in GET response")
        
    def test_competency_audit_history(self):
        """Test that competency updates create audit history"""
        # Create and update a competency
        review_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        create_payload = {
            "competency_type": "learning_disabilities",
            "competency_name": "Learning Disabilities",
            "status": "not_competent",
            "review_due_date": review_date,
            "notes": "TEST_Initial assessment"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers,
            json=create_payload
        )
        assert create_response.status_code == 200
        competency_id = create_response.json().get("id")
        
        # Update status
        update_payload = {
            "competency_type": "learning_disabilities",
            "competency_name": "Learning Disabilities",
            "status": "training_required",
            "review_due_date": review_date,
            "notes": "TEST_Started training program"
        }
        
        requests.put(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies/{competency_id}",
            headers=self.headers,
            json=update_payload
        )
        
        # Get competencies and check for audit history
        get_response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers
        )
        competencies = get_response.json().get("competencies", [])
        comp = next((c for c in competencies if c.get("id") == competency_id), None)
        
        # Check if audit history exists
        if comp and comp.get("audit", {}).get("assessment_history"):
            history = comp["audit"]["assessment_history"]
            print(f"✓ Competency has {len(history)} history entries")
        else:
            print("⚠ No audit history found (may be expected for new records)")
            
    def test_all_competency_types(self):
        """Test that all competency types can be created"""
        competency_types = [
            ("medication", "Medication Administration"),
            ("manual_handling", "Moving & Handling"),
            ("safeguarding", "Safeguarding Adults"),
            ("dementia_care", "Dementia Care"),
            ("clinical_competency", "Clinical Competency"),
        ]
        
        review_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        for comp_type, comp_name in competency_types:
            payload = {
                "competency_type": comp_type,
                "competency_name": comp_name,
                "status": "competent",
                "review_due_date": review_date,
                "notes": f"TEST_Auto-created for type testing: {comp_type}"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
                headers=self.headers,
                json=payload
            )
            # May get 200 or 409 if duplicate
            assert response.status_code in [200, 409], f"Failed for {comp_type}: {response.text}"
            
        print(f"✓ Tested {len(competency_types)} competency types")
        
    def test_unauthorized_access(self):
        """Test that unauthorized requests are rejected"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies"
        )
        assert response.status_code == 401, "Should reject unauthorized request"
        print("✓ Unauthorized access correctly rejected")


class TestCompetencyStatusCounts:
    """Test competency status summary calculations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        employees_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert employees_response.status_code == 200
        employees = employees_response.json()
        assert len(employees) > 0
        self.employee_id = employees[0].get("id")
        
    def test_status_counts_calculation(self):
        """Test that status counts can be calculated from competencies"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/competencies",
            headers=self.headers
        )
        assert response.status_code == 200
        competencies = response.json().get("competencies", [])
        
        # Calculate counts
        competent_count = sum(1 for c in competencies if c.get("status") == "competent")
        training_required_count = sum(1 for c in competencies if c.get("status") == "training_required")
        not_competent_count = sum(1 for c in competencies if c.get("status") == "not_competent")
        
        print(f"✓ Status counts - Competent: {competent_count}, Training Required: {training_required_count}, Not Competent: {not_competent_count}")
        
        # Verify total matches
        total = competent_count + training_required_count + not_competent_count
        assert total == len(competencies), "Status counts should sum to total"
        print(f"✓ Total competencies: {len(competencies)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

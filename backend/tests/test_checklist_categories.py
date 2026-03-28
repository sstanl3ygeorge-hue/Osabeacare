"""
Test checklist category ordering and compliance requirements API
Tests the new category structure: 1_Legal_Safety, 2_Core_Training, 3_Role_Readiness, etc.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestChecklistCategories:
    """Tests for checklist category ordering and compliance requirements"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        # Login to get token
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get employee OCS-0002
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert response.status_code == 200
        employees = response.json()
        self.employee = next((e for e in employees if e["employee_code"] == "OCS-0002"), None)
        assert self.employee is not None, "Employee OCS-0002 not found"
    
    def test_compliance_requirements_endpoint_returns_categories(self):
        """Test that compliance requirements endpoint returns correct categories"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee['id']}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check that requirements exist
        assert "requirements" in data
        assert len(data["requirements"]) > 0
        
        # Get unique categories
        categories = set(req["category"] for req in data["requirements"])
        
        # Verify expected categories exist
        expected_categories = {
            "1_Legal_Safety",
            "2_Core_Training", 
            "3_Role_Readiness",
            "4_Employment",
            "5_Agreements",
            "6_Admin"
        }
        
        for expected in expected_categories:
            assert expected in categories, f"Category {expected} not found in requirements"
    
    def test_legal_safety_category_has_correct_items(self):
        """Test that Legal & Safety category has the expected items"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee['id']}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        legal_safety_items = [
            req for req in data["requirements"] 
            if req["category"] == "1_Legal_Safety"
        ]
        
        # Should have at least 5 items: RTW docs, RTW check, ID docs, DBS cert, DBS check
        assert len(legal_safety_items) >= 5, f"Expected at least 5 Legal & Safety items, got {len(legal_safety_items)}"
        
        # Check for specific items
        item_ids = [item["id"] for item in legal_safety_items]
        assert "right_to_work_documents" in item_ids
        assert "right_to_work_check" in item_ids
        assert "identity_documents" in item_ids
        assert "dbs_certificate" in item_ids
        assert "dbs_check" in item_ids
    
    def test_core_training_category_has_correct_items(self):
        """Test that Core Training category has the expected training items"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee['id']}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        training_items = [
            req for req in data["requirements"] 
            if req["category"] == "2_Core_Training"
        ]
        
        # Should have at least 6 training items
        assert len(training_items) >= 6, f"Expected at least 6 Core Training items, got {len(training_items)}"
        
        # Check for specific training items
        item_ids = [item["id"] for item in training_items]
        assert "safeguarding" in item_ids
        assert "manual_handling" in item_ids
        assert "infection_control" in item_ids
        assert "bls" in item_ids
        assert "fire_safety" in item_ids
        assert "health_safety" in item_ids
    
    def test_role_readiness_category_has_correct_items(self):
        """Test that Role Readiness category has the expected items"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee['id']}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        role_readiness_items = [
            req for req in data["requirements"] 
            if req["category"] == "3_Role_Readiness"
        ]
        
        # Should have at least 3 items
        assert len(role_readiness_items) >= 3, f"Expected at least 3 Role Readiness items, got {len(role_readiness_items)}"
        
        # Check for specific items
        item_ids = [item["id"] for item in role_readiness_items]
        assert "health_screening" in item_ids
        assert "induction" in item_ids
        assert "interview_record" in item_ids
    
    def test_requirements_have_status_fields(self):
        """Test that each requirement has the necessary status fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee['id']}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for req in data["requirements"]:
            # Check required fields exist
            assert "id" in req, f"Requirement missing 'id' field"
            assert "name" in req, f"Requirement missing 'name' field"
            assert "category" in req, f"Requirement missing 'category' field"
            assert "type" in req, f"Requirement missing 'type' field"
            assert "has_evidence" in req, f"Requirement missing 'has_evidence' field"
    
    def test_employee_compliance_endpoint(self):
        """Test the employee compliance summary endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee['id']}/compliance",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "employee_id" in data
        assert "compliance" in data
        assert "items" in data["compliance"]
        assert "total_items" in data["compliance"]
        assert "complete_count" in data["compliance"]
        assert "completion_percentage" in data["compliance"]


class TestStatusBadges:
    """Tests for status badge logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        employees = response.json()
        self.employee = next((e for e in employees if e["employee_code"] == "OCS-0002"), None)
    
    def test_requirements_without_evidence_show_still_needed(self):
        """Test that requirements without evidence have has_evidence=False"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee['id']}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # For a new employee, most items should not have evidence
        items_without_evidence = [
            req for req in data["requirements"]
            if not req.get("has_evidence", False)
        ]
        
        # Should have many items without evidence for a new employee
        assert len(items_without_evidence) > 0, "Expected some items without evidence"
        
        # Each item without evidence should have has_evidence=False
        for item in items_without_evidence:
            assert item["has_evidence"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

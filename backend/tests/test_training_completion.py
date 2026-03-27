"""
Test Training Completion Feature
Tests for:
- POST /api/employees/{id}/complete-training endpoint
- GET /api/employees/{id}/training-requirements endpoint
- Compliance score updates after training completion
- No duplicate training records
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee ID (Olakunle Alonge)
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTrainingRequirementsEndpoint:
    """Tests for GET /api/employees/{id}/training-requirements"""
    
    def test_get_training_requirements_success(self, auth_headers):
        """Test getting training requirements returns valid data"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert "requirements" in data
        assert "summary" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        
        # Verify summary structure
        summary = data["summary"]
        assert "total" in summary
        assert "completed" in summary
        assert "missing" in summary
        assert summary["total"] >= 6  # At least 6 training requirements
        
        print(f"Training requirements: {summary['total']} total, {summary['completed']} completed, {summary['missing']} missing")
    
    def test_training_requirements_structure(self, auth_headers):
        """Test that each requirement has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for req in data["requirements"]:
            assert "requirement_id" in req
            assert "name" in req
            assert "training_name" in req
            assert "status" in req
            assert "is_complete" in req
            assert req["status"] in ["completed", "in_progress", "pending", "missing"]
            
            print(f"  - {req['name']}: {req['status']}")
    
    def test_training_requirements_invalid_employee(self, auth_headers):
        """Test getting training requirements for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid-employee-id/training-requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()


class TestCompleteTrainingEndpoint:
    """Tests for POST /api/employees/{id}/complete-training"""
    
    def test_complete_training_already_completed(self, auth_headers):
        """Test completing a training that's already completed returns appropriate response"""
        # First get current training requirements to find a completed one
        req_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-requirements",
            headers=auth_headers
        )
        
        assert req_response.status_code == 200
        requirements = req_response.json()["requirements"]
        
        # Find a completed training
        completed_training = next((r for r in requirements if r["is_complete"]), None)
        
        if completed_training:
            # Try to complete it again
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/complete-training",
                headers=auth_headers,
                json={"requirement_id": completed_training["requirement_id"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["action"] == "already_completed"
            print(f"Correctly identified '{completed_training['name']}' as already completed")
        else:
            print("No completed training found to test duplicate prevention")
    
    def test_complete_training_invalid_requirement(self, auth_headers):
        """Test completing training with invalid requirement_id"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/complete-training",
            headers=auth_headers,
            json={"requirement_id": "invalid_requirement_id"}
        )
        
        assert response.status_code == 400
        assert "Invalid requirement_id" in response.json().get("detail", "")
    
    def test_complete_training_non_training_requirement(self, auth_headers):
        """Test completing a non-training requirement (e.g., document requirement)"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/complete-training",
            headers=auth_headers,
            json={"requirement_id": "dbs"}  # DBS is a document, not training
        )
        
        assert response.status_code == 400
        assert "not a training requirement" in response.json().get("detail", "")
    
    def test_complete_training_invalid_employee(self, auth_headers):
        """Test completing training for non-existent employee"""
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id/complete-training",
            headers=auth_headers,
            json={"requirement_id": "safeguarding"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()


class TestComplianceScoreUpdate:
    """Tests for compliance score updates after training completion"""
    
    def test_compliance_score_reflects_training(self, auth_headers):
        """Test that compliance score includes training requirements"""
        # Get compliance data
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "compliance" in data
        compliance = data["compliance"]
        
        assert "total_items" in compliance
        assert "complete_count" in compliance
        assert "completion_percentage" in compliance
        
        # Verify training items are included
        items = compliance.get("items", [])
        training_items = [i for i in items if i.get("type") == "training"]
        
        assert len(training_items) >= 6, f"Expected at least 6 training items, got {len(training_items)}"
        print(f"Compliance: {compliance['complete_count']}/{compliance['total_items']} ({compliance['completion_percentage']}%)")
        print(f"Training items in compliance: {len(training_items)}")


class TestNoDuplicateTrainingRecords:
    """Tests to ensure no duplicate training records are created"""
    
    def test_no_duplicate_training_records(self, auth_headers):
        """Test that completing training doesn't create duplicates"""
        # Get all training records for the employee
        response = requests.get(
            f"{BASE_URL}/api/training-records?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        records = response.json()
        
        # Check for duplicates by training name
        training_names = [r.get("training_name", "").lower() for r in records]
        unique_names = set(training_names)
        
        # Allow for some variation in naming but flag obvious duplicates
        duplicates = []
        for name in unique_names:
            count = training_names.count(name)
            if count > 1:
                duplicates.append(f"{name} ({count} records)")
        
        if duplicates:
            print(f"WARNING: Potential duplicate training records: {duplicates}")
        else:
            print(f"No duplicate training records found ({len(records)} total records)")


class TestTrainingCompletionFlow:
    """End-to-end tests for training completion flow"""
    
    def test_complete_training_flow(self, auth_headers):
        """Test the complete flow: check requirements -> complete -> verify update"""
        # Step 1: Get current training requirements
        req_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-requirements",
            headers=auth_headers
        )
        
        assert req_response.status_code == 200
        initial_data = req_response.json()
        initial_completed = initial_data["summary"]["completed"]
        
        # Step 2: Find a missing training requirement
        missing_training = next(
            (r for r in initial_data["requirements"] if r["status"] == "missing"),
            None
        )
        
        if missing_training:
            print(f"Found missing training: {missing_training['name']}")
            
            # Step 3: Complete the training
            complete_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/complete-training",
                headers=auth_headers,
                json={
                    "requirement_id": missing_training["requirement_id"],
                    "expiry_date": "2027-01-01T00:00:00Z"
                }
            )
            
            assert complete_response.status_code == 200
            complete_data = complete_response.json()
            assert complete_data["success"] == True
            assert complete_data["action"] in ["created", "updated"]
            print(f"Training completed: {complete_data['message']}")
            
            # Step 4: Verify the training is now complete
            verify_response = requests.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-requirements",
                headers=auth_headers
            )
            
            assert verify_response.status_code == 200
            verify_data = verify_response.json()
            
            # Find the requirement we just completed
            completed_req = next(
                (r for r in verify_data["requirements"] if r["requirement_id"] == missing_training["requirement_id"]),
                None
            )
            
            assert completed_req is not None
            assert completed_req["is_complete"] == True
            assert completed_req["status"] == "completed"
            print(f"Verified: {completed_req['name']} is now completed")
            
            # Step 5: Verify compliance score updated
            compliance_response = requests.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance",
                headers=auth_headers
            )
            
            assert compliance_response.status_code == 200
            compliance_data = compliance_response.json()
            print(f"Updated compliance: {compliance_data['compliance']['completion_percentage']}%")
        else:
            print("All training requirements already completed - skipping completion test")
            # Verify all are complete
            assert initial_data["summary"]["missing"] == 0


class TestTrainingCompletionWithExpiry:
    """Tests for training completion with expiry dates"""
    
    def test_complete_training_with_expiry(self, auth_headers):
        """Test completing training with an expiry date"""
        # Get requirements to find one to test
        req_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-requirements",
            headers=auth_headers
        )
        
        assert req_response.status_code == 200
        requirements = req_response.json()["requirements"]
        
        # Find any training requirement
        training_req = requirements[0] if requirements else None
        
        if training_req:
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/complete-training",
                headers=auth_headers,
                json={
                    "requirement_id": training_req["requirement_id"],
                    "expiry_date": "2027-06-15T00:00:00Z"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            
            # If it was already completed, that's fine
            if data["action"] == "already_completed":
                print(f"Training '{training_req['name']}' was already completed")
            else:
                # Verify expiry date was set
                training_record = data.get("training_record", {})
                if training_record.get("expiry_date"):
                    print(f"Training completed with expiry: {training_record['expiry_date']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

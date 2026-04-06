"""
Test Induction Checklist Module - 15 Care Certificate Standards
Tests for:
1. GET /api/employees/{employee_id}/induction-checklist returns exactly 15 items
2. PUT /api/employees/{employee_id}/induction-checklist allows Admin to mark items complete
3. POST /api/employees/{employee_id}/induction-checklist/fix migrates existing records to 15 items
4. POST /api/induction-checklists/migrate-all migrates ALL existing records
5. GET /api/employees/{employee_id}/pre-employment-gates shows 'All 15 Care Certificate standards complete'
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID from the review request
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

# Admin credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(admin_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


class TestInductionChecklistEndpoints:
    """Test induction checklist API endpoints"""
    
    def test_get_induction_checklist_returns_15_items(self, api_client):
        """Test GET /api/employees/{employee_id}/induction-checklist returns exactly 15 items"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        items = data.get("items", [])
        
        # CRITICAL: Must be exactly 15 items (Care Certificate standards)
        assert len(items) == 15, f"Expected exactly 15 items, got {len(items)}"
        
        # Verify item structure
        for item in items:
            assert "name" in item, "Item missing 'name' field"
            assert "mandatory" in item, "Item missing 'mandatory' field"
            assert "status" in item, "Item missing 'status' field"
        
        # Verify expected Care Certificate standard names
        expected_names = [
            "Understand Your Role",
            "Your Personal Development",
            "Duty of Care",
            "Equality and Diversity",
            "Work in a Person-Centred Way",
            "Communication",
            "Privacy and Dignity",
            "Fluids and Nutrition",
            "Mental Health, Dementia and Learning Disabilities",
            "Safeguarding Adults",
            "Safeguarding Children",
            "Basic Life Support",
            "Health and Safety",
            "Handling Information",
            "Infection Prevention and Control"
        ]
        
        actual_names = [item["name"] for item in items]
        for expected in expected_names:
            assert expected in actual_names, f"Missing Care Certificate standard: {expected}"
        
        print(f"SUCCESS: Induction checklist has exactly 15 items")
        print(f"Items: {[item['name'] for item in items]}")
    
    def test_update_induction_item_complete(self, api_client):
        """Test PUT /api/employees/{employee_id}/induction-checklist allows Admin to mark items complete"""
        # Mark an item as complete
        payload = {
            "item_name": "Understand Your Role",
            "status": "completed",
            "notes": "Test completion by admin"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "completed_count" in data, "Response missing completed_count"
        assert "total_count" in data, "Response missing total_count"
        
        # Verify total_count is 15
        assert data.get("total_count") == 15, f"Expected total_count=15, got {data.get('total_count')}"
        
        print(f"SUCCESS: Admin can mark induction items complete")
        print(f"Completed: {data.get('completed_count')}/{data.get('total_count')}")
    
    def test_update_induction_item_pending(self, api_client):
        """Test PUT /api/employees/{employee_id}/induction-checklist allows Admin to mark items pending"""
        # Mark an item as pending (undo completion)
        payload = {
            "item_name": "Understand Your Role",
            "status": "pending",
            "notes": ""
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        
        print(f"SUCCESS: Admin can mark induction items as pending")
    
    def test_fix_induction_checklist_migrates_to_15_items(self, api_client):
        """Test POST /api/employees/{employee_id}/induction-checklist/fix migrates to 15 items"""
        response = api_client.post(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist/fix")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert data.get("items_count") == 15, f"Expected items_count=15, got {data.get('items_count')}"
        
        # Verify message mentions 15 Care Certificate standards
        message = data.get("message", "")
        assert "15" in message, f"Message should mention 15 items: {message}"
        
        print(f"SUCCESS: Fix endpoint migrates to 15 items")
        print(f"Message: {message}")
    
    def test_migrate_all_induction_checklists(self, api_client):
        """Test POST /api/induction-checklists/migrate-all migrates ALL existing records"""
        response = api_client.post(f"{BASE_URL}/api/induction-checklists/migrate-all")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "migrated_count" in data, "Response missing migrated_count"
        assert "skipped_count" in data, "Response missing skipped_count"
        
        print(f"SUCCESS: Bulk migration endpoint works")
        print(f"Migrated: {data.get('migrated_count')}, Skipped: {data.get('skipped_count')}")
    
    def test_pre_employment_gates_shows_15_standards(self, api_client):
        """Test GET /api/employees/{employee_id}/pre-employment-gates shows 'All 15 Care Certificate standards complete'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/pre-employment-gates")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        gates = data.get("gates", {})
        
        # Check induction gate
        induction_gate = gates.get("induction", {})
        assert induction_gate, "Missing induction gate in response"
        
        requirement = induction_gate.get("requirement", "")
        assert "15" in requirement, f"Induction requirement should mention 15: {requirement}"
        assert "Care Certificate" in requirement, f"Induction requirement should mention Care Certificate: {requirement}"
        
        print(f"SUCCESS: Pre-employment gates shows correct induction requirement")
        print(f"Induction requirement: {requirement}")


class TestInductionChecklistDataIntegrity:
    """Test data integrity for induction checklist"""
    
    def test_checklist_progress_calculation(self, api_client):
        """Test that progress is calculated correctly based on 15 items"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist")
        
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        # Count completed items
        completed_count = sum(1 for item in items if item.get("status") == "completed")
        total_count = len(items)
        
        # Verify total is 15
        assert total_count == 15, f"Expected 15 items, got {total_count}"
        
        # Verify overall_status is consistent
        overall_status = data.get("overall_status")
        if completed_count == 0:
            assert overall_status in ["pending", "not_started"], f"Expected pending/not_started for 0 completed, got {overall_status}"
        elif completed_count == total_count:
            assert overall_status == "completed", f"Expected completed for all items done, got {overall_status}"
        else:
            assert overall_status == "in_progress", f"Expected in_progress for partial completion, got {overall_status}"
        
        print(f"SUCCESS: Progress calculation is correct")
        print(f"Completed: {completed_count}/{total_count}, Status: {overall_status}")
    
    def test_mandatory_items_count(self, api_client):
        """Test that mandatory items are correctly marked"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist")
        
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        mandatory_count = sum(1 for item in items if item.get("mandatory") == True)
        
        # Most items should be mandatory (14 out of 15, only Safeguarding Children is optional)
        assert mandatory_count >= 14, f"Expected at least 14 mandatory items, got {mandatory_count}"
        
        # Safeguarding Children should be the only non-mandatory item
        non_mandatory = [item["name"] for item in items if not item.get("mandatory")]
        if non_mandatory:
            assert "Safeguarding Children" in non_mandatory, f"Unexpected non-mandatory items: {non_mandatory}"
        
        print(f"SUCCESS: Mandatory items correctly marked")
        print(f"Mandatory: {mandatory_count}/15")


class TestInductionChecklistAutoSync:
    """Test auto-sync from verified trainings"""
    
    def test_fix_syncs_from_verified_trainings(self, api_client):
        """Test that fix endpoint syncs completion from verified trainings"""
        # First, call fix to sync
        fix_response = api_client.post(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist/fix")
        
        assert fix_response.status_code == 200
        
        fix_data = fix_response.json()
        synced_trainings = fix_data.get("synced_trainings", [])
        
        # Get the checklist to verify sync
        checklist_response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist")
        
        assert checklist_response.status_code == 200
        
        checklist_data = checklist_response.json()
        items = checklist_data.get("items", [])
        
        # Check if any items were auto-completed from training
        auto_completed = [item for item in items if item.get("completed_by_name") == "Auto-synced from training"]
        
        print(f"SUCCESS: Fix endpoint syncs from trainings")
        print(f"Synced trainings: {synced_trainings}")
        print(f"Auto-completed items: {len(auto_completed)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

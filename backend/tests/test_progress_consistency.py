"""
Test Progress Calculation Consistency - P0 Fix Verification
Tests that Admin (unified-progress) and Worker (worker/dashboard) views show identical progress.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
WORKER_EMAIL = "otunbakunlelonge85@gmail.com"
WORKER_PASSWORD = "Welcome123!"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def worker_token():
    """Get worker authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/worker/login",
        json={"email": WORKER_EMAIL, "password": WORKER_PASSWORD}
    )
    assert response.status_code == 200, f"Worker login failed: {response.text}"
    return response.json().get("token")


class TestProgressConsistency:
    """Test that progress calculations are consistent across Admin and Worker views"""
    
    def test_unified_progress_endpoint_returns_correct_values(self, admin_token):
        """Test GET /api/employees/{id}/unified-progress returns expected 66% / 16/24"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Unified progress failed: {response.text}"
        
        data = response.json()
        
        # Verify expected values
        assert data["overall_percentage"] == 66, f"Expected 66%, got {data['overall_percentage']}%"
        assert data["completed_requirements"] == 16, f"Expected 16 completed, got {data['completed_requirements']}"
        assert data["total_requirements"] == 24, f"Expected 24 total, got {data['total_requirements']}"
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        
        print(f"✓ Unified progress: {data['overall_percentage']}% ({data['completed_requirements']}/{data['total_requirements']})")
    
    def test_worker_dashboard_returns_correct_values(self, worker_token):
        """Test GET /api/worker/dashboard returns expected 66% / 16/24"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200, f"Worker dashboard failed: {response.text}"
        
        data = response.json()
        progress = data.get("progress", {})
        
        # Verify expected values
        assert progress.get("percentage") == 66, f"Expected 66%, got {progress.get('percentage')}%"
        assert progress.get("completed") == 16, f"Expected 16 completed, got {progress.get('completed')}"
        assert progress.get("required") == 24, f"Expected 24 total, got {progress.get('required')}"
        
        print(f"✓ Worker dashboard: {progress['percentage']}% ({progress['completed']}/{progress['required']})")
    
    def test_admin_and_worker_progress_match(self, admin_token, worker_token):
        """P0 FIX: Verify Admin and Worker views show IDENTICAL progress"""
        # Get admin view (unified-progress)
        admin_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 200
        admin_data = admin_response.json()
        
        # Get worker view (worker/dashboard)
        worker_response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert worker_response.status_code == 200
        worker_data = worker_response.json()
        worker_progress = worker_data.get("progress", {})
        
        # Compare values - MUST be identical
        admin_pct = admin_data["overall_percentage"]
        worker_pct = worker_progress.get("percentage")
        assert admin_pct == worker_pct, f"Progress mismatch! Admin: {admin_pct}%, Worker: {worker_pct}%"
        
        admin_completed = admin_data["completed_requirements"]
        worker_completed = worker_progress.get("completed")
        assert admin_completed == worker_completed, f"Completed mismatch! Admin: {admin_completed}, Worker: {worker_completed}"
        
        admin_total = admin_data["total_requirements"]
        worker_total = worker_progress.get("required")
        assert admin_total == worker_total, f"Total mismatch! Admin: {admin_total}, Worker: {worker_total}"
        
        print(f"✓ Admin and Worker progress MATCH: {admin_pct}% ({admin_completed}/{admin_total})")
    
    def test_employee_data_in_worker_dashboard(self, worker_token):
        """Verify worker dashboard returns correct employee info"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        employee = data.get("employee", {})
        
        # Verify employee data
        assert employee.get("id") == TEST_EMPLOYEE_ID
        assert employee.get("name") == "Olakunle Alonge"
        assert employee.get("email") == WORKER_EMAIL
        
        print(f"✓ Employee data correct: {employee.get('name')} ({employee.get('id')})")
    
    def test_unified_progress_has_categories(self, admin_token):
        """Verify unified-progress returns category breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        categories = data.get("categories", {})
        
        # Verify categories exist
        assert "documents" in categories
        assert "forms" in categories
        assert "training" in categories
        assert "references" in categories
        assert "agreements" in categories
        assert "induction" in categories
        
        print(f"✓ Categories present: {list(categories.keys())}")
    
    def test_unified_progress_has_blockers(self, admin_token):
        """Verify unified-progress returns blockers list"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        blockers = data.get("blockers", [])
        
        # Blockers should be a list
        assert isinstance(blockers, list)
        
        print(f"✓ Blockers: {len(blockers)} items")


class TestWorkerDashboardDetails:
    """Test worker dashboard returns all required data"""
    
    def test_worker_dashboard_has_documents(self, worker_token):
        """Verify worker dashboard returns document status"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check document sections exist
        assert "missing_documents" in data
        assert "completed_documents" in data
        
        print(f"✓ Documents: {len(data.get('completed_documents', []))} completed, {len(data.get('missing_documents', []))} missing")
    
    def test_worker_dashboard_has_trainings(self, worker_token):
        """Verify worker dashboard returns training status"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check training sections exist
        assert "completed_trainings" in data
        assert "missing_trainings" in data
        assert "all_mandatory_trainings" in data
        
        print(f"✓ Trainings: {len(data.get('completed_trainings', []))} completed")
    
    def test_worker_dashboard_has_forms(self, worker_token):
        """Verify worker dashboard returns form status"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check forms section exists
        assert "forms" in data
        forms = data.get("forms", [])
        assert len(forms) > 0, "Expected at least one form"
        
        # Verify form structure
        for form in forms:
            assert "id" in form
            assert "name" in form
            assert "status" in form
        
        print(f"✓ Forms: {len(forms)} forms available")
    
    def test_worker_dashboard_has_induction(self, worker_token):
        """Verify worker dashboard returns induction checklist"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check induction section exists
        assert "induction" in data
        induction = data.get("induction", {})
        
        assert "total" in induction
        assert "completed" in induction
        assert "items" in induction
        
        print(f"✓ Induction: {induction.get('completed')}/{induction.get('total')} completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

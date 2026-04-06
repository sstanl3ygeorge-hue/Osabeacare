"""
Test Worker Dashboard and Admin Progress Sync
==============================================
Verifies:
1. Worker Dashboard API /api/worker/dashboard returns 'agreements' array
2. Worker Dashboard progress percentage matches Admin unified-progress endpoint
3. Admin /api/employees/{id}/unified-progress endpoint works without 500 error
4. Progress percentage is consistent between Worker and Admin views

Test Employee: d88335f6-1b18-435a-8086-28af4a583f77 (Olakunle Alonge)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
WORKER_EMAIL = "otunbakunlelonge85@gmail.com"
WORKER_PASSWORD = "Welcome123!"
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestWorkerAdminProgressSync:
    """Test Worker Dashboard and Admin Progress Sync"""
    
    @pytest.fixture(scope="class")
    def worker_token(self):
        """Get worker authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": WORKER_EMAIL, "password": WORKER_PASSWORD}
        )
        assert response.status_code == 200, f"Worker login failed: {response.text}"
        data = response.json()
        assert "token" in data, f"No token in response: {data}"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, f"No token in response: {data}"
        return data["token"]
    
    def test_worker_login_success(self, worker_token):
        """Test worker can login successfully"""
        assert worker_token is not None
        assert len(worker_token) > 0
        print(f"✓ Worker login successful, token length: {len(worker_token)}")
    
    def test_admin_login_success(self, admin_token):
        """Test admin can login successfully"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful, token length: {len(admin_token)}")
    
    def test_worker_dashboard_returns_agreements(self, worker_token):
        """Test Worker Dashboard API returns 'agreements' array"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200, f"Worker dashboard failed: {response.text}"
        data = response.json()
        
        # Verify agreements field exists
        assert "agreements" in data, f"'agreements' field missing from worker dashboard response. Keys: {list(data.keys())}"
        
        agreements = data["agreements"]
        assert isinstance(agreements, list), f"'agreements' should be a list, got {type(agreements)}"
        
        # Verify agreements structure
        print(f"✓ Worker dashboard returns 'agreements' array with {len(agreements)} items")
        
        for agreement in agreements:
            assert "id" in agreement, f"Agreement missing 'id': {agreement}"
            assert "name" in agreement, f"Agreement missing 'name': {agreement}"
            assert "signed" in agreement, f"Agreement missing 'signed': {agreement}"
            assert "verified" in agreement, f"Agreement missing 'verified': {agreement}"
            print(f"  - {agreement['name']}: signed={agreement['signed']}, verified={agreement['verified']}")
        
        return data
    
    def test_worker_dashboard_agreements_contains_contract_and_handbook(self, worker_token):
        """Test Worker Dashboard agreements contains Contract Acceptance and Employee Handbook"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        agreements = data.get("agreements", [])
        agreement_ids = [a.get("id") for a in agreements]
        agreement_names = [a.get("name") for a in agreements]
        
        # Check for Contract Acceptance
        has_contract = any("contract" in (a.get("id") or "").lower() or "contract" in (a.get("name") or "").lower() for a in agreements)
        assert has_contract, f"Contract Acceptance not found in agreements. IDs: {agreement_ids}, Names: {agreement_names}"
        print("✓ Contract Acceptance found in agreements")
        
        # Check for Employee Handbook
        has_handbook = any("handbook" in (a.get("id") or "").lower() or "handbook" in (a.get("name") or "").lower() for a in agreements)
        assert has_handbook, f"Employee Handbook not found in agreements. IDs: {agreement_ids}, Names: {agreement_names}"
        print("✓ Employee Handbook found in agreements")
    
    def test_admin_unified_progress_no_500_error(self, admin_token):
        """Test Admin unified-progress endpoint works without 500 error"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should NOT return 500
        assert response.status_code != 500, f"Admin unified-progress returned 500 error: {response.text}"
        
        # Should return 200 or 404 (if employee not found)
        assert response.status_code in [200, 404], f"Unexpected status code: {response.status_code}, response: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "overall_percentage" in data, f"Missing 'overall_percentage' in response: {data.keys()}"
            print(f"✓ Admin unified-progress endpoint works, progress: {data['overall_percentage']}%")
            return data
        else:
            print(f"⚠ Employee {TEST_EMPLOYEE_ID} not found (404)")
            pytest.skip(f"Test employee {TEST_EMPLOYEE_ID} not found")
    
    def test_progress_percentage_consistency(self, worker_token, admin_token):
        """Test progress percentage is consistent between Worker and Admin views"""
        # Get worker dashboard progress
        worker_response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert worker_response.status_code == 200, f"Worker dashboard failed: {worker_response.text}"
        worker_data = worker_response.json()
        
        worker_progress = worker_data.get("progress", {}).get("percentage", -1)
        worker_employee_id = worker_data.get("employee", {}).get("id")
        
        print(f"Worker Dashboard Progress: {worker_progress}%")
        print(f"Worker Employee ID: {worker_employee_id}")
        
        # Get admin unified-progress for the same employee
        admin_response = requests.get(
            f"{BASE_URL}/api/employees/{worker_employee_id}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if admin_response.status_code == 404:
            pytest.skip(f"Employee {worker_employee_id} not found in admin view")
        
        assert admin_response.status_code == 200, f"Admin unified-progress failed: {admin_response.text}"
        admin_data = admin_response.json()
        
        admin_progress = admin_data.get("overall_percentage", -1)
        print(f"Admin Unified Progress: {admin_progress}%")
        
        # Progress should match (both use unified_compliance_engine)
        assert worker_progress == admin_progress, f"Progress mismatch! Worker: {worker_progress}%, Admin: {admin_progress}%"
        print(f"✓ Progress percentage is consistent: {worker_progress}% (Worker) == {admin_progress}% (Admin)")
    
    def test_worker_dashboard_has_all_required_fields(self, worker_token):
        """Test Worker Dashboard returns all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required top-level fields
        required_fields = [
            "employee",
            "progress",
            "agreements",  # P0 FIX: Must include agreements
            "missing_documents",
            "completed_documents",
            "missing_trainings",
            "completed_trainings",
            "contract_signed",
            "references",
            "induction"
        ]
        
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from worker dashboard. Keys: {list(data.keys())}"
            print(f"✓ Field '{field}' present")
        
        # Verify progress structure
        progress = data.get("progress", {})
        assert "percentage" in progress, f"'percentage' missing from progress: {progress}"
        assert "completed" in progress, f"'completed' missing from progress: {progress}"
        assert "required" in progress, f"'required' missing from progress: {progress}"
        print(f"✓ Progress structure valid: {progress['percentage']}% ({progress['completed']}/{progress['required']})")
    
    def test_admin_unified_progress_structure(self, admin_token):
        """Test Admin unified-progress returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 404:
            pytest.skip(f"Test employee {TEST_EMPLOYEE_ID} not found")
        
        assert response.status_code == 200, f"Admin unified-progress failed: {response.text}"
        data = response.json()
        
        # Required fields
        required_fields = [
            "employee_id",
            "overall_percentage",
            "completed_requirements",
            "total_requirements",
            "categories",
            "blockers",
            "is_work_ready",
            "can_promote"
        ]
        
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from unified-progress. Keys: {list(data.keys())}"
            print(f"✓ Field '{field}' present")
        
        # Verify categories structure
        categories = data.get("categories", {})
        expected_categories = ["documents", "forms", "training", "references", "agreements", "induction"]
        for cat in expected_categories:
            assert cat in categories, f"Category '{cat}' missing from categories: {list(categories.keys())}"
            print(f"✓ Category '{cat}' present: {categories[cat]}")


class TestUnifiedComplianceEngineIntegrity:
    """Test unified compliance engine doesn't throw errors"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json().get("token")
    
    def test_unified_progress_handles_missing_ref_doc(self, admin_token):
        """Test unified-progress handles missing ref_doc gracefully (no NoneType error)"""
        # This tests the fix for the NoneType error in unified_compliance_engine.py
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should NOT return 500 (which would indicate NoneType error)
        assert response.status_code != 500, f"Got 500 error - likely NoneType issue: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            # Verify references category exists
            categories = data.get("categories", {})
            assert "references" in categories, f"References category missing: {categories.keys()}"
            print(f"✓ References category: {categories['references']}")
        
        print("✓ Unified progress handles ref_doc gracefully (no 500 error)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

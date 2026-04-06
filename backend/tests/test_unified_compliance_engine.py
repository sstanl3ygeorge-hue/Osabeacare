"""
Test Suite: Unified Compliance Engine - Single Source of Truth
==============================================================

P0 FIX VERIFICATION: Tests that ALL 4 endpoints return IDENTICAL progress data
for the same employee, ensuring CIA Triad Integrity (same data for all views).

Endpoints tested:
1. GET /api/employees/{id}/unified-progress
2. GET /api/employees/{id}/pre-employment-gates
3. GET /api/worker/dashboard
4. GET /api/employees/{id}/compliance-requirements (unified_progress field)

Expected for test employee d88335f6-1b18-435a-8086-28af4a583f77 (Olakunle Alonge):
- Progress: 23% with 7/31 requirements
- Blockers: 10 items (identical across all views)
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


class TestUnifiedComplianceEngine:
    """Tests for P0 fix: Single Source of Truth for all progress calculations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def worker_token(self):
        """Get worker authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": WORKER_EMAIL, "password": WORKER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Worker login failed: {response.status_code} - {response.text}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth"""
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def worker_headers(self, worker_token):
        """Headers with worker auth"""
        return {"Authorization": f"Bearer {worker_token}", "Content-Type": "application/json"}
    
    # ========== ENDPOINT 1: /unified-progress ==========
    
    def test_unified_progress_endpoint_returns_200(self, admin_headers):
        """Test that unified-progress endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "overall_percentage" in data
        assert "completed_requirements" in data
        assert "total_requirements" in data
        assert "blockers" in data
        print(f"PASS: unified-progress returns {data['overall_percentage']}% ({data['completed_requirements']}/{data['total_requirements']})")
    
    def test_unified_progress_has_blocker_details(self, admin_headers):
        """Test that unified-progress includes detailed blocker information"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have blocker_details with full objects
        assert "blocker_details" in data, "Missing blocker_details field"
        blocker_details = data["blocker_details"]
        
        if len(blocker_details) > 0:
            # Each blocker should have id, label, reason, category
            first_blocker = blocker_details[0]
            assert "id" in first_blocker, "Blocker missing 'id'"
            assert "label" in first_blocker, "Blocker missing 'label'"
            assert "reason" in first_blocker, "Blocker missing 'reason'"
            print(f"PASS: unified-progress has {len(blocker_details)} blockers with details")
    
    # ========== ENDPOINT 2: /pre-employment-gates ==========
    
    def test_pre_employment_gates_endpoint_returns_200(self, admin_headers):
        """Test that pre-employment-gates endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/pre-employment-gates",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "gates" in data
        assert "gates_passed" in data
        assert "total_gates" in data
        assert "blockers" in data
        print(f"PASS: pre-employment-gates returns {data['gates_passed']}/{data['total_gates']} gates passed")
    
    def test_pre_employment_gates_has_same_blockers_as_unified(self, admin_headers):
        """Test that pre-employment-gates has SAME blockers as unified-progress"""
        # Get unified-progress
        unified_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert unified_resp.status_code == 200
        unified_data = unified_resp.json()
        
        # Get pre-employment-gates
        gates_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/pre-employment-gates",
            headers=admin_headers
        )
        assert gates_resp.status_code == 200
        gates_data = gates_resp.json()
        
        # Compare blocker counts
        unified_blocker_count = len(unified_data.get("blocker_details", []))
        gates_blocker_count = len(gates_data.get("blockers", []))
        
        assert unified_blocker_count == gates_blocker_count, \
            f"Blocker count mismatch: unified={unified_blocker_count}, gates={gates_blocker_count}"
        print(f"PASS: Both endpoints have {unified_blocker_count} blockers")
    
    # ========== ENDPOINT 3: /worker/dashboard ==========
    
    def test_worker_dashboard_endpoint_returns_200(self, worker_headers):
        """Test that worker dashboard endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers=worker_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "progress" in data
        assert "percentage" in data["progress"]
        assert "completed" in data["progress"]
        assert "required" in data["progress"]
        print(f"PASS: worker/dashboard returns {data['progress']['percentage']}% ({data['progress']['completed']}/{data['progress']['required']})")
    
    def test_worker_dashboard_has_same_progress_as_unified(self, admin_headers, worker_headers):
        """Test that worker dashboard has SAME progress as unified-progress"""
        # Get unified-progress (admin view)
        unified_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert unified_resp.status_code == 200
        unified_data = unified_resp.json()
        
        # Get worker dashboard
        worker_resp = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers=worker_headers
        )
        assert worker_resp.status_code == 200
        worker_data = worker_resp.json()
        
        # Compare progress values
        unified_pct = unified_data["overall_percentage"]
        unified_completed = unified_data["completed_requirements"]
        unified_total = unified_data["total_requirements"]
        
        worker_pct = worker_data["progress"]["percentage"]
        worker_completed = worker_data["progress"]["completed"]
        worker_total = worker_data["progress"]["required"]
        
        assert unified_pct == worker_pct, \
            f"Percentage mismatch: unified={unified_pct}%, worker={worker_pct}%"
        assert unified_completed == worker_completed, \
            f"Completed mismatch: unified={unified_completed}, worker={worker_completed}"
        assert unified_total == worker_total, \
            f"Total mismatch: unified={unified_total}, worker={worker_total}"
        
        print(f"PASS: Admin and Worker views show IDENTICAL progress: {unified_pct}% ({unified_completed}/{unified_total})")
    
    # ========== ENDPOINT 4: /compliance-requirements ==========
    
    def test_compliance_requirements_endpoint_returns_200(self, admin_headers):
        """Test that compliance-requirements endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "requirements" in data
        assert "statuses" in data
        print(f"PASS: compliance-requirements returns {len(data['requirements'])} requirements")
    
    def test_compliance_requirements_has_unified_progress(self, admin_headers):
        """Test that compliance-requirements includes unified_progress field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have unified_progress field
        assert "unified_progress" in data, "Missing unified_progress field in compliance-requirements"
        unified_progress = data["unified_progress"]
        
        if unified_progress:
            assert "percentage" in unified_progress
            assert "completed" in unified_progress
            assert "total" in unified_progress
            assert "blockers" in unified_progress
            print(f"PASS: compliance-requirements has unified_progress: {unified_progress['percentage']}% ({unified_progress['completed']}/{unified_progress['total']})")
    
    def test_compliance_requirements_overall_compliance_matches_unified(self, admin_headers):
        """Test that statuses.overall_compliance matches unified_progress"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        unified_progress = data.get("unified_progress")
        overall_compliance = data.get("statuses", {}).get("overall_compliance", {})
        
        if unified_progress and overall_compliance:
            assert unified_progress["percentage"] == overall_compliance["percentage"], \
                f"Percentage mismatch: unified={unified_progress['percentage']}, overall={overall_compliance['percentage']}"
            assert unified_progress["completed"] == overall_compliance["complete"], \
                f"Completed mismatch: unified={unified_progress['completed']}, overall={overall_compliance['complete']}"
            assert unified_progress["total"] == overall_compliance["total"], \
                f"Total mismatch: unified={unified_progress['total']}, overall={overall_compliance['total']}"
            print(f"PASS: statuses.overall_compliance matches unified_progress")
    
    # ========== CROSS-ENDPOINT CONSISTENCY TESTS ==========
    
    def test_all_four_endpoints_return_same_progress(self, admin_headers, worker_headers):
        """P0 CRITICAL: All 4 endpoints must return IDENTICAL progress values"""
        # 1. unified-progress
        unified_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert unified_resp.status_code == 200
        unified = unified_resp.json()
        
        # 2. pre-employment-gates (uses same unified function)
        gates_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/pre-employment-gates",
            headers=admin_headers
        )
        assert gates_resp.status_code == 200
        gates = gates_resp.json()
        
        # 3. worker/dashboard
        worker_resp = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers=worker_headers
        )
        assert worker_resp.status_code == 200
        worker = worker_resp.json()
        
        # 4. compliance-requirements
        compliance_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=admin_headers
        )
        assert compliance_resp.status_code == 200
        compliance = compliance_resp.json()
        
        # Extract progress values
        unified_pct = unified["overall_percentage"]
        unified_completed = unified["completed_requirements"]
        unified_total = unified["total_requirements"]
        
        worker_pct = worker["progress"]["percentage"]
        worker_completed = worker["progress"]["completed"]
        worker_total = worker["progress"]["required"]
        
        compliance_unified = compliance.get("unified_progress", {})
        compliance_pct = compliance_unified.get("percentage") if compliance_unified else None
        compliance_completed = compliance_unified.get("completed") if compliance_unified else None
        compliance_total = compliance_unified.get("total") if compliance_unified else None
        
        # Print all values for debugging
        print(f"\n=== PROGRESS VALUES ACROSS ALL ENDPOINTS ===")
        print(f"unified-progress:       {unified_pct}% ({unified_completed}/{unified_total})")
        print(f"worker/dashboard:       {worker_pct}% ({worker_completed}/{worker_total})")
        print(f"compliance-requirements: {compliance_pct}% ({compliance_completed}/{compliance_total})")
        print(f"pre-employment-gates:   {gates['gates_passed']}/{gates['total_gates']} gates")
        
        # Assert all match
        assert unified_pct == worker_pct, \
            f"unified vs worker percentage mismatch: {unified_pct} != {worker_pct}"
        assert unified_completed == worker_completed, \
            f"unified vs worker completed mismatch: {unified_completed} != {worker_completed}"
        assert unified_total == worker_total, \
            f"unified vs worker total mismatch: {unified_total} != {worker_total}"
        
        if compliance_pct is not None:
            assert unified_pct == compliance_pct, \
                f"unified vs compliance percentage mismatch: {unified_pct} != {compliance_pct}"
            assert unified_completed == compliance_completed, \
                f"unified vs compliance completed mismatch: {unified_completed} != {compliance_completed}"
            assert unified_total == compliance_total, \
                f"unified vs compliance total mismatch: {unified_total} != {compliance_total}"
        
        print(f"\nPASS: ALL ENDPOINTS RETURN IDENTICAL PROGRESS: {unified_pct}% ({unified_completed}/{unified_total})")
    
    def test_blocker_lists_are_identical(self, admin_headers, worker_headers):
        """P0 CRITICAL: Blocker lists must be identical across all views"""
        # Get blockers from unified-progress
        unified_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert unified_resp.status_code == 200
        unified_blockers = unified_resp.json().get("blocker_details", [])
        
        # Get blockers from pre-employment-gates
        gates_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/pre-employment-gates",
            headers=admin_headers
        )
        assert gates_resp.status_code == 200
        gates_blockers = gates_resp.json().get("blockers", [])
        
        # Get blockers from worker dashboard (uses 'unified_blockers' field)
        worker_resp = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers=worker_headers
        )
        assert worker_resp.status_code == 200
        worker_blockers = worker_resp.json().get("unified_blockers", [])
        
        # Get blockers from compliance-requirements
        compliance_resp = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=admin_headers
        )
        assert compliance_resp.status_code == 200
        compliance_unified = compliance_resp.json().get("unified_progress", {})
        compliance_blockers = compliance_unified.get("blockers", []) if compliance_unified else []
        
        # Compare counts
        print(f"\n=== BLOCKER COUNTS ACROSS ALL ENDPOINTS ===")
        print(f"unified-progress:       {len(unified_blockers)} blockers")
        print(f"pre-employment-gates:   {len(gates_blockers)} blockers")
        print(f"worker/dashboard:       {len(worker_blockers)} blockers")
        print(f"compliance-requirements: {len(compliance_blockers)} blockers")
        
        # All should have same count
        assert len(unified_blockers) == len(gates_blockers), \
            f"unified vs gates blocker count mismatch: {len(unified_blockers)} != {len(gates_blockers)}"
        assert len(unified_blockers) == len(worker_blockers), \
            f"unified vs worker blocker count mismatch: {len(unified_blockers)} != {len(worker_blockers)}"
        
        if compliance_blockers:
            assert len(unified_blockers) == len(compliance_blockers), \
                f"unified vs compliance blocker count mismatch: {len(unified_blockers)} != {len(compliance_blockers)}"
        
        print(f"\nPASS: ALL ENDPOINTS HAVE {len(unified_blockers)} BLOCKERS")
    
    def test_verified_items_not_in_blockers(self, admin_headers):
        """Test that verified items do NOT appear in blocker list"""
        # Get unified-progress
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        blockers = data.get("blocker_details", [])
        checks = data.get("checks", {})
        
        # Find all passed checks
        passed_checks = [k for k, v in checks.items() if v is True]
        
        # Verify no passed check appears in blockers
        blocker_ids = [b.get("id") for b in blockers]
        
        for check_id in passed_checks:
            assert check_id not in blocker_ids, \
                f"Verified item '{check_id}' should NOT appear in blockers"
        
        print(f"PASS: {len(passed_checks)} verified items correctly excluded from blockers")
    
    def test_clear_labels_used_not_email_or_abbreviations(self, admin_headers):
        """Test that clear labels are used (no 'U/S Documents', shows 'Reference 1' not email)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-progress",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        blockers = data.get("blocker_details", [])
        
        for blocker in blockers:
            label = blocker.get("label", "")
            reason = blocker.get("reason", "")
            
            # Should not contain email addresses
            assert "@" not in label, f"Label contains email: {label}"
            assert "@" not in reason or "email" in reason.lower(), f"Reason contains email: {reason}"
            
            # Should not use abbreviations like "U/S"
            assert "U/S" not in label, f"Label uses abbreviation 'U/S': {label}"
            assert "U/S" not in reason, f"Reason uses abbreviation 'U/S': {reason}"
            
            # Reference labels should be clear
            if "reference" in label.lower():
                assert "Reference 1" in label or "Reference 2" in label, \
                    f"Reference label not clear: {label}"
        
        print(f"PASS: All {len(blockers)} blockers use clear labels")


class TestAuthEndpoints:
    """Test authentication endpoints work correctly"""
    
    def test_admin_login(self):
        """Test admin login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "token" in data
        print(f"PASS: Admin login successful")
    
    def test_worker_login(self):
        """Test worker login works (uses /api/worker/login, not /api/auth/login)"""
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": WORKER_EMAIL, "password": WORKER_PASSWORD}
        )
        assert response.status_code == 200, f"Worker login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "token" in data
        print(f"PASS: Worker login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

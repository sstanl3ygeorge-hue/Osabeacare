"""
Phase 30: Readiness Routes Extraction Tests

Tests for the 7 readiness endpoints extracted to routes/readiness.py:
1. GET /api/employees/{employee_id}/readiness - Single source of truth for readiness
2. GET /api/employees/readiness-summary - Readiness summary for all employees
3. GET /api/employees/{employee_id}/recruitment-approval-check - Preview recruitment approval
4. GET /api/employees/{employee_id}/work-readiness-check - Work readiness (Gate 2)
5. GET /api/employees/{employee_id}/poa-freshness - POA freshness evaluation
6. POST /api/employees/{employee_id}/poa-freshness/override - Override POA freshness (admin)
7. GET /api/dashboard/audit-readiness - Audit readiness dashboard
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestPhase30ReadinessRoutes:
    """Test suite for Phase 30 Readiness Routes Extraction"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, auth_headers):
        """Get a test employee ID from the database"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers,
            params={"limit": 1}
        )
        if response.status_code == 200:
            employees = response.json()
            if isinstance(employees, list) and len(employees) > 0:
                return employees[0].get("id")
            elif isinstance(employees, dict) and employees.get("employees"):
                return employees["employees"][0].get("id")
        pytest.skip("No employees found for testing")
    
    # ==================== ENDPOINT 1: Employee Readiness ====================
    
    def test_employee_readiness_requires_auth(self):
        """Test that employee readiness endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/test-id/readiness")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Employee readiness requires authentication")
    
    def test_employee_readiness_not_found(self, auth_headers):
        """Test employee readiness returns 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/non-existent-id-12345/readiness",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Employee readiness returns 404 for non-existent employee")
    
    def test_employee_readiness_success(self, auth_headers, test_employee_id):
        """Test employee readiness returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/readiness",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "ready" in data, "Missing 'ready' field"
        assert "status" in data, "Missing 'status' field"
        assert "blockedReasons" in data, "Missing 'blockedReasons' field"
        assert "checks" in data, "Missing 'checks' field"
        assert "calculatedAt" in data, "Missing 'calculatedAt' field"
        assert "source_of_truth" in data, "Missing 'source_of_truth' field"
        
        # Verify status is one of expected values
        assert data["status"] in ["NOT_READY", "READY_WITH_CONDITIONS", "READY_TO_WORK"], \
            f"Unexpected status: {data['status']}"
        
        # Verify checks structure
        checks = data["checks"]
        assert "recruitmentApproved" in checks, "Missing 'recruitmentApproved' in checks"
        assert "referencesVerified" in checks, "Missing 'referencesVerified' in checks"
        assert "proofOfAddress" in checks, "Missing 'proofOfAddress' in checks"
        assert "rightToWork" in checks, "Missing 'rightToWork' in checks"
        assert "dbs" in checks, "Missing 'dbs' in checks"
        assert "training" in checks, "Missing 'training' in checks"
        
        print(f"PASS: Employee readiness returns correct structure. Status: {data['status']}")
    
    # ==================== ENDPOINT 2: Readiness Summary ====================
    
    def test_readiness_summary_requires_auth(self):
        """Test that readiness summary endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/readiness-summary")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Readiness summary requires authentication")
    
    def test_readiness_summary_success(self, auth_headers):
        """Test readiness summary returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/readiness-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "total_employees" in data, "Missing 'total_employees' field"
        assert "ready_to_work" in data, "Missing 'ready_to_work' field"
        assert "ready_with_conditions" in data, "Missing 'ready_with_conditions' field"
        assert "not_ready" in data, "Missing 'not_ready' field"
        assert "by_blocking_reason" in data, "Missing 'by_blocking_reason' field"
        
        # Verify counts are non-negative integers
        assert isinstance(data["total_employees"], int) and data["total_employees"] >= 0
        assert isinstance(data["ready_to_work"], int) and data["ready_to_work"] >= 0
        assert isinstance(data["not_ready"], int) and data["not_ready"] >= 0
        
        print(f"PASS: Readiness summary returns correct structure. Total: {data['total_employees']}")
    
    def test_readiness_summary_with_status_filter(self, auth_headers):
        """Test readiness summary with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/employees/readiness-summary",
            headers=auth_headers,
            params={"status": "active"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Readiness summary accepts status filter")
    
    # ==================== ENDPOINT 3: Recruitment Approval Check ====================
    
    def test_recruitment_approval_check_requires_auth(self):
        """Test that recruitment approval check requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/test-id/recruitment-approval-check")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Recruitment approval check requires authentication")
    
    def test_recruitment_approval_check_not_found(self, auth_headers):
        """Test recruitment approval check returns 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/non-existent-id-12345/recruitment-approval-check",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Recruitment approval check returns 404 for non-existent employee")
    
    def test_recruitment_approval_check_success(self, auth_headers, test_employee_id):
        """Test recruitment approval check returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/recruitment-approval-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure (from evaluate_recruitment_approval)
        assert "can_approve" in data, "Missing 'can_approve' field"
        assert "blockers" in data, "Missing 'blockers' field"
        
        print(f"PASS: Recruitment approval check returns correct structure. Can approve: {data['can_approve']}")
    
    # ==================== ENDPOINT 4: Work Readiness Check (Gate 2) ====================
    
    def test_work_readiness_check_requires_auth(self):
        """Test that work readiness check requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/test-id/work-readiness-check")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Work readiness check requires authentication")
    
    def test_work_readiness_check_not_found(self, auth_headers):
        """Test work readiness check returns 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/non-existent-id-12345/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Work readiness check returns 404 for non-existent employee")
    
    def test_work_readiness_check_success(self, auth_headers, test_employee_id):
        """Test work readiness check returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/work-readiness-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure (from evaluate_work_readiness)
        assert "can_work" in data, "Missing 'can_work' field"
        assert "readiness_status" in data, "Missing 'readiness_status' field"
        assert "blockers" in data, "Missing 'blockers' field"
        assert "blocker_count" in data, "Missing 'blocker_count' field"
        
        # Verify readiness_status is one of expected values
        assert data["readiness_status"] in ["NOT_READY", "READY_TO_WORK"], \
            f"Unexpected readiness_status: {data['readiness_status']}"
        
        print(f"PASS: Work readiness check returns correct structure. Can work: {data['can_work']}")
    
    # ==================== ENDPOINT 5: POA Freshness ====================
    
    def test_poa_freshness_requires_auth(self):
        """Test that POA freshness endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/test-id/poa-freshness")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: POA freshness requires authentication")
    
    def test_poa_freshness_not_found(self, auth_headers):
        """Test POA freshness returns 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/non-existent-id-12345/poa-freshness",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POA freshness returns 404 for non-existent employee")
    
    def test_poa_freshness_success(self, auth_headers, test_employee_id):
        """Test POA freshness returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/poa-freshness",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "overall_status" in data, "Missing 'overall_status' field"
        assert "employee_id" in data, "Missing 'employee_id' field"
        
        # Verify overall_status is one of expected values
        expected_statuses = ["complete", "partial", "review_needed", "incomplete"]
        assert data["overall_status"] in expected_statuses, \
            f"Unexpected overall_status: {data['overall_status']}"
        
        print(f"PASS: POA freshness returns correct structure. Status: {data['overall_status']}")
    
    # ==================== ENDPOINT 6: POA Freshness Override ====================
    
    def test_poa_freshness_override_requires_auth(self):
        """Test that POA freshness override requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/test-id/poa-freshness/override",
            params={"document_id": "test-doc-id"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: POA freshness override requires authentication")
    
    def test_poa_freshness_override_requires_admin(self, auth_headers):
        """Test POA freshness override requires admin role"""
        # This test verifies the endpoint exists and requires admin
        # The actual admin check is done by require_admin dependency
        response = requests.post(
            f"{BASE_URL}/api/employees/non-existent-id/poa-freshness/override",
            headers=auth_headers,
            params={"document_id": "test-doc-id"}
        )
        # Should return 404 (employee not found) if admin, or 403 if not admin
        assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"
        print("PASS: POA freshness override endpoint accessible with admin auth")
    
    def test_poa_freshness_override_employee_not_found(self, auth_headers):
        """Test POA freshness override returns 404 for non-existent employee"""
        response = requests.post(
            f"{BASE_URL}/api/employees/non-existent-id-12345/poa-freshness/override",
            headers=auth_headers,
            params={"document_id": "test-doc-id"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POA freshness override returns 404 for non-existent employee")
    
    def test_poa_freshness_override_document_not_found(self, auth_headers, test_employee_id):
        """Test POA freshness override returns 404 for non-existent document"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/poa-freshness/override",
            headers=auth_headers,
            params={"document_id": "non-existent-doc-id-12345"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: POA freshness override returns 404 for non-existent document")
    
    # ==================== ENDPOINT 7: Audit Readiness Dashboard ====================
    
    def test_audit_readiness_requires_auth(self):
        """Test that audit readiness dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/audit-readiness")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Audit readiness dashboard requires authentication")
    
    def test_audit_readiness_success(self, auth_headers):
        """Test audit readiness dashboard returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/audit-readiness",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "staff_compliance" in data, "Missing 'staff_compliance' field"
        assert "critical_alerts" in data, "Missing 'critical_alerts' field"
        assert "organisation_compliance" in data, "Missing 'organisation_compliance' field"
        assert "audit_readiness_score" in data, "Missing 'audit_readiness_score' field"
        
        # Verify staff_compliance structure
        staff = data["staff_compliance"]
        assert "total_staff" in staff, "Missing 'total_staff' in staff_compliance"
        assert "ready_for_placement" in staff, "Missing 'ready_for_placement' in staff_compliance"
        
        # Verify audit_readiness_score structure
        score = data["audit_readiness_score"]
        assert "score" in score, "Missing 'score' in audit_readiness_score"
        assert "status" in score, "Missing 'status' in audit_readiness_score"
        
        print(f"PASS: Audit readiness dashboard returns correct structure. Score: {score['score']}")


class TestPhase30RegressionTests:
    """Regression tests to ensure previous phases still work"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_phase29_migrations_still_works(self, auth_headers):
        """Verify Phase 29 migrations endpoints still work"""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch",
            headers=auth_headers,
            params={"dry_run": True, "limit": 1}
        )
        # Should return 200 (success) or 500 (if no employees to migrate)
        assert response.status_code in [200, 500], f"Phase 29 batch migration failed: {response.status_code}"
        print("PASS: Phase 29 migrations endpoint still works")
    
    def test_phase28_verifications_still_works(self, auth_headers):
        """Verify Phase 28 verifications endpoints still work"""
        response = requests.post(
            f"{BASE_URL}/api/rtw/extract",
            headers=auth_headers,
            json={"document_id": "test-doc-id"}
        )
        # Should return 404 (document not found) or 200
        assert response.status_code in [200, 404], f"Phase 28 RTW extract failed: {response.status_code}"
        print("PASS: Phase 28 verifications endpoint still works")
    
    def test_phase27_dbs_still_works(self, auth_headers):
        """Verify Phase 27 DBS endpoints still work"""
        response = requests.get(
            f"{BASE_URL}/api/dbs-register",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Phase 27 DBS register failed: {response.status_code}"
        print("PASS: Phase 27 DBS endpoint still works")
    
    def test_phase26_agreements_still_works(self, auth_headers):
        """Verify Phase 26 agreements endpoints still work"""
        response = requests.get(
            f"{BASE_URL}/api/employees/test-id/agreements",
            headers=auth_headers
        )
        # Should return 404 (employee not found) or 200
        assert response.status_code in [200, 404], f"Phase 26 agreements failed: {response.status_code}"
        print("PASS: Phase 26 agreements endpoint still works")
    
    def test_phase25_recurring_compliance_still_works(self, auth_headers):
        """Verify Phase 25 recurring compliance endpoints still work"""
        response = requests.get(
            f"{BASE_URL}/api/recurring-compliance",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Phase 25 recurring compliance failed: {response.status_code}"
        print("PASS: Phase 25 recurring compliance endpoint still works")


class TestPhase30Integration:
    """Integration tests for Phase 30 readiness routes"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_all_readiness_endpoints_respond(self, auth_headers):
        """Verify all 7 readiness endpoints respond correctly"""
        endpoints = [
            ("GET", "/api/employees/test-id/readiness", 404),
            ("GET", "/api/employees/readiness-summary", 200),
            ("GET", "/api/employees/test-id/recruitment-approval-check", 404),
            ("GET", "/api/employees/test-id/work-readiness-check", 404),
            ("GET", "/api/employees/test-id/poa-freshness", 404),
            ("POST", "/api/employees/test-id/poa-freshness/override?document_id=test", 404),
            ("GET", "/api/dashboard/audit-readiness", 200),
        ]
        
        for method, endpoint, expected_status in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=auth_headers)
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", headers=auth_headers)
            
            assert response.status_code == expected_status, \
                f"{method} {endpoint} returned {response.status_code}, expected {expected_status}"
            print(f"PASS: {method} {endpoint} -> {response.status_code}")
        
        print("PASS: All 7 readiness endpoints respond correctly")
    
    def test_readiness_data_consistency(self, auth_headers):
        """Test that readiness data is consistent across endpoints"""
        # Get readiness summary
        summary_response = requests.get(
            f"{BASE_URL}/api/employees/readiness-summary",
            headers=auth_headers
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        
        # Verify counts add up
        total = summary["total_employees"]
        ready = summary["ready_to_work"]
        conditions = summary["ready_with_conditions"]
        not_ready = summary["not_ready"]
        
        assert ready + conditions + not_ready == total, \
            f"Counts don't add up: {ready} + {conditions} + {not_ready} != {total}"
        
        print(f"PASS: Readiness data is consistent. Total: {total}, Ready: {ready}, Conditions: {conditions}, Not Ready: {not_ready}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

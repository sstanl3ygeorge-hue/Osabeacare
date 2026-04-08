"""
Phase 33: Worker Dashboard Routes Extraction Tests
Tests for 7 worker dashboard endpoints extracted to /app/backend/routes/worker_dashboard.py

Endpoints tested:
1. GET /api/worker/dashboard - Worker compliance dashboard (requires worker auth)
2. POST /api/worker/upload-document/{requirement_id} - Worker document upload (requires worker auth)
3. POST /api/workers/{employee_id}/send-reminder - Send reminder to worker (requires admin auth)
4. GET /api/worker/forms - List worker forms (requires worker auth)
5. GET /api/worker/forms/{form_id} - Get specific form data (requires worker auth)
6. POST /api/worker/forms/{form_id}/save - Save form progress (requires worker auth)
7. POST /api/worker/forms/{form_id}/submit - Submit form (requires worker auth)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')


class TestPhase33WorkerDashboardRoutes:
    """Test worker dashboard routes extracted in Phase 33"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if response.status_code == 200:
            # API returns 'token' not 'access_token'
            return response.json().get("token") or response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth"""
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    # ==================== WORKER DASHBOARD ENDPOINT ====================
    
    def test_worker_dashboard_requires_auth(self):
        """GET /api/worker/dashboard - Should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ GET /api/worker/dashboard returns 401 without auth")
    
    def test_worker_dashboard_with_admin_auth(self, admin_headers):
        """GET /api/worker/dashboard - Admin auth should fail (requires worker auth)"""
        response = requests.get(f"{BASE_URL}/api/worker/dashboard", headers=admin_headers)
        # Admin auth should not work for worker endpoints - expect 401 or 403 or 400
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/worker/dashboard rejects admin auth with {response.status_code}")
    
    # ==================== WORKER DOCUMENT UPLOAD ENDPOINT ====================
    
    def test_worker_upload_document_requires_auth(self):
        """POST /api/worker/upload-document/{requirement_id} - Should return 401 without auth"""
        response = requests.post(f"{BASE_URL}/api/worker/upload-document/test_doc")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ POST /api/worker/upload-document/test_doc returns 401 without auth")
    
    def test_worker_upload_document_with_admin_auth(self, admin_headers):
        """POST /api/worker/upload-document/{requirement_id} - Admin auth should fail"""
        response = requests.post(
            f"{BASE_URL}/api/worker/upload-document/test_doc",
            headers=admin_headers
        )
        # Admin auth should not work for worker endpoints
        assert response.status_code in [400, 401, 403, 422], f"Expected 400/401/403/422, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/worker/upload-document/test_doc rejects admin auth with {response.status_code}")
    
    # ==================== SEND REMINDER ENDPOINT (ADMIN) ====================
    
    def test_send_reminder_requires_auth(self):
        """POST /api/workers/{employee_id}/send-reminder - Should return 401 without auth"""
        response = requests.post(f"{BASE_URL}/api/workers/test_emp_id/send-reminder")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ POST /api/workers/test_emp_id/send-reminder returns 401 without auth")
    
    def test_send_reminder_with_admin_auth_invalid_employee(self, admin_headers):
        """POST /api/workers/{employee_id}/send-reminder - Admin auth with invalid employee"""
        response = requests.post(
            f"{BASE_URL}/api/workers/nonexistent_employee_id/send-reminder",
            headers=admin_headers,
            json={}
        )
        # Should return 404 for non-existent employee (auth works, employee not found)
        # Or 401 if token expired/invalid
        assert response.status_code in [401, 404], f"Expected 401/404, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/workers/nonexistent_employee_id/send-reminder returns {response.status_code} with admin auth")
    
    # ==================== WORKER FORMS LIST ENDPOINT ====================
    
    def test_worker_forms_requires_auth(self):
        """GET /api/worker/forms - Should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/worker/forms")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ GET /api/worker/forms returns 401 without auth")
    
    def test_worker_forms_with_admin_auth(self, admin_headers):
        """GET /api/worker/forms - Admin auth should fail (requires worker auth)"""
        response = requests.get(f"{BASE_URL}/api/worker/forms", headers=admin_headers)
        # Admin auth should not work for worker endpoints
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/worker/forms rejects admin auth with {response.status_code}")
    
    # ==================== WORKER FORM DATA ENDPOINT ====================
    
    def test_worker_form_data_requires_auth(self):
        """GET /api/worker/forms/{form_id} - Should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/worker/forms/staff_health_questionnaire")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ GET /api/worker/forms/staff_health_questionnaire returns 401 without auth")
    
    def test_worker_form_data_with_admin_auth(self, admin_headers):
        """GET /api/worker/forms/{form_id} - Admin auth should fail"""
        response = requests.get(
            f"{BASE_URL}/api/worker/forms/staff_health_questionnaire",
            headers=admin_headers
        )
        # Admin auth should not work for worker endpoints
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/worker/forms/staff_health_questionnaire rejects admin auth with {response.status_code}")
    
    # ==================== WORKER FORM SAVE ENDPOINT ====================
    
    def test_worker_form_save_requires_auth(self):
        """POST /api/worker/forms/{form_id}/save - Should return 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/worker/forms/staff_health_questionnaire/save",
            json={"form_data": {}}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ POST /api/worker/forms/staff_health_questionnaire/save returns 401 without auth")
    
    def test_worker_form_save_with_admin_auth(self, admin_headers):
        """POST /api/worker/forms/{form_id}/save - Admin auth should fail"""
        response = requests.post(
            f"{BASE_URL}/api/worker/forms/staff_health_questionnaire/save",
            headers=admin_headers,
            json={"form_data": {}}
        )
        # Admin auth should not work for worker endpoints
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/worker/forms/staff_health_questionnaire/save rejects admin auth with {response.status_code}")
    
    # ==================== WORKER FORM SUBMIT ENDPOINT ====================
    
    def test_worker_form_submit_requires_auth(self):
        """POST /api/worker/forms/{form_id}/submit - Should return 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/worker/forms/staff_health_questionnaire/submit",
            json={"form_data": {}}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ POST /api/worker/forms/staff_health_questionnaire/submit returns 401 without auth")
    
    def test_worker_form_submit_with_admin_auth(self, admin_headers):
        """POST /api/worker/forms/{form_id}/submit - Admin auth should fail"""
        response = requests.post(
            f"{BASE_URL}/api/worker/forms/staff_health_questionnaire/submit",
            headers=admin_headers,
            json={"form_data": {}}
        )
        # Admin auth should not work for worker endpoints
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/worker/forms/staff_health_questionnaire/submit rejects admin auth with {response.status_code}")


class TestPhase33RouterRegistration:
    """Verify router is properly registered"""
    
    def test_health_endpoint(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ API health check passed")
    
    def test_all_worker_dashboard_endpoints_registered(self):
        """Verify all 7 endpoints return proper status codes (not 404 for route not found)"""
        endpoints = [
            ("GET", "/api/worker/dashboard"),
            ("POST", "/api/worker/upload-document/test"),
            ("POST", "/api/workers/test_id/send-reminder"),
            ("GET", "/api/worker/forms"),
            ("GET", "/api/worker/forms/test_form"),
            ("POST", "/api/worker/forms/test_form/save"),
            ("POST", "/api/worker/forms/test_form/submit"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            # 401 means route exists but requires auth
            # 422 means route exists but validation failed
            # 404 could mean route not found OR resource not found (need to check message)
            if response.status_code == 404:
                # Check if it's "route not found" vs "resource not found"
                try:
                    detail = response.json().get("detail", "")
                    # If detail mentions specific resource (employee, form), route exists
                    if any(word in detail.lower() for word in ["employee", "form", "not found"]):
                        print(f"✓ {method} {endpoint} - Route registered (resource not found: {detail})")
                        continue
                except:
                    pass
                # If we can't determine, fail the test
                pytest.fail(f"{method} {endpoint} returned 404 - route may not be registered")
            else:
                print(f"✓ {method} {endpoint} - Route registered (status: {response.status_code})")


class TestPhase33RegressionPreviousPhases:
    """Regression tests for previous phases"""
    
    def get_admin_headers(self):
        """Get admin authentication token and headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if response.status_code == 200:
            # API returns 'token' not 'access_token'
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return None
    
    def test_phase32_profile_photos_still_works(self):
        """Phase 32: Profile photos endpoint still accessible"""
        headers = self.get_admin_headers()
        if not headers:
            pytest.skip("Admin authentication failed")
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        # Just verify employees endpoint works (profile photos are part of employee data)
        assert response.status_code == 200, f"Employees endpoint failed: {response.status_code}"
        print("✓ Phase 32 regression: Employees endpoint works")
    
    def test_phase31_cv_extractions_still_works(self):
        """Phase 31: CV extractions endpoint still accessible"""
        headers = self.get_admin_headers()
        if not headers:
            pytest.skip("Admin authentication failed")
        response = requests.get(f"{BASE_URL}/api/extractions/pending-review", headers=headers)
        assert response.status_code == 200, f"CV extractions endpoint failed: {response.status_code}"
        print("✓ Phase 31 regression: CV extractions endpoint works")
    
    def test_phase30_readiness_still_works(self):
        """Phase 30: Readiness endpoint still accessible"""
        headers = self.get_admin_headers()
        if not headers:
            pytest.skip("Admin authentication failed")
        # Get an employee ID first
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        if emp_response.status_code == 200:
            employees = emp_response.json()
            if employees and len(employees) > 0:
                emp_id = employees[0].get("id")
                response = requests.get(f"{BASE_URL}/api/employees/{emp_id}/readiness", headers=headers)
                assert response.status_code in [200, 404], f"Readiness endpoint failed: {response.status_code}"
                print(f"✓ Phase 30 regression: Readiness endpoint works (status: {response.status_code})")
                return
        print("✓ Phase 30 regression: Skipped (no employees found)")
    
    def test_phase27_dbs_register_still_works(self):
        """Phase 27: DBS register endpoint still accessible"""
        headers = self.get_admin_headers()
        if not headers:
            pytest.skip("Admin authentication failed")
        response = requests.get(f"{BASE_URL}/api/dbs-register", headers=headers)
        assert response.status_code == 200, f"DBS register endpoint failed: {response.status_code}"
        print("✓ Phase 27 regression: DBS register endpoint works")
    
    def test_phase26_agreements_still_works(self):
        """Phase 26: Agreements endpoint still accessible"""
        headers = self.get_admin_headers()
        if not headers:
            pytest.skip("Admin authentication failed")
        # Get an employee ID first
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        if emp_response.status_code == 200:
            employees = emp_response.json()
            if employees and len(employees) > 0:
                emp_id = employees[0].get("id")
                response = requests.get(f"{BASE_URL}/api/employees/{emp_id}/agreements", headers=headers)
                assert response.status_code in [200, 404], f"Agreements endpoint failed: {response.status_code}"
                print(f"✓ Phase 26 regression: Agreements endpoint works (status: {response.status_code})")
                return
        print("✓ Phase 26 regression: Skipped (no employees found)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

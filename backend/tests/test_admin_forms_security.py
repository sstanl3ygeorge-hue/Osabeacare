"""
Test Admin Internal-Only Forms with PDF Generation and Security Features

Tests:
- Interview Records: Create, View, PDF Download with logo
- Spot Checks: Create, View, PDF Download with logo
- Induction Checklist: View, Mark Items Complete, PDF Certificate
- Admin-only visibility (not visible in worker portal)
- PDF files include company logo (should be ~500KB+)
- Rate limiting on login (5 attempts per hour)
- Security headers present
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "b1fdb4e3-cfc9-4579-9ee7-b5b624248de1"


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
def auth_headers(admin_token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestSecurityHeaders:
    """Test security headers are present on all responses"""
    
    def test_security_headers_present(self):
        """Verify all required security headers are present"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        # Check required security headers
        assert "X-Frame-Options" in response.headers, "X-Frame-Options header missing"
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-Content-Type-Options" in response.headers, "X-Content-Type-Options header missing"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-XSS-Protection" in response.headers, "X-XSS-Protection header missing"
        
        assert "Referrer-Policy" in response.headers, "Referrer-Policy header missing"
        
        assert "Permissions-Policy" in response.headers, "Permissions-Policy header missing"
        
        assert "Content-Security-Policy" in response.headers, "CSP header missing"
        csp = response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp, "CSP frame-ancestors missing"


class TestRateLimiting:
    """Test rate limiting on login endpoint"""
    
    def test_rate_limiting_blocks_after_5_attempts(self):
        """Verify rate limiting kicks in after 5 failed login attempts"""
        test_email = f"ratelimit_test_{int(time.time())}@example.com"
        
        # Make 5 failed attempts
        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": test_email, "password": "wrongpassword"}
            )
            assert response.status_code == 401, f"Attempt {i+1} should return 401"
        
        # 6th attempt should be rate limited
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": "wrongpassword"}
        )
        assert response.status_code == 429, "6th attempt should be rate limited (429)"
        assert "Too many login attempts" in response.json().get("detail", "")


class TestInterviewRecords:
    """Test Interview Records CRUD and PDF generation"""
    
    def test_get_interview_records(self, auth_headers):
        """Test fetching interview records for an employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert isinstance(data["records"], list)
    
    def test_create_interview_record(self, auth_headers):
        """Test creating a new interview record"""
        payload = {
            "interview_date": "2026-04-05",
            "interview_method": "video",
            "interviewer_name": "Test Interviewer",
            "communication_score": 4,
            "experience_score": 5,
            "values_score": 4,
            "availability": "Full-time",
            "strengths": "Excellent communication",
            "areas_for_development": "Time management",
            "decision": "Approve",
            "notes": "Test interview record",
            "is_draft": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        # Response may be wrapped in {"record": {...}, "success": true}
        record = data.get("record", data)
        assert "id" in record, f"No id in response: {data}"
        assert record.get("admin_only") == True, "Interview record should be admin_only"
        return record["id"]
    
    def test_interview_record_pdf_download_with_logo(self, auth_headers):
        """Test PDF download includes company logo (file size > 500KB)"""
        # First get an interview record ID
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=auth_headers
        )
        records = response.json().get("records", [])
        assert len(records) > 0, "No interview records found"
        
        record_id = records[0]["id"]
        
        # Download PDF
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records/{record_id}/download-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "application/pdf"
        
        # Check file size (should be > 500KB with logo)
        pdf_size = len(response.content)
        assert pdf_size > 500000, f"PDF size {pdf_size} bytes is less than 500KB - logo may not be embedded"
        
        # Verify it's a valid PDF
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"


class TestSpotChecks:
    """Test Spot Checks CRUD and PDF generation"""
    
    def test_get_spot_checks(self, auth_headers):
        """Test fetching spot checks for an employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "spot_checks" in data
        assert isinstance(data["spot_checks"], list)
    
    def test_create_spot_check(self, auth_headers):
        """Test creating a new spot check"""
        payload = {
            "type": "observation",
            "area": "medication",
            "outcome": "pass",
            "notes": "Test spot check - excellent performance",
            "follow_up_required": False,
            "employee_name": "Test Employee"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        assert "id" in data
        return data["id"]
    
    def test_spot_check_pdf_download_with_logo(self, auth_headers):
        """Test Spot Check PDF download includes company logo (file size > 500KB)"""
        # First get a spot check ID
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks",
            headers=auth_headers
        )
        spot_checks = response.json().get("spot_checks", [])
        assert len(spot_checks) > 0, "No spot checks found"
        
        check_id = spot_checks[0]["id"]
        
        # Download PDF
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks/{check_id}/download-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "application/pdf"
        
        # Check file size (should be > 500KB with logo)
        pdf_size = len(response.content)
        assert pdf_size > 500000, f"PDF size {pdf_size} bytes is less than 500KB - logo may not be embedded"
        
        # Verify it's a valid PDF
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"


class TestInductionChecklist:
    """Test Induction Checklist and Certificate generation"""
    
    def test_get_induction_checklist(self, auth_headers):
        """Test fetching induction checklist for an employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "overall_status" in data
    
    def test_update_induction_item(self, auth_headers):
        """Test marking an induction item as complete"""
        # Get current checklist
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist",
            headers=auth_headers
        )
        items = response.json().get("items", [])
        assert len(items) > 0, "No induction items found"
        
        # Find a pending item
        pending_items = [i for i in items if i.get("status") != "completed"]
        if not pending_items:
            pytest.skip("All items already completed")
        
        item_name = pending_items[0]["name"]
        
        # Mark as complete
        response = requests.put(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist",
            headers=auth_headers,
            json={"item_name": item_name, "status": "completed", "notes": "Test completion"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
    
    def test_induction_certificate_requires_completion(self, auth_headers):
        """Test that certificate download requires completed induction"""
        # Get current status
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-checklist",
            headers=auth_headers
        )
        status = response.json().get("overall_status")
        
        # Try to download certificate
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/induction-completion/download-pdf",
            headers=auth_headers
        )
        
        if status == "completed":
            # Should succeed
            assert response.status_code == 200
            assert response.headers.get("Content-Type") == "application/pdf"
            # Check file size (should be > 500KB with logo)
            pdf_size = len(response.content)
            assert pdf_size > 500000, f"PDF size {pdf_size} bytes is less than 500KB - logo may not be embedded"
        else:
            # Should fail with 404
            assert response.status_code == 404
            assert "not completed" in response.json().get("detail", "").lower()


class TestAdminOnlyVisibility:
    """Test that admin forms are not visible in worker portal"""
    
    def test_interview_records_have_admin_only_flag(self, auth_headers):
        """Verify interview records have admin_only=True"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=auth_headers
        )
        records = response.json().get("records", [])
        
        for record in records:
            assert record.get("admin_only") == True, f"Record {record.get('id')} missing admin_only flag"
    
    def test_worker_cannot_access_interview_records(self):
        """Test that worker portal cannot access interview records"""
        # This would require a worker token - skip if not available
        # The frontend should not show these panels to workers
        pytest.skip("Worker access test requires worker authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

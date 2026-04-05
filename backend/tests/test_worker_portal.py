"""
Worker Portal API Tests - Worker Self-Service Portal Compliance Features
Tests for CQC audit-readiness features:
- Dashboard status banners (Onboarding vs Cleared to Work)
- Document verification badges (Verified vs Pending Verification)
- Training verification badges
- Expiry alerts with color-coded severity
- Professional registration section
- View button for verified documents
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')

# Test worker token (provided in test request)
WORKER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJvdHVuYmFrdW5sZWxvbmdlODVAZ21haWwuY29tIiwidXNlcl9pZCI6Indvcmtlcl9kODgzMzVmNi0xYjE4LTQzNWEtODA4Ni0yOGFmNGE1ODNmNzciLCJlbXBsb3llZV9pZCI6ImQ4ODMzNWY2LTFiMTgtNDM1YS04MDg2LTI4YWY0YTU4M2Y3NyIsInJvbGUiOiJ3b3JrZXIiLCJuYW1lIjoiT2xha3VubGUgQWxvbmdlIiwiZXhwIjoxNzc2MDAyMjIzfQ.P3eRB0qZjAgUW-80FCpfZQKfDFMnPYWWNMMHq0AkUVI"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture
def worker_client():
    """Session with worker auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WORKER_TOKEN}"
    })
    return session


class TestWorkerDashboardAPI:
    """Tests for /api/worker/dashboard endpoint"""
    
    def test_dashboard_returns_200(self, worker_client):
        """Dashboard endpoint should return 200 for authenticated worker"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ Dashboard returns 200")
    
    def test_dashboard_employee_data(self, worker_client):
        """Dashboard should return employee data with status fields"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        employee = data.get("employee", {})
        
        # Verify employee fields
        assert "id" in employee, "Missing employee.id"
        assert "name" in employee, "Missing employee.name"
        assert "status" in employee, "Missing employee.status"
        assert "employee_status" in employee, "Missing employee.employee_status"
        assert "is_active_employee" in employee, "Missing employee.is_active_employee"
        
        print(f"✅ Employee data: id={employee['id'][:20]}..., status={employee['status']}, is_active={employee['is_active_employee']}")
    
    def test_onboarding_employee_not_active(self, worker_client):
        """Onboarding employee should have is_active_employee=False"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        employee = data.get("employee", {})
        
        # Test employee has onboarding status
        assert employee.get("employee_status") == "onboarding", f"Expected onboarding, got {employee.get('employee_status')}"
        assert employee.get("is_active_employee") == False, "Onboarding employee should not be active"
        
        print("✅ Onboarding employee correctly marked as not active")
    
    def test_completed_documents_have_file_url(self, worker_client):
        """Completed documents should include file_url field"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        completed_docs = data.get("completed_documents", [])
        
        assert len(completed_docs) > 0, "Expected at least one completed document"
        
        for doc in completed_docs:
            assert "file_url" in doc, f"Missing file_url in document {doc.get('type')}"
            assert "type" in doc, "Missing type field"
            assert "name" in doc, "Missing name field"
            print(f"  - {doc['type']}: file_url={'present' if doc['file_url'] else 'null'}")
        
        print(f"✅ All {len(completed_docs)} completed documents have file_url field")
    
    def test_completed_documents_have_verification_stamp(self, worker_client):
        """Completed documents should include verification_stamp field"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        completed_docs = data.get("completed_documents", [])
        
        assert len(completed_docs) > 0, "Expected at least one completed document"
        
        for doc in completed_docs:
            assert "verification_stamp" in doc, f"Missing verification_stamp in document {doc.get('type')}"
            print(f"  - {doc['type']}: verification_stamp={doc['verification_stamp']}")
        
        print(f"✅ All {len(completed_docs)} completed documents have verification_stamp field")
    
    def test_verified_document_has_verified_true(self, worker_client):
        """Documents with verification_stamp should have verified=True"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        completed_docs = data.get("completed_documents", [])
        
        verified_docs = [d for d in completed_docs if d.get("verified") == True]
        unverified_docs = [d for d in completed_docs if d.get("verified") == False]
        
        print(f"  Verified documents: {len(verified_docs)}")
        print(f"  Unverified documents: {len(unverified_docs)}")
        
        # Check that verified docs have proper verification_stamp
        for doc in verified_docs:
            stamp = doc.get("verification_stamp")
            assert stamp not in [None, "", "not_verified"], f"Verified doc {doc['type']} has invalid stamp: {stamp}"
            print(f"  ✅ {doc['type']}: verified=True, stamp={stamp}")
        
        # Check that unverified docs have not_verified stamp
        for doc in unverified_docs:
            stamp = doc.get("verification_stamp")
            assert stamp in [None, "", "not_verified"], f"Unverified doc {doc['type']} has unexpected stamp: {stamp}"
            print(f"  ✅ {doc['type']}: verified=False, stamp={stamp}")
        
        print("✅ Verification status matches verification_stamp")
    
    def test_completed_trainings_have_verified_field(self, worker_client):
        """Completed trainings should include verified field"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        completed_trainings = data.get("completed_trainings", [])
        
        assert len(completed_trainings) > 0, "Expected at least one completed training"
        
        for training in completed_trainings:
            assert "verified" in training, f"Missing verified field in training {training.get('name')}"
            assert "name" in training, "Missing name field"
            print(f"  - {training['name']}: verified={training['verified']}")
        
        print(f"✅ All {len(completed_trainings)} completed trainings have verified field")
    
    def test_alerts_structure(self, worker_client):
        """Alerts should have proper structure for expiry tracking"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        alerts = data.get("alerts", [])
        
        print(f"  Total alerts: {len(alerts)}")
        
        for alert in alerts:
            assert "type" in alert, "Missing type field in alert"
            assert "title" in alert, "Missing title field in alert"
            assert "date" in alert, "Missing date field in alert"
            assert "days_left" in alert, "Missing days_left field in alert"
            assert "urgent" in alert, "Missing urgent field in alert"
            
            # Verify days_left is numeric
            assert isinstance(alert["days_left"], int), f"days_left should be int, got {type(alert['days_left'])}"
            
            print(f"  - {alert['type']}: {alert['title']}, days_left={alert['days_left']}, urgent={alert['urgent']}")
        
        print("✅ Alerts have proper structure")
    
    def test_professional_registration_field_exists(self, worker_client):
        """Dashboard should include professional_registration field"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        
        # Field should exist (can be null if not applicable)
        assert "professional_registration" in data, "Missing professional_registration field"
        
        prof_reg = data.get("professional_registration")
        if prof_reg:
            assert "type" in prof_reg, "Missing type in professional_registration"
            assert "status" in prof_reg, "Missing status in professional_registration"
            print(f"✅ Professional registration: type={prof_reg['type']}, status={prof_reg['status']}")
        else:
            print("✅ Professional registration: null (not required for this role)")
    
    def test_progress_calculation(self, worker_client):
        """Progress should be calculated correctly"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        progress = data.get("progress", {})
        
        assert "percentage" in progress, "Missing percentage in progress"
        assert "completed" in progress, "Missing completed in progress"
        assert "required" in progress, "Missing required in progress"
        
        print(f"✅ Progress: {progress['completed']}/{progress['required']} = {progress['percentage']}%")
    
    def test_forms_for_onboarding_employee(self, worker_client):
        """Onboarding employee should have forms to complete"""
        response = worker_client.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        forms = data.get("forms", [])
        
        # Onboarding employee should have forms
        assert len(forms) > 0, "Onboarding employee should have forms to complete"
        
        for form in forms:
            assert "id" in form, "Missing id in form"
            assert "name" in form, "Missing name in form"
            assert "status" in form, "Missing status in form"
            print(f"  - {form['name']}: status={form['status']}")
        
        print(f"✅ Found {len(forms)} forms for onboarding employee")


class TestWorkerDashboardUnauthorized:
    """Tests for unauthorized access"""
    
    def test_dashboard_requires_auth(self):
        """Dashboard should return 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/worker/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ Dashboard requires authentication")
    
    def test_dashboard_rejects_invalid_token(self):
        """Dashboard should reject invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ Dashboard rejects invalid token")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

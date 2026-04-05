"""
Test Admin Forms (Interview Record, Spot Check) with PDF Generation
Tests for admin-only internal forms with PDF download functionality.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')
TEST_EMPLOYEE_ID = "b1fdb4e3-cfc9-4579-9ee7-b5b624248de1"


class TestAdminFormsAndPDF:
    """Test admin forms (Interview Record, Spot Check) and PDF generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ===== INTERVIEW RECORDS TESTS =====
    
    def test_get_interview_records(self):
        """Test GET interview records endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        print(f"Found {len(data['records'])} interview records")
    
    def test_create_interview_record(self):
        """Test POST create interview record with all fields"""
        payload = {
            "interview_date": "2026-04-05",
            "interview_method": "video",
            "interviewer_name": "Test Admin",
            "communication_score": 4,
            "experience_score": 5,
            "values_score": 4,
            "availability": "Full-time, weekdays",
            "strengths": "Excellent communication skills",
            "areas_for_development": "Time management",
            "decision": "Approve",
            "notes": "Strong candidate - test record",
            "is_draft": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=self.headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "record" in data
        
        # Verify record data
        record = data["record"]
        assert record["form_data"]["decision"] == "Approve"
        assert record["form_data"]["communication_score"] == 4
        assert record["admin_only"] == True
        
        # Store record ID for PDF test
        self.created_record_id = record["id"]
        print(f"Created interview record: {self.created_record_id}")
        
        return record["id"]
    
    def test_interview_record_pdf_download(self):
        """Test interview record PDF download"""
        # First get existing records
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=self.headers
        )
        assert response.status_code == 200
        records = response.json().get("records", [])
        assert len(records) > 0, "No interview records found"
        
        record_id = records[0]["id"]
        
        # Download PDF
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records/{record_id}/download-pdf",
            headers=self.headers
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 1000, "PDF content too small"
        
        # Verify PDF header
        assert response.content[:4] == b'%PDF', "Invalid PDF header"
        print(f"Downloaded interview record PDF: {len(response.content)} bytes")
    
    def test_interview_record_admin_only_flag(self):
        """Test that interview records have admin_only flag set to True"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=self.headers
        )
        assert response.status_code == 200
        records = response.json().get("records", [])
        
        for record in records:
            assert record.get("admin_only") == True, f"Record {record['id']} missing admin_only flag"
        
        print(f"All {len(records)} records have admin_only=True")
    
    # ===== SPOT CHECK TESTS =====
    
    def test_get_spot_checks(self):
        """Test GET spot checks endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "spot_checks" in data
        print(f"Found {len(data['spot_checks'])} spot checks")
    
    def test_create_spot_check(self):
        """Test POST create spot check"""
        payload = {
            "type": "observation",
            "area": "medication",
            "outcome": "pass",
            "notes": "Test spot check - excellent medication administration",
            "follow_up_required": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks",
            headers=self.headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "id" in data
        
        print(f"Created spot check: {data['id']}")
        return data["id"]
    
    def test_spot_check_pdf_download(self):
        """Test spot check PDF download"""
        # First get existing spot checks
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks",
            headers=self.headers
        )
        assert response.status_code == 200
        spot_checks = response.json().get("spot_checks", [])
        assert len(spot_checks) > 0, "No spot checks found"
        
        check_id = spot_checks[0]["id"]
        
        # Download PDF
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/spot-checks/{check_id}/download-pdf",
            headers=self.headers
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 1000, "PDF content too small"
        
        # Verify PDF header
        assert response.content[:4] == b'%PDF', "Invalid PDF header"
        print(f"Downloaded spot check PDF: {len(response.content)} bytes")
    
    # ===== SAVE AS DRAFT TEST =====
    
    def test_interview_record_save_as_draft(self):
        """Test saving interview record as draft"""
        payload = {
            "interview_date": "2026-04-05",
            "interview_method": "phone",
            "interviewer_name": "Draft Test Admin",
            "communication_score": 3,
            "experience_score": 3,
            "values_score": 3,
            "notes": "Draft record for testing",
            "is_draft": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers=self.headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        record = data["record"]
        assert record["status"] == "draft"
        print(f"Created draft interview record: {record['id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

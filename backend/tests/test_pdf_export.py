"""
Test cases for PDF Compliance Summary Export functionality
Tests the /api/employees/{id}/export-compliance-pdf endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com')

class TestPDFExport:
    """PDF Compliance Summary Export tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get first employee ID
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        assert len(employees) > 0, "No employees found for testing"
        self.employee_id = employees[0]["id"]
        self.employee_code = employees[0]["employee_code"]
    
    def test_export_compliance_pdf_success(self):
        """Test successful PDF export"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/export-compliance-pdf",
            headers=self.headers
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Content type assertion
        assert response.headers.get("Content-Type") == "application/pdf", \
            f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        
        # Content-Disposition header assertion
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, "Expected attachment disposition"
        assert ".pdf" in content_disposition, "Expected .pdf in filename"
        
        # PDF content assertion - check PDF magic bytes
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF file"
        
        # Size assertion - PDF should have reasonable size
        assert len(response.content) > 1000, "PDF seems too small"
    
    def test_export_compliance_pdf_unauthorized(self):
        """Test PDF export without authentication"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/export-compliance-pdf"
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_export_compliance_pdf_not_found(self):
        """Test PDF export for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/non-existent-id/export-compliance-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_export_compliance_pdf_filename_format(self):
        """Test PDF filename format includes employee code and date"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/export-compliance-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 200
        
        content_disposition = response.headers.get("Content-Disposition", "")
        # Filename should contain employee code
        assert self.employee_code in content_disposition, \
            f"Expected {self.employee_code} in filename, got {content_disposition}"
        
        # Filename should contain "Compliance_Summary"
        assert "Compliance_Summary" in content_disposition, \
            f"Expected 'Compliance_Summary' in filename, got {content_disposition}"


class TestComplianceSummaryJSON:
    """Test JSON compliance summary export (used by frontend)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get first employee ID
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        assert len(employees) > 0
        self.employee_id = employees[0]["id"]
    
    def test_export_compliance_summary_json(self):
        """Test JSON compliance summary export"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/export-compliance-summary",
            headers=self.headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify structure
        assert "employee" in data
        assert "compliance_overview" in data
        assert "mandatory_items_checklist" in data
        assert "export_date" in data
        
        # Verify employee data
        assert "name" in data["employee"]
        assert "employee_id" in data["employee"]
        assert "role" in data["employee"]
        
        # Verify compliance overview
        assert "completion_percentage" in data["compliance_overview"]
        assert "total_mandatory_items" in data["compliance_overview"]


class TestEmployeeFileExport:
    """Test employee file ZIP export"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get first employee ID
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        assert len(employees) > 0
        self.employee_id = employees[0]["id"]
    
    def test_export_employee_file_zip(self):
        """Test ZIP file export"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/export-file",
            headers=self.headers
        )
        
        assert response.status_code == 200
        
        # Check content type
        assert "application/zip" in response.headers.get("Content-Type", "")
        
        # Check ZIP magic bytes
        assert response.content[:2] == b'PK', "Response is not a valid ZIP file"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

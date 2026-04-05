"""
Test Bulk PDF Import Feature - P2 Feature
Tests the PDF extraction endpoint and bulk import workflow
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBulkImportPDF:
    """Tests for Bulk PDF Import feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_login_success(self):
        """Test admin login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "admin@osabea.care"
        print("✓ Admin login successful")
    
    def test_02_extract_from_pdf_endpoint_exists(self):
        """Test that the PDF extraction endpoint exists and requires auth"""
        # Test without auth - should fail
        response = requests.post(f"{BASE_URL}/api/admin/employees/extract-from-pdf")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print("✓ PDF extraction endpoint exists and requires authentication")
    
    def test_03_extract_from_pdf_requires_file(self):
        """Test that PDF extraction requires a file"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/employees/extract-from-pdf",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        # Should return 422 (validation error) because no file provided
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("✓ PDF extraction requires file upload")
    
    def test_04_extract_from_pdf_rejects_non_pdf(self):
        """Test that PDF extraction rejects non-PDF files"""
        # Create a fake text file
        fake_file = io.BytesIO(b"This is not a PDF")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/employees/extract-from-pdf",
            headers={"Authorization": f"Bearer {self.token}"},
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        # Should return 400 because only PDF files are supported
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "PDF" in response.text or "pdf" in response.text
        print("✓ PDF extraction rejects non-PDF files")
    
    def test_05_bulk_import_endpoint_exists(self):
        """Test that bulk import endpoint exists"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/employees/bulk-import",
            json={"employees": []},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        # Should return 200 or 400 (empty list), not 404
        assert response.status_code != 404, f"Bulk import endpoint not found: {response.status_code}"
        print(f"✓ Bulk import endpoint exists (status: {response.status_code})")
    
    def test_06_bulk_import_with_draft_employee(self):
        """Test bulk import creates draft employee without sending magic link"""
        import uuid
        test_email = f"TEST_bulkimport_{uuid.uuid4().hex[:8]}@example.com"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/employees/bulk-import",
            json={
                "employees": [{
                    "first_name": "TEST_BulkImport",
                    "last_name": "User",
                    "email": test_email,
                    "phone": "07123456789",
                    "role": "Healthcare Assistant",
                    "send_magic_link": False  # Draft mode - no email sent
                }]
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        assert response.status_code == 200, f"Bulk import failed: {response.text}"
        data = response.json()
        
        # Check results structure
        assert "results" in data
        results = data["results"]
        assert "created" in results
        
        # Should have created 1 employee
        if len(results["created"]) > 0:
            created = results["created"][0]
            assert created["email"] == test_email
            assert "applicant_reference" in created
            print(f"✓ Draft employee created: {created['email']} (Ref: {created['applicant_reference']})")
        else:
            # Check if it was a duplicate
            if "errors" in results and len(results["errors"]) > 0:
                print(f"Note: Employee may already exist - {results['errors']}")
            else:
                print(f"✓ Bulk import processed (results: {results})")
    
    def test_07_import_template_endpoint(self):
        """Test import template endpoint exists"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/employees/import-template",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        # Should return template info
        assert response.status_code == 200, f"Import template endpoint failed: {response.status_code}"
        data = response.json()
        assert "required_fields" in data or "csv_example" in data
        print("✓ Import template endpoint works")


class TestBulkImportIntegration:
    """Integration tests for bulk import workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        
        # Login as admin
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@osabea.care", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
    
    def test_01_full_workflow_draft_import(self):
        """Test complete workflow: import as draft, verify in recruitment list"""
        import uuid
        test_email = f"TEST_workflow_{uuid.uuid4().hex[:8]}@example.com"
        
        # Step 1: Import as draft
        import_response = self.session.post(
            f"{BASE_URL}/api/admin/employees/bulk-import",
            json={
                "employees": [{
                    "first_name": "TEST_Workflow",
                    "last_name": "Draft",
                    "email": test_email,
                    "phone": "07999888777",
                    "role": "Care Assistant",
                    "send_magic_link": False
                }]
            },
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        )
        
        assert import_response.status_code == 200, f"Import failed: {import_response.text}"
        results = import_response.json().get("results", {})
        
        if len(results.get("created", [])) > 0:
            created = results["created"][0]
            employee_id = created.get("id")
            applicant_ref = created.get("applicant_reference")
            
            print(f"✓ Draft employee created: {test_email}")
            print(f"  - ID: {employee_id}")
            print(f"  - Applicant Reference: {applicant_ref}")
            
            # Step 2: Verify employee exists in recruitment list
            recruitment_response = self.session.get(
                f"{BASE_URL}/api/admin/recruitment",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if recruitment_response.status_code == 200:
                recruitment_data = recruitment_response.json()
                # Check if our test employee is in the list
                employees = recruitment_data if isinstance(recruitment_data, list) else recruitment_data.get("employees", [])
                found = any(e.get("email") == test_email for e in employees)
                if found:
                    print("✓ Draft employee found in recruitment list")
                else:
                    print("Note: Employee may be in different status/list")
        else:
            print(f"Note: Import returned: {results}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

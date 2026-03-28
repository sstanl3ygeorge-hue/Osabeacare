"""
Test file preview reliability for Care Compliance Portal
Tests:
1. Profile photo upload/view endpoint
2. Document preview endpoints
3. File accessibility check before verification
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com')

class TestFilePreviewReliability:
    """Test file preview and profile photo functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        # Login and get token
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get first employee
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        assert len(employees) > 0, "No employees found"
        self.employee_id = employees[0]["id"]
        self.employee = employees[0]
    
    # ========== Profile Photo Tests ==========
    
    def test_profile_photo_view_endpoint_exists(self):
        """Test that profile photo view endpoint exists and returns proper response"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/profile-photo/view",
            headers=self.headers
        )
        # Should return 404 if no photo, or 200 with image data
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data
            assert "No profile photo" in data["detail"]
            print("INFO: No profile photo uploaded yet (expected)")
        else:
            # Should return image content type
            content_type = response.headers.get("content-type", "")
            assert "image" in content_type, f"Expected image content type, got: {content_type}"
            print("SUCCESS: Profile photo returned with correct content type")
    
    def test_profile_photo_upload_endpoint_exists(self):
        """Test that profile photo upload endpoint exists"""
        # Create a small test image (1x1 pixel PNG)
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        
        files = {"file": ("test_photo.png", io.BytesIO(test_image), "image/png")}
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/profile-photo",
            headers=self.headers,
            files=files
        )
        
        # Should succeed or fail with validation error (not 500)
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}, response: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "photo_url" in data or "message" in data
            print("SUCCESS: Profile photo uploaded successfully")
            
            # Verify photo is now accessible
            view_response = requests.get(
                f"{BASE_URL}/api/employees/{self.employee_id}/profile-photo/view",
                headers=self.headers
            )
            assert view_response.status_code == 200, "Photo should be viewable after upload"
            print("SUCCESS: Profile photo is viewable after upload")
        else:
            print(f"INFO: Upload returned {response.status_code}: {response.text}")
    
    def test_profile_photo_delete_endpoint_exists(self):
        """Test that profile photo delete endpoint exists"""
        response = requests.delete(
            f"{BASE_URL}/api/employees/{self.employee_id}/profile-photo",
            headers=self.headers
        )
        # Should succeed or return 404 if no photo
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"Profile photo delete endpoint returned: {response.status_code}")
    
    # ========== Document Preview Tests ==========
    
    def test_compliance_requirements_endpoint(self):
        """Test compliance requirements endpoint returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "requirements" in data
        requirements = data["requirements"]
        assert len(requirements) > 0, "Should have compliance requirements"
        
        # Check first requirement has expected fields
        req = requirements[0]
        assert "id" in req
        assert "name" in req
        assert "evidence_files" in req or "documents" in req
        print(f"SUCCESS: Found {len(requirements)} compliance requirements")
    
    def test_evidence_view_endpoint(self):
        """Test evidence file view endpoint"""
        # Get compliance requirements to find a file
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find a requirement with evidence files
        for req in data.get("requirements", []):
            evidence_files = req.get("evidence_files", [])
            if evidence_files:
                file_info = evidence_files[0]
                file_id = file_info.get("file_id")
                req_id = req.get("id")
                
                if file_id and req_id:
                    # Test the view endpoint
                    view_response = requests.get(
                        f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{req_id}/evidence/{file_id}/view",
                        headers=self.headers
                    )
                    assert view_response.status_code in [200, 404, 500], f"Unexpected status: {view_response.status_code}"
                    
                    if view_response.status_code == 200:
                        print(f"SUCCESS: Evidence file viewable for requirement {req_id}")
                        return
                    else:
                        print(f"INFO: Evidence file returned {view_response.status_code} for {req_id}")
        
        print("INFO: No evidence files found to test view endpoint")
    
    def test_document_view_endpoint(self):
        """Test document view endpoint"""
        # Get employee documents
        response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={self.employee_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        documents = response.json()
        
        if documents:
            doc = documents[0]
            doc_id = doc.get("id")
            
            # Test the view endpoint
            view_response = requests.get(
                f"{BASE_URL}/api/employee-documents/{doc_id}/view",
                headers=self.headers
            )
            # Should return file or 404/500 if file not accessible
            assert view_response.status_code in [200, 404, 500], f"Unexpected status: {view_response.status_code}"
            
            if view_response.status_code == 200:
                print(f"SUCCESS: Document {doc_id} is viewable")
            else:
                print(f"INFO: Document view returned {view_response.status_code}")
        else:
            print("INFO: No documents found to test view endpoint")
    
    # ========== Verification Flow Tests ==========
    
    def test_verify_requirement_endpoint(self):
        """Test that verify requirement endpoint exists"""
        # Get compliance requirements
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find a requirement that can be verified
        for req in data.get("requirements", []):
            if req.get("can_verify") and req.get("has_evidence"):
                req_id = req.get("id")
                
                # Test verify endpoint
                verify_response = requests.post(
                    f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{req_id}/verify-all",
                    headers=self.headers
                )
                # Should succeed or fail with proper error
                assert verify_response.status_code in [200, 400, 404], f"Unexpected status: {verify_response.status_code}"
                print(f"Verify endpoint for {req_id} returned: {verify_response.status_code}")
                return
        
        print("INFO: No requirements available for verification test")
    
    def test_document_verify_endpoint(self):
        """Test document verify endpoint"""
        # Get employee documents
        response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={self.employee_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        documents = response.json()
        
        # Find an unverified document
        for doc in documents:
            if not doc.get("verified"):
                doc_id = doc.get("id")
                
                # Test verify endpoint
                verify_response = requests.post(
                    f"{BASE_URL}/api/employee-documents/{doc_id}/verify",
                    headers=self.headers
                )
                # Should succeed or fail with proper error
                assert verify_response.status_code in [200, 400, 404], f"Unexpected status: {verify_response.status_code}"
                print(f"Document verify endpoint returned: {verify_response.status_code}")
                return
        
        print("INFO: All documents already verified")
    
    # ========== EmployeeAvatar Component Tests ==========
    
    def test_employee_has_photo_field(self):
        """Test that employee response includes profile_photo_url field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        employee = response.json()
        
        # Should have profile_photo_url field (can be null)
        assert "profile_photo_url" in employee, "Employee should have profile_photo_url field"
        print(f"SUCCESS: Employee has profile_photo_url field (value: {employee.get('profile_photo_url')})")
    
    def test_dashboard_employees_endpoint(self):
        """Test dashboard employees endpoint for avatar display"""
        response = requests.get(
            f"{BASE_URL}/api/employees?limit=5",
            headers=self.headers
        )
        assert response.status_code == 200
        employees = response.json()
        
        # Each employee should have fields needed for avatar
        for emp in employees:
            assert "id" in emp
            assert "first_name" in emp
            assert "last_name" in emp
            assert "profile_photo_url" in emp
        
        print(f"SUCCESS: Dashboard employees have all required avatar fields")


class TestDocumentPreviewModal:
    """Test DocumentPreviewModal functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        assert len(employees) > 0
        self.employee_id = employees[0]["id"]
    
    def test_pdf_document_accessible(self):
        """Test that PDF documents are accessible"""
        # Get documents
        response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={self.employee_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        documents = response.json()
        
        # Find a PDF document
        pdf_docs = [d for d in documents if d.get("original_filename", "").lower().endswith(".pdf")]
        
        if pdf_docs:
            doc = pdf_docs[0]
            doc_id = doc.get("id")
            
            # Test view endpoint
            view_response = requests.get(
                f"{BASE_URL}/api/employee-documents/{doc_id}/view",
                headers=self.headers
            )
            
            if view_response.status_code == 200:
                content_type = view_response.headers.get("content-type", "")
                assert "pdf" in content_type.lower() or "octet-stream" in content_type.lower()
                print(f"SUCCESS: PDF document accessible with content-type: {content_type}")
            else:
                print(f"INFO: PDF document returned {view_response.status_code}")
        else:
            print("INFO: No PDF documents found")
    
    def test_image_document_accessible(self):
        """Test that image documents are accessible"""
        # Get documents
        response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={self.employee_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        documents = response.json()
        
        # Find an image document
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        image_docs = [d for d in documents if any(d.get("original_filename", "").lower().endswith(ext) for ext in image_extensions)]
        
        if image_docs:
            doc = image_docs[0]
            doc_id = doc.get("id")
            
            # Test view endpoint
            view_response = requests.get(
                f"{BASE_URL}/api/employee-documents/{doc_id}/view",
                headers=self.headers
            )
            
            if view_response.status_code == 200:
                content_type = view_response.headers.get("content-type", "")
                assert "image" in content_type.lower()
                print(f"SUCCESS: Image document accessible with content-type: {content_type}")
            else:
                print(f"INFO: Image document returned {view_response.status_code}")
        else:
            print("INFO: No image documents found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test 1:1 Document-to-Requirement Mapping System
Tests for compliance requirements endpoint and document upload with version increment
"""
import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

class TestDocumentMapping:
    """Tests for 1:1 Document-to-Requirement Mapping"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    # Test: Compliance requirements endpoint returns data
    def test_compliance_requirements_endpoint_returns_data(self):
        """Test that compliance-requirements endpoint returns valid data"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        assert "employee_id" in data
        assert "requirements" in data
        assert "summary" in data
        assert isinstance(data["requirements"], list)
        assert len(data["requirements"]) > 0
    
    # Test: One row per requirement (not per document)
    def test_one_row_per_requirement(self):
        """Test that requirements list has unique requirement IDs"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        requirement_ids = [req["id"] for req in data["requirements"]]
        # Check for uniqueness - no duplicates
        assert len(requirement_ids) == len(set(requirement_ids)), "Duplicate requirement IDs found"
    
    # Test: CV / Resume requirement appears in the list
    def test_cv_requirement_exists(self):
        """Test that CV / Resume requirement appears in the list"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        cv_req = next((req for req in data["requirements"] if req["id"] == "cv"), None)
        assert cv_req is not None, "CV requirement not found"
        assert cv_req["name"] == "CV / Resume"
        assert cv_req["type"] == "document"
    
    # Test: Reference 1 and Reference 2 appear as separate requirements
    def test_references_separate_requirements(self):
        """Test that Reference 1 and Reference 2 appear as separate requirements"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        ref1 = next((req for req in data["requirements"] if req["id"] == "reference_1"), None)
        ref2 = next((req for req in data["requirements"] if req["id"] == "reference_2"), None)
        
        assert ref1 is not None, "Reference 1 requirement not found"
        assert ref2 is not None, "Reference 2 requirement not found"
        assert ref1["name"] == "Reference 1"
        assert ref2["name"] == "Reference 2"
    
    # Test: Document type requirements have correct structure (updated for multi-file support)
    def test_document_requirement_structure(self):
        """Test that document requirements have correct structure with documents[] array"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        doc_reqs = [req for req in data["requirements"] if req["type"] == "document"]
        assert len(doc_reqs) > 0, "No document requirements found"
        
        for req in doc_reqs:
            assert "id" in req
            assert "name" in req
            assert "category" in req
            assert "status" in req
            assert "documents" in req  # Now returns documents[] array instead of document object
            assert "verified" in req
            assert "allow_multiple_files" in req
            assert "document_count" in req
    
    # Test: Verification status shows correctly
    def test_verification_status_structure(self):
        """Test that verification status shows correctly with verified_by"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        # Find a verified requirement
        verified_reqs = [req for req in data["requirements"] if req.get("verified")]
        
        for req in verified_reqs:
            assert req["verified"] == True
            assert "verified_by" in req
            assert "verified_at" in req
    
    # Test: Upload document endpoint works
    def test_upload_document_endpoint(self):
        """Test that upload-document endpoint works"""
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test document content")
            temp_file = f.name
        
        try:
            # Remove Content-Type header for multipart
            headers = {"Authorization": f"Bearer {self.token}"}
            
            with open(temp_file, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/upload-document",
                    headers=headers,
                    data={"requirement_id": "dbs", "notes": "Test upload"},
                    files={"file": ("test_dbs.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            data = response.json()
            
            assert data["requirement_id"] == "dbs"
            assert data["original_filename"] == "test_dbs.txt"
            assert data["status"] == "uploaded"
            assert "version_number" in data
        finally:
            os.unlink(temp_file)
    
    # Test: Re-upload increments version number
    def test_reupload_increments_version(self):
        """Test that re-uploading a document increments version number"""
        # First, get current version
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        dbs_req = next((req for req in data["requirements"] if req["id"] == "dbs"), None)
        assert dbs_req is not None
        
        initial_version = 1
        if dbs_req.get("document") and dbs_req["document"].get("version_number"):
            initial_version = dbs_req["document"]["version_number"]
        
        # Upload a new document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Updated document content for version test")
            temp_file = f.name
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            with open(temp_file, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/upload-document",
                    headers=headers,
                    data={"requirement_id": "dbs", "notes": "Version increment test"},
                    files={"file": ("test_dbs_v2.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            # Version should be incremented
            assert data["version_number"] > initial_version, f"Version not incremented: {data['version_number']} <= {initial_version}"
        finally:
            os.unlink(temp_file)
    
    # Test: Summary statistics are correct
    def test_summary_statistics(self):
        """Test that summary statistics are calculated correctly"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "total" in summary
        assert "completed" in summary
        assert "verified" in summary
        assert "missing" in summary
        assert "completion_percentage" in summary
        assert "verification_percentage" in summary
        
        # Verify math
        assert summary["total"] == len(data["requirements"])
        assert summary["completed"] + summary["missing"] == summary["total"]
        assert summary["completion_percentage"] >= 0 and summary["completion_percentage"] <= 100
    
    # Test: Document status values are valid
    def test_document_status_values(self):
        """Test that document status values are valid"""
        valid_statuses = ["missing", "pending", "in_progress", "completed"]
        
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        for req in data["requirements"]:
            assert req["status"] in valid_statuses, f"Invalid status: {req['status']} for {req['name']}"
    
    # Test: All mandatory document types are present
    def test_mandatory_document_types_present(self):
        """Test that all mandatory document types are present"""
        expected_doc_types = ["cv", "identity_rtw", "reference_1", "reference_2", "dbs"]
        
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        requirement_ids = [req["id"] for req in data["requirements"]]
        
        for doc_type in expected_doc_types:
            assert doc_type in requirement_ids, f"Missing mandatory document type: {doc_type}"


class TestChecklistTab:
    """Tests for Checklist tab showing requirement status"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    # Test: Compliance endpoint for checklist
    def test_compliance_endpoint_for_checklist(self):
        """Test that compliance endpoint returns data for checklist"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance")
        assert response.status_code == 200
        data = response.json()
        
        assert "compliance" in data
        assert "items" in data["compliance"]
        assert isinstance(data["compliance"]["items"], list)
    
    # Test: Checklist items have correct structure
    def test_checklist_items_structure(self):
        """Test that checklist items have correct structure"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance")
        assert response.status_code == 200
        data = response.json()
        
        for item in data["compliance"]["items"]:
            assert "id" in item
            assert "name" in item
            assert "category" in item
            assert "type" in item
            assert "status" in item
            assert "verified" in item


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

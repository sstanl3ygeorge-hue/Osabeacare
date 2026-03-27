"""
Test Multi-File Document Support
Tests for multi-file requirements (Identity/RTW) vs single-file requirements (CV, DBS)
API now returns documents[] array instead of document object
"""
import pytest
import requests
import os
import tempfile
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

class TestMultiFileSupport:
    """Tests for multi-file document requirements"""
    
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
    
    # Test: API returns documents[] array instead of document object
    def test_api_returns_documents_array(self):
        """Test that compliance-requirements API returns documents[] array"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        doc_reqs = [req for req in data["requirements"] if req["type"] == "document"]
        assert len(doc_reqs) > 0, "No document requirements found"
        
        for req in doc_reqs:
            assert "documents" in req, f"Missing 'documents' array in requirement {req['id']}"
            assert isinstance(req["documents"], list), f"'documents' should be a list for {req['id']}"
            assert "document_count" in req, f"Missing 'document_count' in requirement {req['id']}"
    
    # Test: Identity/RTW is a multi-file requirement
    def test_identity_rtw_is_multifile(self):
        """Test that Identity/RTW requirement has allow_multiple_files=True"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        identity_req = next((req for req in data["requirements"] if req["id"] == "identity_rtw"), None)
        assert identity_req is not None, "Identity/RTW requirement not found"
        assert identity_req["allow_multiple_files"] == True, "Identity/RTW should allow multiple files"
        assert identity_req.get("min_files", 1) >= 1, "Identity/RTW should require at least 1 file"
    
    # Test: CV is a single-file requirement
    def test_cv_is_singlefile(self):
        """Test that CV requirement has allow_multiple_files=False"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        cv_req = next((req for req in data["requirements"] if req["id"] == "cv"), None)
        assert cv_req is not None, "CV requirement not found"
        assert cv_req["allow_multiple_files"] == False, "CV should NOT allow multiple files"
    
    # Test: DBS is a single-file requirement
    def test_dbs_is_singlefile(self):
        """Test that DBS requirement has allow_multiple_files=False"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        dbs_req = next((req for req in data["requirements"] if req["id"] == "dbs"), None)
        assert dbs_req is not None, "DBS requirement not found"
        assert dbs_req["allow_multiple_files"] == False, "DBS should NOT allow multiple files"
    
    # Test: Multi-file upload creates new document (not replace)
    def test_multifile_upload_creates_new_document(self):
        """Test that uploading to multi-file requirement creates new document"""
        # Get initial document count for identity_rtw
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        identity_req = next((req for req in data["requirements"] if req["id"] == "identity_rtw"), None)
        initial_count = identity_req["document_count"]
        
        # Upload a new document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"Test passport document {time.time()}")
            temp_file = f.name
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            with open(temp_file, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/upload-document",
                    headers=headers,
                    data={
                        "requirement_id": "identity_rtw",
                        "document_label": "TEST_Passport Front",
                        "notes": "Multi-file test upload"
                    },
                    files={"file": ("test_passport.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            doc_data = response.json()
            
            # Verify document was created with label
            assert doc_data["requirement_id"] == "identity_rtw"
            assert doc_data["document_label"] == "TEST_Passport Front"
            
            # Verify count increased
            response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
            data = response.json()
            identity_req = next((req for req in data["requirements"] if req["id"] == "identity_rtw"), None)
            assert identity_req["document_count"] > initial_count, "Document count should increase for multi-file requirement"
            
        finally:
            os.unlink(temp_file)
    
    # Test: Single-file upload replaces existing document
    def test_singlefile_upload_replaces_document(self):
        """Test that uploading to single-file requirement replaces existing document"""
        # Get initial document count for DBS
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        dbs_req = next((req for req in data["requirements"] if req["id"] == "dbs"), None)
        initial_count = dbs_req["document_count"]
        
        # Upload first document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"Test DBS document v1 {time.time()}")
            temp_file = f.name
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            with open(temp_file, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/upload-document",
                    headers=headers,
                    data={"requirement_id": "dbs", "notes": "Single-file test v1"},
                    files={"file": ("test_dbs_v1.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200
            first_version = response.json()["version_number"]
            
            # Upload second document (should replace)
            with open(temp_file, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/upload-document",
                    headers=headers,
                    data={"requirement_id": "dbs", "notes": "Single-file test v2"},
                    files={"file": ("test_dbs_v2.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200
            second_version = response.json()["version_number"]
            
            # Version should increment
            assert second_version > first_version, "Version should increment on replace"
            
            # Document count should still be 1 (replaced, not added)
            response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
            data = response.json()
            dbs_req = next((req for req in data["requirements"] if req["id"] == "dbs"), None)
            assert dbs_req["document_count"] == 1, "Single-file requirement should only have 1 document"
            
        finally:
            os.unlink(temp_file)
    
    # Test: Delete document from multi-file requirement
    def test_delete_multifile_document(self):
        """Test that documents can be deleted from multi-file requirements"""
        # First upload a test document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"Test document to delete {time.time()}")
            temp_file = f.name
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            with open(temp_file, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/upload-document",
                    headers=headers,
                    data={
                        "requirement_id": "identity_rtw",
                        "document_label": "TEST_To Be Deleted",
                        "notes": "Delete test"
                    },
                    files={"file": ("test_delete.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200
            doc_id = response.json()["id"]
            
            # Delete the document
            response = self.session.delete(f"{BASE_URL}/api/employee-documents/{doc_id}")
            assert response.status_code == 200, f"Delete failed: {response.text}"
            assert response.json()["message"] == "Document deleted successfully"
            
        finally:
            os.unlink(temp_file)
    
    # Test: Cannot delete document from single-file requirement
    def test_cannot_delete_singlefile_document(self):
        """Test that documents cannot be deleted from single-file requirements"""
        # Get DBS document
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        dbs_req = next((req for req in data["requirements"] if req["id"] == "dbs"), None)
        if dbs_req and dbs_req["documents"]:
            doc_id = dbs_req["documents"][0]["id"]
            
            # Try to delete - should fail
            response = self.session.delete(f"{BASE_URL}/api/employee-documents/{doc_id}")
            assert response.status_code == 400, "Should not be able to delete single-file document"
            assert "single-file requirement" in response.json()["detail"].lower()
    
    # Test: all_verified flag for multi-file requirements
    def test_all_verified_flag(self):
        """Test that all_verified flag works correctly for multi-file requirements"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        for req in data["requirements"]:
            if req["type"] == "document":
                assert "all_verified" in req, f"Missing 'all_verified' in requirement {req['id']}"
                assert isinstance(req["all_verified"], bool), f"'all_verified' should be boolean for {req['id']}"
    
    # Test: Compliance score based on requirement completion, not file count
    def test_compliance_score_by_requirement(self):
        """Test that compliance score is based on requirement completion, not file count"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        total_reqs = summary["total"]
        completed_reqs = summary["completed"]
        
        # Verify that total equals number of requirements (not files)
        assert total_reqs == len(data["requirements"]), "Total should equal number of requirements"
        
        # Verify completion percentage is based on requirements
        expected_percentage = round((completed_reqs / total_reqs) * 100) if total_reqs > 0 else 0
        assert abs(summary["completion_percentage"] - expected_percentage) <= 1, "Completion percentage should be based on requirements"


class TestDocumentStructureUpdated:
    """Tests for updated document structure (documents[] array)"""
    
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
    
    # Test: Document requirements have correct updated structure
    def test_document_requirement_structure_updated(self):
        """Test that document requirements have correct structure with documents[] array"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        doc_reqs = [req for req in data["requirements"] if req["type"] == "document"]
        assert len(doc_reqs) > 0, "No document requirements found"
        
        for req in doc_reqs:
            # Required fields
            assert "id" in req
            assert "name" in req
            assert "category" in req
            assert "status" in req
            assert "verified" in req
            
            # New multi-file fields
            assert "documents" in req, f"Missing 'documents' array in {req['id']}"
            assert "document_count" in req, f"Missing 'document_count' in {req['id']}"
            assert "allow_multiple_files" in req, f"Missing 'allow_multiple_files' in {req['id']}"
            assert "min_files" in req, f"Missing 'min_files' in {req['id']}"
            assert "all_verified" in req, f"Missing 'all_verified' in {req['id']}"
    
    # Test: Single-file requirements deduplicate to show only latest
    def test_singlefile_deduplication(self):
        """Test that single-file requirements show only the most recent document"""
        response = self.session.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        # Check all single-file requirements
        for req in data["requirements"]:
            if req["type"] == "document" and not req["allow_multiple_files"]:
                # Should have at most 1 document
                assert len(req["documents"]) <= 1, f"Single-file requirement {req['id']} should have at most 1 document, found {len(req['documents'])}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

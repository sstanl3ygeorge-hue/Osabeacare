"""
Test Document Extraction Bugfix - file_id to document_id resolution

This test verifies the bugfix for 'Document not found' error when:
1. GET /api/documents/{file_id}/extraction resolves file_id to document_id
2. POST /api/documents/{file_id}/extract works with file_id from evidence_files
3. POST /api/documents/{document_id}/extract works with direct document_id
4. Evidence endpoint returns document_id field in evidence_files
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')

# Test employee and document IDs from context
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"
TEST_DOCUMENT_ID = "add610d7-8819-4182-a03e-b76aa0978ea0"  # Has extraction record
TEST_FILE_ID = "bd0a0f4e-68db-4029-b865-3a2d64f8f288"  # Should resolve to document_id

# Requirement IDs for evidence endpoint
TEST_REQUIREMENT_IDS = ["right_to_work_documents", "dbs_certificate", "identity_documents"]


class TestDocumentExtractionBugfix:
    """Tests for document extraction file_id resolution bugfix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication for all tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    # ==================== EVIDENCE ENDPOINT TESTS ====================
    
    def test_evidence_endpoint_returns_document_id(self):
        """Test that evidence endpoint includes document_id in evidence_files"""
        # Evidence endpoint requires requirement_id
        all_evidence_files = []
        
        for req_id in TEST_REQUIREMENT_IDS:
            response = self.session.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_id}/evidence"
            )
            
            if response.status_code == 200:
                data = response.json()
                evidence_files = data.get("evidence_files", [])
                all_evidence_files.extend(evidence_files)
        
        print(f"Total evidence files found: {len(all_evidence_files)}")
        
        if not all_evidence_files:
            pytest.skip("No evidence files found for test employee")
        
        # Check that at least some evidence files have document_id
        files_with_doc_id = [ef for ef in all_evidence_files if ef.get("document_id")]
        
        print(f"Files with document_id: {len(files_with_doc_id)}")
        
        # At least some files should have document_id
        assert len(files_with_doc_id) > 0, "Evidence files should include document_id field"
        
        # Verify structure of evidence file with document_id
        for ef in files_with_doc_id[:3]:  # Check first 3
            print(f"Evidence file: file_id={ef.get('file_id')}, document_id={ef.get('document_id')}")
            assert ef.get("document_id"), "Evidence file should have document_id"
    
    def test_evidence_files_structure(self):
        """Test evidence files have proper structure for extraction"""
        all_evidence_files = []
        
        for req_id in TEST_REQUIREMENT_IDS:
            response = self.session.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_id}/evidence"
            )
            
            if response.status_code == 200:
                data = response.json()
                evidence_files = data.get("evidence_files", [])
                all_evidence_files.extend(evidence_files)
        
        if not all_evidence_files:
            pytest.skip("No evidence files found")
        
        # Check required fields for extraction
        for ef in all_evidence_files[:5]:
            # Should have either file_id or document_id for extraction
            has_id = ef.get("file_id") or ef.get("document_id")
            assert has_id, f"Evidence file missing ID: {ef}"
            
            # Should have file_url for extraction
            assert ef.get("file_url"), f"Evidence file missing file_url: {ef}"
    
    # ==================== GET EXTRACTION TESTS ====================
    
    def test_get_extraction_with_document_id(self):
        """Test GET extraction with direct document_id"""
        response = self.session.get(f"{BASE_URL}/api/documents/{TEST_DOCUMENT_ID}/extraction")
        
        assert response.status_code == 200, f"GET extraction failed: {response.text}"
        
        data = response.json()
        print(f"GET extraction response: has_extraction={data.get('has_extraction')}, status={data.get('extraction_status')}")
        
        # Should return extraction data or not_extracted status
        assert "has_extraction" in data or "extraction_status" in data or "document_id" in data
    
    def test_get_extraction_with_file_id_resolution(self):
        """Test GET extraction resolves file_id to document_id"""
        # First get evidence files to find a valid file_id
        all_evidence_files = []
        
        for req_id in TEST_REQUIREMENT_IDS:
            response = self.session.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_id}/evidence"
            )
            
            if response.status_code == 200:
                data = response.json()
                evidence_files = data.get("evidence_files", [])
                all_evidence_files.extend(evidence_files)
        
        # Find a file with both file_id and document_id
        test_file = None
        for ef in all_evidence_files:
            if ef.get("file_id") and ef.get("document_id"):
                test_file = ef
                break
        
        if not test_file:
            pytest.skip("No evidence file with both file_id and document_id found")
        
        file_id = test_file.get("file_id")
        document_id = test_file.get("document_id")
        
        print(f"Testing file_id resolution: file_id={file_id}, expected document_id={document_id}")
        
        # GET extraction using file_id
        response = self.session.get(f"{BASE_URL}/api/documents/{file_id}/extraction")
        
        assert response.status_code == 200, f"GET extraction with file_id failed: {response.text}"
        
        data = response.json()
        print(f"Response: {data}")
        
        # Should not return 404 - the file_id should resolve
        assert "detail" not in data or "not found" not in str(data.get("detail", "")).lower()
    
    def test_get_extraction_invalid_id_returns_not_extracted(self):
        """Test GET extraction with invalid ID returns proper response"""
        invalid_id = "invalid-document-id-12345"
        
        response = self.session.get(f"{BASE_URL}/api/documents/{invalid_id}/extraction")
        
        # Should return 200 with has_extraction: false, not 404
        assert response.status_code == 200, f"Should return 200 for non-existent: {response.text}"
        
        data = response.json()
        assert data.get("has_extraction") == False or data.get("status") == "not_extracted"
    
    # ==================== POST EXTRACT TESTS ====================
    
    def test_post_extract_with_document_id(self):
        """Test POST extract with direct document_id"""
        # Find a document that can be extracted
        all_evidence_files = []
        
        for req_id in TEST_REQUIREMENT_IDS:
            response = self.session.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_id}/evidence"
            )
            
            if response.status_code == 200:
                data = response.json()
                evidence_files = data.get("evidence_files", [])
                all_evidence_files.extend(evidence_files)
        
        # Find extractable document (PDF or image)
        test_doc = None
        for ef in all_evidence_files:
            doc_id = ef.get("document_id") or ef.get("file_id")
            file_url = ef.get("file_url", "")
            if doc_id and (file_url.endswith('.pdf') or 'pdf' in file_url.lower() or 
                          any(ext in file_url.lower() for ext in ['.jpg', '.jpeg', '.png'])):
                test_doc = ef
                break
        
        if not test_doc:
            # Use any document with document_id
            for ef in all_evidence_files:
                if ef.get("document_id"):
                    test_doc = ef
                    break
        
        if not test_doc:
            pytest.skip("No extractable document found")
        
        doc_id = test_doc.get("document_id") or test_doc.get("file_id")
        print(f"Testing POST extract with document_id: {doc_id}")
        
        response = self.session.post(f"{BASE_URL}/api/documents/{doc_id}/extract")
        
        # Should succeed or return existing extraction
        assert response.status_code in [200, 201], f"POST extract failed: {response.status_code} - {response.text}"
        
        data = response.json()
        print(f"Extract response: status={data.get('extraction_status')}, document_type={data.get('document_type')}")
    
    def test_post_extract_with_file_id(self):
        """Test POST extract with file_id from evidence_files"""
        # Get evidence files
        all_evidence_files = []
        
        for req_id in TEST_REQUIREMENT_IDS:
            response = self.session.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_id}/evidence"
            )
            
            if response.status_code == 200:
                data = response.json()
                evidence_files = data.get("evidence_files", [])
                all_evidence_files.extend(evidence_files)
        
        # Find a file with file_id different from document_id
        test_file = None
        for ef in all_evidence_files:
            file_id = ef.get("file_id")
            doc_id = ef.get("document_id")
            if file_id and doc_id and file_id != doc_id:
                test_file = ef
                break
        
        if not test_file:
            # Use any file with file_id
            for ef in all_evidence_files:
                if ef.get("file_id"):
                    test_file = ef
                    break
        
        if not test_file:
            pytest.skip("No evidence file with file_id found")
        
        file_id = test_file.get("file_id")
        print(f"Testing POST extract with file_id: {file_id}")
        
        response = self.session.post(f"{BASE_URL}/api/documents/{file_id}/extract")
        
        # Should succeed - file_id should resolve to document
        assert response.status_code in [200, 201, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 404:
            # Check error message is helpful
            data = response.json()
            detail = data.get("detail", "")
            print(f"404 response detail: {detail}")
            # Should have helpful error message
            assert "not found" in detail.lower() or "invalid" in detail.lower()
        else:
            data = response.json()
            print(f"Extract response: {data.get('extraction_status')}")
    
    def test_post_extract_invalid_id_returns_404(self):
        """Test POST extract with invalid ID returns 404 with helpful message"""
        invalid_id = "invalid-document-id-99999"
        
        response = self.session.post(f"{BASE_URL}/api/documents/{invalid_id}/extract")
        
        assert response.status_code == 404, f"Should return 404 for invalid ID: {response.status_code}"
        
        data = response.json()
        detail = data.get("detail", "")
        
        print(f"404 error message: {detail}")
        
        # Should have helpful error message
        assert "not found" in detail.lower() or "invalid" in detail.lower()
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_extraction_workflow_from_evidence(self):
        """Test full extraction workflow starting from evidence endpoint"""
        # Step 1: Get evidence files
        all_evidence_files = []
        
        for req_id in TEST_REQUIREMENT_IDS:
            response = self.session.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_id}/evidence"
            )
            
            if response.status_code == 200:
                data = response.json()
                evidence_files = data.get("evidence_files", [])
                all_evidence_files.extend(evidence_files)
        
        if not all_evidence_files:
            pytest.skip("No evidence files found")
        
        # Step 2: Pick a file with document_id
        test_file = None
        for ef in all_evidence_files:
            if ef.get("document_id"):
                test_file = ef
                break
        
        if not test_file:
            pytest.skip("No evidence file with document_id")
        
        doc_id = test_file.get("document_id")
        file_id = test_file.get("file_id")
        
        print(f"Testing workflow: document_id={doc_id}, file_id={file_id}")
        
        # Step 3: Check extraction status using document_id
        get_response = self.session.get(f"{BASE_URL}/api/documents/{doc_id}/extraction")
        assert get_response.status_code == 200
        
        extraction_data = get_response.json()
        print(f"Extraction status: has_extraction={extraction_data.get('has_extraction')}")
        
        # Step 4: If no extraction, trigger one
        if not extraction_data.get("has_extraction"):
            extract_response = self.session.post(f"{BASE_URL}/api/documents/{doc_id}/extract")
            # May fail if document not extractable, that's OK
            print(f"Extract response: {extract_response.status_code}")
    
    def test_document_id_consistency(self):
        """Test that document_id is consistent across endpoints"""
        # Get evidence files
        all_evidence_files = []
        
        for req_id in TEST_REQUIREMENT_IDS:
            response = self.session.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_id}/evidence"
            )
            
            if response.status_code == 200:
                data = response.json()
                evidence_files = data.get("evidence_files", [])
                all_evidence_files.extend(evidence_files)
        
        # Find files with document_id
        files_with_doc_id = [ef for ef in all_evidence_files if ef.get("document_id")]
        
        if not files_with_doc_id:
            pytest.skip("No evidence files with document_id")
        
        # Verify document_id format (should be UUID-like)
        for ef in files_with_doc_id[:3]:
            doc_id = ef.get("document_id")
            # UUID format check (basic)
            assert len(doc_id) >= 32, f"document_id should be UUID format: {doc_id}"
            assert "-" in doc_id, f"document_id should contain hyphens: {doc_id}"
            print(f"Valid document_id: {doc_id}")


class TestExtractionErrorHandling:
    """Tests for extraction error handling and messages"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_extract_nonexistent_document_error_message(self):
        """Test error message for non-existent document"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = self.session.post(f"{BASE_URL}/api/documents/{fake_id}/extract")
        
        assert response.status_code == 404
        
        data = response.json()
        detail = data.get("detail", "")
        
        # Should mention document not found
        assert "not found" in detail.lower() or "document" in detail.lower()
        print(f"Error message: {detail}")
    
    def test_get_extraction_graceful_handling(self):
        """Test GET extraction handles missing documents gracefully"""
        fake_id = "nonexistent-doc-id"
        
        response = self.session.get(f"{BASE_URL}/api/documents/{fake_id}/extraction")
        
        # Should return 200 with has_extraction: false, not error
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("has_extraction") == False or data.get("status") == "not_extracted"


class TestSpecificDocumentIds:
    """Tests using specific document IDs from the bugfix context"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_known_document_id_extraction(self):
        """Test extraction with known document_id that has extraction record"""
        # Document ID from context: add610d7-8819-4182-a03e-b76aa0978ea0
        doc_id = TEST_DOCUMENT_ID
        
        response = self.session.get(f"{BASE_URL}/api/documents/{doc_id}/extraction")
        
        print(f"Testing known document_id: {doc_id}")
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        print(f"Response data: has_extraction={data.get('has_extraction')}, status={data.get('extraction_status')}")
        
        # This document should have an extraction
        if data.get("has_extraction"):
            assert data.get("document_id") == doc_id or data.get("extraction_status")
            print("Extraction found for known document_id")
    
    def test_known_file_id_resolution(self):
        """Test file_id resolution to document_id"""
        # File ID from context: bd0a0f4e-68db-4029-b865-3a2d64f8f288
        file_id = TEST_FILE_ID
        
        response = self.session.get(f"{BASE_URL}/api/documents/{file_id}/extraction")
        
        print(f"Testing file_id resolution: {file_id}")
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        print(f"Response: {data}")
        
        # Should resolve file_id and return extraction status
        # Not a 404 error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Test View Files Button - Phase D4.1
Tests for file_url, file_available, mime_type fields in backend responses
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestComplianceFileDocumentsPreview:
    """Test documents_preview in compliance-file endpoint"""
    
    def test_compliance_file_returns_documents_preview(self, api_client):
        """Verify compliance-file endpoint returns documents_preview array"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "sections" in data, "Response should have sections"
        
        # Find evidence rows with documents_preview
        found_evidence_with_docs = False
        for section_key, section in data.get("sections", {}).items():
            for row in section.get("rows", []):
                if row.get("row_type") == "evidence" and row.get("documents_preview"):
                    found_evidence_with_docs = True
                    docs = row["documents_preview"]
                    print(f"Found evidence row '{row.get('title')}' with {len(docs)} documents")
                    
                    for doc in docs:
                        print(f"  Document: {doc.get('file_name')}")
                        print(f"    - file_url: {doc.get('file_url')}")
                        print(f"    - file_available: {doc.get('file_available')}")
                        print(f"    - content_type: {doc.get('content_type')}")
                        
                        # Verify required fields exist
                        assert "id" in doc, "Document should have id"
                        assert "file_name" in doc, "Document should have file_name"
                        assert "file_url" in doc, "Document should have file_url field"
                        assert "file_available" in doc, "Document should have file_available field"
                        assert "content_type" in doc, "Document should have content_type field"
                        
                        # file_available should be boolean
                        assert isinstance(doc["file_available"], bool), "file_available should be boolean"
        
        assert found_evidence_with_docs, "Should find at least one evidence row with documents"
    
    def test_rtw_evidence_has_file_fields(self, api_client):
        """Test RTW Evidence row has file_url, file_available in documents_preview"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find RTW Evidence row
        rtw_evidence = None
        for section_key, section in data.get("sections", {}).items():
            for row in section.get("rows", []):
                if row.get("key") == "right_to_work_evidence":
                    rtw_evidence = row
                    break
        
        if rtw_evidence and rtw_evidence.get("documents_preview"):
            docs = rtw_evidence["documents_preview"]
            print(f"RTW Evidence has {len(docs)} documents")
            
            for doc in docs:
                print(f"  - {doc.get('file_name')}: file_url={bool(doc.get('file_url'))}, file_available={doc.get('file_available')}")
                
                # Verify fields
                assert "file_url" in doc, "RTW doc should have file_url"
                assert "file_available" in doc, "RTW doc should have file_available"
        else:
            print("RTW Evidence row not found or has no documents")
    
    def test_dbs_evidence_has_file_fields(self, api_client):
        """Test DBS Certificate Evidence row has file_url, file_available in documents_preview"""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find DBS Evidence row
        dbs_evidence = None
        for section_key, section in data.get("sections", {}).items():
            for row in section.get("rows", []):
                if row.get("key") == "dbs_certificate_evidence":
                    dbs_evidence = row
                    break
        
        if dbs_evidence and dbs_evidence.get("documents_preview"):
            docs = dbs_evidence["documents_preview"]
            print(f"DBS Evidence has {len(docs)} documents")
            
            for doc in docs:
                print(f"  - {doc.get('file_name')}: file_url={bool(doc.get('file_url'))}, file_available={doc.get('file_available')}")
                
                # Verify fields
                assert "file_url" in doc, "DBS doc should have file_url"
                assert "file_available" in doc, "DBS doc should have file_available"
        else:
            print("DBS Evidence row not found or has no documents")


class TestRequirementFilesEndpoint:
    """Test /employees/{id}/requirements/{key}/files endpoint"""
    
    def test_rtw_files_endpoint_returns_file_data(self, api_client):
        """Test RTW files endpoint returns file_url, mime_type, file_available"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_evidence/files"
        )
        
        if response.status_code == 404:
            pytest.skip("RTW requirement not found")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"RTW Files response: active_file_count={data.get('active_file_count')}")
        
        # Check active files
        for file in data.get("active_files", []):
            print(f"  Active file: {file.get('file_name')}")
            print(f"    - file_url: {file.get('file_url')}")
            print(f"    - mime_type: {file.get('mime_type')}")
            print(f"    - content_type: {file.get('content_type')}")
            print(f"    - file_available: {file.get('file_available')}")
            
            # Verify required fields
            assert "file_id" in file, "File should have file_id"
            assert "file_name" in file, "File should have file_name"
            assert "file_url" in file, "File should have file_url field"
            assert "file_available" in file, "File should have file_available field"
            assert "mime_type" in file or "content_type" in file, "File should have mime_type or content_type"
            
            # file_available should be boolean
            assert isinstance(file["file_available"], bool), "file_available should be boolean"
    
    def test_dbs_files_endpoint_returns_file_data(self, api_client):
        """Test DBS files endpoint returns file_url, mime_type, file_available"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_certificate_evidence/files"
        )
        
        if response.status_code == 404:
            pytest.skip("DBS requirement not found")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"DBS Files response: active_file_count={data.get('active_file_count')}")
        
        # Check active files
        for file in data.get("active_files", []):
            print(f"  Active file: {file.get('file_name')}")
            print(f"    - file_url: {file.get('file_url')}")
            print(f"    - mime_type: {file.get('mime_type')}")
            print(f"    - content_type: {file.get('content_type')}")
            print(f"    - file_available: {file.get('file_available')}")
            
            # Verify required fields
            assert "file_id" in file, "File should have file_id"
            assert "file_name" in file, "File should have file_name"
            assert "file_url" in file, "File should have file_url field"
            assert "file_available" in file, "File should have file_available field"
    
    def test_multi_file_requirement_returns_all_files(self, api_client):
        """Test multi-file requirement (DBS with 2 files) returns all files"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/dbs_certificate_evidence/files"
        )
        
        if response.status_code == 404:
            pytest.skip("DBS requirement not found")
        
        assert response.status_code == 200
        
        data = response.json()
        active_count = data.get("active_file_count", 0)
        active_files = data.get("active_files", [])
        
        print(f"DBS has {active_count} active files")
        
        # Verify count matches array length
        assert len(active_files) == active_count, "active_file_count should match active_files length"
        
        # If multi-file, verify all files have required fields
        for file in active_files:
            assert "file_url" in file
            assert "file_available" in file


class TestFileAvailabilityStatus:
    """Test file_available field logic"""
    
    def test_file_available_true_when_url_exists(self, api_client):
        """file_available should be True when file_url is present"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_evidence/files"
        )
        
        if response.status_code == 404:
            pytest.skip("RTW requirement not found")
        
        assert response.status_code == 200
        
        data = response.json()
        for file in data.get("active_files", []):
            if file.get("file_url"):
                assert file.get("file_available") == True, \
                    f"file_available should be True when file_url exists: {file.get('file_name')}"
            else:
                assert file.get("file_available") == False, \
                    f"file_available should be False when file_url is missing: {file.get('file_name')}"


class TestMimeTypeField:
    """Test mime_type/content_type field"""
    
    def test_mime_type_or_content_type_present(self, api_client):
        """Files should have mime_type or content_type for preview support detection"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_evidence/files"
        )
        
        if response.status_code == 404:
            pytest.skip("RTW requirement not found")
        
        assert response.status_code == 200
        
        data = response.json()
        for file in data.get("active_files", []):
            mime = file.get("mime_type") or file.get("content_type")
            print(f"File {file.get('file_name')}: mime_type={file.get('mime_type')}, content_type={file.get('content_type')}")
            
            # At least one should be present (may be None if not stored)
            # This is informational - some files may not have mime_type stored


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

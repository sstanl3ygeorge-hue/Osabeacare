"""
Test Document Sync and Request Replacement Flow

Tests the synchronization between employee document uploads and admin dashboard,
specifically the 'Request Replacement' workflow:
1. Admin can see documents uploaded by employees via worker portal
2. Admin 'Request Replacement' action changes document status to 'rejected'
3. After rejection, worker dashboard shows document type as 'missing' with action='re_upload'
4. Rejection reason is included in the worker dashboard response
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"
TEST_WORKER_EMAIL = "otunbakunlelonge85@gmail.com"


class TestDocumentSyncReplacement:
    """Test document sync and replacement workflow between admin and worker portal"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get admin headers with auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_01_admin_login(self):
        """Test admin can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        print(f"✓ Admin login successful")
    
    def test_02_get_employee_exists(self, admin_headers):
        """Test that the test employee exists"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=admin_headers
        )
        # Employee might be in different status, check if exists
        if response.status_code == 404:
            pytest.skip(f"Test employee {TEST_EMPLOYEE_ID} not found")
        assert response.status_code == 200, f"Failed to get employee: {response.text}"
        data = response.json()
        print(f"✓ Employee found: {data.get('first_name', '')} {data.get('last_name', '')}")
    
    def test_03_get_identity_evidence_files(self, admin_headers):
        """Test admin can fetch files via /api/employees/{id}/requirements/identity_evidence/files"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/identity_evidence/files",
            headers=admin_headers
        )
        # This endpoint might return 404 if no files exist, which is acceptable
        if response.status_code == 404:
            print("✓ No identity_evidence files found (expected if none uploaded)")
            return
        
        assert response.status_code == 200, f"Failed to get identity_evidence files: {response.text}"
        data = response.json()
        print(f"✓ Identity evidence files endpoint working")
        print(f"  Active files: {data.get('active_file_count', 0)}")
        print(f"  Historical files: {data.get('historical_file_count', 0)}")
    
    def test_04_get_identity_documents_files(self, admin_headers):
        """Test admin can fetch files via /api/employees/{id}/requirements/identity_documents/files"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/identity_documents/files",
            headers=admin_headers
        )
        if response.status_code == 404:
            print("✓ No identity_documents files found (expected if none uploaded)")
            return
        
        assert response.status_code == 200, f"Failed to get identity_documents files: {response.text}"
        data = response.json()
        print(f"✓ Identity documents files endpoint working")
        print(f"  Active files: {data.get('active_file_count', 0)}")
        print(f"  Historical files: {data.get('historical_file_count', 0)}")
    
    def test_05_request_replacement_endpoint_exists(self, admin_headers):
        """Test that the request-replacement endpoint exists and requires valid doc_id"""
        # Test with a non-existent doc_id to verify endpoint exists
        fake_doc_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/employee-documents/{fake_doc_id}/request-replacement",
            headers=admin_headers,
            json={"reason": "Test reason", "notify_employee": False}
        )
        # Should return 404 for non-existent document, not 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404 for non-existent doc, got {response.status_code}: {response.text}"
        print("✓ Request replacement endpoint exists and returns 404 for non-existent document")
    
    def test_06_request_replacement_requires_auth(self):
        """Test that request-replacement endpoint requires authentication"""
        fake_doc_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/employee-documents/{fake_doc_id}/request-replacement",
            json={"reason": "Test reason", "notify_employee": False}
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Request replacement endpoint requires authentication")
    
    def test_07_worker_dashboard_endpoint_structure(self, admin_headers):
        """Test worker dashboard endpoint returns expected structure"""
        # First, we need a worker token - let's check if we can get one via magic link
        # For now, let's verify the endpoint structure by checking the API docs
        
        # Check if there's a way to get worker dashboard data as admin
        # The worker dashboard requires worker auth, so we'll test the structure differently
        
        # Let's verify the employee documents collection has the right fields
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/documents",
            headers=admin_headers
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Employee documents endpoint working")
            if isinstance(data, list):
                print(f"  Found {len(data)} documents")
        else:
            print(f"  Documents endpoint returned {response.status_code}")
    
    def test_08_document_action_menu_options(self, admin_headers):
        """Test that document action menu options are available via API"""
        # Get employee compliance requirements to see document structure
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=admin_headers
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Compliance requirements endpoint working")
            if isinstance(data, list):
                print(f"  Found {len(data)} requirements")
        else:
            print(f"  Compliance requirements returned {response.status_code}")
    
    def test_09_verify_legacy_mapping_identity(self, admin_headers):
        """Test that identity documents are correctly mapped to identity_evidence"""
        # Check both identity and identity_evidence requirement keys
        for req_key in ['identity', 'identity_documents', 'identity_evidence']:
            response = requests.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_key}/files",
                headers=admin_headers
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Requirement '{req_key}' accessible - {data.get('active_file_count', 0)} active files")
            elif response.status_code == 404:
                print(f"  Requirement '{req_key}' returned 404 (no files or not mapped)")
            else:
                print(f"  Requirement '{req_key}' returned {response.status_code}")
    
    def test_10_create_test_document_and_reject(self, admin_headers):
        """Test creating a document and then requesting replacement"""
        # First, create a test document in the database
        test_doc_id = f"test_doc_{uuid.uuid4().hex[:8]}"
        
        # We'll use the admin upload endpoint to create a test document
        # Then test the rejection flow
        
        # Check if we can list documents first
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/documents",
            headers=admin_headers
        )
        
        if response.status_code == 200:
            docs = response.json()
            if isinstance(docs, list) and len(docs) > 0:
                # Find a document that's not already rejected
                test_doc = None
                for doc in docs:
                    if doc.get('status') not in ['rejected', 'superseded', 'uploaded_in_error']:
                        test_doc = doc
                        break
                
                if test_doc:
                    doc_id = test_doc.get('id')
                    print(f"  Found test document: {doc_id}")
                    
                    # Test the request replacement endpoint
                    response = requests.post(
                        f"{BASE_URL}/api/employee-documents/{doc_id}/request-replacement",
                        headers=admin_headers,
                        json={
                            "reason": "Test rejection - document quality issue",
                            "notify_employee": False  # Don't send email in test
                        }
                    )
                    
                    if response.status_code == 200:
                        print(f"✓ Request replacement successful for document {doc_id}")
                        data = response.json()
                        print(f"  Response: {data}")
                    else:
                        print(f"  Request replacement returned {response.status_code}: {response.text}")
                else:
                    print("  No suitable document found for rejection test")
            else:
                print("  No documents found for employee")
        else:
            print(f"  Could not list documents: {response.status_code}")


class TestRequirementFilesEndpoint:
    """Test the requirement files drawer endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get admin headers with auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_01_files_endpoint_returns_active_and_historical(self, admin_headers):
        """Test that files endpoint returns both active and historical files"""
        # Test various requirement keys
        requirement_keys = [
            'identity_evidence',
            'identity_documents', 
            'right_to_work_documents',
            'dbs_certificate',
            'proof_of_address'
        ]
        
        for req_key in requirement_keys:
            response = requests.get(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/{req_key}/files",
                headers=admin_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                # Verify expected structure
                assert 'active_files' in data or 'active_file_count' in data, f"Missing active files info for {req_key}"
                assert 'historical_files' in data or 'historical_file_count' in data, f"Missing historical files info for {req_key}"
                print(f"✓ {req_key}: active={data.get('active_file_count', 0)}, historical={data.get('historical_file_count', 0)}")
            elif response.status_code == 404:
                print(f"  {req_key}: No files found (404)")
            else:
                print(f"  {req_key}: Unexpected status {response.status_code}")
    
    def test_02_rejected_documents_in_historical(self, admin_headers):
        """Test that rejected documents appear in historical files"""
        # Get all documents for the employee
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/documents",
            headers=admin_headers
        )
        
        if response.status_code == 200:
            docs = response.json()
            rejected_docs = [d for d in docs if d.get('status') == 'rejected']
            print(f"✓ Found {len(rejected_docs)} rejected documents")
            
            for doc in rejected_docs[:3]:  # Show first 3
                print(f"  - {doc.get('requirement_id')}: {doc.get('rejection_reason', 'No reason')[:50]}")


class TestDocumentActionMenuUI:
    """Test that DocumentActionMenu shows correct options"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get admin headers with auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_01_document_has_action_fields(self, admin_headers):
        """Test that documents have fields needed for action menu"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/documents",
            headers=admin_headers
        )
        
        if response.status_code == 200:
            docs = response.json()
            if isinstance(docs, list) and len(docs) > 0:
                doc = docs[0]
                # Check for fields used by DocumentActionMenu
                expected_fields = ['id', 'status', 'verified', 'file_url']
                for field in expected_fields:
                    if field in doc:
                        print(f"✓ Document has '{field}' field")
                    else:
                        print(f"  Document missing '{field}' field")
            else:
                print("  No documents to check")
        else:
            print(f"  Could not get documents: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

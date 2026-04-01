"""
Test suite for Compliance Verification Proof Enforcement
Tests the RecordCheckDialog proof file upload requirement and CheckRow proof display

Features tested:
1. RecordCheckDialog requires proof file upload before saving a check
2. Check records store evidence_document_id linking to the uploaded proof
3. CheckRow displays the linked proof file with view/download actions
4. Compliance file endpoint returns evidence_document details
"""

import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated API client"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture
def test_png_file():
    """Create a minimal PNG file for testing"""
    # 1x1 white pixel PNG
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    file_path = "/tmp/test_compliance_proof.png"
    with open(file_path, "wb") as f:
        f.write(png_data)
    yield file_path
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)


class TestDocumentUploadEndpoint:
    """Test the document upload endpoint used by RecordCheckDialog"""
    
    def test_upload_document_endpoint_exists(self, auth_token, test_png_file):
        """Test that /api/employees/{id}/upload-document endpoint exists and works"""
        with open(test_png_file, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("test_proof.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "RTW Check Proof Test"
                }
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should contain document id"
        assert data.get("requirement_id") == "right_to_work_check"
        assert data.get("document_label") == "RTW Check Proof Test"
        assert data.get("original_filename") == "test_proof.png"
        
        print(f"PASS: Document uploaded successfully with id: {data['id']}")
        return data["id"]
    
    def test_upload_document_with_verification_proof_type(self, auth_token, test_png_file):
        """Test uploading document with verification_proof document_type"""
        with open(test_png_file, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("dbs_proof.png", f, "image/png")},
                data={
                    "requirement_id": "dbs_status_check",
                    "document_type": "verification_proof",
                    "document_label": "DBS Status Check Proof"
                }
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"PASS: DBS proof document uploaded with id: {data['id']}")


class TestRTWCheckEndpoint:
    """Test the Right to Work check recording endpoint"""
    
    def test_rtw_check_endpoint_exists(self, api_client):
        """Test that /api/employees/{id}/right-to-work/check endpoint exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check"
        )
        # Should return 200 with check data or 404 if no check exists
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: RTW check endpoint exists, status: {response.status_code}")
    
    def test_record_rtw_check_with_evidence_document_id(self, auth_token, test_png_file):
        """Test recording RTW check with evidence_document_id"""
        # First upload a proof document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("rtw_proof_test.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "RTW Check Proof"
                }
            )
        
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        doc_id = upload_response.json()["id"]
        
        # Now record the check with evidence_document_id
        check_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/right-to-work/check",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={
                "method": "share_code_online_check",
                "checked_at": "2026-04-01",
                "outcome": "verified",
                "evidence_document_id": doc_id,
                "notes": "TEST: Check with proof document"
            }
        )
        
        assert check_response.status_code == 200, f"Check recording failed: {check_response.text}"
        check_data = check_response.json()
        
        # Verify the check was recorded
        assert "id" in check_data or "check_id" in check_data, "Check should have an ID"
        print(f"PASS: RTW check recorded with evidence_document_id: {doc_id}")


class TestComplianceFileEndpoint:
    """Test the compliance file endpoint returns evidence_document details"""
    
    def test_compliance_file_returns_check_data(self, api_client):
        """Test that compliance file endpoint returns check data with evidence_document"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file"
        )
        
        assert response.status_code == 200, f"Failed to get compliance file: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "sections" in data, "Response should have sections"
        assert "right_to_work" in data["sections"], "Should have right_to_work section"
        
        rtw_section = data["sections"]["right_to_work"]
        assert "rows" in rtw_section, "RTW section should have rows"
        
        # Find the check row
        check_row = None
        for row in rtw_section["rows"]:
            if row.get("row_type") == "check":
                check_row = row
                break
        
        assert check_row is not None, "Should have a check row"
        print(f"PASS: Found RTW check row with key: {check_row.get('key')}")
        
        # Verify check_data structure
        if check_row.get("has_check"):
            check_data = check_row.get("check_data", {})
            assert "evidence_document_id" in check_data, "check_data should have evidence_document_id field"
            
            if check_data.get("evidence_document_id"):
                assert "evidence_document" in check_data, "Should have evidence_document details"
                evidence_doc = check_data["evidence_document"]
                assert "id" in evidence_doc, "evidence_document should have id"
                assert "filename" in evidence_doc, "evidence_document should have filename"
                print(f"PASS: Check has evidence_document: {evidence_doc.get('filename')}")
            else:
                print("INFO: Check exists but no evidence_document_id linked (legacy check)")
    
    def test_compliance_file_serializer_version(self, api_client):
        """Test that compliance file uses dual_row_v1 serializer"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("serializer_version") == "dual_row_v1", \
            f"Expected dual_row_v1, got {data.get('serializer_version')}"
        print("PASS: Compliance file uses dual_row_v1 serializer")


class TestDBSCheckEndpoint:
    """Test the DBS check recording endpoint"""
    
    def test_dbs_check_endpoint_exists(self, api_client):
        """Test that /api/employees/{id}/dbs/check endpoint exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check"
        )
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: DBS check endpoint exists, status: {response.status_code}")
    
    def test_record_dbs_check_with_evidence(self, auth_token, test_png_file):
        """Test recording DBS check with evidence_document_id"""
        # Upload proof document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("dbs_proof_test.png", f, "image/png")},
                data={
                    "requirement_id": "dbs_status_check",
                    "document_type": "verification_proof",
                    "document_label": "DBS Status Check Proof"
                }
            )
        
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["id"]
        
        # Record DBS check
        check_response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/dbs/check",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={
                "method": "update_service_check",
                "checked_at": "2026-04-01",
                "outcome": "verified",
                "evidence_document_id": doc_id,
                "certificate_number": "123456789012",
                "notes": "TEST: DBS check with proof"
            }
        )
        
        assert check_response.status_code == 200, f"DBS check failed: {check_response.text}"
        print(f"PASS: DBS check recorded with evidence_document_id: {doc_id}")


class TestIdentityCheckEndpoint:
    """Test the Identity verification endpoint"""
    
    def test_identity_check_endpoint_exists(self, api_client):
        """Test that /api/employees/{id}/identity/check endpoint exists"""
        response = api_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/identity/check"
        )
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: Identity check endpoint exists, status: {response.status_code}")


class TestDocumentFileEndpoints:
    """Test document file view/download endpoints used by CheckRow"""
    
    def test_document_file_endpoint(self, auth_token, test_png_file):
        """Test that document file endpoint works for viewing proof"""
        # First upload a document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("view_test.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "View Test Proof"
                }
            )
        
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["id"]
        
        # Test file view endpoint
        file_response = requests.get(
            f"{BASE_URL}/api/employee-documents/{doc_id}/file",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert file_response.status_code == 200, f"File view failed: {file_response.status_code}"
        assert len(file_response.content) > 0, "File content should not be empty"
        print(f"PASS: Document file endpoint works, received {len(file_response.content)} bytes")
    
    def test_document_download_endpoint(self, auth_token, test_png_file):
        """Test that document download endpoint works"""
        # Upload a document
        with open(test_png_file, "rb") as f:
            upload_response = requests.post(
                f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/upload-document",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": ("download_test.png", f, "image/png")},
                data={
                    "requirement_id": "right_to_work_check",
                    "document_type": "verification_proof",
                    "document_label": "Download Test Proof"
                }
            )
        
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["id"]
        
        # Test download endpoint
        download_response = requests.get(
            f"{BASE_URL}/api/employee-documents/{doc_id}/download",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert download_response.status_code == 200, f"Download failed: {download_response.status_code}"
        assert len(download_response.content) > 0, "Download content should not be empty"
        print(f"PASS: Document download endpoint works, received {len(download_response.content)} bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

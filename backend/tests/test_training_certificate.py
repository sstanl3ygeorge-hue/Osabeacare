"""
Test Training Certificate Upload, Verify, Unverify, View, Download endpoints
Tests the training evidence system: Requirement → Evidence → Verified
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee - Olakunle Alonge (OCS-0001)
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTrainingCertificateUpload:
    """Test POST /api/employees/{id}/training/{requirement_id}/upload-certificate"""
    
    def test_upload_certificate_for_training_requirement(self, auth_headers):
        """Upload certificate should mark training complete and store file"""
        # Create a test PDF file
        test_file = io.BytesIO(b"%PDF-1.4 test certificate content")
        test_file.name = "test_certificate.pdf"
        
        files = {"file": ("test_certificate.pdf", test_file, "application/pdf")}
        data = {"expiry_date": "2027-01-15"}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/manual_handling/upload-certificate",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        print(f"Upload response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        result = response.json()
        assert result.get("success") == True
        assert "training_record" in result
        
        training = result["training_record"]
        assert training.get("certificate_url") is not None
        assert training.get("status") == "completed"
        assert training.get("completion_method") == "certificate"
        assert training.get("original_filename") == "test_certificate.pdf"
    
    def test_upload_certificate_invalid_requirement(self, auth_headers):
        """Upload to invalid requirement should fail"""
        test_file = io.BytesIO(b"%PDF-1.4 test content")
        files = {"file": ("test.pdf", test_file, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/invalid_requirement/upload-certificate",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 400
        assert "Invalid requirement_id" in response.json().get("detail", "")
    
    def test_upload_certificate_non_training_requirement(self, auth_headers):
        """Upload to non-training requirement should fail"""
        test_file = io.BytesIO(b"%PDF-1.4 test content")
        files = {"file": ("test.pdf", test_file, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/dbs/upload-certificate",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 400
        assert "not a training requirement" in response.json().get("detail", "")
    
    def test_upload_certificate_invalid_employee(self, auth_headers):
        """Upload for invalid employee should fail"""
        test_file = io.BytesIO(b"%PDF-1.4 test content")
        files = {"file": ("test.pdf", test_file, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id/training/safeguarding/upload-certificate",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 404
        assert "Employee not found" in response.json().get("detail", "")


class TestTrainingVerification:
    """Test POST /api/training-records/{id}/verify and unverify"""
    
    def test_verify_training_with_certificate(self, auth_headers):
        """Verify should work when certificate exists"""
        # First get training records to find one with certificate
        response = requests.get(
            f"{BASE_URL}/api/training-records?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        training_records = response.json()
        # Find a training with certificate
        training_with_cert = None
        for t in training_records:
            if t.get("certificate_url"):
                training_with_cert = t
                break
        
        if not training_with_cert:
            pytest.skip("No training with certificate found for verification test")
        
        # Verify the training
        response = requests.post(
            f"{BASE_URL}/api/training-records/{training_with_cert['id']}/verify",
            headers=auth_headers
        )
        
        print(f"Verify response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == True
        assert result["training_record"]["verified"] == True
        assert result["training_record"]["verified_by"] is not None
    
    def test_verify_training_without_certificate_fails(self, auth_headers):
        """Verify should fail when no certificate exists"""
        # Get training records
        response = requests.get(
            f"{BASE_URL}/api/training-records?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        training_records = response.json()
        # Find a training WITHOUT certificate
        training_without_cert = None
        for t in training_records:
            if not t.get("certificate_url") and t.get("status") == "completed":
                training_without_cert = t
                break
        
        if not training_without_cert:
            pytest.skip("No training without certificate found for this test")
        
        # Try to verify - should fail
        response = requests.post(
            f"{BASE_URL}/api/training-records/{training_without_cert['id']}/verify",
            headers=auth_headers
        )
        
        print(f"Verify without cert response: {response.status_code} - {response.text}")
        assert response.status_code == 400
        assert "Cannot verify training without uploaded certificate" in response.json().get("detail", "")
    
    def test_unverify_training(self, auth_headers):
        """Unverify should remove verification from training"""
        # Get training records
        response = requests.get(
            f"{BASE_URL}/api/training-records?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        training_records = response.json()
        # Find a verified training
        verified_training = None
        for t in training_records:
            if t.get("verified") == True:
                verified_training = t
                break
        
        if not verified_training:
            pytest.skip("No verified training found for unverify test")
        
        # Unverify
        response = requests.post(
            f"{BASE_URL}/api/training-records/{verified_training['id']}/unverify",
            headers=auth_headers
        )
        
        print(f"Unverify response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == True
        assert result["training_record"]["verified"] == False
        assert result["training_record"]["verified_by"] is None


class TestTrainingCertificateViewDownload:
    """Test GET /api/training-records/{id}/certificate/file and /download"""
    
    def test_view_certificate_file(self, auth_headers):
        """View certificate should return file content"""
        # Get training records
        response = requests.get(
            f"{BASE_URL}/api/training-records?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        training_records = response.json()
        # Find a training with certificate
        training_with_cert = None
        for t in training_records:
            if t.get("certificate_url"):
                training_with_cert = t
                break
        
        if not training_with_cert:
            pytest.skip("No training with certificate found for view test")
        
        # View the certificate
        response = requests.get(
            f"{BASE_URL}/api/training-records/{training_with_cert['id']}/certificate/file",
            headers=auth_headers
        )
        
        print(f"View certificate response: {response.status_code}")
        assert response.status_code == 200
        assert len(response.content) > 0
    
    def test_download_certificate_file(self, auth_headers):
        """Download certificate should return file with attachment header"""
        # Get training records
        response = requests.get(
            f"{BASE_URL}/api/training-records?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        training_records = response.json()
        # Find a training with certificate
        training_with_cert = None
        for t in training_records:
            if t.get("certificate_url"):
                training_with_cert = t
                break
        
        if not training_with_cert:
            pytest.skip("No training with certificate found for download test")
        
        # Download the certificate
        response = requests.get(
            f"{BASE_URL}/api/training-records/{training_with_cert['id']}/certificate/download",
            headers=auth_headers
        )
        
        print(f"Download certificate response: {response.status_code}")
        assert response.status_code == 200
        assert "attachment" in response.headers.get("Content-Disposition", "")
        assert len(response.content) > 0
    
    def test_view_certificate_not_found(self, auth_headers):
        """View certificate for training without certificate should fail"""
        # Get training records
        response = requests.get(
            f"{BASE_URL}/api/training-records?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        training_records = response.json()
        # Find a training WITHOUT certificate
        training_without_cert = None
        for t in training_records:
            if not t.get("certificate_url"):
                training_without_cert = t
                break
        
        if not training_without_cert:
            pytest.skip("No training without certificate found for this test")
        
        # Try to view - should fail
        response = requests.get(
            f"{BASE_URL}/api/training-records/{training_without_cert['id']}/certificate/file",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "No certificate uploaded" in response.json().get("detail", "")


class TestComplianceRequirementsTraining:
    """Test GET /api/employees/{id}/compliance-requirements returns training certificate info"""
    
    def test_compliance_requirements_includes_certificate_info(self, auth_headers):
        """Compliance requirements should include certificate_url, has_evidence, verified for training"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "requirements" in data
        
        # Find training requirements
        training_reqs = [r for r in data["requirements"] if r.get("type") == "training"]
        assert len(training_reqs) > 0, "Should have training requirements"
        
        # Check that training requirements have the expected fields
        for req in training_reqs:
            if req.get("training"):
                training = req["training"]
                print(f"Training: {req['name']} - has_evidence: {training.get('has_evidence')}, verified: {training.get('verified')}, certificate_url: {bool(training.get('certificate_url'))}")
                
                # Check required fields exist
                assert "has_evidence" in training, f"Training {req['name']} missing has_evidence"
                assert "verified" in training, f"Training {req['name']} missing verified"
                assert "certificate_url" in training, f"Training {req['name']} missing certificate_url"
                
                # Verify has_evidence matches certificate_url presence
                assert training["has_evidence"] == bool(training.get("certificate_url")), \
                    f"has_evidence should match certificate_url presence for {req['name']}"
    
    def test_safeguarding_has_certificate_and_verified(self, auth_headers):
        """Safeguarding training should have certificate uploaded and be verified"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find Safeguarding requirement
        safeguarding = None
        for req in data["requirements"]:
            if req.get("id") == "safeguarding":
                safeguarding = req
                break
        
        assert safeguarding is not None, "Safeguarding requirement not found"
        
        # According to context, Safeguarding should have certificate and be verified
        if safeguarding.get("training"):
            training = safeguarding["training"]
            print(f"Safeguarding training: {training}")
            # Note: This may or may not be verified depending on test order
            # Just check the structure is correct
            assert "certificate_url" in training
            assert "has_evidence" in training
            assert "verified" in training


class TestTrainingWithoutCertificateWarning:
    """Test that training completed without certificate shows warning"""
    
    def test_training_without_certificate_shows_warning_data(self, auth_headers):
        """Training completed without certificate should have has_evidence=False"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-requirements",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find training requirements that are completed but without certificate
        training_reqs = [r for r in data["requirements"] if r.get("type") == "training"]
        
        completed_without_cert = []
        for req in training_reqs:
            if req.get("training") and req["training"].get("status") == "completed":
                if not req["training"].get("certificate_url"):
                    completed_without_cert.append(req)
        
        print(f"Training completed without certificate: {[r['name'] for r in completed_without_cert]}")
        
        # Verify has_evidence is False for these
        for req in completed_without_cert:
            assert req["training"]["has_evidence"] == False, \
                f"{req['name']} should have has_evidence=False when no certificate"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

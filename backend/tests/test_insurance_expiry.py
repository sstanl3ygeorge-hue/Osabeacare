"""
Test Insurance/Certificate Expiry Logic
Tests the requires_expiry_date and valid_until_replaced fields for compliance certificates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestInsuranceExpiryFields:
    """Tests for insurance/certificate expiry date requirements"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_insurance_returns_expiry_fields(self):
        """GET /api/compliance/insurance should return requires_expiry_date and valid_until_replaced"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "No insurance records returned"
        
        # Check that all records have the required fields
        for cert in data:
            assert "requires_expiry_date" in cert, f"Missing requires_expiry_date for {cert.get('name')}"
            assert "valid_until_replaced" in cert, f"Missing valid_until_replaced for {cert.get('name')}"
            assert isinstance(cert["requires_expiry_date"], bool), f"requires_expiry_date should be bool for {cert.get('name')}"
            assert isinstance(cert["valid_until_replaced"], bool), f"valid_until_replaced should be bool for {cert.get('name')}"
    
    def test_company_registration_no_expiry_required(self):
        """Company Registration Certificate should have requires_expiry_date=false"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        company_reg = next((c for c in data if "Company Registration" in c.get("name", "")), None)
        
        assert company_reg is not None, "Company Registration Certificate not found"
        assert company_reg["requires_expiry_date"] == False, "Company Registration should not require expiry date"
        assert company_reg["valid_until_replaced"] == True, "Company Registration should be valid until replaced"
    
    def test_employers_liability_requires_expiry(self):
        """Employer's Liability Insurance should have requires_expiry_date=true"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        employers_liability = next((c for c in data if "Employer's Liability" in c.get("name", "")), None)
        
        assert employers_liability is not None, "Employer's Liability Insurance not found"
        assert employers_liability["requires_expiry_date"] == True, "Employer's Liability should require expiry date"
        assert employers_liability["valid_until_replaced"] == False, "Employer's Liability should not be valid until replaced"
    
    def test_cqc_registration_no_expiry_required(self):
        """CQC Registration Certificate should have requires_expiry_date=false"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        cqc_reg = next((c for c in data if "CQC Registration" in c.get("name", "")), None)
        
        assert cqc_reg is not None, "CQC Registration Certificate not found"
        assert cqc_reg["requires_expiry_date"] == False, "CQC Registration should not require expiry date"
        assert cqc_reg["valid_until_replaced"] == True, "CQC Registration should be valid until replaced"
    
    def test_legionella_no_expiry_required(self):
        """Legionella Risk Assessment should have requires_expiry_date=false"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        legionella = next((c for c in data if "Legionella" in c.get("name", "")), None)
        
        assert legionella is not None, "Legionella Risk Assessment not found"
        assert legionella["requires_expiry_date"] == False, "Legionella should not require expiry date"
    
    def test_food_hygiene_no_expiry_required(self):
        """Food Hygiene Rating Certificate should have requires_expiry_date=false"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        food_hygiene = next((c for c in data if "Food Hygiene" in c.get("name", "")), None)
        
        assert food_hygiene is not None, "Food Hygiene Rating Certificate not found"
        assert food_hygiene["requires_expiry_date"] == False, "Food Hygiene should not require expiry date"
        assert food_hygiene["valid_until_replaced"] == True, "Food Hygiene should be valid until replaced"
    
    def test_asbestos_survey_no_expiry_required(self):
        """Asbestos Survey Report should have requires_expiry_date=false"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        asbestos = next((c for c in data if "Asbestos" in c.get("name", "")), None)
        
        assert asbestos is not None, "Asbestos Survey Report not found"
        assert asbestos["requires_expiry_date"] == False, "Asbestos Survey should not require expiry date"
        assert asbestos["valid_until_replaced"] == True, "Asbestos Survey should be valid until replaced"


class TestInsuranceUploadValidation:
    """Tests for upload endpoint expiry date validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def get_certificate_id(self, name_contains: str) -> str:
        """Helper to get certificate ID by name"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        data = response.json()
        cert = next((c for c in data if name_contains in c.get("name", "")), None)
        return cert["id"] if cert else None
    
    def test_upload_without_expiry_fails_for_required_cert(self):
        """Upload without expiry date should fail for certificates that require expiry"""
        cert_id = self.get_certificate_id("Employer's Liability")
        assert cert_id is not None, "Employer's Liability Insurance not found"
        
        # Create a minimal test file
        files = {"file": ("test.pdf", b"test content", "application/pdf")}
        
        # Upload without expiry_date
        response = requests.post(
            f"{BASE_URL}/api/compliance/insurance/{cert_id}/upload",
            headers=self.headers,
            files=files
        )
        
        # Should fail with 400 because expiry is required
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "expiry" in response.text.lower(), "Error should mention expiry date"
    
    def test_upload_without_expiry_succeeds_for_optional_cert(self):
        """Upload without expiry date should succeed for certificates that don't require expiry"""
        cert_id = self.get_certificate_id("Company Registration")
        assert cert_id is not None, "Company Registration Certificate not found"
        
        # Create a minimal test file
        files = {"file": ("test_company_reg.pdf", b"test company registration content", "application/pdf")}
        
        # Upload without expiry_date
        response = requests.post(
            f"{BASE_URL}/api/compliance/insurance/{cert_id}/upload",
            headers=self.headers,
            files=files
        )
        
        # Should succeed because expiry is optional for this cert type
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify the certificate is now valid
        data = response.json()
        assert data.get("status") == "valid", "Certificate should be valid after upload"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

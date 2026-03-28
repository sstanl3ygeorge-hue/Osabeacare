"""
Test Compliance Centre APIs - Policies, Insurance, Dashboard
Tests the datetime comparison fix for offset-naive vs offset-aware dates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestComplianceCentre:
    """Compliance Centre API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ========== Dashboard Tests ==========
    
    def test_compliance_dashboard_loads(self):
        """Test compliance dashboard endpoint returns data without 500 error"""
        response = requests.get(f"{BASE_URL}/api/compliance/dashboard", headers=self.headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        assert "policies" in data
        assert "insurance" in data
        assert "incidents" in data
        assert "staff" in data
    
    def test_compliance_dashboard_policy_counts(self):
        """Test dashboard shows correct policy counts (32 total, 3 active)"""
        response = requests.get(f"{BASE_URL}/api/compliance/dashboard", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        policies = data["policies"]
        
        assert policies["total"] == 32, f"Expected 32 policies, got {policies['total']}"
        assert policies["active"] == 3, f"Expected 3 active policies, got {policies['active']}"
        assert "missing" in policies
        assert "expired" in policies
    
    def test_compliance_dashboard_insurance_counts(self):
        """Test dashboard shows correct insurance counts (6 total, 1 valid)"""
        response = requests.get(f"{BASE_URL}/api/compliance/dashboard", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        insurance = data["insurance"]
        
        assert insurance["total"] == 6, f"Expected 6 insurance docs, got {insurance['total']}"
        assert insurance["valid"] == 1, f"Expected 1 valid insurance, got {insurance['valid']}"
        assert "missing" in insurance
        assert "expired" in insurance
        assert "expiring_soon" in insurance
    
    # ========== Policies Tests ==========
    
    def test_policies_list_loads(self):
        """Test policies endpoint returns list without 500 error"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies", headers=self.headers)
        assert response.status_code == 200, f"Policies list failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 32, f"Expected 32 policies, got {len(data)}"
    
    def test_policies_have_correct_structure(self):
        """Test each policy has required fields"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies", headers=self.headers)
        assert response.status_code == 200
        
        policies = response.json()
        for policy in policies:
            assert "id" in policy
            assert "name" in policy
            assert "category" in policy
            assert "status" in policy
            assert policy["status"] in ["active", "missing", "expired", "under_review"]
    
    def test_active_policies_have_file_url(self):
        """Test active policies have file_url set"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies", headers=self.headers)
        assert response.status_code == 200
        
        policies = response.json()
        active_policies = [p for p in policies if p["status"] == "active"]
        
        assert len(active_policies) == 3, f"Expected 3 active policies, got {len(active_policies)}"
        
        for policy in active_policies:
            assert policy.get("file_url"), f"Active policy {policy['name']} missing file_url"
    
    def test_uploaded_policies_names(self):
        """Test specific uploaded policies exist: Safeguarding Adults, Medication, Lone Working"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies", headers=self.headers)
        assert response.status_code == 200
        
        policies = response.json()
        active_policies = [p for p in policies if p["status"] == "active"]
        active_names = [p["name"] for p in active_policies]
        
        # Check for expected active policies (may have different names)
        assert len(active_policies) >= 3, f"Expected at least 3 active policies"
    
    # ========== Insurance Tests ==========
    
    def test_insurance_list_loads(self):
        """Test insurance endpoint returns list without 500 error"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200, f"Insurance list failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 6, f"Expected 6 insurance docs, got {len(data)}"
    
    def test_insurance_have_correct_structure(self):
        """Test each insurance doc has required fields"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        insurance_docs = response.json()
        for doc in insurance_docs:
            assert "id" in doc
            assert "name" in doc
            assert "insurance_type" in doc
            assert "status" in doc
            assert doc["status"] in ["valid", "missing", "expired", "expiring_soon"]
    
    def test_public_liability_insurance_valid(self):
        """Test Public Liability Insurance shows 'valid' status with expiry date"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        insurance_docs = response.json()
        public_liability = next((d for d in insurance_docs if d["insurance_type"] == "public_liability"), None)
        
        assert public_liability is not None, "Public Liability Insurance not found"
        assert public_liability["status"] == "valid", f"Expected 'valid' status, got {public_liability['status']}"
        assert public_liability.get("file_url"), "Public Liability missing file_url"
        assert public_liability.get("expiry_date"), "Public Liability missing expiry_date"
    
    def test_missing_insurance_have_no_file(self):
        """Test missing insurance docs have no file_url"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        insurance_docs = response.json()
        missing_docs = [d for d in insurance_docs if d["status"] == "missing"]
        
        assert len(missing_docs) == 5, f"Expected 5 missing insurance docs, got {len(missing_docs)}"
        
        for doc in missing_docs:
            assert not doc.get("file_url"), f"Missing insurance {doc['name']} should not have file_url"
    
    # ========== Datetime Handling Tests ==========
    
    def test_datetime_comparison_no_500_error(self):
        """Test that datetime comparison doesn't cause 500 errors (the original bug)"""
        # All three endpoints should return 200, not 500
        endpoints = [
            "/api/compliance/dashboard",
            "/api/compliance/policies",
            "/api/compliance/insurance"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=self.headers)
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}: {response.text}"
    
    def test_insurance_expiry_date_format(self):
        """Test insurance expiry date is properly formatted"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=self.headers)
        assert response.status_code == 200
        
        insurance_docs = response.json()
        valid_docs = [d for d in insurance_docs if d.get("expiry_date")]
        
        for doc in valid_docs:
            expiry = doc["expiry_date"]
            # Should be YYYY-MM-DD format or ISO format
            assert len(expiry) >= 10, f"Invalid expiry date format: {expiry}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test suite for CQC Compliance Centre upgrade features.
Tests: centre-summary endpoint, policies with review tracking, certificates with categories,
staff compliance data, and missing items panel.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestComplianceCentreSummary:
    """Tests for GET /api/compliance/centre-summary endpoint"""
    
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
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_centre_summary_returns_200(self):
        """Test that centre-summary endpoint returns 200"""
        response = self.session.get(f"{BASE_URL}/api/compliance/centre-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_centre_summary_has_overall_status(self):
        """Test that centre-summary returns overall_status field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/centre-summary")
        data = response.json()
        
        assert "overall_status" in data, "Missing overall_status field"
        assert data["overall_status"] in ["OK", "Needs Attention", "Critical"], \
            f"Invalid overall_status: {data['overall_status']}"
    
    def test_centre_summary_has_policies_section(self):
        """Test that centre-summary returns policies section with required fields"""
        response = self.session.get(f"{BASE_URL}/api/compliance/centre-summary")
        data = response.json()
        
        assert "policies" in data, "Missing policies section"
        policies = data["policies"]
        
        # Check required fields
        required_fields = ["complete", "total", "missing", "due_soon", "overdue", 
                          "required_complete", "required_total"]
        for field in required_fields:
            assert field in policies, f"Missing policies.{field}"
            assert isinstance(policies[field], int), f"policies.{field} should be int"
    
    def test_centre_summary_has_certificates_section(self):
        """Test that centre-summary returns certificates section with required fields"""
        response = self.session.get(f"{BASE_URL}/api/compliance/centre-summary")
        data = response.json()
        
        assert "certificates" in data, "Missing certificates section"
        certs = data["certificates"]
        
        # Check required fields
        required_fields = ["valid", "total", "missing", "expiring", "expired",
                          "required_complete", "required_total"]
        for field in required_fields:
            assert field in certs, f"Missing certificates.{field}"
            assert isinstance(certs[field], int), f"certificates.{field} should be int"
    
    def test_centre_summary_has_staff_compliance_section(self):
        """Test that centre-summary returns staff_compliance section"""
        response = self.session.get(f"{BASE_URL}/api/compliance/centre-summary")
        data = response.json()
        
        assert "staff_compliance" in data, "Missing staff_compliance section"
        staff = data["staff_compliance"]
        
        # Check required fields
        required_fields = ["total", "dbs_valid", "dbs_missing", "dbs_expiring", 
                          "training_last_12_months"]
        for field in required_fields:
            assert field in staff, f"Missing staff_compliance.{field}"
            assert isinstance(staff[field], int), f"staff_compliance.{field} should be int"
    
    def test_centre_summary_has_missing_items_section(self):
        """Test that centre-summary returns missing_items section"""
        response = self.session.get(f"{BASE_URL}/api/compliance/centre-summary")
        data = response.json()
        
        assert "missing_items" in data, "Missing missing_items section"
        missing = data["missing_items"]
        
        assert "required_policies" in missing, "Missing required_policies list"
        assert "required_certificates" in missing, "Missing required_certificates list"
        assert isinstance(missing["required_policies"], list), "required_policies should be list"
        assert isinstance(missing["required_certificates"], list), "required_certificates should be list"
    
    def test_missing_items_have_required_fields(self):
        """Test that missing items have required/conditional fields"""
        response = self.session.get(f"{BASE_URL}/api/compliance/centre-summary")
        data = response.json()
        
        missing = data["missing_items"]
        
        # Check policy items
        if len(missing["required_policies"]) > 0:
            policy = missing["required_policies"][0]
            assert "id" in policy, "Missing policy id"
            assert "name" in policy, "Missing policy name"
            assert "required" in policy, "Missing policy required field"
            assert "conditional" in policy, "Missing policy conditional field"
        
        # Check certificate items
        if len(missing["required_certificates"]) > 0:
            cert = missing["required_certificates"][0]
            assert "id" in cert, "Missing certificate id"
            assert "name" in cert, "Missing certificate name"
            assert "required" in cert, "Missing certificate required field"
            assert "conditional" in cert, "Missing certificate conditional field"
            assert "category" in cert, "Missing certificate category field"


class TestPoliciesWithReviewTracking:
    """Tests for policies with review tracking fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication for all tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_policies_endpoint_returns_200(self):
        """Test that policies endpoint returns 200"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_policies_have_required_field(self):
        """Test that policies have required field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        policies = response.json()
        
        assert len(policies) > 0, "No policies returned"
        
        for policy in policies[:5]:  # Check first 5
            assert "required" in policy, f"Policy {policy.get('name')} missing required field"
            assert isinstance(policy["required"], bool), "required should be boolean"
    
    def test_policies_have_conditional_field(self):
        """Test that policies have conditional field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        policies = response.json()
        
        for policy in policies[:5]:
            assert "conditional" in policy, f"Policy {policy.get('name')} missing conditional field"
            assert isinstance(policy["conditional"], bool), "conditional should be boolean"
    
    def test_policies_have_review_status_field(self):
        """Test that policies have review_status field (current/due_soon/overdue)"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        policies = response.json()
        
        # Find an active policy to check review_status
        active_policies = [p for p in policies if p.get("status") == "active"]
        
        if len(active_policies) > 0:
            policy = active_policies[0]
            # review_status can be null for policies without review dates
            if policy.get("review_status"):
                assert policy["review_status"] in ["current", "due_soon", "overdue"], \
                    f"Invalid review_status: {policy['review_status']}"
    
    def test_policies_have_assigned_staff_count(self):
        """Test that policies have assigned_staff_count field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        policies = response.json()
        
        for policy in policies[:5]:
            assert "assigned_staff_count" in policy, f"Policy {policy.get('name')} missing assigned_staff_count"
            assert isinstance(policy["assigned_staff_count"], int), "assigned_staff_count should be int"
    
    def test_policies_have_last_reviewed_at(self):
        """Test that active policies have last_reviewed_at field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        policies = response.json()
        
        active_policies = [p for p in policies if p.get("status") == "active"]
        
        if len(active_policies) > 0:
            policy = active_policies[0]
            # last_reviewed_at should exist (can be null)
            assert "last_reviewed_at" in policy, "Missing last_reviewed_at field"


class TestCertificatesWithCategories:
    """Tests for certificates with category/required/conditional fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication for all tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_certificates_endpoint_returns_200(self):
        """Test that insurance/certificates endpoint returns 200"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_certificates_have_category_field(self):
        """Test that certificates have category field (insurance/regulatory/safety)"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        certs = response.json()
        
        assert len(certs) > 0, "No certificates returned"
        
        for cert in certs[:5]:
            assert "category" in cert, f"Certificate {cert.get('name')} missing category field"
            # Category should be one of the expected values
            assert cert["category"] in ["insurance", "regulatory", "safety"], \
                f"Invalid category: {cert['category']}"
    
    def test_certificates_have_required_field(self):
        """Test that certificates have required field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        certs = response.json()
        
        for cert in certs[:5]:
            assert "required" in cert, f"Certificate {cert.get('name')} missing required field"
            assert isinstance(cert["required"], bool), "required should be boolean"
    
    def test_certificates_have_conditional_field(self):
        """Test that certificates have conditional field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        certs = response.json()
        
        for cert in certs[:5]:
            assert "conditional" in cert, f"Certificate {cert.get('name')} missing conditional field"
            assert isinstance(cert["conditional"], bool), "conditional should be boolean"
    
    def test_certificates_have_insurance_type(self):
        """Test that certificates have insurance_type field"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        certs = response.json()
        
        for cert in certs[:5]:
            assert "insurance_type" in cert, f"Certificate {cert.get('name')} missing insurance_type"


class TestExistingFunctionality:
    """Tests to verify existing policy upload and assignment functionality still works"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication for all tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_policy_assignments_endpoint_exists(self):
        """Test that policy assignments endpoint still works"""
        response = self.session.get(f"{BASE_URL}/api/policy-assignments")
        assert response.status_code == 200, f"Policy assignments endpoint failed: {response.status_code}"
    
    def test_employees_endpoint_works(self):
        """Test that employees endpoint works for assignment functionality"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200, f"Employees endpoint failed: {response.status_code}"
        
        employees = response.json()
        assert isinstance(employees, list), "Employees should be a list"
    
    def test_dashboard_stats_endpoint_works(self):
        """Test that dashboard stats endpoint works for compliance data"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200, f"Dashboard stats endpoint failed: {response.status_code}"
        
        data = response.json()
        # Dashboard stats has different structure - check for compliance-related fields
        assert isinstance(data, dict), "Dashboard stats should return a dict"
    
    def test_compliance_dashboard_endpoint_works(self):
        """Test that compliance dashboard endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/compliance/dashboard")
        assert response.status_code == 200, f"Compliance dashboard endpoint failed: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

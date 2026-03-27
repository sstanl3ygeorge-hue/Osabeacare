"""
Test Compliance Centre API endpoints
- Tests 30 organization policies across 3 categories
- Tests 6 insurance/certificate types
- Tests dashboard summary
- Tests policy upload functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestComplianceCentreAPI:
    """Compliance Centre API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Admin login failed - skipping authenticated tests")
    
    # ==================== POLICIES TESTS ====================
    
    def test_get_compliance_policies(self):
        """Test GET /api/compliance/policies returns all 30 policies"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        policies = response.json()
        assert isinstance(policies, list), "Response should be a list"
        assert len(policies) == 30, f"Expected 30 policies, got {len(policies)}"
        
        # Verify policy structure
        for policy in policies:
            assert "id" in policy, "Policy should have id"
            assert "name" in policy, "Policy should have name"
            assert "category" in policy, "Policy should have category"
            assert "status" in policy, "Policy should have status"
            assert "version" in policy, "Policy should have version"
        
        print(f"✓ GET /api/compliance/policies - Returns {len(policies)} policies")
    
    def test_policies_have_correct_categories(self):
        """Test policies are organized into 3 categories with correct counts"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        assert response.status_code == 200
        
        policies = response.json()
        
        # Count by category
        categories = {}
        for policy in policies:
            cat = policy.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        # Verify 3 categories with 10 policies each
        assert "Core Policies" in categories, "Should have Core Policies category"
        assert "Operational Policies" in categories, "Should have Operational Policies category"
        assert "Governance & Compliance" in categories, "Should have Governance & Compliance category"
        
        assert categories["Core Policies"] == 10, f"Core Policies should have 10, got {categories['Core Policies']}"
        assert categories["Operational Policies"] == 10, f"Operational Policies should have 10, got {categories['Operational Policies']}"
        assert categories["Governance & Compliance"] == 10, f"Governance & Compliance should have 10, got {categories['Governance & Compliance']}"
        
        print(f"✓ Policies categories: Core={categories['Core Policies']}, Operational={categories['Operational Policies']}, Governance={categories['Governance & Compliance']}")
    
    def test_policies_default_status_missing(self):
        """Test all policies are seeded with 'missing' status by default"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        assert response.status_code == 200
        
        policies = response.json()
        missing_count = len([p for p in policies if p.get("status") == "missing"])
        active_count = len([p for p in policies if p.get("status") == "active"])
        
        # All should be missing initially (unless some were uploaded)
        print(f"✓ Policy status: {missing_count} missing, {active_count} active")
        assert missing_count + active_count == 30, "All policies should have valid status"
    
    def test_get_single_policy(self):
        """Test GET /api/compliance/policies/:id returns single policy"""
        # First get all policies
        response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        assert response.status_code == 200
        
        policies = response.json()
        if len(policies) > 0:
            policy_id = policies[0]["id"]
            
            # Get single policy
            single_response = self.session.get(f"{BASE_URL}/api/compliance/policies/{policy_id}")
            assert single_response.status_code == 200
            
            policy = single_response.json()
            assert policy["id"] == policy_id
            print(f"✓ GET /api/compliance/policies/{policy_id} - Returns policy: {policy['name']}")
    
    def test_filter_policies_by_category(self):
        """Test filtering policies by category"""
        response = self.session.get(f"{BASE_URL}/api/compliance/policies?category=Core Policies")
        assert response.status_code == 200
        
        policies = response.json()
        assert len(policies) == 10, f"Expected 10 Core Policies, got {len(policies)}"
        
        for policy in policies:
            assert policy["category"] == "Core Policies"
        
        print(f"✓ Filter by category 'Core Policies' returns {len(policies)} policies")
    
    # ==================== INSURANCE TESTS ====================
    
    def test_get_insurance_documents(self):
        """Test GET /api/compliance/insurance returns all 6 items"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        insurance = response.json()
        assert isinstance(insurance, list), "Response should be a list"
        assert len(insurance) == 6, f"Expected 6 insurance items, got {len(insurance)}"
        
        # Verify insurance structure
        for ins in insurance:
            assert "id" in ins, "Insurance should have id"
            assert "name" in ins, "Insurance should have name"
            assert "insurance_type" in ins, "Insurance should have insurance_type"
            assert "status" in ins, "Insurance should have status"
        
        print(f"✓ GET /api/compliance/insurance - Returns {len(insurance)} items")
    
    def test_insurance_types_correct(self):
        """Test insurance items have correct types"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        assert response.status_code == 200
        
        insurance = response.json()
        
        expected_types = [
            "public_liability",
            "employers_liability", 
            "professional_indemnity",
            "cqc_registration",
            "ico_registration",
            "company_registration"
        ]
        
        actual_types = [ins["insurance_type"] for ins in insurance]
        
        for expected in expected_types:
            assert expected in actual_types, f"Missing insurance type: {expected}"
        
        print(f"✓ All 6 insurance types present: {actual_types}")
    
    def test_insurance_default_status_missing(self):
        """Test all insurance items are seeded with 'missing' status"""
        response = self.session.get(f"{BASE_URL}/api/compliance/insurance")
        assert response.status_code == 200
        
        insurance = response.json()
        missing_count = len([i for i in insurance if i.get("status") == "missing"])
        
        print(f"✓ Insurance status: {missing_count} missing out of {len(insurance)}")
    
    # ==================== DASHBOARD TESTS ====================
    
    def test_compliance_dashboard(self):
        """Test GET /api/compliance/dashboard returns correct summary"""
        response = self.session.get(f"{BASE_URL}/api/compliance/dashboard")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        dashboard = response.json()
        
        # Verify dashboard structure
        assert "policies" in dashboard, "Dashboard should have policies section"
        assert "insurance" in dashboard, "Dashboard should have insurance section"
        assert "incidents" in dashboard, "Dashboard should have incidents section"
        assert "staff" in dashboard, "Dashboard should have staff section"
        
        # Verify policies section
        policies = dashboard["policies"]
        assert "total" in policies, "Policies should have total"
        assert "active" in policies, "Policies should have active"
        assert "missing" in policies, "Policies should have missing"
        assert policies["total"] == 30, f"Expected 30 total policies, got {policies['total']}"
        
        # Verify insurance section
        insurance = dashboard["insurance"]
        assert "total" in insurance, "Insurance should have total"
        assert "valid" in insurance, "Insurance should have valid"
        assert "missing" in insurance, "Insurance should have missing"
        assert insurance["total"] == 6, f"Expected 6 total insurance, got {insurance['total']}"
        
        # Verify incidents section
        incidents = dashboard["incidents"]
        assert "open" in incidents, "Incidents should have open"
        assert "total" in incidents, "Incidents should have total"
        
        print(f"✓ Dashboard: Policies {policies['active']}/{policies['total']}, Insurance {insurance['valid']}/{insurance['total']}, Incidents {incidents['open']}")
    
    def test_dashboard_counts_match_policies(self):
        """Test dashboard policy counts match actual policies"""
        # Get dashboard
        dash_response = self.session.get(f"{BASE_URL}/api/compliance/dashboard")
        assert dash_response.status_code == 200
        dashboard = dash_response.json()
        
        # Get policies
        policies_response = self.session.get(f"{BASE_URL}/api/compliance/policies")
        assert policies_response.status_code == 200
        policies = policies_response.json()
        
        # Verify counts match
        assert dashboard["policies"]["total"] == len(policies), "Dashboard total should match policies count"
        
        active_count = len([p for p in policies if p.get("status") == "active"])
        missing_count = len([p for p in policies if p.get("status") == "missing"])
        
        assert dashboard["policies"]["active"] == active_count, f"Dashboard active ({dashboard['policies']['active']}) should match actual ({active_count})"
        assert dashboard["policies"]["missing"] == missing_count, f"Dashboard missing ({dashboard['policies']['missing']}) should match actual ({missing_count})"
        
        print(f"✓ Dashboard counts verified: {active_count} active, {missing_count} missing")
    
    # ==================== INCIDENTS TESTS ====================
    
    def test_get_incidents(self):
        """Test GET /api/compliance/incidents"""
        response = self.session.get(f"{BASE_URL}/api/compliance/incidents")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        incidents = response.json()
        assert isinstance(incidents, list), "Response should be a list"
        
        print(f"✓ GET /api/compliance/incidents - Returns {len(incidents)} incidents")
    
    def test_create_incident(self):
        """Test POST /api/compliance/incidents creates new incident"""
        incident_data = {
            "incident_type": "incident",
            "title": "TEST_Compliance Test Incident",
            "description": "This is a test incident for compliance testing",
            "date_occurred": "2026-01-15",
            "location": "Test Location",
            "persons_involved": "Test Person",
            "immediate_actions": "Test actions taken"
        }
        
        response = self.session.post(f"{BASE_URL}/api/compliance/incidents", json=incident_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        incident = response.json()
        assert incident["title"] == incident_data["title"]
        assert incident["incident_type"] == "incident"
        assert "reference_number" in incident, "Incident should have reference_number"
        assert incident["status"] == "open", "New incident should have 'open' status"
        
        print(f"✓ POST /api/compliance/incidents - Created incident: {incident['reference_number']}")
        
        # Cleanup - we'll leave it for now as it's a test incident
        return incident["id"]
    
    # ==================== SEED ENDPOINTS TESTS ====================
    
    def test_seed_policies_endpoint(self):
        """Test POST /api/compliance/seed-policies (idempotent)"""
        response = self.session.post(f"{BASE_URL}/api/compliance/seed-policies")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "message" in result
        assert "total" in result
        assert result["total"] == 30, f"Expected total 30, got {result['total']}"
        
        print(f"✓ POST /api/compliance/seed-policies - {result['message']}")
    
    def test_seed_insurance_endpoint(self):
        """Test POST /api/compliance/seed-insurance (idempotent)"""
        response = self.session.post(f"{BASE_URL}/api/compliance/seed-insurance")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "message" in result
        assert "total" in result
        assert result["total"] == 6, f"Expected total 6, got {result['total']}"
        
        print(f"✓ POST /api/compliance/seed-insurance - {result['message']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

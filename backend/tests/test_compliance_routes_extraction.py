"""
Test Suite: Compliance Routes Extraction (Phase 10)

Tests the newly extracted compliance routes module (routes/compliance.py):
- Organization policies management (CRUD, upload, review tracking)
- Insurance/certificates management (CRUD, upload, expiry tracking)
- Incident logs management (CRUD, audit trail)
- Compliance reports (staff-dbs, training)

Also verifies:
- No route collisions between compliance.py and server.py
- Existing compliance routes in server.py still work (dashboard, centre-summary)
- Previous routes still working (email/templates, references status, auth)
"""

import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestAuthLogin:
    """Test auth login to get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login_success(self, auth_token):
        """Verify login returns valid token"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Auth login successful, token obtained")


class TestCompliancePoliciesRoutes:
    """Test compliance policies routes from routes/compliance.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_policies_requires_auth(self):
        """GET /api/compliance/policies requires authentication"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies")
        assert response.status_code == 401
        print("✓ GET /api/compliance/policies requires auth")
    
    def test_get_policies_with_auth(self, headers):
        """GET /api/compliance/policies returns list of policies"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/policies returned {len(data)} policies")
    
    def test_get_policies_filter_by_category(self, headers):
        """GET /api/compliance/policies supports category filter"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies?category=Core",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # If there are results, verify they match the filter
        for policy in data:
            assert policy.get("category") == "Core"
        print(f"✓ GET /api/compliance/policies?category=Core returned {len(data)} policies")
    
    def test_get_policies_filter_by_status(self, headers):
        """GET /api/compliance/policies supports status filter"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies?status=missing",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/policies?status=missing returned {len(data)} policies")
    
    def test_get_policy_not_found(self, headers):
        """GET /api/compliance/policies/{policy_id} returns 404 for non-existent"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies/non-existent-id",
            headers=headers
        )
        assert response.status_code == 404
        print("✓ GET /api/compliance/policies/{policy_id} returns 404 for non-existent")


class TestComplianceInsuranceRoutes:
    """Test compliance insurance routes from routes/compliance.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_insurance_requires_auth(self):
        """GET /api/compliance/insurance requires authentication"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance")
        assert response.status_code == 401
        print("✓ GET /api/compliance/insurance requires auth")
    
    def test_get_insurance_with_auth(self, headers):
        """GET /api/compliance/insurance returns list of insurance docs"""
        response = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/insurance returned {len(data)} documents")
    
    def test_get_insurance_filter_by_category(self, headers):
        """GET /api/compliance/insurance supports category filter"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/insurance?category=insurance",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/insurance?category=insurance returned {len(data)} docs")
    
    def test_get_insurance_filter_by_status(self, headers):
        """GET /api/compliance/insurance supports status filter"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/insurance?status=missing",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/insurance?status=missing returned {len(data)} docs")


class TestComplianceIncidentsRoutes:
    """Test compliance incidents routes from routes/compliance.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_incidents_requires_auth(self):
        """GET /api/compliance/incidents requires authentication"""
        response = requests.get(f"{BASE_URL}/api/compliance/incidents")
        assert response.status_code == 401
        print("✓ GET /api/compliance/incidents requires auth")
    
    def test_get_incidents_with_auth(self, headers):
        """GET /api/compliance/incidents returns list of incidents"""
        response = requests.get(f"{BASE_URL}/api/compliance/incidents", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/incidents returned {len(data)} incidents")
    
    def test_get_incidents_filter_by_type(self, headers):
        """GET /api/compliance/incidents supports incident_type filter"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/incidents?incident_type=incident",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/incidents?incident_type=incident returned {len(data)} incidents")
    
    def test_get_incidents_filter_by_status(self, headers):
        """GET /api/compliance/incidents supports status filter"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/incidents?status=open",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/compliance/incidents?status=open returned {len(data)} incidents")


class TestComplianceReportsRoutes:
    """Test compliance reports routes from routes/compliance.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_staff_dbs_report_requires_admin(self):
        """GET /api/compliance/reports/staff-dbs requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/compliance/reports/staff-dbs")
        assert response.status_code == 401
        print("✓ GET /api/compliance/reports/staff-dbs requires auth")
    
    def test_staff_dbs_report_with_auth(self, headers):
        """GET /api/compliance/reports/staff-dbs returns DBS report"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/reports/staff-dbs",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "employees" in data
        assert "total" in data
        assert isinstance(data["employees"], list)
        print(f"✓ GET /api/compliance/reports/staff-dbs returned {data['total']} employees")
    
    def test_training_report_requires_admin(self):
        """GET /api/compliance/reports/training requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/compliance/reports/training")
        assert response.status_code == 401
        print("✓ GET /api/compliance/reports/training requires auth")
    
    def test_training_report_with_auth(self, headers):
        """GET /api/compliance/reports/training returns training report"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/reports/training",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "employees" in data
        assert "total" in data
        assert isinstance(data["employees"], list)
        print(f"✓ GET /api/compliance/reports/training returned {data['total']} employees")


class TestComplianceDashboardServerPy:
    """Test compliance dashboard routes that remain in server.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_compliance_dashboard_requires_auth(self):
        """GET /api/compliance/dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/compliance/dashboard")
        assert response.status_code == 401
        print("✓ GET /api/compliance/dashboard requires auth")
    
    def test_compliance_dashboard_with_auth(self, headers):
        """GET /api/compliance/dashboard returns dashboard data"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/dashboard",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        # Verify expected structure
        assert isinstance(data, dict)
        print(f"✓ GET /api/compliance/dashboard returned data with keys: {list(data.keys())[:5]}...")
    
    def test_compliance_centre_summary_requires_auth(self):
        """GET /api/compliance/centre-summary requires authentication"""
        response = requests.get(f"{BASE_URL}/api/compliance/centre-summary")
        assert response.status_code == 401
        print("✓ GET /api/compliance/centre-summary requires auth")
    
    def test_compliance_centre_summary_with_auth(self, headers):
        """GET /api/compliance/centre-summary returns summary data"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/centre-summary",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        print(f"✓ GET /api/compliance/centre-summary returned data with keys: {list(data.keys())[:5]}...")


class TestPreviousRoutesStillWorking:
    """Verify previous routes still work after compliance extraction"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_email_templates_still_works(self, headers):
        """GET /api/email/templates still works (from notifications.py)"""
        response = requests.get(f"{BASE_URL}/api/email/templates", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"✓ GET /api/email/templates still works - {len(data['templates'])} templates")
    
    def test_references_status_still_works(self, headers):
        """GET /api/references/{employee_id}/status returns 404 for non-existent (from references.py)"""
        response = requests.get(
            f"{BASE_URL}/api/references/non-existent-id/status",
            headers=headers
        )
        assert response.status_code == 404
        print("✓ GET /api/references/{employee_id}/status still works (404 for non-existent)")
    
    def test_dashboard_stats_still_works(self, headers):
        """GET /api/dashboard/stats still works (from server.py)"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        print(f"✓ GET /api/dashboard/stats still works")
    
    def test_employees_list_still_works(self, headers):
        """GET /api/employees still works (from employees.py)"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/employees still works - {len(data)} employees")


class TestNoRouteCollisions:
    """Verify no route collisions between compliance.py and server.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_policies_and_dashboard_both_work(self, headers):
        """Both /compliance/policies (compliance.py) and /compliance/dashboard (server.py) work"""
        # From compliance.py
        resp1 = requests.get(f"{BASE_URL}/api/compliance/policies", headers=headers)
        assert resp1.status_code == 200
        
        # From server.py
        resp2 = requests.get(f"{BASE_URL}/api/compliance/dashboard", headers=headers)
        assert resp2.status_code == 200
        
        print("✓ No collision: /compliance/policies and /compliance/dashboard both work")
    
    def test_insurance_and_centre_summary_both_work(self, headers):
        """Both /compliance/insurance (compliance.py) and /compliance/centre-summary (server.py) work"""
        # From compliance.py
        resp1 = requests.get(f"{BASE_URL}/api/compliance/insurance", headers=headers)
        assert resp1.status_code == 200
        
        # From server.py
        resp2 = requests.get(f"{BASE_URL}/api/compliance/centre-summary", headers=headers)
        assert resp2.status_code == 200
        
        print("✓ No collision: /compliance/insurance and /compliance/centre-summary both work")
    
    def test_incidents_and_reports_both_work(self, headers):
        """Both /compliance/incidents and /compliance/reports/* work"""
        # From compliance.py
        resp1 = requests.get(f"{BASE_URL}/api/compliance/incidents", headers=headers)
        assert resp1.status_code == 200
        
        resp2 = requests.get(f"{BASE_URL}/api/compliance/reports/staff-dbs", headers=headers)
        assert resp2.status_code == 200
        
        resp3 = requests.get(f"{BASE_URL}/api/compliance/reports/training", headers=headers)
        assert resp3.status_code == 200
        
        print("✓ No collision: /compliance/incidents and /compliance/reports/* all work")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

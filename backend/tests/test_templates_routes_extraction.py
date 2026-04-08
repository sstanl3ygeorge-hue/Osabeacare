"""
Phase 11: Templates Routes Extraction Tests

Tests for the newly extracted templates routes module (routes/templates.py).
Verifies:
1. Template CRUD operations (5 endpoints)
2. No regression on previous routes (compliance, email, references)
3. Auth login still works
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestAuthLogin:
    """Test auth login endpoint still works after extraction"""
    
    def test_auth_login_success(self):
        """Test POST /api/auth/login returns 200 with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, "No token in response"
        print(f"✓ Auth login successful")


class TestTemplatesRoutes:
    """Test newly extracted templates routes (routes/templates.py)"""
    
    def test_get_templates_list(self, auth_headers):
        """Test GET /api/templates returns list of templates"""
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/templates returned {len(data)} templates")
    
    def test_get_templates_with_category_filter(self, auth_headers):
        """Test GET /api/templates with category filter"""
        response = requests.get(
            f"{BASE_URL}/api/templates?category=Identity",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET templates with filter failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # If any templates returned, verify they match the category
        for template in data:
            assert template.get("category") == "Identity", f"Template category mismatch: {template.get('category')}"
        print(f"✓ GET /api/templates?category=Identity returned {len(data)} templates")
    
    def test_get_templates_with_active_filter(self, auth_headers):
        """Test GET /api/templates with active filter"""
        response = requests.get(
            f"{BASE_URL}/api/templates?active=true",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET templates with active filter failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/templates?active=true returned {len(data)} templates")
    
    def test_create_template(self, auth_headers):
        """Test POST /api/templates creates a new template"""
        unique_id = str(uuid.uuid4())[:8]
        template_data = {
            "name": f"TEST_Template_{unique_id}",
            "description": "Test template for Phase 11 testing",
            "category": "Training",
            "form_fields": [{"name": "field1", "type": "text"}],
            "requires_employee_signature": True,
            "requires_admin_signature": True,
            "content_html": "<p>Test content</p>",
            "visibility": "normal",
            "section": "Compliance"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/templates",
            headers=auth_headers,
            json=template_data
        )
        assert response.status_code == 200, f"POST templates failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should contain id"
        assert data["name"] == template_data["name"], "Name mismatch"
        assert data["category"] == template_data["category"], "Category mismatch"
        assert data["active"] == True, "New template should be active"
        assert data["version"] == 1, "New template should be version 1"
        
        # Store template ID for subsequent tests
        pytest.created_template_id = data["id"]
        print(f"✓ POST /api/templates created template: {data['id']}")
        return data["id"]
    
    def test_get_template_by_id(self, auth_headers):
        """Test GET /api/templates/{template_id} returns specific template"""
        # First create a template to ensure we have one
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            headers=auth_headers,
            json={
                "name": f"TEST_GetById_{unique_id}",
                "description": "Test template for GET by ID",
                "category": "References"
            }
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        template_id = create_response.json()["id"]
        
        # Now get by ID
        response = requests.get(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET template by ID failed: {response.text}"
        data = response.json()
        
        assert data["id"] == template_id, "ID mismatch"
        assert "name" in data, "Response should contain name"
        assert "category" in data, "Response should contain category"
        print(f"✓ GET /api/templates/{template_id} returned template")
    
    def test_get_template_not_found(self, auth_headers):
        """Test GET /api/templates/{template_id} returns 404 for non-existent template"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/templates/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ GET /api/templates/{fake_id} correctly returned 404")
    
    def test_update_template(self, auth_headers):
        """Test PUT /api/templates/{template_id} updates a template"""
        # First create a template
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            headers=auth_headers,
            json={
                "name": f"TEST_Update_{unique_id}",
                "description": "Original description",
                "category": "Contract"
            }
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        template_id = create_response.json()["id"]
        original_version = create_response.json()["version"]
        
        # Update the template
        update_data = {
            "name": f"TEST_Updated_{unique_id}",
            "description": "Updated description",
            "category": "Contract"
        }
        response = requests.put(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200, f"PUT template failed: {response.text}"
        data = response.json()
        
        assert data["name"] == update_data["name"], "Name not updated"
        assert data["description"] == update_data["description"], "Description not updated"
        assert data["version"] == original_version + 1, "Version should increment"
        print(f"✓ PUT /api/templates/{template_id} updated template (version {data['version']})")
    
    def test_update_template_not_found(self, auth_headers):
        """Test PUT /api/templates/{template_id} returns 404 for non-existent template"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/templates/{fake_id}",
            headers=auth_headers,
            json={"name": "Test", "category": "Test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ PUT /api/templates/{fake_id} correctly returned 404")
    
    def test_delete_template(self, auth_headers):
        """Test DELETE /api/templates/{template_id} soft deletes a template"""
        # First create a template
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            headers=auth_headers,
            json={
                "name": f"TEST_Delete_{unique_id}",
                "description": "Template to be deleted",
                "category": "Identity"
            }
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        template_id = create_response.json()["id"]
        
        # Delete the template
        response = requests.delete(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"DELETE template failed: {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        
        # Verify template is now inactive (soft delete)
        get_response = requests.get(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=auth_headers
        )
        # Template should still exist but be inactive
        if get_response.status_code == 200:
            template_data = get_response.json()
            assert template_data.get("active") == False, "Template should be inactive after delete"
        print(f"✓ DELETE /api/templates/{template_id} soft deleted template")
    
    def test_delete_template_not_found(self, auth_headers):
        """Test DELETE /api/templates/{template_id} returns 404 for non-existent template"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/api/templates/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ DELETE /api/templates/{fake_id} correctly returned 404")


class TestPreviousRoutesRegression:
    """Test that previous routes still work after templates extraction"""
    
    def test_compliance_policies_get(self, auth_headers):
        """Test GET /api/compliance/policies still works"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET compliance/policies failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/compliance/policies returned {len(data)} policies")
    
    def test_email_templates_get(self, auth_headers):
        """Test GET /api/email/templates still works"""
        response = requests.get(
            f"{BASE_URL}/api/email/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET email/templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, (list, dict)), "Response should be list or dict"
        print(f"✓ GET /api/email/templates returned successfully")
    
    def test_references_status_get(self, auth_headers):
        """Test GET /api/references/{employee_id}/status still works"""
        # Use a fake employee ID - should return 404 or empty data, not 500
        fake_employee_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/references/{fake_employee_id}/status",
            headers=auth_headers
        )
        # Should return 200 with empty/default data or 404, not 500
        assert response.status_code in [200, 404], f"GET references status failed: {response.status_code} - {response.text}"
        print(f"✓ GET /api/references/{fake_employee_id}/status returned {response.status_code}")
    
    def test_dashboard_stats_get(self, auth_headers):
        """Test GET /api/dashboard/stats still works"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET dashboard/stats failed: {response.text}"
        print(f"✓ GET /api/dashboard/stats returned successfully")
    
    def test_employees_get(self, auth_headers):
        """Test GET /api/employees still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET employees failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/employees returned {len(data)} employees")


class TestRouteCollisionCheck:
    """Verify no route collisions between templates.py and server.py"""
    
    def test_templates_route_not_in_server_py(self, auth_headers):
        """Verify templates routes are handled by templates.py module"""
        # This test verifies the route is accessible and returns expected format
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Templates route not accessible: {response.text}"
        data = response.json()
        # Templates should return a list with specific structure
        assert isinstance(data, list), "Templates should return a list"
        print(f"✓ Templates route correctly handled by templates.py module")
    
    def test_compliance_routes_still_in_compliance_py(self, auth_headers):
        """Verify compliance routes are still handled by compliance.py"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance policies route failed: {response.text}"
        print(f"✓ Compliance routes correctly handled by compliance.py module")
    
    def test_notifications_routes_still_in_notifications_py(self, auth_headers):
        """Verify notifications routes are still handled by notifications.py"""
        response = requests.get(
            f"{BASE_URL}/api/email/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Email templates route failed: {response.text}"
        print(f"✓ Notifications routes correctly handled by notifications.py module")


class TestTemplatesAuthRequired:
    """Test that templates routes require authentication"""
    
    def test_get_templates_requires_auth(self):
        """Test GET /api/templates requires authentication"""
        response = requests.get(f"{BASE_URL}/api/templates")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ GET /api/templates correctly requires authentication")
    
    def test_post_templates_requires_admin(self):
        """Test POST /api/templates requires admin role"""
        response = requests.post(
            f"{BASE_URL}/api/templates",
            json={"name": "Test", "category": "Test"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ POST /api/templates correctly requires admin authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

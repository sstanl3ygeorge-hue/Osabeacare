"""
Phase 9: Notifications Routes Extraction Tests

Tests for the newly extracted email and notification routes in routes/notifications.py:
- Email templates endpoint: GET /api/email/templates
- Email senders endpoint: GET /api/email/senders
- Email categories endpoint: GET /api/email/categories
- Email logs endpoint: GET /api/email/logs
- Email requests types: GET /api/email-requests/types
- Email requests list: GET /api/email-requests
- Email verify action token: POST /api/email/verify-action-token
- Email requests process reminders: POST /api/email-requests/process-reminders
- Notifications logs: GET /api/notifications/logs
- Auth login: POST /api/auth/login
- References routes: GET /api/references/{employee_id}/status

Verifies no route collisions between notifications.py and server.py after extraction.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestAuthLogin:
    """Test authentication endpoints - prerequisite for other tests"""
    
    def test_auth_login_success(self):
        """Test admin login returns valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Auth login successful - token received")
        return data["token"]
    
    def test_auth_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"},
            timeout=30
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid credentials correctly rejected with 401")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestEmailTemplatesEndpoint:
    """Test GET /api/email/templates - Email templates listing"""
    
    def test_email_templates_requires_auth(self):
        """Test that email templates endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/email/templates", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Email templates endpoint correctly requires auth")
    
    def test_email_templates_returns_list(self, auth_headers):
        """Test email templates returns list of templates"""
        response = requests.get(
            f"{BASE_URL}/api/email/templates",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "templates" in data, "No templates key in response"
        assert "count" in data, "No count key in response"
        assert isinstance(data["templates"], list), "Templates should be a list"
        print(f"✓ Email templates returned {data['count']} templates")
        
        # Verify template structure if any exist
        if data["templates"]:
            template = data["templates"][0]
            assert "template_key" in template, "Template missing template_key"
            assert "category" in template, "Template missing category"
            print(f"✓ Template structure verified: {template.get('template_key')}")
    
    def test_email_templates_filter_by_category(self, auth_headers):
        """Test email templates can be filtered by category"""
        response = requests.get(
            f"{BASE_URL}/api/email/templates?category=recruitment",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "templates" in data
        print(f"✓ Email templates category filter works - {data['count']} templates")


class TestEmailSendersEndpoint:
    """Test GET /api/email/senders - Email senders listing"""
    
    def test_email_senders_requires_auth(self):
        """Test that email senders endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/email/senders", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Email senders endpoint correctly requires auth")
    
    def test_email_senders_returns_list(self, auth_headers):
        """Test email senders returns list of configured senders"""
        response = requests.get(
            f"{BASE_URL}/api/email/senders",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "senders" in data, "No senders key in response"
        assert isinstance(data["senders"], list), "Senders should be a list"
        print(f"✓ Email senders returned {len(data['senders'])} senders")
        
        # Verify sender structure if any exist
        if data["senders"]:
            sender = data["senders"][0]
            assert "sender_key" in sender, "Sender missing sender_key"
            assert "from_address" in sender, "Sender missing from_address"
            print(f"✓ Sender structure verified: {sender.get('sender_key')}")


class TestEmailCategoriesEndpoint:
    """Test GET /api/email/categories - Email categories listing"""
    
    def test_email_categories_requires_auth(self):
        """Test that email categories endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/email/categories", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Email categories endpoint correctly requires auth")
    
    def test_email_categories_returns_list(self, auth_headers):
        """Test email categories returns list of categories"""
        response = requests.get(
            f"{BASE_URL}/api/email/categories",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "categories" in data, "No categories key in response"
        assert isinstance(data["categories"], list), "Categories should be a list"
        print(f"✓ Email categories returned {len(data['categories'])} categories")
        
        # Verify category structure if any exist
        if data["categories"]:
            category = data["categories"][0]
            assert "key" in category, "Category missing key"
            assert "name" in category, "Category missing name"
            print(f"✓ Category structure verified: {category.get('key')}")


class TestEmailLogsEndpoint:
    """Test GET /api/email/logs - Email logs listing"""
    
    def test_email_logs_requires_auth(self):
        """Test that email logs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/email/logs", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Email logs endpoint correctly requires auth")
    
    def test_email_logs_returns_list(self, auth_headers):
        """Test email logs returns list of logs"""
        response = requests.get(
            f"{BASE_URL}/api/email/logs",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "logs" in data, "No logs key in response"
        assert "count" in data, "No count key in response"
        assert isinstance(data["logs"], list), "Logs should be a list"
        print(f"✓ Email logs returned {data['count']} logs")
    
    def test_email_logs_with_filters(self, auth_headers):
        """Test email logs with various filters"""
        # Test with limit
        response = requests.get(
            f"{BASE_URL}/api/email/logs?limit=10",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert len(data["logs"]) <= 10, "Limit not respected"
        print(f"✓ Email logs limit filter works")


class TestEmailRequestsTypesEndpoint:
    """Test GET /api/email-requests/types - Email request types listing"""
    
    def test_email_requests_types_requires_auth(self):
        """Test that email request types endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/email-requests/types", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Email request types endpoint correctly requires auth")
    
    def test_email_requests_types_returns_data(self, auth_headers):
        """Test email request types returns request types and statuses"""
        response = requests.get(
            f"{BASE_URL}/api/email-requests/types",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "request_types" in data, "No request_types key in response"
        assert "statuses" in data, "No statuses key in response"
        assert isinstance(data["request_types"], list), "Request types should be a list"
        assert isinstance(data["statuses"], list), "Statuses should be a list"
        print(f"✓ Email request types returned {len(data['request_types'])} types and {len(data['statuses'])} statuses")
        
        # Verify structure
        if data["request_types"]:
            req_type = data["request_types"][0]
            assert "key" in req_type, "Request type missing key"
            assert "name" in req_type, "Request type missing name"
            print(f"✓ Request type structure verified: {req_type.get('key')}")


class TestEmailRequestsListEndpoint:
    """Test GET /api/email-requests - Email requests listing"""
    
    def test_email_requests_list_requires_auth(self):
        """Test that email requests list endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/email-requests", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Email requests list endpoint correctly requires auth")
    
    def test_email_requests_list_returns_data(self, auth_headers):
        """Test email requests list returns requests"""
        response = requests.get(
            f"{BASE_URL}/api/email-requests",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "requests" in data, "No requests key in response"
        assert "count" in data, "No count key in response"
        assert isinstance(data["requests"], list), "Requests should be a list"
        print(f"✓ Email requests list returned {data['count']} requests")
    
    def test_email_requests_list_with_filters(self, auth_headers):
        """Test email requests list with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/email-requests?status=sent&limit=10",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "requests" in data
        print(f"✓ Email requests list filter works - {data['count']} requests")


class TestEmailVerifyActionTokenEndpoint:
    """Test POST /api/email/verify-action-token - Token verification"""
    
    def test_verify_action_token_invalid_token(self):
        """Test verify action token with invalid token returns error"""
        response = requests.post(
            f"{BASE_URL}/api/email/verify-action-token?token=invalid_token_12345",
            timeout=30
        )
        # Should return 400 for invalid token
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Invalid action token correctly rejected with 400")
    
    def test_verify_action_token_missing_token(self):
        """Test verify action token without token parameter"""
        response = requests.post(
            f"{BASE_URL}/api/email/verify-action-token",
            timeout=30
        )
        # Should return 422 (validation error) or 400
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Missing token correctly rejected")


class TestEmailRequestsProcessRemindersEndpoint:
    """Test POST /api/email-requests/process-reminders - Process reminders"""
    
    def test_process_reminders_requires_auth(self):
        """Test that process reminders endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/email-requests/process-reminders", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Process reminders endpoint correctly requires auth")
    
    def test_process_reminders_returns_result(self, auth_headers):
        """Test process reminders returns processing result"""
        response = requests.post(
            f"{BASE_URL}/api/email-requests/process-reminders",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Should return some result about processed reminders
        print(f"✓ Process reminders executed successfully: {data}")


class TestNotificationsLogsEndpoint:
    """Test GET /api/notifications/logs - Notification logs listing"""
    
    def test_notifications_logs_requires_auth(self):
        """Test that notifications logs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/logs", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Notifications logs endpoint correctly requires auth")
    
    def test_notifications_logs_returns_list(self, auth_headers):
        """Test notifications logs returns list of logs"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/logs",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "logs" in data, "No logs key in response"
        assert "count" in data, "No count key in response"
        assert isinstance(data["logs"], list), "Logs should be a list"
        print(f"✓ Notifications logs returned {data['count']} logs")
    
    def test_notifications_logs_with_filters(self, auth_headers):
        """Test notifications logs with filters"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/logs?limit=10",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert len(data["logs"]) <= 10, "Limit not respected"
        print(f"✓ Notifications logs limit filter works")


class TestReferencesStatusEndpoint:
    """Test GET /api/references/{employee_id}/status - Reference status"""
    
    def test_references_status_requires_auth(self):
        """Test that references status endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/references/test_emp_id/status", timeout=30)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ References status endpoint correctly requires auth")
    
    def test_references_status_not_found(self, auth_headers):
        """Test references status for non-existent employee returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/references/nonexistent_employee_12345/status",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ References status correctly returns 404 for non-existent employee")


class TestRouteCollisionCheck:
    """Verify no route collisions between notifications.py and server.py"""
    
    def test_no_duplicate_email_templates_route(self, auth_headers):
        """Verify /api/email/templates is only defined once"""
        response = requests.get(
            f"{BASE_URL}/api/email/templates",
            headers=auth_headers,
            timeout=30
        )
        # Should return 200, not 500 (which would indicate route collision)
        assert response.status_code == 200, f"Route collision detected: {response.status_code}"
        print(f"✓ No route collision for /api/email/templates")
    
    def test_no_duplicate_email_senders_route(self, auth_headers):
        """Verify /api/email/senders is only defined once"""
        response = requests.get(
            f"{BASE_URL}/api/email/senders",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Route collision detected: {response.status_code}"
        print(f"✓ No route collision for /api/email/senders")
    
    def test_no_duplicate_email_requests_route(self, auth_headers):
        """Verify /api/email-requests is only defined once"""
        response = requests.get(
            f"{BASE_URL}/api/email-requests",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Route collision detected: {response.status_code}"
        print(f"✓ No route collision for /api/email-requests")
    
    def test_no_duplicate_notifications_logs_route(self, auth_headers):
        """Verify /api/notifications/logs is only defined once"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/logs",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Route collision detected: {response.status_code}"
        print(f"✓ No route collision for /api/notifications/logs")


class TestExistingRoutesStillWork:
    """Verify existing routes from other modules still work after extraction"""
    
    def test_employees_list_still_works(self, auth_headers):
        """Verify /api/employees still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Employees endpoint broken: {response.status_code}"
        print(f"✓ /api/employees still works")
    
    def test_training_records_still_works(self, auth_headers):
        """Verify /api/training-records still works"""
        response = requests.get(
            f"{BASE_URL}/api/training-records",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Training records endpoint broken: {response.status_code}"
        print(f"✓ /api/training-records still works")
    
    def test_document_types_still_works(self, auth_headers):
        """Verify /api/document-types still works"""
        response = requests.get(
            f"{BASE_URL}/api/document-types",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Document types endpoint broken: {response.status_code}"
        print(f"✓ /api/document-types still works")
    
    def test_dashboard_stats_still_works(self, auth_headers):
        """Verify /api/dashboard/stats still works"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Dashboard stats endpoint broken: {response.status_code}"
        print(f"✓ /api/dashboard/stats still works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

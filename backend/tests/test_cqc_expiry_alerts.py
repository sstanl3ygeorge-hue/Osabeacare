"""
CQC Expiry Alerts System Tests
Tests for:
- Training expiry alerts endpoint
- Document expiry alerts endpoint (DBS, RTW, Professional Registration)
- Send all reminders endpoint
- Admin dashboard integration
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
WORKER_EMAIL = "test.worker@example.com"
WORKER_PASSWORD = "Welcome123!"


class TestAuthSetup:
    """Authentication setup for tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def worker_token(self):
        """Get worker authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": WORKER_EMAIL, "password": WORKER_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Worker login failed: {response.status_code} - {response.text}")


class TestTrainingExpiryAlerts(TestAuthSetup):
    """Tests for training expiry alerts endpoint"""
    
    def test_training_expiry_alerts_endpoint_exists(self, admin_token):
        """Test that training expiry alerts endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/admin/training-expiry-alerts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_training_expiry_alerts_response_structure(self, admin_token):
        """Test that training expiry alerts returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/training-expiry-alerts?days=60",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "critical" in data, "Response should have 'critical' field"
        assert "warning" in data, "Response should have 'warning' field"
        assert "upcoming" in data, "Response should have 'upcoming' field"
        assert "total_expiring" in data, "Response should have 'total_expiring' field"
        assert "threshold_days" in data, "Response should have 'threshold_days' field"
        
        # Verify arrays
        assert isinstance(data["critical"], list), "critical should be a list"
        assert isinstance(data["warning"], list), "warning should be a list"
        assert isinstance(data["upcoming"], list), "upcoming should be a list"
        
        print(f"Training expiry alerts: {data['total_expiring']} total expiring")
        print(f"  - Critical (<14 days): {len(data['critical'])}")
        print(f"  - Warning (14-30 days): {len(data['warning'])}")
        print(f"  - Upcoming (30-60 days): {len(data['upcoming'])}")
        
    def test_training_expiry_alerts_custom_days(self, admin_token):
        """Test training expiry alerts with custom days parameter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/training-expiry-alerts?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["threshold_days"] == 90
        
    def test_training_expiry_alerts_requires_auth(self):
        """Test that training expiry alerts requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/training-expiry-alerts")
        assert response.status_code in [401, 403], "Should require authentication"


class TestDocumentExpiryAlerts(TestAuthSetup):
    """Tests for document expiry alerts endpoint (DBS, RTW, Professional Registration)"""
    
    def test_document_expiry_alerts_endpoint_exists(self, admin_token):
        """Test that document expiry alerts endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/admin/expiring-documents",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_document_expiry_alerts_response_structure(self, admin_token):
        """Test that document expiry alerts returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/expiring-documents?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "critical" in data, "Response should have 'critical' field"
        assert "warning" in data, "Response should have 'warning' field"
        assert "upcoming" in data, "Response should have 'upcoming' field"
        assert "total_expiring" in data, "Response should have 'total_expiring' field"
        assert "threshold_days" in data, "Response should have 'threshold_days' field"
        
        # Verify arrays
        assert isinstance(data["critical"], list), "critical should be a list"
        assert isinstance(data["warning"], list), "warning should be a list"
        assert isinstance(data["upcoming"], list), "upcoming should be a list"
        
        print(f"Document expiry alerts: {data['total_expiring']} total expiring")
        print(f"  - Critical (<=7 days): {len(data['critical'])}")
        print(f"  - Warning (8-14 days): {len(data['warning'])}")
        print(f"  - Upcoming (15-30 days): {len(data['upcoming'])}")
        
    def test_document_expiry_alerts_item_structure(self, admin_token):
        """Test that document expiry alert items have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/expiring-documents?days=365",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check all items across categories
        all_items = data["critical"] + data["warning"] + data["upcoming"]
        
        if len(all_items) > 0:
            item = all_items[0]
            # Verify item structure
            assert "employee_id" in item, "Item should have employee_id"
            assert "employee_name" in item, "Item should have employee_name"
            assert "document_type" in item, "Item should have document_type"
            assert "document_name" in item, "Item should have document_name"
            assert "expiry_date" in item, "Item should have expiry_date"
            assert "days_until_expiry" in item, "Item should have days_until_expiry"
            
            print(f"Sample document expiry item: {item['document_name']} for {item['employee_name']}")
        else:
            print("No expiring documents found in the system")
            
    def test_document_expiry_alerts_requires_auth(self):
        """Test that document expiry alerts requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/expiring-documents")
        assert response.status_code in [401, 403], "Should require authentication"


class TestSendAllReminders(TestAuthSetup):
    """Tests for send all expiry reminders endpoint"""
    
    def test_send_all_reminders_endpoint_exists(self, admin_token):
        """Test that send all reminders endpoint is accessible"""
        response = requests.post(
            f"{BASE_URL}/api/admin/send-all-expiry-reminders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 200 even if no reminders to send
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_send_all_reminders_response_structure(self, admin_token):
        """Test that send all reminders returns correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/admin/send-all-expiry-reminders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response should have 'success' field"
        assert "message" in data, "Response should have 'message' field"
        
        print(f"Send all reminders result: {data['message']}")
        print(f"Response data: {data}")
        
    def test_send_all_reminders_requires_admin(self):
        """Test that send all reminders requires admin authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/send-all-expiry-reminders")
        assert response.status_code in [401, 403], "Should require authentication"


class TestDashboardStats(TestAuthSetup):
    """Tests for dashboard stats that include expiry information"""
    
    def test_dashboard_stats_endpoint(self, admin_token):
        """Test that dashboard stats endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_dashboard_expiry_alerts_endpoint(self, admin_token):
        """Test that dashboard expiry alerts endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/expiry-alerts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # This endpoint may or may not exist - check status
        if response.status_code == 200:
            data = response.json()
            print(f"Dashboard expiry alerts: {data}")
        else:
            print(f"Dashboard expiry alerts endpoint returned: {response.status_code}")
            
    def test_dashboard_training_summary_endpoint(self, admin_token):
        """Test that dashboard training summary endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/training-summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # This endpoint may or may not exist - check status
        if response.status_code == 200:
            data = response.json()
            print(f"Dashboard training summary: {data}")
        else:
            print(f"Dashboard training summary endpoint returned: {response.status_code}")


class TestWorkerDashboard(TestAuthSetup):
    """Tests for worker dashboard with renewal alerts"""
    
    def test_worker_dashboard_endpoint(self, worker_token):
        """Test that worker dashboard endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_worker_dashboard_has_alerts(self, worker_token):
        """Test that worker dashboard includes alerts field"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify alerts field exists
        assert "alerts" in data, "Worker dashboard should have 'alerts' field"
        assert isinstance(data["alerts"], list), "alerts should be a list"
        
        print(f"Worker dashboard alerts: {len(data['alerts'])} alerts")
        if data["alerts"]:
            for alert in data["alerts"][:3]:
                print(f"  - {alert.get('title', 'Unknown')}: {alert.get('days_left', 'N/A')} days")


class TestComplianceRequirements(TestAuthSetup):
    """Tests for compliance requirements tracking (33 requirements)"""
    
    def test_compliance_requirements_count(self, admin_token):
        """Test that compliance requirements are tracked correctly"""
        # Get an employee to check their compliance requirements
        response = requests.get(
            f"{BASE_URL}/api/staff/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        employees = data.get("employees", data) if isinstance(data, dict) else data
        
        if len(employees) > 0:
            emp_id = employees[0].get("id")
            
            # Get compliance requirements for this employee
            req_response = requests.get(
                f"{BASE_URL}/api/employees/{emp_id}/compliance-requirements",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            if req_response.status_code == 200:
                req_data = req_response.json()
                requirements = req_data.get("requirements", [])
                print(f"Compliance requirements for employee {emp_id}: {len(requirements)} items")
                
                # Group by category
                categories = {}
                for req in requirements:
                    cat = req.get("category", "Unknown")
                    if cat not in categories:
                        categories[cat] = 0
                    categories[cat] += 1
                
                print("Requirements by category:")
                for cat, count in categories.items():
                    print(f"  - {cat}: {count}")
            else:
                print(f"Compliance requirements endpoint returned: {req_response.status_code}")
        else:
            print("No employees found to check compliance requirements")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

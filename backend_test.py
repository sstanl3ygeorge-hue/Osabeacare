import requests
import sys
import json
from datetime import datetime

class CareRecruitmentAPITester:
    def __init__(self, base_url="https://caretrust-portal.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.employee_id = None
        self.document_type_id = None
        self.policy_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_login(self):
        """Test login with demo credentials"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@osabea.care", "password": "admin123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_get_me(self):
        """Test get current user"""
        return self.run_test("Get Current User", "GET", "auth/me", 200)

    def test_seed_data(self):
        """Test seed data creation"""
        return self.run_test("Seed Data", "POST", "seed-data", 200)

    def test_get_document_types(self):
        """Test get document types"""
        success, response = self.run_test("Get Document Types", "GET", "document-types", 200)
        if success and response and len(response) > 0:
            self.document_type_id = response[0]['id']
            print(f"   Found {len(response)} document types")
            return True
        return success

    def test_create_employee(self):
        """Test create employee"""
        employee_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": f"john.doe.{datetime.now().strftime('%H%M%S')}@test.com",
            "phone": "07123456789",
            "role": "Care Assistant",
            "branch": "London",
            "status": "new"
        }
        success, response = self.run_test(
            "Create Employee",
            "POST",
            "employees",
            200,
            data=employee_data
        )
        if success and 'id' in response:
            self.employee_id = response['id']
            print(f"   Employee created with ID: {self.employee_id}")
            return True
        return success

    def test_get_employees(self):
        """Test get employees list"""
        return self.run_test("Get Employees", "GET", "employees", 200)

    def test_get_employee_by_id(self):
        """Test get specific employee"""
        if not self.employee_id:
            print("❌ No employee ID available for testing")
            return False
        return self.run_test(f"Get Employee {self.employee_id}", "GET", f"employees/{self.employee_id}", 200)

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        return self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)

    def test_create_policy(self):
        """Test create policy"""
        policy_data = {
            "title": "Test Policy",
            "version": "1.0",
            "description": "Test policy for API testing",
            "category": "General",
            "effective_date": "2024-01-01"
        }
        success, response = self.run_test(
            "Create Policy",
            "POST",
            "policies",
            200,
            data=policy_data
        )
        if success and 'id' in response:
            self.policy_id = response['id']
            print(f"   Policy created with ID: {self.policy_id}")
            return True
        return success

    def test_get_policies(self):
        """Test get policies"""
        return self.run_test("Get Policies", "GET", "policies", 200)

    def test_get_training_records(self):
        """Test get training records"""
        return self.run_test("Get Training Records", "GET", "training-records", 200)

    def test_get_branches(self):
        """Test get branches"""
        return self.run_test("Get Branches", "GET", "branches", 200)

    def test_get_roles(self):
        """Test get roles"""
        return self.run_test("Get Roles", "GET", "roles", 200)

    def test_contact_form(self):
        """Test contact form submission"""
        contact_data = {
            "full_name": "Test User",
            "email": "test@example.com",
            "phone": "07123456789",
            "organisation": "Test Org",
            "subject": "Test Enquiry",
            "message": "This is a test message"
        }
        return self.run_test(
            "Contact Form",
            "POST",
            "contact",
            200,
            data=contact_data
        )

    def test_application_form(self):
        """Test application form submission"""
        app_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": f"jane.smith.{datetime.now().strftime('%H%M%S')}@test.com",
            "phone": "07987654321",
            "address": "123 Test Street",
            "postcode": "SW1A 1AA",
            "role_applied": "Care Assistant",
            "availability": "Full-time",
            "right_to_work": True,
            "has_dbs": False,
            "experience_summary": "Previous care experience",
            "how_heard": "Website"
        }
        return self.run_test(
            "Application Form",
            "POST",
            "apply",
            200,
            data=app_data
        )

    def test_employee_documents(self):
        """Test employee documents endpoint"""
        if not self.employee_id:
            print("❌ No employee ID available for testing")
            return False
        return self.run_test(
            "Get Employee Documents",
            "GET",
            f"employee-documents?employee_id={self.employee_id}",
            200
        )

    def test_audit_logs(self):
        """Test audit logs"""
        return self.run_test("Get Audit Logs", "GET", "audit-logs", 200)

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Care Recruitment API Tests")
        print(f"   Base URL: {self.base_url}")
        print("=" * 60)

        # Basic health checks
        self.test_health_check()
        self.test_root_endpoint()

        # Authentication
        if not self.test_login():
            print("❌ Login failed, stopping authenticated tests")
            self.print_results()
            return 1

        self.test_get_me()

        # Setup data
        self.test_seed_data()
        self.test_get_document_types()

        # Employee management
        self.test_create_employee()
        self.test_get_employees()
        self.test_get_employee_by_id()

        # Dashboard
        self.test_dashboard_stats()

        # Policies
        self.test_create_policy()
        self.test_get_policies()

        # Training
        self.test_get_training_records()

        # Public endpoints
        self.test_get_branches()
        self.test_get_roles()
        self.test_contact_form()
        self.test_application_form()

        # Documents and audit
        self.test_employee_documents()
        self.test_audit_logs()

        self.print_results()
        return 0 if self.tests_passed == self.tests_run else 1

    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")

def main():
    tester = CareRecruitmentAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
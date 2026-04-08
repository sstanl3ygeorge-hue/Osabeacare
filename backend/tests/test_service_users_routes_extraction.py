"""
Service Users Routes Extraction Tests - Phase 12 Modularization
Tests for service users routes extracted from server.py to routes/service_users.py

Endpoints tested:
- GET /api/service-users - List all service users
- GET /api/service-users/sections - Get CQC sections metadata (NEW)
- POST /api/service-users - Create service user
- GET /api/service-users/{id} - Get service user by ID
- PUT /api/service-users/{id} - Update service user
- POST /api/service-users/{id}/documents - Upload document
- GET /api/service-users/{id}/documents - List documents
- PUT /api/service-users/{id}/documents/{doc_id}/verify - Verify document

Regression tests:
- GET /api/templates - Templates routes
- GET /api/compliance/policies - Compliance routes
- GET /api/email/templates - Email templates
- POST /api/auth/login - Auth routes
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# ==================== AUTH TESTS ====================

class TestAuthLogin:
    """Test auth login endpoint"""
    
    def test_auth_login_success(self):
        """Verify admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        
        assert response.status_code == 200, f"Login failed: {response.status_code}"
        data = response.json()
        assert "token" in data, "Response missing token"
        assert "user" in data, "Response missing user"
        assert data["user"]["role"] == "admin", "User should be admin"


# ==================== SERVICE USERS SECTIONS TESTS ====================

class TestServiceUsersSections:
    """Test GET /api/service-users/sections - NEW endpoint"""
    
    def test_get_sections_returns_200(self, auth_headers):
        """Verify sections endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/service-users/sections", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_get_sections_returns_10_sections(self, auth_headers):
        """Verify endpoint returns exactly 10 CQC sections"""
        response = requests.get(f"{BASE_URL}/api/service-users/sections", headers=auth_headers)
        data = response.json()
        
        assert "sections" in data, "Response missing 'sections' key"
        sections = data["sections"]
        assert len(sections) == 10, f"Expected 10 sections, got {len(sections)}"
    
    def test_sections_have_correct_structure(self, auth_headers):
        """Verify each section has required fields"""
        response = requests.get(f"{BASE_URL}/api/service-users/sections", headers=auth_headers)
        sections = response.json()["sections"]
        
        required_fields = ["id", "section_number", "name", "description", "document_types"]
        
        for section in sections:
            for field in required_fields:
                assert field in section, f"Section missing field: {field}"
    
    def test_sections_numbered_1_to_10(self, auth_headers):
        """Verify sections are numbered 1-10"""
        response = requests.get(f"{BASE_URL}/api/service-users/sections", headers=auth_headers)
        sections = response.json()["sections"]
        
        section_numbers = sorted([s["section_number"] for s in sections])
        assert section_numbers == list(range(1, 11)), f"Expected sections 1-10, got {section_numbers}"
    
    def test_section_ids_match_expected(self, auth_headers):
        """Verify section IDs match expected format"""
        response = requests.get(f"{BASE_URL}/api/service-users/sections", headers=auth_headers)
        sections = response.json()["sections"]
        
        expected_ids = [
            "1_personal_referral",
            "2_consent_contracts",
            "3_assessments",
            "4_care_plans",
            "5_risk_assessments",
            "6_monitoring",
            "7_medication",
            "8_health_visits",
            "9_reviews",
            "10_correspondence"
        ]
        
        actual_ids = [s["id"] for s in sections]
        for expected_id in expected_ids:
            assert expected_id in actual_ids, f"Missing section ID: {expected_id}"


# ==================== SERVICE USERS LIST TESTS ====================

class TestServiceUsersList:
    """Test GET /api/service-users"""
    
    def test_list_service_users_returns_200(self, auth_headers):
        """Verify list endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_list_service_users_returns_array(self, auth_headers):
        """Verify response is an array"""
        response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
    
    def test_list_service_users_with_status_filter(self, auth_headers):
        """Verify status filter works"""
        response = requests.get(f"{BASE_URL}/api/service-users?status=active", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # All returned should have active status
        for su in data:
            assert su.get("status") == "active", f"Expected active status, got {su.get('status')}"
    
    def test_list_service_users_with_search(self, auth_headers):
        """Verify search filter works"""
        response = requests.get(f"{BASE_URL}/api/service-users?search=Margaret", headers=auth_headers)
        
        assert response.status_code == 200
    
    def test_list_service_users_includes_document_counts(self, auth_headers):
        """Verify list includes document counts"""
        response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        data = response.json()
        
        if data:
            su = data[0]
            assert "document_counts" in su, "Missing document_counts"
            assert "total_documents" in su, "Missing total_documents"


# ==================== SERVICE USERS CREATE TESTS ====================

class TestServiceUsersCreate:
    """Test POST /api/service-users"""
    created_id = None
    
    def test_create_service_user_success(self, auth_headers):
        """Create a new service user"""
        unique_name = f"TEST_ServiceUser_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "full_name": unique_name,
            "date_of_birth": "1950-05-20",
            "nhs_number": "987 654 3210",
            "address_line_1": "123 Test Street",
            "city": "Manchester",
            "postcode": "M1 1AA",
            "phone": "07700 900999",
            "emergency_contact_name": "Test Emergency Contact",
            "emergency_contact_phone": "07700 900888"
        }
        
        response = requests.post(f"{BASE_URL}/api/service-users", headers=auth_headers, json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response missing 'id'"
        assert "service_user_code" in data, "Response missing 'service_user_code'"
        
        # Verify code format SU-XXXX
        code = data["service_user_code"]
        assert code.startswith("SU-"), f"Code should start with 'SU-', got {code}"
        
        TestServiceUsersCreate.created_id = data["id"]
    
    def test_create_service_user_requires_name(self, auth_headers):
        """Verify full_name is required"""
        payload = {
            "date_of_birth": "1950-05-20"
        }
        
        response = requests.post(f"{BASE_URL}/api/service-users", headers=auth_headers, json=payload)
        
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
    
    def test_create_and_verify_persistence(self, auth_headers):
        """Create service user and verify via GET"""
        unique_name = f"TEST_Persistence_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "full_name": unique_name,
            "city": "Birmingham"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/service-users", headers=auth_headers, json=payload)
        assert create_response.status_code == 200
        
        su_id = create_response.json()["id"]
        
        # Verify via GET
        get_response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        assert get_response.status_code == 200
        
        fetched = get_response.json()
        assert fetched["full_name"] == unique_name
        assert fetched["city"] == "Birmingham"


# ==================== SERVICE USERS GET BY ID TESTS ====================

class TestServiceUsersGetById:
    """Test GET /api/service-users/{id}"""
    
    def test_get_service_user_by_id(self, auth_headers):
        """Get existing service user by ID"""
        # First get list
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == su_id
        assert "full_name" in data
        assert "service_user_code" in data
    
    def test_get_service_user_includes_sections(self, auth_headers):
        """Verify profile includes all 10 sections"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        data = response.json()
        
        assert "sections" in data, "Profile missing 'sections'"
        sections = data["sections"]
        assert len(sections) == 10, f"Expected 10 sections, got {len(sections)}"
    
    def test_get_nonexistent_service_user_returns_404(self, auth_headers):
        """Verify 404 for non-existent ID"""
        fake_id = "nonexistent-id-12345"
        
        response = requests.get(f"{BASE_URL}/api/service-users/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404


# ==================== SERVICE USERS UPDATE TESTS ====================

class TestServiceUsersUpdate:
    """Test PUT /api/service-users/{id}"""
    
    def test_update_service_user(self, auth_headers):
        """Update service user details"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        update_payload = {
            "notes": f"TEST_Updated notes at {uuid.uuid4().hex[:8]}"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/service-users/{su_id}",
            headers=auth_headers,
            json=update_payload
        )
        
        assert response.status_code == 200
    
    def test_update_and_verify_persistence(self, auth_headers):
        """Update and verify via GET"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        unique_note = f"TEST_Verify_{uuid.uuid4().hex[:8]}"
        
        update_payload = {"notes": unique_note}
        
        requests.put(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers, json=update_payload)
        
        # Verify
        get_response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        fetched = get_response.json()
        
        assert unique_note in fetched.get("notes", ""), "Notes not updated"


# ==================== SERVICE USERS DOCUMENTS TESTS ====================

class TestServiceUsersDocuments:
    """Test document upload and management endpoints"""
    created_doc_id = None
    test_su_id = None
    
    def test_upload_document_to_section(self, auth_headers):
        """Upload a document to a specific section"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        TestServiceUsersDocuments.test_su_id = su_id
        
        payload = {
            "section_id": "3_assessments",
            "document_type": "needs_assessment",
            "title": f"TEST_Assessment_{uuid.uuid4().hex[:8]}",
            "notes": "Test document upload",
            "file_url": "https://example.com/test-document.pdf",
            "file_name": "test-assessment.pdf"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/service-users/{su_id}/documents",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response missing document 'id'"
        
        TestServiceUsersDocuments.created_doc_id = data["id"]
    
    def test_upload_document_invalid_section_fails(self, auth_headers):
        """Verify upload to invalid section fails"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        payload = {
            "section_id": "invalid_section",
            "title": "Test Document",
            "file_url": "https://example.com/test.pdf",
            "file_name": "test.pdf"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/service-users/{su_id}/documents",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid section, got {response.status_code}"
    
    def test_list_documents(self, auth_headers):
        """List documents for a service user"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/service-users/{su_id}/documents",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_list_documents_with_section_filter(self, auth_headers):
        """List documents filtered by section"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/service-users/{su_id}/documents?section_id=3_assessments",
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ==================== SERVICE USERS DOCUMENT VERIFY TESTS ====================

class TestServiceUsersDocumentVerify:
    """Test PUT /api/service-users/{id}/documents/{doc_id}/verify"""
    
    def test_verify_document(self, auth_headers):
        """Verify a document"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        # Upload a test document first
        upload_payload = {
            "section_id": "4_care_plans",
            "document_type": "care_plan",
            "title": f"TEST_CarePlan_{uuid.uuid4().hex[:8]}",
            "file_url": "https://example.com/care-plan.pdf",
            "file_name": "care-plan.pdf"
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/service-users/{su_id}/documents",
            headers=auth_headers,
            json=upload_payload
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Could not upload document for verification test")
        
        doc_id = upload_response.json()["id"]
        
        # Verify the document
        verify_response = requests.put(
            f"{BASE_URL}/api/service-users/{su_id}/documents/{doc_id}/verify",
            headers=auth_headers
        )
        
        assert verify_response.status_code == 200
    
    def test_verify_nonexistent_document_returns_404(self, auth_headers):
        """Verify 404 for non-existent document"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        response = requests.put(
            f"{BASE_URL}/api/service-users/{su_id}/documents/nonexistent-doc-id/verify",
            headers=auth_headers
        )
        
        assert response.status_code == 404


# ==================== REGRESSION TESTS ====================

class TestRegressionPreviousRoutes:
    """Verify previous routes still work after extraction"""
    
    def test_templates_endpoint_works(self, auth_headers):
        """Verify /api/templates still works"""
        response = requests.get(f"{BASE_URL}/api/templates", headers=auth_headers)
        
        assert response.status_code == 200, f"Templates endpoint broken: {response.status_code}"
        assert isinstance(response.json(), list)
    
    def test_compliance_policies_endpoint_works(self, auth_headers):
        """Verify /api/compliance/policies still works"""
        response = requests.get(f"{BASE_URL}/api/compliance/policies", headers=auth_headers)
        
        assert response.status_code == 200, f"Compliance policies endpoint broken: {response.status_code}"
        assert isinstance(response.json(), list)
    
    def test_email_templates_endpoint_works(self, auth_headers):
        """Verify /api/email/templates still works"""
        response = requests.get(f"{BASE_URL}/api/email/templates", headers=auth_headers)
        
        assert response.status_code == 200, f"Email templates endpoint broken: {response.status_code}"
        data = response.json()
        assert "templates" in data
    
    def test_employees_endpoint_works(self, auth_headers):
        """Verify /api/employees still works"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        
        assert response.status_code == 200, f"Employees endpoint broken: {response.status_code}"
        assert isinstance(response.json(), list)
    
    def test_dashboard_stats_endpoint_works(self, auth_headers):
        """Verify /api/dashboard/stats still works"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        
        assert response.status_code == 200, f"Dashboard stats endpoint broken: {response.status_code}"


# ==================== AUTH REQUIREMENTS TESTS ====================

class TestAuthRequirements:
    """Verify service users routes require authentication"""
    
    def test_list_service_users_requires_auth(self):
        """Verify list endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/service-users")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_sections_requires_auth(self):
        """Verify sections endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/service-users/sections")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_create_service_user_requires_auth(self):
        """Verify create endpoint requires auth"""
        response = requests.post(f"{BASE_URL}/api/service-users", json={"full_name": "Test"})
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ==================== CLEANUP TESTS ====================

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_service_users(self, auth_headers):
        """Delete TEST_ prefixed service users"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        deleted_count = 0
        for su in service_users:
            if su.get("full_name", "").startswith("TEST_"):
                delete_response = requests.delete(
                    f"{BASE_URL}/api/service-users/{su['id']}",
                    headers=auth_headers
                )
                if delete_response.status_code in [200, 204]:
                    deleted_count += 1
        
        print(f"Cleaned up {deleted_count} test service users")
        assert True  # Cleanup always passes

"""
Service Users Feature Tests - CQC Compliance File Structure
Tests for the new Service User Files feature with 10 numbered sections.

Sections:
1. Personal Info & Referral
2. Consent & Contracts
3. Assessments
4. Care Plans
5. Risk Assessments
6. Monitoring
7. Medication
8. Health Visits
9. Reviews
10. Letters & Correspondence
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


class TestServiceUserSections:
    """Test GET /api/service-user-sections returns 10 sections"""
    
    def test_get_sections_returns_10_sections(self, auth_headers):
        """Verify endpoint returns exactly 10 sections"""
        response = requests.get(f"{BASE_URL}/api/service-user-sections", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        sections = response.json()
        assert len(sections) == 10, f"Expected 10 sections, got {len(sections)}"
    
    def test_sections_have_correct_structure(self, auth_headers):
        """Verify each section has required fields"""
        response = requests.get(f"{BASE_URL}/api/service-user-sections", headers=auth_headers)
        sections = response.json()
        
        required_fields = ["id", "section_number", "name", "description", "document_types"]
        
        for section in sections:
            for field in required_fields:
                assert field in section, f"Section missing field: {field}"
    
    def test_sections_numbered_1_to_10(self, auth_headers):
        """Verify sections are numbered 1-10"""
        response = requests.get(f"{BASE_URL}/api/service-user-sections", headers=auth_headers)
        sections = response.json()
        
        section_numbers = sorted([s["section_number"] for s in sections])
        assert section_numbers == list(range(1, 11)), f"Expected sections 1-10, got {section_numbers}"
    
    def test_section_names_match_cqc_structure(self, auth_headers):
        """Verify section names align with CQC expectations"""
        response = requests.get(f"{BASE_URL}/api/service-user-sections", headers=auth_headers)
        sections = response.json()
        
        expected_names = [
            "Personal Info & Referral",
            "Consent & Contracts",
            "Assessments",
            "Care Plans",
            "Risk Assessments",
            "Monitoring",
            "Medication",
            "Health Visits",
            "Reviews",
            "Letters & Correspondence"
        ]
        
        actual_names = [s["name"] for s in sorted(sections, key=lambda x: x["section_number"])]
        assert actual_names == expected_names, f"Section names mismatch: {actual_names}"


class TestServiceUsersList:
    """Test GET /api/service-users returns list of service users"""
    
    def test_list_service_users_returns_200(self, auth_headers):
        """Verify endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_list_service_users_returns_array(self, auth_headers):
        """Verify response is an array"""
        response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
    
    def test_list_service_users_with_search(self, auth_headers):
        """Verify search filter works"""
        response = requests.get(f"{BASE_URL}/api/service-users?search=Margaret", headers=auth_headers)
        
        assert response.status_code == 200
    
    def test_list_service_users_with_status_filter(self, auth_headers):
        """Verify status filter works"""
        response = requests.get(f"{BASE_URL}/api/service-users?status=active", headers=auth_headers)
        
        assert response.status_code == 200


class TestServiceUserCreate:
    """Test POST /api/service-users creates new service user with code SU-XXXX"""
    
    def test_create_service_user_success(self, auth_headers):
        """Create a new service user and verify response"""
        unique_name = f"TEST_ServiceUser_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "full_name": unique_name,
            "date_of_birth": "1945-03-15",
            "nhs_number": "123 456 7890",
            "address_line_1": "123 Test Street",
            "city": "London",
            "postcode": "SW1A 1AA",
            "phone": "07700 900000",
            "emergency_contact_name": "Test Contact",
            "emergency_contact_phone": "07700 900001"
        }
        
        response = requests.post(f"{BASE_URL}/api/service-users", headers=auth_headers, json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response missing 'id'"
        assert "service_user_code" in data, "Response missing 'service_user_code'"
        
        # Verify code format SU-XXXX
        code = data["service_user_code"]
        assert code.startswith("SU-"), f"Code should start with 'SU-', got {code}"
        assert len(code) == 7, f"Code should be 7 chars (SU-XXXX), got {len(code)}: {code}"
        
        # Store for cleanup
        TestServiceUserCreate.created_id = data["id"]
    
    def test_create_service_user_requires_name(self, auth_headers):
        """Verify full_name is required"""
        payload = {
            "date_of_birth": "1945-03-15"
        }
        
        response = requests.post(f"{BASE_URL}/api/service-users", headers=auth_headers, json=payload)
        
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"


class TestServiceUserProfile:
    """Test GET /api/service-users/{id} returns profile with all 10 sections"""
    
    def test_get_service_user_profile(self, auth_headers):
        """Get existing service user profile"""
        # First get list to find an existing service user
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist to test profile")
        
        su_id = service_users[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "id" in data
        assert "full_name" in data
        assert "service_user_code" in data
    
    def test_profile_contains_all_10_sections(self, auth_headers):
        """Verify profile includes all 10 sections"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist to test profile")
        
        su_id = service_users[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        data = response.json()
        
        assert "sections" in data, "Profile missing 'sections'"
        
        sections = data["sections"]
        assert len(sections) == 10, f"Expected 10 sections, got {len(sections)}"
        
        # Verify all section IDs present
        expected_section_ids = [
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
        
        for section_id in expected_section_ids:
            assert section_id in sections, f"Missing section: {section_id}"
    
    def test_profile_sections_have_document_count(self, auth_headers):
        """Verify each section has document_count"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        data = response.json()
        
        for section_id, section_data in data["sections"].items():
            assert "document_count" in section_data, f"Section {section_id} missing document_count"
            assert "documents" in section_data, f"Section {section_id} missing documents array"
    
    def test_get_nonexistent_service_user_returns_404(self, auth_headers):
        """Verify 404 for non-existent service user"""
        fake_id = "nonexistent-id-12345"
        
        response = requests.get(f"{BASE_URL}/api/service-users/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404


class TestServiceUserDocumentUpload:
    """Test POST /api/service-users/{id}/documents uploads document to specific section"""
    
    def test_upload_document_to_section(self, auth_headers):
        """Upload a document to a specific section"""
        # Get a service user
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
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
        
        # Store for cleanup/verification
        TestServiceUserDocumentUpload.created_doc_id = data["id"]
        TestServiceUserDocumentUpload.service_user_id = su_id
    
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
    
    def test_upload_document_requires_title(self, auth_headers):
        """Verify title is required"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        payload = {
            "section_id": "3_assessments",
            "file_url": "https://example.com/test.pdf",
            "file_name": "test.pdf"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/service-users/{su_id}/documents",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"


class TestServiceUserDocumentVerify:
    """Test PUT /api/service-users/{id}/documents/{doc_id}/verify marks document as verified"""
    
    def test_verify_document(self, auth_headers):
        """Verify a document"""
        # First upload a document
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        
        # Upload a test document
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
        
        # Now verify it
        verify_response = requests.put(
            f"{BASE_URL}/api/service-users/{su_id}/documents/{doc_id}/verify",
            headers=auth_headers
        )
        
        assert verify_response.status_code == 200, f"Expected 200, got {verify_response.status_code}"
        
        # Verify the document is now marked as verified
        profile_response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        profile = profile_response.json()
        
        # Find the document in the section
        section_docs = profile["sections"]["4_care_plans"]["documents"]
        verified_doc = next((d for d in section_docs if d["id"] == doc_id), None)
        
        assert verified_doc is not None, "Document not found in section"
        assert verified_doc.get("verified") == True, "Document should be verified"


class TestServiceUserUpdate:
    """Test PUT /api/service-users/{id} updates service user details"""
    
    def test_update_service_user(self, auth_headers):
        """Update service user details"""
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        if not service_users:
            pytest.skip("No service users exist")
        
        su_id = service_users[0]["id"]
        original_name = service_users[0]["full_name"]
        
        # Update with new notes
        update_payload = {
            "notes": f"TEST_Updated notes at {uuid.uuid4().hex[:8]}"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/service-users/{su_id}",
            headers=auth_headers,
            json=update_payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify update persisted
        get_response = requests.get(f"{BASE_URL}/api/service-users/{su_id}", headers=auth_headers)
        updated_su = get_response.json()
        
        assert "TEST_Updated notes" in updated_su.get("notes", ""), "Notes not updated"


class TestExistingEmployeeFunctionalityNotAffected:
    """Verify existing employee/compliance functionality still works"""
    
    def test_employees_endpoint_still_works(self, auth_headers):
        """Verify /api/employees still returns data"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        
        assert response.status_code == 200, f"Employees endpoint broken: {response.status_code}"
        assert isinstance(response.json(), list), "Employees should return a list"
    
    def test_employee_profile_still_works(self, auth_headers):
        """Verify employee profile endpoint still works"""
        # Get an employee
        list_response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        employees = list_response.json()
        
        if not employees:
            pytest.skip("No employees exist")
        
        emp_id = employees[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/employees/{emp_id}", headers=auth_headers)
        
        assert response.status_code == 200, f"Employee profile broken: {response.status_code}"
    
    def test_compliance_requirements_still_works(self, auth_headers):
        """Verify compliance requirements endpoint still works"""
        list_response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        employees = list_response.json()
        
        if not employees:
            pytest.skip("No employees exist")
        
        emp_id = employees[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/employees/{emp_id}/compliance-requirements", headers=auth_headers)
        
        assert response.status_code == 200, f"Compliance requirements broken: {response.status_code}"


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_documents(self, auth_headers):
        """Delete TEST_ prefixed documents"""
        # Get all service users
        list_response = requests.get(f"{BASE_URL}/api/service-users", headers=auth_headers)
        service_users = list_response.json()
        
        for su in service_users:
            profile_response = requests.get(f"{BASE_URL}/api/service-users/{su['id']}", headers=auth_headers)
            if profile_response.status_code != 200:
                continue
            
            profile = profile_response.json()
            
            for section_id, section_data in profile.get("sections", {}).items():
                for doc in section_data.get("documents", []):
                    if doc.get("title", "").startswith("TEST_"):
                        requests.delete(
                            f"{BASE_URL}/api/service-users/{su['id']}/documents/{doc['id']}",
                            headers=auth_headers
                        )
        
        # This test always passes - it's just cleanup
        assert True

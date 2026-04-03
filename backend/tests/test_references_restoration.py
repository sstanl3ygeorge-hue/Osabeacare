"""
Test References Restoration - Verifies db.references insertion during public application submission
and compliance-file endpoint returns references with status='declared' for new applicants.

Tests:
1. Public application submission creates employee record with reference fields
2. Public application submission creates db.references record
3. Compliance-file endpoint returns references with status='declared'
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReferencesRestoration:
    """Test references insertion and retrieval for new applicants"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test employee ID from main agent context
        self.test_employee_id = "5bc0b72f-e298-4a97-bc63-25eece5cf9cf"
    
    def test_employee_has_reference_fields(self):
        """Verify employee record has reference_1_* and reference_2_* fields populated"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get employee: {response.text}"
        
        employee = response.json()
        
        # Reference 1 fields
        assert employee.get("reference_1_name") is not None, "reference_1_name should be populated"
        assert employee.get("reference_1_email") is not None, "reference_1_email should be populated"
        print(f"Reference 1: {employee.get('reference_1_name')} ({employee.get('reference_1_email')})")
        
        # Reference 2 fields
        assert employee.get("reference_2_name") is not None, "reference_2_name should be populated"
        assert employee.get("reference_2_email") is not None, "reference_2_email should be populated"
        print(f"Reference 2: {employee.get('reference_2_name')} ({employee.get('reference_2_email')})")
    
    def test_compliance_file_references_section_exists(self):
        """Verify compliance-file endpoint returns references section"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get compliance-file: {response.text}"
        
        data = response.json()
        sections = data.get("sections", {})
        
        assert "references" in sections, "References section should exist in compliance-file"
        refs_section = sections["references"]
        
        assert "rows" in refs_section, "References section should have rows"
        assert len(refs_section["rows"]) >= 2, "Should have at least 2 reference rows"
        print(f"References section found with {len(refs_section['rows'])} rows")
    
    def test_references_have_declared_status(self):
        """Verify references show status='declared' for new applicants"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        refs_section = data.get("sections", {}).get("references", {})
        rows = refs_section.get("rows", [])
        
        for row in rows:
            key = row.get("key")
            status = row.get("status")
            lifecycle_status = row.get("lifecycle_status")
            has_declared = row.get("has_declared")
            
            print(f"{key}: status={status}, lifecycle={lifecycle_status}, has_declared={has_declared}")
            
            # For new applicants with declared references, status should be 'declared'
            assert status == "declared", f"{key} should have status='declared', got '{status}'"
            assert has_declared == True, f"{key} should have has_declared=True"
            assert lifecycle_status == "not_requested", f"{key} should have lifecycle_status='not_requested'"
    
    def test_references_have_declared_referee_details(self):
        """Verify declared_referee contains referee details"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        refs_section = data.get("sections", {}).get("references", {})
        rows = refs_section.get("rows", [])
        
        for row in rows:
            key = row.get("key")
            declared_referee = row.get("declared_referee", {})
            
            assert declared_referee is not None, f"{key} should have declared_referee"
            assert declared_referee.get("name") is not None, f"{key} declared_referee should have name"
            assert declared_referee.get("email") is not None, f"{key} declared_referee should have email"
            
            print(f"{key}: {declared_referee.get('name')} ({declared_referee.get('email')})")
    
    def test_references_status_summary(self):
        """Verify status_summary shows 'Referee declared • not yet requested'"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-file",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        refs_section = data.get("sections", {}).get("references", {})
        rows = refs_section.get("rows", [])
        
        for row in rows:
            key = row.get("key")
            status_summary = row.get("status_summary", "")
            
            assert "declared" in status_summary.lower(), f"{key} status_summary should mention 'declared'"
            print(f"{key}: {status_summary}")


class TestNewApplicationReferencesInsertion:
    """Test that new application submissions create references correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for new application tests"""
        self.unique_email = f"test_ref_{uuid.uuid4().hex[:8]}@testapplicant.com"
    
    def test_structured_application_creates_references(self):
        """Submit a new structured application and verify references are created"""
        # Build application payload with 2 references
        application_data = {
            "title": "Mr",
            "first_name": "Test",
            "middle_name": "",
            "last_name": f"RefApplicant{uuid.uuid4().hex[:4]}",
            "preferred_name": "",
            "date_of_birth": "1990-01-15",
            "national_insurance": "AB123456C",
            "email": self.unique_email,
            "phone": "07700900123",
            "phone_secondary": "",
            "address_line_1": "123 Test Street",
            "address_line_2": "",
            "city": "London",
            "county": "Greater London",
            "postcode": "SW1A 1AA",
            "years_at_current_address": 3,
            "previous_addresses": [],
            "role_applied": "Care Assistant",
            "availability": "Full-time",
            "earliest_start_date": "2026-02-01",
            "preferred_locations": ["London"],
            "has_driving_licence": True,
            "has_own_transport": True,
            "employment_history": [
                {
                    "employer_name": "Previous Care Home",
                    "job_title": "Care Worker",
                    "start_date": "2020-01-01",
                    "end_date": "2025-12-31",
                    "duties": "Providing care to residents",
                    "reason_for_leaving": "Career progression",
                    "employer_address": "456 Care Street, London",
                    "employer_phone": "02012345678",
                    "can_contact": True
                }
            ],
            "has_employment_gaps": False,
            "employment_gap_explanation": "",
            "references": [
                {
                    "referee_name": "Test Referee One",
                    "referee_job_title": "Manager",
                    "referee_organisation": "Test Org One",
                    "referee_email": "referee1@testorg.com",
                    "referee_phone": "07700900001",
                    "relationship": "Line Manager",
                    "years_known": 3,
                    "is_professional": True,
                    "can_contact_before_offer": True
                },
                {
                    "referee_name": "Test Referee Two",
                    "referee_job_title": "Supervisor",
                    "referee_organisation": "Test Org Two",
                    "referee_email": "referee2@testorg.com",
                    "referee_phone": "07700900002",
                    "relationship": "Supervisor",
                    "years_known": 2,
                    "is_professional": True,
                    "can_contact_before_offer": False
                }
            ],
            "highest_qualification": "NVQ Level 2",
            "relevant_qualifications": ["Care Certificate"],
            "care_certificate_completed": True,
            "mandatory_training_completed": True,
            "health_declaration": {
                "has_condition_affecting_work": False,
                "condition_details": "",
                "requires_reasonable_adjustments": False,
                "adjustment_details": "",
                "health_declaration_accurate": True
            },
            "criminal_declaration": {
                "has_criminal_convictions": False,
                "conviction_details": "",
                "understands_dbs_required": True,
                "consents_to_dbs_check": True
            },
            "right_to_work": {
                "has_right_to_work_uk": True,
                "citizenship_status": "british_citizen",
                "visa_type": "",
                "visa_expiry": ""
            },
            "declarations": {
                "information_accurate": True,
                "consents_to_reference_checks": True,
                "consents_to_background_checks": True,
                "consents_to_data_processing": True,
                "has_professional_registration": False,
                "registration_body": "",
                "registration_number": ""
            },
            "additional_info": "",
            "how_heard": "Website",
            "cv_file_id": None
        }
        
        # Submit application (no auth required for public endpoint)
        response = requests.post(
            f"{BASE_URL}/api/applications/structured",
            json=application_data
        )
        
        assert response.status_code == 200, f"Application submission failed: {response.text}"
        result = response.json()
        
        assert "reference" in result, "Response should contain applicant reference"
        applicant_ref = result.get("reference")
        print(f"Application submitted with reference: {applicant_ref}")
        
        # Now login and verify the employee was created with references
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Find the employee by email
        employees_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=headers,
            params={"search": self.unique_email}
        )
        assert employees_response.status_code == 200
        
        employees = employees_response.json()
        matching = [e for e in employees if e.get("email") == self.unique_email]
        assert len(matching) == 1, f"Should find exactly 1 employee with email {self.unique_email}"
        
        employee = matching[0]
        employee_id = employee.get("id")
        
        # Verify reference fields on employee
        assert employee.get("reference_1_name") == "Test Referee One"
        assert employee.get("reference_1_email") == "referee1@testorg.com"
        assert employee.get("reference_2_name") == "Test Referee Two"
        assert employee.get("reference_2_email") == "referee2@testorg.com"
        print("Employee reference fields verified")
        
        # Verify compliance-file shows references as declared
        compliance_response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/compliance-file",
            headers=headers
        )
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        refs_section = compliance_data.get("sections", {}).get("references", {})
        rows = refs_section.get("rows", [])
        
        assert len(rows) >= 2, "Should have at least 2 reference rows"
        
        for row in rows:
            assert row.get("status") == "declared", f"{row.get('key')} should have status='declared'"
            assert row.get("has_declared") == True
            print(f"{row.get('key')}: status={row.get('status')}, declared_referee={row.get('declared_referee', {}).get('name')}")
        
        print("New application references insertion verified successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

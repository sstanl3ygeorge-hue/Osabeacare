"""
Test Agreement Templates UI - Ticket D Part 2

Tests for:
- Agreement template listing
- Agreement submission viewing with form_data
- Agreement drawer in view mode
- Agreement drawer in create mode
- PDF export functionality
- Verify/Reject actions
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAgreementTemplates:
    """Test agreement template endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Test employee IDs
        self.employee_with_submission = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge
        self.employee_without_submission = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"  # Lawrence Egbeni
    
    def test_list_agreement_templates(self):
        """Test GET /api/agreement-templates returns both templates"""
        response = self.session.get(f"{BASE_URL}/api/agreement-templates")
        assert response.status_code == 200
        
        data = response.json()
        assert "templates" in data
        templates = data["templates"]
        
        # Should have 2 templates
        assert len(templates) == 2
        
        # Check template IDs
        template_ids = [t["template_id"] for t in templates]
        assert "ZERO_HOUR_CONTRACT_V1" in template_ids
        assert "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1" in template_ids
        
        # Check template structure
        for template in templates:
            assert "template_id" in template
            assert "template_name" in template
            assert "version" in template
            assert "company_name" in template
    
    def test_get_zero_hour_contract_template(self):
        """Test GET /api/agreement-templates/ZERO_HOUR_CONTRACT_V1"""
        response = self.session.get(f"{BASE_URL}/api/agreement-templates/ZERO_HOUR_CONTRACT_V1")
        assert response.status_code == 200
        
        template = response.json()
        assert template["template_id"] == "ZERO_HOUR_CONTRACT_V1"
        assert template["template_name"] == "Zero Hour Contract - Statement of Main Terms"
        assert "sections" in template
        assert len(template["sections"]) > 0
    
    def test_get_employee_handbook_template(self):
        """Test GET /api/agreement-templates/EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"""
        response = self.session.get(f"{BASE_URL}/api/agreement-templates/EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1")
        assert response.status_code == 200
        
        template = response.json()
        assert template["template_id"] == "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"
        assert template["template_name"] == "Employee Handbook Acknowledgement"
        assert "sections" in template
        
        # Check for acknowledgement section with checkboxes
        ack_section = next((s for s in template["sections"] if s["key"] == "acknowledgements"), None)
        assert ack_section is not None
        assert len(ack_section["fields"]) >= 6  # 6 acknowledgement checkboxes
    
    def test_get_nonexistent_template(self):
        """Test GET /api/agreement-templates/INVALID returns 404"""
        response = self.session.get(f"{BASE_URL}/api/agreement-templates/INVALID_TEMPLATE")
        assert response.status_code == 404


class TestComplianceFileAgreements:
    """Test compliance file agreement rows with submission_data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        self.employee_with_submission = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.employee_without_submission = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"
    
    def test_compliance_file_has_agreements_section(self):
        """Test compliance file includes agreements section"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_with_submission}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        assert "sections" in data
        assert "agreements" in data["sections"]
        
        agreements = data["sections"]["agreements"]
        assert "rows" in agreements
        assert len(agreements["rows"]) == 2  # contract_acceptance and handbook_acknowledgement
    
    def test_handbook_row_has_submission_data(self):
        """Test handbook acknowledgement row includes submission_data with form_data"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_with_submission}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        agreements = data["sections"]["agreements"]["rows"]
        
        # Find handbook row
        handbook_row = next((r for r in agreements if r["key"] == "handbook_acknowledgement"), None)
        assert handbook_row is not None
        
        # Check submission_data is present
        assert handbook_row["submission_data"] is not None
        submission = handbook_row["submission_data"]
        
        # Check submission structure
        assert "id" in submission
        assert "template_id" in submission
        assert submission["template_id"] == "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"
        assert "form_data" in submission
        
        # Check form_data contains expected fields
        form_data = submission["form_data"]
        assert "employee_name" in form_data
        assert form_data["employee_name"] == "Olakunle Alonge"
        assert "employee_role" in form_data
        assert form_data["employee_role"] == "Healthcare Assistant"
        
        # Check acknowledgement checkboxes
        assert form_data.get("ack_received") == True
        assert form_data.get("ack_read") == True
        assert form_data.get("ack_policies") == True
        assert form_data.get("ack_updates") == True
        assert form_data.get("ack_ask_questions") == True
        assert form_data.get("ack_compliance") == True
        
        # Check signature
        assert "signature_name" in form_data
        assert form_data["signature_name"] == "Olakunle Alonge"
    
    def test_handbook_row_verified_status(self):
        """Test handbook row shows verified status"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_with_submission}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        agreements = data["sections"]["agreements"]["rows"]
        handbook_row = next((r for r in agreements if r["key"] == "handbook_acknowledgement"), None)
        
        assert handbook_row["is_verified"] == True
        assert handbook_row["status"] == "verified"
        assert "Verified" in handbook_row["status_summary"]
    
    def test_not_started_agreement_has_no_submission_data(self):
        """Test not-started agreement has null submission_data"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_without_submission}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        agreements = data["sections"]["agreements"]["rows"]
        
        # Both agreements should have no submission_data
        for row in agreements:
            assert row["submission_data"] is None
            assert row["has_acknowledgement"] == False
            assert row["is_verified"] == False
            assert row["status"] == "not_completed"


class TestAgreementSubmissions:
    """Test agreement submission endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        self.employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        self.submission_id = "agr_sub_395820da1c9b"
    
    def test_get_agreement_submission(self):
        """Test GET /api/agreement-submissions/{id} returns submission with template"""
        response = self.session.get(f"{BASE_URL}/api/agreement-submissions/{self.submission_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "submission" in data
        assert "template" in data
        
        submission = data["submission"]
        assert submission["id"] == self.submission_id
        assert submission["template_id"] == "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"
        assert "form_data" in submission
        
        # Check form_data
        form_data = submission["form_data"]
        assert form_data["employee_name"] == "Olakunle Alonge"
        assert form_data["employee_role"] == "Healthcare Assistant"
        
        # Check template is included
        template = data["template"]
        assert template["template_id"] == "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"
        assert "sections" in template
    
    def test_get_nonexistent_submission(self):
        """Test GET /api/agreement-submissions/invalid returns 404"""
        response = self.session.get(f"{BASE_URL}/api/agreement-submissions/invalid_id")
        assert response.status_code == 404
    
    def test_export_submission_pdf(self):
        """Test GET /api/agreement-submissions/{id}/pdf returns HTML content"""
        response = self.session.get(f"{BASE_URL}/api/agreement-submissions/{self.submission_id}/pdf")
        assert response.status_code == 200
        
        data = response.json()
        assert "html_content" in data
        assert "submission_id" in data
        
        # Check HTML contains expected content
        html = data["html_content"]
        assert "Employee Handbook" in html
        assert "Olakunle Alonge" in html
    
    def test_get_employee_submissions(self):
        """Test GET /api/employees/{id}/agreement-submissions"""
        response = self.session.get(f"{BASE_URL}/api/employees/{self.employee_id}/agreement-submissions")
        assert response.status_code == 200
        
        data = response.json()
        assert "submissions" in data
        
        # Should have at least one submission
        submissions = data["submissions"]
        assert len(submissions) >= 1
        
        # Find handbook submission
        handbook_sub = next((s for s in submissions if s["template_id"] == "EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1"), None)
        assert handbook_sub is not None


class TestAgreementVerification:
    """Test agreement verification and rejection endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_reject_requires_reason(self):
        """Test rejection requires at least 10 character reason"""
        # Use a fake submission ID - should fail validation before 404
        response = self.session.post(
            f"{BASE_URL}/api/agreement-submissions/fake_id/reject",
            json={"reason": "short"}
        )
        # Should fail with 400 for short reason
        assert response.status_code == 400
        assert "10 characters" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

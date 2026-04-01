"""
Test Compliance File New Sections - Iteration 103
Tests the new form-type requirement sections:
- recruitment_record (Interview Record, Application Form, CV, Recruitment Checklist)
- health_competency (Staff Health Questionnaire, Induction)
- admin_forms (Staff Personal Info, HMRC Starter Checklist, Equal Opportunities)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestComplianceFileNewSections:
    """Test the new compliance file sections."""
    
    def test_compliance_file_returns_new_sections(self, auth_headers):
        """Test that compliance file returns the 3 new sections."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify serializer version
        assert data.get("serializer_version") == "dual_row_v1", "Expected dual_row_v1 serializer"
        
        # Verify sections exist
        sections = data.get("sections", {})
        assert "recruitment_record" in sections, "Missing recruitment_record section"
        assert "health_competency" in sections, "Missing health_competency section"
        assert "admin_forms" in sections, "Missing admin_forms section"
        
        print(f"✓ All 3 new sections present in compliance file")
    
    def test_recruitment_record_section_structure(self, auth_headers):
        """Test recruitment_record section has correct rows."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        recruitment_record = data.get("sections", {}).get("recruitment_record", {})
        
        # Check title
        assert recruitment_record.get("title") == "Recruitment Record", f"Expected 'Recruitment Record', got {recruitment_record.get('title')}"
        
        # Check rows
        rows = recruitment_record.get("rows", [])
        assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"
        
        # Verify row keys
        row_keys = [r.get("key") for r in rows]
        expected_keys = ["interview_record", "application_form", "cv", "recruitment_checklist"]
        for key in expected_keys:
            assert key in row_keys, f"Missing row key: {key}"
        
        print(f"✓ Recruitment Record section has 4 rows: {row_keys}")
    
    def test_health_competency_section_structure(self, auth_headers):
        """Test health_competency section has correct rows."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        health_competency = data.get("sections", {}).get("health_competency", {})
        
        # Check title
        assert health_competency.get("title") == "Health & Competency", f"Expected 'Health & Competency', got {health_competency.get('title')}"
        
        # Check rows
        rows = health_competency.get("rows", [])
        assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
        
        # Verify row keys
        row_keys = [r.get("key") for r in rows]
        expected_keys = ["staff_health_questionnaire", "induction"]
        for key in expected_keys:
            assert key in row_keys, f"Missing row key: {key}"
        
        print(f"✓ Health & Competency section has 2 rows: {row_keys}")
    
    def test_admin_forms_section_structure(self, auth_headers):
        """Test admin_forms section has correct rows."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        admin_forms = data.get("sections", {}).get("admin_forms", {})
        
        # Check title
        assert admin_forms.get("title") == "Admin Forms", f"Expected 'Admin Forms', got {admin_forms.get('title')}"
        
        # Check rows
        rows = admin_forms.get("rows", [])
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
        
        # Verify row keys
        row_keys = [r.get("key") for r in rows]
        expected_keys = ["staff_personal_info", "hmrc_starter_checklist", "equal_opportunities"]
        for key in expected_keys:
            assert key in row_keys, f"Missing row key: {key}"
        
        print(f"✓ Admin Forms section has 3 rows: {row_keys}")


class TestFormRowStructure:
    """Test form-type row structure and properties."""
    
    def test_form_row_has_correct_row_type(self, auth_headers):
        """Test that form rows have row_type='form'."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check form rows in recruitment_record
        recruitment_rows = data.get("sections", {}).get("recruitment_record", {}).get("rows", [])
        for row in recruitment_rows:
            if row.get("key") != "cv":  # CV is evidence type
                assert row.get("row_type") == "form", f"Row {row.get('key')} should have row_type='form', got {row.get('row_type')}"
        
        # Check form rows in health_competency
        health_rows = data.get("sections", {}).get("health_competency", {}).get("rows", [])
        for row in health_rows:
            assert row.get("row_type") == "form", f"Row {row.get('key')} should have row_type='form', got {row.get('row_type')}"
        
        # Check form rows in admin_forms
        admin_rows = data.get("sections", {}).get("admin_forms", {}).get("rows", [])
        for row in admin_rows:
            assert row.get("row_type") == "form", f"Row {row.get('key')} should have row_type='form', got {row.get('row_type')}"
        
        print("✓ All form rows have correct row_type='form'")
    
    def test_cv_row_has_evidence_type(self, auth_headers):
        """Test that CV row has row_type='evidence'."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        recruitment_rows = data.get("sections", {}).get("recruitment_record", {}).get("rows", [])
        cv_row = next((r for r in recruitment_rows if r.get("key") == "cv"), None)
        
        assert cv_row is not None, "CV row not found"
        assert cv_row.get("row_type") == "evidence", f"CV row should have row_type='evidence', got {cv_row.get('row_type')}"
        
        # CV should have file-related fields
        assert "has_files" in cv_row, "CV row missing has_files field"
        assert "file_count" in cv_row, "CV row missing file_count field"
        
        print(f"✓ CV row has correct evidence type with file_count={cv_row.get('file_count')}")
    
    def test_form_rows_have_delivery_mode(self, auth_headers):
        """Test that form rows have delivery_mode field."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Expected delivery modes
        expected_modes = {
            "interview_record": "admin_only",
            "application_form": "hybrid",
            "recruitment_checklist": "admin_only",
            "staff_health_questionnaire": "employee_sendable",
            "induction": "admin_only",
            "staff_personal_info": "employee_sendable",
            "hmrc_starter_checklist": "employee_sendable",
            "equal_opportunities": "employee_sendable"
        }
        
        # Collect all form rows
        all_rows = []
        for section_key in ["recruitment_record", "health_competency", "admin_forms"]:
            section = data.get("sections", {}).get(section_key, {})
            all_rows.extend(section.get("rows", []))
        
        for row in all_rows:
            key = row.get("key")
            if key in expected_modes:
                assert row.get("delivery_mode") == expected_modes[key], \
                    f"Row {key} should have delivery_mode='{expected_modes[key]}', got '{row.get('delivery_mode')}'"
        
        print("✓ All form rows have correct delivery_mode")
    
    def test_form_rows_have_allowed_actions(self, auth_headers):
        """Test that form rows have allowed_actions array."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Collect all form rows
        all_rows = []
        for section_key in ["recruitment_record", "health_competency", "admin_forms"]:
            section = data.get("sections", {}).get(section_key, {})
            all_rows.extend(section.get("rows", []))
        
        for row in all_rows:
            key = row.get("key")
            allowed_actions = row.get("allowed_actions", [])
            
            assert isinstance(allowed_actions, list), f"Row {key} allowed_actions should be a list"
            assert len(allowed_actions) > 0, f"Row {key} should have at least one allowed action"
            
            # All rows should have 'history' action
            assert "history" in allowed_actions, f"Row {key} missing 'history' action"
        
        print("✓ All form rows have allowed_actions with 'history'")
    
    def test_sendable_forms_have_send_action(self, auth_headers):
        """Test that employee_sendable forms have 'send' action when not completed."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sendable_keys = ["staff_health_questionnaire", "staff_personal_info", "hmrc_starter_checklist", "equal_opportunities"]
        
        # Collect all form rows
        all_rows = []
        for section_key in ["recruitment_record", "health_competency", "admin_forms"]:
            section = data.get("sections", {}).get(section_key, {})
            all_rows.extend(section.get("rows", []))
        
        for row in all_rows:
            key = row.get("key")
            if key in sendable_keys:
                has_submission = row.get("has_submission", False)
                allowed_actions = row.get("allowed_actions", [])
                
                if not has_submission:
                    assert "send" in allowed_actions, \
                        f"Sendable form {key} without submission should have 'send' action"
                    assert "fill_form" in allowed_actions, \
                        f"Sendable form {key} without submission should have 'fill_form' action"
        
        print("✓ Sendable forms have correct actions based on state")
    
    def test_admin_only_forms_no_send_action(self, auth_headers):
        """Test that admin_only forms don't have 'send' action."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        admin_only_keys = ["interview_record", "recruitment_checklist", "induction"]
        
        # Collect all form rows
        all_rows = []
        for section_key in ["recruitment_record", "health_competency", "admin_forms"]:
            section = data.get("sections", {}).get(section_key, {})
            all_rows.extend(section.get("rows", []))
        
        for row in all_rows:
            key = row.get("key")
            if key in admin_only_keys:
                allowed_actions = row.get("allowed_actions", [])
                assert "send" not in allowed_actions, \
                    f"Admin-only form {key} should NOT have 'send' action"
        
        print("✓ Admin-only forms don't have 'send' action")


class TestFormRowStatus:
    """Test form row status and blocker logic."""
    
    def test_form_rows_have_status_field(self, auth_headers):
        """Test that form rows have status field."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        valid_statuses = ["verified", "awaiting_review", "recorded", "not_completed"]
        
        # Collect all form rows
        all_rows = []
        for section_key in ["recruitment_record", "health_competency", "admin_forms"]:
            section = data.get("sections", {}).get(section_key, {})
            all_rows.extend(section.get("rows", []))
        
        for row in all_rows:
            key = row.get("key")
            status = row.get("status")
            
            assert status in valid_statuses, \
                f"Row {key} has invalid status '{status}', expected one of {valid_statuses}"
            
            # Also check status_summary exists
            assert row.get("status_summary"), f"Row {key} missing status_summary"
        
        print("✓ All form rows have valid status and status_summary")
    
    def test_blocking_requirements_have_blocker_text(self, auth_headers):
        """Test that blocking requirements have blocker_text when not verified."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Requirements that affect readiness
        blocking_keys = ["staff_health_questionnaire", "induction"]
        
        # Collect all form rows
        all_rows = []
        for section_key in ["recruitment_record", "health_competency", "admin_forms"]:
            section = data.get("sections", {}).get(section_key, {})
            all_rows.extend(section.get("rows", []))
        
        for row in all_rows:
            key = row.get("key")
            if key in blocking_keys:
                affects_readiness = row.get("affects_readiness", False)
                is_verified = row.get("is_verified", False)
                blocker_text = row.get("blocker_text")
                
                assert affects_readiness, f"Row {key} should have affects_readiness=True"
                
                if not is_verified:
                    assert blocker_text, f"Unverified blocking row {key} should have blocker_text"
                    print(f"  - {key}: blocker_text='{blocker_text}'")
        
        print("✓ Blocking requirements have correct blocker_text")
    
    def test_optional_forms_have_optional_flag(self, auth_headers):
        """Test that optional forms have optional=True."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Equal opportunities is optional
        admin_rows = data.get("sections", {}).get("admin_forms", {}).get("rows", [])
        eq_row = next((r for r in admin_rows if r.get("key") == "equal_opportunities"), None)
        
        assert eq_row is not None, "Equal opportunities row not found"
        assert eq_row.get("optional") == True, "Equal opportunities should be optional"
        
        # Optional forms should NOT have blocker_text even if not verified
        assert eq_row.get("blocker_text") is None, "Optional form should not have blocker_text"
        
        print("✓ Optional forms have correct optional flag and no blocker_text")


class TestComplianceFileSummary:
    """Test compliance file summary includes new section blockers."""
    
    def test_summary_includes_blocking_count(self, auth_headers):
        """Test that summary includes blocking requirements count."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        summary = data.get("summary", {})
        
        assert "blocking_requirements" in summary, "Summary missing blocking_requirements"
        assert isinstance(summary.get("blocking_requirements"), int), "blocking_requirements should be int"
        
        print(f"✓ Summary has blocking_requirements={summary.get('blocking_requirements')}")
    
    def test_summary_blocking_items_include_new_sections(self, auth_headers):
        """Test that blocking_items can include items from new sections."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        summary = data.get("summary", {})
        blocking_items = summary.get("blocking_items", [])
        
        # Check structure of blocking items
        for item in blocking_items:
            assert "section" in item, "Blocking item missing 'section'"
            assert "row_key" in item, "Blocking item missing 'row_key'"
            assert "message" in item, "Blocking item missing 'message'"
        
        # Check if any blocking items are from new sections
        new_section_blockers = [
            item for item in blocking_items 
            if item.get("section") in ["recruitment_record", "health_competency", "admin_forms"]
        ]
        
        print(f"✓ Summary has {len(blocking_items)} blocking items, {len(new_section_blockers)} from new sections")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

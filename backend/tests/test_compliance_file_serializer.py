"""
Test Suite: Phase 3 - Compliance File Serializer (Dual-Row Structure)
Tests GET /api/employees/{id}/compliance-file endpoint

Features tested:
- serializer_version: dual_row_v1
- row_type: evidence | check | form_acknowledgement
- allowed_actions arrays
- affects_readiness and is_supporting_evidence flags
- blocker_text for blocking rows
- Evidence row counts (active_files, verified, awaiting_verification, pending_requests, history)
- Check row check_data (method, outcome, checked_at, checked_by)
- Check row follow_up_info
- Agreement row acknowledgement_data (version, completion_mode, verification_status)
- Address Verification verified_count/required_count (X/2 format)
- Migration info for migrated check records
- Summary blocking_items with section and row_key
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee with known data
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestComplianceFileSerializer:
    """Test the dual-row compliance file serializer (Phase 3)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")  # API returns 'token' not 'access_token'
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_compliance_file_returns_serializer_version(self):
        """Test that compliance-file returns serializer_version: dual_row_v1"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "serializer_version" in data, "Missing serializer_version field"
        assert data["serializer_version"] == "dual_row_v1", f"Expected dual_row_v1, got {data['serializer_version']}"
    
    def test_compliance_file_has_required_sections(self):
        """Test that compliance-file returns all required sections"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        assert "sections" in data, "Missing sections field"
        
        required_sections = ["right_to_work", "dbs", "identity", "proof_of_address", "agreements", "references", "training"]
        for section in required_sections:
            assert section in data["sections"], f"Missing section: {section}"
    
    def test_evidence_row_structure(self):
        """Test evidence row has correct structure with row_type, allowed_actions, counts"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        # Find evidence row
        evidence_row = None
        for row in rtw_section.get("rows", []):
            if row.get("row_type") == "evidence":
                evidence_row = row
                break
        
        assert evidence_row is not None, "No evidence row found in right_to_work section"
        
        # Check row_type
        assert evidence_row["row_type"] == "evidence", f"Expected row_type 'evidence', got {evidence_row['row_type']}"
        
        # Check allowed_actions is array
        assert "allowed_actions" in evidence_row, "Missing allowed_actions"
        assert isinstance(evidence_row["allowed_actions"], list), "allowed_actions should be a list"
        
        # Check readiness flags
        assert "affects_readiness" in evidence_row, "Missing affects_readiness"
        assert evidence_row["affects_readiness"] == False, "Evidence row should not affect readiness directly"
        assert "is_supporting_evidence" in evidence_row, "Missing is_supporting_evidence"
        assert evidence_row["is_supporting_evidence"] == True, "Evidence row should be supporting evidence"
        
        # Check blocker_text (should be None for evidence rows)
        assert "blocker_text" in evidence_row, "Missing blocker_text"
        assert evidence_row["blocker_text"] is None, "Evidence rows should not have blocker_text"
        
        # Check counts structure
        assert "counts" in evidence_row, "Missing counts"
        counts = evidence_row["counts"]
        required_count_fields = ["active_files", "verified", "awaiting_verification", "pending_requests", "history"]
        for field in required_count_fields:
            assert field in counts, f"Missing count field: {field}"
            assert isinstance(counts[field], int), f"Count field {field} should be integer"
    
    def test_check_row_structure(self):
        """Test check row has correct structure with row_type, check_data, allowed_actions"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        # Find check row
        check_row = None
        for row in rtw_section.get("rows", []):
            if row.get("row_type") == "check":
                check_row = row
                break
        
        assert check_row is not None, "No check row found in right_to_work section"
        
        # Check row_type
        assert check_row["row_type"] == "check", f"Expected row_type 'check', got {check_row['row_type']}"
        
        # Check allowed_actions is array
        assert "allowed_actions" in check_row, "Missing allowed_actions"
        assert isinstance(check_row["allowed_actions"], list), "allowed_actions should be a list"
        
        # Check readiness flags
        assert "affects_readiness" in check_row, "Missing affects_readiness"
        assert check_row["affects_readiness"] == True, "Check row should affect readiness"
        assert "is_supporting_evidence" in check_row, "Missing is_supporting_evidence"
        assert check_row["is_supporting_evidence"] == False, "Check row should not be supporting evidence"
        
        # Check blocker_text (may or may not be present depending on verification status)
        assert "blocker_text" in check_row, "Missing blocker_text field"
        
        # Check check_data structure when check exists
        if check_row.get("has_check"):
            assert "check_data" in check_row, "Missing check_data"
            check_data = check_row["check_data"]
            assert check_data is not None, "check_data should not be None when has_check is True"
            
            # Verify check_data fields
            expected_check_fields = ["method", "outcome", "checked_at", "checked_by"]
            for field in expected_check_fields:
                assert field in check_data, f"Missing check_data field: {field}"
    
    def test_check_row_allowed_actions(self):
        """Test check row allowed_actions contains expected actions"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        check_row = None
        for row in rtw_section.get("rows", []):
            if row.get("row_type") == "check":
                check_row = row
                break
        
        assert check_row is not None
        allowed_actions = check_row["allowed_actions"]
        
        # Should have either record_check or update_check
        has_record_or_update = "record_check" in allowed_actions or "update_check" in allowed_actions
        assert has_record_or_update, "Check row should have record_check or update_check action"
        
        # Should have view_history
        assert "view_history" in allowed_actions, "Check row should have view_history action"
    
    def test_evidence_row_allowed_actions(self):
        """Test evidence row allowed_actions contains expected actions"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        evidence_row = None
        for row in rtw_section.get("rows", []):
            if row.get("row_type") == "evidence":
                evidence_row = row
                break
        
        assert evidence_row is not None
        allowed_actions = evidence_row["allowed_actions"]
        
        # Should have upload action
        assert "upload" in allowed_actions, "Evidence row should have upload action"
        
        # Should have view_history
        assert "view_history" in allowed_actions, "Evidence row should have view_history action"
    
    def test_agreement_row_structure(self):
        """Test agreement row has correct structure with row_type form_acknowledgement"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        agreements_section = data["sections"]["agreements"]
        
        # Find form_acknowledgement row
        agreement_row = None
        for row in agreements_section.get("rows", []):
            if row.get("row_type") == "form_acknowledgement":
                agreement_row = row
                break
        
        assert agreement_row is not None, "No form_acknowledgement row found in agreements section"
        
        # Check row_type
        assert agreement_row["row_type"] == "form_acknowledgement"
        
        # Check allowed_actions
        assert "allowed_actions" in agreement_row
        assert isinstance(agreement_row["allowed_actions"], list)
        
        # Check readiness flags
        assert "affects_readiness" in agreement_row
        assert agreement_row["affects_readiness"] == True
        
        # Check acknowledgement_data structure when acknowledgement exists
        if agreement_row.get("has_acknowledgement"):
            assert "acknowledgement_data" in agreement_row
            ack_data = agreement_row["acknowledgement_data"]
            assert ack_data is not None
            
            # Verify acknowledgement_data fields
            expected_ack_fields = ["version_acknowledged", "completion_mode", "verification_status"]
            for field in expected_ack_fields:
                assert field in ack_data, f"Missing acknowledgement_data field: {field}"
    
    def test_address_verification_row_structure(self):
        """Test address verification row shows verified_count/required_count (X/2 format)"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        poa_section = data["sections"]["proof_of_address"]
        
        # Find address verification row (check type)
        addr_row = None
        for row in poa_section.get("rows", []):
            if row.get("key") == "address_verification":
                addr_row = row
                break
        
        assert addr_row is not None, "No address_verification row found"
        
        # Check row_type is check
        assert addr_row["row_type"] == "check"
        
        # Check counts has verified_count and required_count
        assert "counts" in addr_row
        counts = addr_row["counts"]
        assert "verified_count" in counts, "Missing verified_count in address verification"
        assert "required_count" in counts, "Missing required_count in address verification"
        assert counts["required_count"] == 2, "Address verification should require 2 documents"
        
        # Check status_summary shows X/2 format
        assert "status_summary" in addr_row
        assert "/2" in addr_row["status_summary"], f"Status summary should show X/2 format, got: {addr_row['status_summary']}"
        
        # Check check_data has minimum_required
        if addr_row.get("check_data"):
            assert "minimum_required" in addr_row["check_data"]
            assert addr_row["check_data"]["minimum_required"] == 2
    
    def test_check_row_follow_up_info(self):
        """Test check row has follow_up_info when applicable"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        dbs_section = data["sections"]["dbs"]
        
        # Find DBS check row
        dbs_check_row = None
        for row in dbs_section.get("rows", []):
            if row.get("row_type") == "check":
                dbs_check_row = row
                break
        
        assert dbs_check_row is not None
        
        # follow_up_info field should exist (may be null)
        assert "follow_up_info" in dbs_check_row, "Missing follow_up_info field"
        
        # If follow_up_info exists, check structure
        if dbs_check_row["follow_up_info"]:
            follow_up = dbs_check_row["follow_up_info"]
            expected_fields = ["label", "date", "days_until", "is_overdue", "is_due_soon"]
            for field in expected_fields:
                assert field in follow_up, f"Missing follow_up_info field: {field}"
    
    def test_check_row_migration_info(self):
        """Test check row has migration_info for migrated records"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check all check rows for migration_info field
        for section_key, section in data["sections"].items():
            if "rows" in section:
                for row in section["rows"]:
                    if row.get("row_type") == "check":
                        assert "migration_info" in row, f"Missing migration_info in {section_key} check row"
                        
                        # If migration_info exists, check structure
                        if row["migration_info"]:
                            migration = row["migration_info"]
                            assert "created_source" in migration
                            assert migration["created_source"] == "migration"
    
    def test_summary_has_blocking_items(self):
        """Test summary includes blocking_items with section and row_key"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        assert "summary" in data, "Missing summary field"
        summary = data["summary"]
        
        # Check required summary fields
        assert "blocking_requirements" in summary, "Missing blocking_requirements count"
        assert "blocking_items" in summary, "Missing blocking_items array"
        assert "awaiting_review" in summary, "Missing awaiting_review count"
        
        # Check blocking_items structure
        assert isinstance(summary["blocking_items"], list)
        
        # If there are blocking items, verify structure
        for item in summary["blocking_items"]:
            assert "section" in item, "Blocking item missing section"
            assert "row_key" in item, "Blocking item missing row_key"
            assert "message" in item, "Blocking item missing message"
    
    def test_all_sections_have_rows_array(self):
        """Test that sections with dual-row model have rows array"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        # Sections that should have rows array
        dual_row_sections = ["right_to_work", "dbs", "identity", "proof_of_address", "agreements"]
        
        for section_key in dual_row_sections:
            section = data["sections"][section_key]
            assert "rows" in section, f"Section {section_key} missing rows array"
            assert isinstance(section["rows"], list), f"Section {section_key} rows should be a list"
            assert len(section["rows"]) > 0, f"Section {section_key} should have at least one row"
    
    def test_paired_keys_are_correct(self):
        """Test that evidence and check rows have correct paired keys"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check RTW section
        rtw_section = data["sections"]["right_to_work"]
        evidence_row = None
        check_row = None
        
        for row in rtw_section["rows"]:
            if row["row_type"] == "evidence":
                evidence_row = row
            elif row["row_type"] == "check":
                check_row = row
        
        assert evidence_row is not None and check_row is not None
        
        # Evidence row should point to check row
        assert "paired_check_key" in evidence_row
        assert evidence_row["paired_check_key"] == check_row["key"]
        
        # Check row should point to evidence row
        assert "paired_evidence_key" in check_row
        assert check_row["paired_evidence_key"] == evidence_row["key"]
    
    def test_employee_info_in_response(self):
        """Test that response includes employee_id and employee_name"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        assert "employee_id" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        
        assert "employee_name" in data
        assert isinstance(data["employee_name"], str)
        assert len(data["employee_name"]) > 0
    
    def test_nonexistent_employee_returns_404(self):
        """Test that non-existent employee returns 404"""
        response = self.session.get(f"{BASE_URL}/api/employees/nonexistent-id-12345/compliance-file")
        assert response.status_code == 404
    
    def test_dbs_section_structure(self):
        """Test DBS section has evidence and check rows"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        dbs_section = data["sections"]["dbs"]
        
        row_types = [row["row_type"] for row in dbs_section["rows"]]
        assert "evidence" in row_types, "DBS section missing evidence row"
        assert "check" in row_types, "DBS section missing check row"
    
    def test_identity_section_structure(self):
        """Test Identity section has evidence and check rows"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        identity_section = data["sections"]["identity"]
        
        row_types = [row["row_type"] for row in identity_section["rows"]]
        assert "evidence" in row_types, "Identity section missing evidence row"
        assert "check" in row_types, "Identity section missing check row"
    
    def test_agreements_section_has_multiple_rows(self):
        """Test Agreements section has contract and handbook rows"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        agreements_section = data["sections"]["agreements"]
        
        row_keys = [row["key"] for row in agreements_section["rows"]]
        assert "contract_acceptance" in row_keys, "Agreements section missing contract_acceptance"
        assert "handbook_acknowledgement" in row_keys, "Agreements section missing handbook_acknowledgement"
    
    def test_references_section_structure(self):
        """Test References section has reference_1 and reference_2"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        references_section = data["sections"]["references"]
        
        assert "reference_1" in references_section
        assert "reference_2" in references_section
        assert "valid_count" in references_section
    
    def test_training_section_structure(self):
        """Test Training section has evaluation"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        training_section = data["sections"]["training"]
        
        assert "evaluation" in training_section
    
    def test_evidence_row_documents_preview(self):
        """Test evidence row has documents_preview array"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        evidence_row = None
        for row in rtw_section["rows"]:
            if row["row_type"] == "evidence":
                evidence_row = row
                break
        
        assert evidence_row is not None
        assert "documents_preview" in evidence_row
        assert isinstance(evidence_row["documents_preview"], list)
        assert "has_more_documents" in evidence_row
    
    def test_evidence_row_status_fields(self):
        """Test evidence row has status and status_summary"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        evidence_row = None
        for row in rtw_section["rows"]:
            if row["row_type"] == "evidence":
                evidence_row = row
                break
        
        assert evidence_row is not None
        assert "status" in evidence_row
        assert "status_summary" in evidence_row
        assert evidence_row["status"] in ["has_files", "empty"]
    
    def test_check_row_status_fields(self):
        """Test check row has status and status_summary"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        check_row = None
        for row in rtw_section["rows"]:
            if row["row_type"] == "check":
                check_row = row
                break
        
        assert check_row is not None
        assert "status" in check_row
        assert "status_summary" in check_row
        assert check_row["status"] in ["verified", "recorded", "not_recorded"]
    
    def test_check_row_has_check_flag(self):
        """Test check row has has_check and is_verified flags"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        rtw_section = data["sections"]["right_to_work"]
        
        check_row = None
        for row in rtw_section["rows"]:
            if row["row_type"] == "check":
                check_row = row
                break
        
        assert check_row is not None
        assert "has_check" in check_row
        assert isinstance(check_row["has_check"], bool)
        assert "is_verified" in check_row
        assert isinstance(check_row["is_verified"], bool)
    
    def test_agreement_row_has_acknowledgement_flag(self):
        """Test agreement row has has_acknowledgement and is_verified flags"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        agreements_section = data["sections"]["agreements"]
        
        agreement_row = None
        for row in agreements_section["rows"]:
            if row["row_type"] == "form_acknowledgement":
                agreement_row = row
                break
        
        assert agreement_row is not None
        assert "has_acknowledgement" in agreement_row
        assert isinstance(agreement_row["has_acknowledgement"], bool)
        assert "is_verified" in agreement_row
        assert isinstance(agreement_row["is_verified"], bool)


class TestComplianceFileWithVerifiedData:
    """Test compliance file with employee that has verified checks"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")  # API returns 'token' not 'access_token'
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_verified_check_has_no_blocker_text(self):
        """Test that verified check rows have no blocker_text"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find any verified check row
        for section_key, section in data["sections"].items():
            if "rows" in section:
                for row in section["rows"]:
                    if row.get("row_type") == "check" and row.get("is_verified"):
                        assert row["blocker_text"] is None, f"Verified check in {section_key} should not have blocker_text"
    
    def test_verified_check_status_summary_format(self):
        """Test verified check status_summary shows method and date"""
        response = self.session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find any verified check row
        for section_key, section in data["sections"].items():
            if "rows" in section:
                for row in section["rows"]:
                    if row.get("row_type") == "check" and row.get("is_verified"):
                        status_summary = row["status_summary"]
                        assert "Verified" in status_summary, f"Verified check status should contain 'Verified'"
                        assert "Method:" in status_summary or "•" in status_summary, f"Status should show method info"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

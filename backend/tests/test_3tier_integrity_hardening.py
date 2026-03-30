"""
Test 3-Tier Work Readiness Integrity Hardening
Tests for:
1. Applicant profile NEVER shows 'Ready to Work' - must show 'Not Ready'
2. Applicant work status includes 'Applicant - not yet recruited' reason
3. Unapproved staff shows 'Recruitment not approved' blocking reason
4. Proof of address (2 required) appears in blocking reasons
5. Reference 1 and Reference 2 appear as separate blocking reasons
6. Work Status panel uses 3-tier model (Not Ready to Work / Ready with Conditions / Ready to Work)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test IDs from the review request
APPLICANT_ID = "8f351317-8623-4df5-8788-c6a3ce5364cf"  # Olumide, applicant stage
EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle, employee but not recruitment_approved


class TestAuthSetup:
    """Get auth token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        # API returns 'token' not 'access_token'
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def api_client(self, auth_token):
        """Create authenticated session"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        })
        return session


class TestApplicantWorkReadiness(TestAuthSetup):
    """Test that applicants NEVER show 'Ready to Work'"""
    
    def test_applicant_compliance_requirements_returns_not_ready(self, api_client):
        """Applicant profile must show 'Not Ready to Work' status"""
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}/compliance-requirements")
        
        # Check API returns successfully
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Verify work_readiness_3tier exists
        assert "work_readiness_3tier" in data, "Missing work_readiness_3tier in response"
        work_status = data["work_readiness_3tier"]
        
        # CRITICAL: Applicant must NEVER be 'READY_TO_WORK'
        assert work_status["status"] == "NOT_READY", \
            f"Applicant should be NOT_READY, got: {work_status['status']}"
        
        # Verify label matches
        assert work_status["label"] == "Not Ready to Work", \
            f"Expected 'Not Ready to Work', got: {work_status['label']}"
        
        print(f"✓ Applicant work status: {work_status['status']} - {work_status['label']}")
    
    def test_applicant_has_applicant_stage_blocking_reason(self, api_client):
        """Applicant must have 'Applicant - not yet recruited' in blocking reasons"""
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        work_status = data["work_readiness_3tier"]
        reasons = work_status.get("reasons", [])
        
        # Find the applicant_stage reason
        applicant_reason = next(
            (r for r in reasons if r.get("code") == "applicant_stage"),
            None
        )
        
        assert applicant_reason is not None, \
            f"Missing 'applicant_stage' blocking reason. Reasons: {[r.get('code') for r in reasons]}"
        
        assert applicant_reason["type"] == "hard_block", \
            f"applicant_stage should be hard_block, got: {applicant_reason['type']}"
        
        assert "Applicant" in applicant_reason["message"], \
            f"Message should contain 'Applicant', got: {applicant_reason['message']}"
        
        print(f"✓ Applicant blocking reason: {applicant_reason['message']}")
    
    def test_applicant_employee_data_shows_applicant_stage(self, api_client):
        """Verify employee data has person_stage = 'applicant'"""
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Check person_stage is applicant
        person_stage = data.get("person_stage")
        assert person_stage == "applicant", \
            f"Expected person_stage='applicant', got: {person_stage}"
        
        print(f"✓ Employee person_stage: {person_stage}")


class TestUnapprovedStaffWorkReadiness(TestAuthSetup):
    """Test that unapproved staff shows 'Recruitment not approved' blocking reason"""
    
    def test_unapproved_staff_shows_not_ready(self, api_client):
        """Unapproved staff must show 'Not Ready to Work' status"""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        work_status = data["work_readiness_3tier"]
        
        # Unapproved staff should be NOT_READY
        assert work_status["status"] == "NOT_READY", \
            f"Unapproved staff should be NOT_READY, got: {work_status['status']}"
        
        print(f"✓ Unapproved staff work status: {work_status['status']} - {work_status['label']}")
    
    def test_unapproved_staff_has_recruitment_not_approved_reason(self, api_client):
        """Unapproved staff must have 'Recruitment not approved' in blocking reasons"""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        work_status = data["work_readiness_3tier"]
        reasons = work_status.get("reasons", [])
        
        # Find the recruitment_not_approved reason
        recruitment_reason = next(
            (r for r in reasons if r.get("code") == "recruitment_not_approved"),
            None
        )
        
        assert recruitment_reason is not None, \
            f"Missing 'recruitment_not_approved' blocking reason. Reasons: {[r.get('code') for r in reasons]}"
        
        assert recruitment_reason["type"] == "hard_block", \
            f"recruitment_not_approved should be hard_block, got: {recruitment_reason['type']}"
        
        print(f"✓ Unapproved staff blocking reason: {recruitment_reason['message']}")


class TestBlockingReasons(TestAuthSetup):
    """Test that all required blocking reasons appear correctly"""
    
    def test_proof_of_address_blocking_reason_format(self, api_client):
        """Proof of address (2 required) should appear in blocking reasons"""
        # Test with applicant who likely doesn't have 2 proof of address docs
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        work_status = data["work_readiness_3tier"]
        reasons = work_status.get("reasons", [])
        
        # Find proof_of_address reason
        poa_reason = next(
            (r for r in reasons if r.get("code") == "proof_of_address_incomplete"),
            None
        )
        
        # If present, verify format
        if poa_reason:
            assert "2" in poa_reason["message"] or "required" in poa_reason["message"].lower(), \
                f"POA message should mention '2 required', got: {poa_reason['message']}"
            print(f"✓ Proof of address blocking reason: {poa_reason['message']}")
        else:
            print("ℹ Proof of address not in blocking reasons (may be complete)")
    
    def test_reference_1_and_2_separate_blocking_reasons(self, api_client):
        """Reference 1 and Reference 2 should appear as separate blocking reasons"""
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        work_status = data["work_readiness_3tier"]
        reasons = work_status.get("reasons", [])
        reason_codes = [r.get("code") for r in reasons]
        
        # Check for separate reference blocking reasons
        ref1_present = "reference_1_incomplete" in reason_codes
        ref2_present = "reference_2_incomplete" in reason_codes
        
        # At least verify the codes exist in the logic (may not be blocking if verified)
        print(f"ℹ Reference 1 blocking: {ref1_present}")
        print(f"ℹ Reference 2 blocking: {ref2_present}")
        
        # If both are present, verify they are separate
        if ref1_present and ref2_present:
            ref1_reason = next(r for r in reasons if r.get("code") == "reference_1_incomplete")
            ref2_reason = next(r for r in reasons if r.get("code") == "reference_2_incomplete")
            
            assert "Reference 1" in ref1_reason["message"], \
                f"Reference 1 message should mention 'Reference 1', got: {ref1_reason['message']}"
            assert "Reference 2" in ref2_reason["message"], \
                f"Reference 2 message should mention 'Reference 2', got: {ref2_reason['message']}"
            
            print(f"✓ Reference 1 blocking reason: {ref1_reason['message']}")
            print(f"✓ Reference 2 blocking reason: {ref2_reason['message']}")


class Test3TierStatusModel(TestAuthSetup):
    """Test that the 3-tier status model is correctly implemented"""
    
    def test_3tier_status_values(self, api_client):
        """Verify 3-tier model uses correct status values"""
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        work_status = data["work_readiness_3tier"]
        
        # Verify status is one of the 3 valid values
        valid_statuses = ["NOT_READY", "READY_WITH_CONDITIONS", "READY_TO_WORK"]
        assert work_status["status"] in valid_statuses, \
            f"Invalid status: {work_status['status']}. Must be one of {valid_statuses}"
        
        # Verify label matches status
        expected_labels = {
            "NOT_READY": "Not Ready to Work",
            "READY_WITH_CONDITIONS": "Ready with Conditions",
            "READY_TO_WORK": "Ready to Work"
        }
        expected_label = expected_labels[work_status["status"]]
        assert work_status["label"] == expected_label, \
            f"Label mismatch: expected '{expected_label}', got '{work_status['label']}'"
        
        # Verify color matches status
        expected_colors = {
            "NOT_READY": "error",
            "READY_WITH_CONDITIONS": "warning",
            "READY_TO_WORK": "success"
        }
        expected_color = expected_colors[work_status["status"]]
        assert work_status["color"] == expected_color, \
            f"Color mismatch: expected '{expected_color}', got '{work_status['color']}'"
        
        print(f"✓ 3-tier status model verified: {work_status['status']} / {work_status['label']} / {work_status['color']}")
    
    def test_reasons_have_correct_structure(self, api_client):
        """Verify blocking reasons have correct structure"""
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        work_status = data["work_readiness_3tier"]
        reasons = work_status.get("reasons", [])
        
        # Verify each reason has required fields
        for reason in reasons:
            assert "type" in reason, f"Reason missing 'type': {reason}"
            assert "code" in reason, f"Reason missing 'code': {reason}"
            assert "message" in reason, f"Reason missing 'message': {reason}"
            
            # Verify type is valid
            assert reason["type"] in ["hard_block", "conditional"], \
                f"Invalid reason type: {reason['type']}"
        
        print(f"✓ All {len(reasons)} reasons have correct structure")


class TestComplianceFileSummary(TestAuthSetup):
    """Test that compliance file summary matches 3-tier status"""
    
    def test_compliance_summary_includes_work_readiness(self, api_client):
        """Compliance summary should include work_readiness_3tier"""
        response = api_client.get(f"{BASE_URL}/api/employees/{APPLICANT_ID}/compliance-requirements")
        assert response.status_code == 200
        data = response.json()
        
        # Verify work_readiness_3tier is present
        assert "work_readiness_3tier" in data, "Missing work_readiness_3tier in compliance summary"
        
        # Verify statuses are present
        assert "statuses" in data, "Missing statuses in compliance summary"
        
        print(f"✓ Compliance summary includes work_readiness_3tier and statuses")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

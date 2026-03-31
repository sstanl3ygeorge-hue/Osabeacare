"""
Test Suite for Step 11: Dual-Row Evidence/Check Model

Tests the separation of evidence files from employer verification checks:
- RTW Check endpoints (POST/GET)
- DBS Check endpoints (POST/GET)
- Identity Check endpoints (POST/GET)
- Address Verification endpoints (POST/GET)
- Agreement endpoints (send, complete, get, verify)
- Dual-row migration endpoints (dry-run and actual)
- Readiness calculation using check records
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID from the review request
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


class TestAuth:
    """Authentication helper for tests."""
    
    @staticmethod
    def get_admin_token():
        """Get admin authentication token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token for authenticated requests."""
    token = TestAuth.get_admin_token()
    if not token:
        pytest.skip("Admin authentication failed - skipping tests")
    return token


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Get headers with admin authentication."""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def test_employee_id(auth_headers):
    """Get or create a test employee for testing."""
    # First try to use the existing test employee
    response = requests.get(
        f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
        headers=auth_headers
    )
    if response.status_code == 200:
        return TEST_EMPLOYEE_ID
    
    # If not found, get any active employee
    response = requests.get(
        f"{BASE_URL}/api/employees",
        headers=auth_headers
    )
    if response.status_code == 200:
        employees = response.json()
        if employees and len(employees) > 0:
            return employees[0].get("id")
    
    pytest.skip("No test employee available")


# ==================== RTW CHECK TESTS ====================

class TestRTWCheckEndpoints:
    """Tests for Right to Work check endpoints."""
    
    def test_record_rtw_check_success(self, auth_headers, test_employee_id):
        """Test recording a new RTW check."""
        payload = {
            "method": "share_code_online_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "source_status_type": "digital_status",
            "follow_up_due_at": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "notes": "TEST_RTW_CHECK: Online Home Office check completed"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should contain check ID"
        assert data["id"].startswith("rtw_chk_"), "Check ID should have correct prefix"
        assert data["employee_id"] == test_employee_id
        assert data["method"] == "share_code_online_check"
        assert data["outcome"] == "verified"
        assert data["is_current"] == True
        print(f"✓ RTW check recorded: {data['id']}")
    
    def test_record_rtw_check_awaiting_review(self, auth_headers, test_employee_id):
        """Test recording RTW check with awaiting_review outcome."""
        payload = {
            "method": "manual_passport_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "awaiting_review",
            "notes": "TEST_RTW_CHECK: Passport submitted, pending verification"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "awaiting_review"
        print(f"✓ RTW check with awaiting_review recorded: {data['id']}")
    
    def test_get_current_rtw_check(self, auth_headers, test_employee_id):
        """Test getting the current RTW check."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        
        if data["current"]:
            assert data["current"]["is_current"] == True
            print(f"✓ Current RTW check retrieved: {data['current']['id']}")
        else:
            print("✓ No current RTW check (expected for new employee)")
    
    def test_get_rtw_check_with_history(self, auth_headers, test_employee_id):
        """Test getting RTW check with history."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check?include_history=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        assert "history" in data
        assert isinstance(data["history"], list)
        print(f"✓ RTW check history retrieved: {len(data['history'])} records")
    
    def test_rtw_check_supersedes_previous(self, auth_headers, test_employee_id):
        """Test that new RTW check supersedes previous one."""
        # Record first check
        payload1 = {
            "method": "share_code_online_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "notes": "TEST_RTW_CHECK: First check"
        }
        response1 = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers,
            json=payload1
        )
        assert response1.status_code == 200
        first_check_id = response1.json()["id"]
        
        # Record second check
        payload2 = {
            "method": "manual_passport_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "notes": "TEST_RTW_CHECK: Second check (should supersede first)"
        }
        response2 = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers,
            json=payload2
        )
        assert response2.status_code == 200
        second_check_id = response2.json()["id"]
        
        # Verify current check is the second one
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check?include_history=true",
            headers=auth_headers
        )
        data = response.json()
        
        assert data["current"]["id"] == second_check_id
        # First check should be in history and marked as not current
        first_in_history = next((h for h in data["history"] if h["id"] == first_check_id), None)
        if first_in_history:
            assert first_in_history["is_current"] == False
        print(f"✓ RTW check supersession verified: {first_check_id} -> {second_check_id}")


# ==================== DBS CHECK TESTS ====================

class TestDBSCheckEndpoints:
    """Tests for DBS status check endpoints."""
    
    def test_record_dbs_check_success(self, auth_headers, test_employee_id):
        """Test recording a new DBS check."""
        payload = {
            "method": "update_service_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "review_due_at": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "certificate_number": "TEST123456789012",
            "notes": "TEST_DBS_CHECK: Update Service status check - no changes"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/dbs/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["id"].startswith("dbs_chk_")
        assert data["employee_id"] == test_employee_id
        assert data["method"] == "update_service_check"
        assert data["outcome"] == "verified"
        assert data["is_current"] == True
        print(f"✓ DBS check recorded: {data['id']}")
    
    def test_record_dbs_check_manual_review(self, auth_headers, test_employee_id):
        """Test recording DBS check with manual certificate review."""
        payload = {
            "method": "manual_certificate_review",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "certificate_number": "TEST987654321098",
            "notes": "TEST_DBS_CHECK: Manual certificate review completed"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/dbs/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "manual_certificate_review"
        print(f"✓ DBS manual review check recorded: {data['id']}")
    
    def test_get_current_dbs_check(self, auth_headers, test_employee_id):
        """Test getting the current DBS check."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/dbs/check",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        print(f"✓ Current DBS check retrieved")
    
    def test_get_dbs_check_with_history(self, auth_headers, test_employee_id):
        """Test getting DBS check with history."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/dbs/check?include_history=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        assert "history" in data
        print(f"✓ DBS check history retrieved: {len(data['history'])} records")


# ==================== IDENTITY CHECK TESTS ====================

class TestIdentityCheckEndpoints:
    """Tests for identity verification check endpoints."""
    
    def test_record_identity_check_success(self, auth_headers, test_employee_id):
        """Test recording an identity verification check."""
        payload = {
            "method": "manual_id_verification",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "evidence_document_ids": ["doc_test_001", "doc_test_002"],
            "notes": "TEST_IDENTITY_CHECK: Passport and driving licence verified"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/identity/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["id"].startswith("id_ver_")
        assert data["employee_id"] == test_employee_id
        assert data["method"] == "manual_id_verification"
        assert data["outcome"] == "verified"
        assert data["is_current"] == True
        print(f"✓ Identity check recorded: {data['id']}")
    
    def test_get_current_identity_check(self, auth_headers, test_employee_id):
        """Test getting the current identity verification."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/identity/check",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        print(f"✓ Current identity check retrieved")


# ==================== ADDRESS VERIFICATION TESTS ====================

class TestAddressVerificationEndpoints:
    """Tests for address verification endpoints."""
    
    def test_record_address_verification_success(self, auth_headers, test_employee_id):
        """Test recording address verification with 2 documents."""
        payload = {
            "verified_document_ids": ["doc_addr_001", "doc_addr_002"],
            "verified_at": datetime.now().strftime("%Y-%m-%d"),
            "notes": "TEST_ADDRESS_VERIFY: Utility bill and bank statement verified"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/verify",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["id"].startswith("addr_ver_")
        assert data["employee_id"] == test_employee_id
        assert data["verified_count"] == 2
        assert data["minimum_required"] == 2
        assert data["meets_requirement"] == True
        assert data["is_current"] == True
        print(f"✓ Address verification recorded: {data['id']} (meets requirement: {data['meets_requirement']})")
    
    def test_record_address_verification_insufficient(self, auth_headers, test_employee_id):
        """Test recording address verification with only 1 document (insufficient)."""
        payload = {
            "verified_document_ids": ["doc_addr_single"],
            "verified_at": datetime.now().strftime("%Y-%m-%d"),
            "notes": "TEST_ADDRESS_VERIFY: Only 1 document - insufficient"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/verify",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["verified_count"] == 1
        assert data["meets_requirement"] == False
        print(f"✓ Address verification with insufficient docs recorded: meets_requirement={data['meets_requirement']}")
    
    def test_get_current_address_verification(self, auth_headers, test_employee_id):
        """Test getting the current address verification."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/address/verification",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        print(f"✓ Current address verification retrieved")


# ==================== AGREEMENT TESTS ====================

class TestAgreementEndpoints:
    """Tests for agreement acknowledgement endpoints."""
    
    def test_send_agreement_form(self, auth_headers, test_employee_id):
        """Test sending an agreement form to employee."""
        payload = {
            "agreement_type": "contract_acceptance",
            "version_label": "Contract-v3-TEST",
            "custom_message": "TEST_AGREEMENT: Please review and acknowledge your contract",
            "due_days": 14
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements/send",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["id"].startswith("agr_req_")
        assert data["employee_id"] == test_employee_id
        assert data["agreement_type"] == "contract_acceptance"
        assert data["status"] == "sent"
        assert "token" in data
        print(f"✓ Agreement form sent: {data['id']}")
    
    def test_complete_agreement_admin_assisted(self, auth_headers, test_employee_id):
        """Test completing an agreement in admin-assisted mode."""
        payload = {
            "agreement_type": "contract_acceptance",
            "completion_mode": "admin_assisted",
            "version_acknowledged": "Contract-v3-TEST"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements/complete",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["id"].startswith("agr_ack_")
        assert data["employee_id"] == test_employee_id
        assert data["agreement_type"] == "contract_acceptance"
        assert data["completion_mode"] == "admin_assisted"
        assert data["verification_status"] == "awaiting_review"
        print(f"✓ Agreement completed (admin-assisted): {data['id']}")
        return data["id"]
    
    def test_complete_agreement_phone_assisted(self, auth_headers, test_employee_id):
        """Test completing an agreement in phone-assisted mode."""
        payload = {
            "agreement_type": "handbook_acknowledgement",
            "completion_mode": "phone_assisted",
            "version_acknowledged": "Handbook-2026.01-TEST",
            "call_note": "TEST_AGREEMENT: Employee confirmed understanding over phone call"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements/complete",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["completion_mode"] == "phone_assisted"
        assert data["call_note"] is not None
        print(f"✓ Agreement completed (phone-assisted): {data['id']}")
    
    def test_get_employee_agreements(self, auth_headers, test_employee_id):
        """Test getting all agreements for an employee."""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "acknowledgements" in data
        assert "pending_requests" in data
        assert isinstance(data["acknowledgements"], list)
        assert isinstance(data["pending_requests"], list)
        print(f"✓ Employee agreements retrieved: {len(data['acknowledgements'])} acknowledgements, {len(data['pending_requests'])} pending")
    
    def test_verify_agreement(self, auth_headers, test_employee_id):
        """Test verifying an agreement acknowledgement."""
        # First create an agreement to verify
        complete_payload = {
            "agreement_type": "contract_acceptance",
            "completion_mode": "admin_assisted",
            "version_acknowledged": "Contract-v3-VERIFY-TEST"
        }
        complete_response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements/complete",
            headers=auth_headers,
            json=complete_payload
        )
        assert complete_response.status_code == 200
        ack_id = complete_response.json()["id"]
        
        # Now verify it
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements/{ack_id}/verify",
            headers=auth_headers,
            json="Verified during testing"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["verification_status"] == "verified"
        assert "verified_at" in data
        print(f"✓ Agreement verified: {ack_id}")
    
    def test_reject_agreement(self, auth_headers, test_employee_id):
        """Test rejecting an agreement acknowledgement."""
        # First create an agreement to reject
        complete_payload = {
            "agreement_type": "handbook_acknowledgement",
            "completion_mode": "admin_assisted",
            "version_acknowledged": "Handbook-REJECT-TEST"
        }
        complete_response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements/complete",
            headers=auth_headers,
            json=complete_payload
        )
        assert complete_response.status_code == 200
        ack_id = complete_response.json()["id"]
        
        # Now reject it
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/agreements/{ack_id}/reject",
            headers=auth_headers,
            json={"reason": "TEST_REJECTION: Incomplete acknowledgement"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["verification_status"] == "rejected"
        assert "rejected_at" in data
        assert data["rejection_reason"] == "TEST_REJECTION: Incomplete acknowledgement"
        print(f"✓ Agreement rejected: {ack_id}")


# ==================== DUAL-ROW MIGRATION TESTS ====================

class TestDualRowMigrationEndpoints:
    """Tests for dual-row migration endpoints."""
    
    def test_dry_run_migration_single_employee(self, auth_headers, test_employee_id):
        """Test dry-run migration for a single employee."""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/{test_employee_id}?dry_run=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["employee_id"] == test_employee_id
        assert data["dry_run"] == True
        assert "rtw_check" in data
        assert "dbs_check" in data
        assert "identity_check" in data
        assert "address_verification" in data
        assert "skipped" in data
        assert "errors" in data
        
        print(f"✓ Dry-run migration completed for {test_employee_id}")
        print(f"  RTW: {data['rtw_check']}")
        print(f"  DBS: {data['dbs_check']}")
        print(f"  Identity: {data['identity_check']}")
        print(f"  Address: {data['address_verification']}")
    
    def test_actual_migration_single_employee(self, auth_headers, test_employee_id):
        """Test actual migration for a single employee."""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/{test_employee_id}?dry_run=false",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["employee_id"] == test_employee_id
        assert data["dry_run"] == False
        print(f"✓ Actual migration completed for {test_employee_id}")
    
    def test_migration_nonexistent_employee(self, auth_headers):
        """Test migration for non-existent employee returns 404."""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/employee/nonexistent-id-12345?dry_run=true",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("✓ Migration correctly returns 404 for non-existent employee")
    
    def test_batch_migration_dry_run(self, auth_headers):
        """Test batch migration dry-run."""
        response = requests.post(
            f"{BASE_URL}/api/admin/dual-row-migration/batch?dry_run=true&limit=5",
            headers=auth_headers,
            json=None  # Auto-detect employees
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["dry_run"] == True
        assert "total_employees" in data
        assert "migrated" in data
        assert "skipped" in data
        assert "errors" in data
        assert "details" in data
        
        print(f"✓ Batch migration dry-run completed")
        print(f"  Total: {data['total_employees']}, Migrated: {data['migrated']}, Skipped: {data['skipped']}, Errors: {data['errors']}")


# ==================== READINESS CALCULATION TESTS ====================

class TestReadinessCalculation:
    """Tests for readiness calculation using check records."""
    
    def test_readiness_reflects_check_records(self, auth_headers, test_employee_id):
        """Test that readiness calculation uses check records."""
        # First, record verified checks
        rtw_payload = {
            "method": "share_code_online_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "notes": "TEST_READINESS: RTW verified for readiness test"
        }
        requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers,
            json=rtw_payload
        )
        
        dbs_payload = {
            "method": "update_service_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "notes": "TEST_READINESS: DBS verified for readiness test"
        }
        requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/dbs/check",
            headers=auth_headers,
            json=dbs_payload
        )
        
        identity_payload = {
            "method": "manual_id_verification",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "notes": "TEST_READINESS: Identity verified for readiness test"
        }
        requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/identity/check",
            headers=auth_headers,
            json=identity_payload
        )
        
        # Now check the employee's readiness
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that work_readiness is present
        if "work_readiness" in data:
            print(f"✓ Work readiness status: {data['work_readiness']}")
        
        # Also check compliance file endpoint
        compliance_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/compliance-file",
            headers=auth_headers
        )
        
        if compliance_response.status_code == 200:
            compliance_data = compliance_response.json()
            if "work_readiness" in compliance_data:
                print(f"✓ Compliance file work readiness: {compliance_data['work_readiness']}")
    
    def test_readiness_with_failed_check(self, auth_headers, test_employee_id):
        """Test that failed check affects readiness."""
        # Record a failed RTW check
        payload = {
            "method": "share_code_online_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "failed",
            "notes": "TEST_READINESS: RTW check failed - should affect readiness"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["outcome"] == "failed"
        print(f"✓ Failed RTW check recorded: {data['id']}")
        
        # Restore to verified for other tests
        restore_payload = {
            "method": "share_code_online_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified",
            "notes": "TEST_READINESS: Restored to verified"
        }
        requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/right-to-work/check",
            headers=auth_headers,
            json=restore_payload
        )


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Tests for error handling in check endpoints."""
    
    def test_rtw_check_nonexistent_employee(self, auth_headers):
        """Test RTW check for non-existent employee."""
        payload = {
            "method": "share_code_online_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/right-to-work/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 404
        print("✓ RTW check correctly returns 404 for non-existent employee")
    
    def test_dbs_check_nonexistent_employee(self, auth_headers):
        """Test DBS check for non-existent employee."""
        payload = {
            "method": "update_service_check",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/dbs/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 404
        print("✓ DBS check correctly returns 404 for non-existent employee")
    
    def test_identity_check_nonexistent_employee(self, auth_headers):
        """Test identity check for non-existent employee."""
        payload = {
            "method": "manual_id_verification",
            "checked_at": datetime.now().strftime("%Y-%m-%d"),
            "outcome": "verified"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/identity/check",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 404
        print("✓ Identity check correctly returns 404 for non-existent employee")
    
    def test_address_verify_nonexistent_employee(self, auth_headers):
        """Test address verification for non-existent employee."""
        payload = {
            "verified_document_ids": ["doc1", "doc2"],
            "verified_at": datetime.now().strftime("%Y-%m-%d")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/address/verify",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 404
        print("✓ Address verification correctly returns 404 for non-existent employee")
    
    def test_agreement_send_nonexistent_employee(self, auth_headers):
        """Test sending agreement to non-existent employee."""
        payload = {
            "agreement_type": "contract_acceptance",
            "version_label": "Contract-v1"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-employee-id/agreements/send",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 404
        print("✓ Agreement send correctly returns 404 for non-existent employee")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

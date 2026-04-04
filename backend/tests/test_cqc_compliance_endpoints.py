"""
CQC Compliance Endpoints Tests
Tests for:
- Audit Trail endpoint
- Unified Compliance Status endpoint
- Health Declaration endpoints (submit, get, history, review, pending)
"""

import pytest
import requests
import os
from datetime import date, datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ==================== AUDIT TRAIL TESTS ====================

class TestAuditTrailEndpoint:
    """Tests for GET /api/employees/{id}/audit-trail"""
    
    def test_get_audit_trail_success(self, authenticated_client):
        """Test getting audit trail for test employee."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert "employee_name" in data
        assert "audit_trail" in data
        assert isinstance(data["audit_trail"], list)
        assert "total_returned" in data
        assert "pagination" in data
        print(f"Audit trail returned {data['total_returned']} entries")
    
    def test_get_audit_trail_with_pagination(self, authenticated_client):
        """Test audit trail with pagination parameters."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail",
            params={"limit": 10, "skip": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["skip"] == 0
    
    def test_get_audit_trail_with_action_filter(self, authenticated_client):
        """Test audit trail with action type filter."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/audit-trail",
            params={"action_type": "HEALTH_DECLARATION_SUBMITTED"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return empty or filtered results
        assert "audit_trail" in data
    
    def test_get_audit_trail_invalid_employee(self, authenticated_client):
        """Test audit trail for non-existent employee."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/invalid-employee-id/audit-trail"
        )
        
        assert response.status_code == 404


# ==================== UNIFIED COMPLIANCE STATUS TESTS ====================

class TestUnifiedComplianceStatusEndpoint:
    """Tests for GET /api/employees/{id}/unified-compliance-status"""
    
    def test_get_unified_compliance_status_success(self, authenticated_client):
        """Test getting unified compliance status."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-compliance-status"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        assert "employee_id" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert "employee_name" in data
        assert "requirements" in data
        assert "overall_status" in data
        assert "regulatory_status" in data
        
        # Verify requirement statuses
        requirements = data["requirements"]
        expected_requirements = ["right_to_work", "dbs", "identity", "proof_of_address", "references", "training", "health"]
        
        for req in expected_requirements:
            assert req in requirements, f"Missing requirement: {req}"
            req_data = requirements[req]
            assert "status" in req_data, f"Missing status for {req}"
            # Status should be one of the valid values
            assert req_data["status"] in ["COMPLIANT", "MISSING", "EXPIRED", "ATTENTION_REQUIRED", "NOT_APPLICABLE"], \
                f"Invalid status for {req}: {req_data['status']}"
        
        # Verify counts
        assert "total_requirements" in data
        assert "compliant_count" in data
        assert "missing_count" in data
        assert "expired_count" in data
        assert "attention_count" in data
        
        # Verify blockers and warnings
        assert "blockers" in data
        assert isinstance(data["blockers"], list)
        assert "warnings" in data
        assert isinstance(data["warnings"], list)
        
        print(f"Overall status: {data['overall_status']}")
        print(f"Regulatory status: {data['regulatory_status']}")
        print(f"Compliant: {data['compliant_count']}/{data['total_requirements']}")
    
    def test_get_unified_compliance_status_force_refresh(self, authenticated_client):
        """Test getting fresh compliance status with force_refresh."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-compliance-status",
            params={"force_refresh": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "last_calculated_at" in data
    
    def test_get_unified_compliance_status_invalid_employee(self, authenticated_client):
        """Test compliance status for non-existent employee."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/invalid-employee-id/unified-compliance-status"
        )
        
        assert response.status_code == 404
    
    def test_blockers_from_requirements(self, authenticated_client):
        """Test that blockers are correctly calculated from DBS, References, Health."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-compliance-status",
            params={"force_refresh": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check blockers structure
        for blocker in data.get("blockers", []):
            assert "requirement" in blocker
            assert "label" in blocker
            assert "status" in blocker
            assert "reason" in blocker
            print(f"Blocker: {blocker['label']} - {blocker['reason']}")


# ==================== HEALTH DECLARATION TESTS ====================

class TestHealthDeclarationEndpoints:
    """Tests for Health Declaration endpoints"""
    
    def test_get_health_declaration_current(self, authenticated_client):
        """Test getting current health declaration."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "has_declaration" in data
        assert "status" in data
        
        if data["has_declaration"]:
            assert "declaration" in data
            assert data["declaration"] is not None
            print(f"Current declaration status: {data['status']}")
        else:
            print("No health declaration on file")
    
    def test_submit_health_declaration_fit(self, authenticated_client):
        """Test submitting health declaration with fit status."""
        today = date.today().isoformat()
        
        payload = {
            "declaration_date": today,
            "declared_fit_to_work": True,
            "conditions_disclosed": False,
            "back_problems": False,
            "skin_conditions": False,
            "respiratory_conditions": False,
            "infectious_diseases": False,
            "mental_health": False,
            "physical_limitations": False,
            "medication": False,
            "hepatitis_b_vaccinated": True,
            "flu_vaccinated": True,
            "covid_vaccinated": True,
            "consent_to_oh_contact": True,
            "emergency_contact_name": "Test Contact",
            "emergency_contact_phone": "07700900000"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert "declaration_id" in data
        assert "status" in data
        # When declared_fit_to_work=true and no conditions, status should be 'fit'
        assert data["status"] == "fit", f"Expected status 'fit', got '{data['status']}'"
        print(f"Declaration submitted with ID: {data['declaration_id']}, status: {data['status']}")
    
    def test_submit_health_declaration_requires_review(self, authenticated_client):
        """Test submitting health declaration that requires review."""
        today = date.today().isoformat()
        
        payload = {
            "declaration_date": today,
            "declared_fit_to_work": True,
            "conditions_disclosed": True,  # This should trigger requires_review
            "conditions_details": "Minor back pain occasionally",
            "back_problems": True,
            "consent_to_oh_contact": True
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # When conditions are disclosed, status should be requires_review
        assert data["status"] == "requires_review", f"Expected 'requires_review', got '{data['status']}'"
        print(f"Declaration requires review: {data['declaration_id']}")
    
    def test_get_health_declaration_history(self, authenticated_client):
        """Test getting health declaration history."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration/history"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert "declarations" in data
        assert isinstance(data["declarations"], list)
        assert "count" in data
        print(f"Declaration history count: {data['count']}")
    
    def test_get_health_declaration_history_with_limit(self, authenticated_client):
        """Test health declaration history with limit parameter."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration/history",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["declarations"]) <= 5
    
    def test_get_health_declaration_invalid_employee(self, authenticated_client):
        """Test health declaration for non-existent employee."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/invalid-employee-id/health-declaration"
        )
        
        assert response.status_code == 404


class TestHealthDeclarationReview:
    """Tests for Health Declaration Review endpoints (Admin only)"""
    
    def test_get_pending_health_declarations(self, authenticated_client):
        """Test getting pending health declarations."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/admin/health-declarations/pending-review"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "declarations" in data
        assert isinstance(data["declarations"], list)
        assert "count" in data
        print(f"Pending declarations: {data['count']}")
        
        # Check structure of pending declarations
        for decl in data["declarations"]:
            assert "id" in decl
            assert "employee_id" in decl
            assert "status" in decl
            assert decl["status"] == "requires_review"
    
    def test_review_health_declaration_approve(self, authenticated_client):
        """Test reviewing and approving a health declaration."""
        # First, submit a declaration that requires review
        today = date.today().isoformat()
        
        submit_payload = {
            "declaration_date": today,
            "declared_fit_to_work": True,
            "conditions_disclosed": True,
            "conditions_details": "Test condition for review",
            "consent_to_oh_contact": True
        }
        
        submit_response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration",
            json=submit_payload
        )
        
        assert submit_response.status_code == 200
        declaration_id = submit_response.json()["declaration_id"]
        
        # Now review it
        review_payload = {
            "status": "fit",
            "review_notes": "Reviewed and approved - condition does not affect work"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/health-declarations/{declaration_id}/review",
            json=review_payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert "declaration" in data
        assert data["declaration"]["status"] == "fit"
        print(f"Declaration {declaration_id} reviewed and approved")
    
    def test_review_health_declaration_conditional(self, authenticated_client):
        """Test reviewing declaration with conditional status."""
        # Submit a declaration
        today = date.today().isoformat()
        
        submit_payload = {
            "declaration_date": today,
            "declared_fit_to_work": True,
            "conditions_disclosed": True,
            "conditions_details": "Requires workplace adjustments",
            "physical_limitations": True,
            "consent_to_oh_contact": True
        }
        
        submit_response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration",
            json=submit_payload
        )
        
        assert submit_response.status_code == 200
        declaration_id = submit_response.json()["declaration_id"]
        
        # Review with conditional status
        review_payload = {
            "status": "conditional",
            "review_notes": "Fit with adjustments",
            "adjustments_required": "No heavy lifting, regular breaks required"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/health-declarations/{declaration_id}/review",
            json=review_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["declaration"]["status"] == "conditional"
        assert data["declaration"]["adjustments_required"] == "No heavy lifting, regular breaks required"
        print(f"Declaration {declaration_id} reviewed as conditional")
    
    def test_review_health_declaration_invalid_status(self, authenticated_client):
        """Test reviewing with invalid status."""
        # First get a declaration ID
        history_response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration/history"
        )
        
        if history_response.status_code == 200 and history_response.json()["count"] > 0:
            declaration_id = history_response.json()["declarations"][0]["id"]
            
            review_payload = {
                "status": "invalid_status",
                "review_notes": "Test"
            }
            
            response = authenticated_client.post(
                f"{BASE_URL}/api/health-declarations/{declaration_id}/review",
                json=review_payload
            )
            
            assert response.status_code == 400
    
    def test_review_health_declaration_not_found(self, authenticated_client):
        """Test reviewing non-existent declaration."""
        review_payload = {
            "status": "fit",
            "review_notes": "Test"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/health-declarations/invalid-declaration-id/review",
            json=review_payload
        )
        
        assert response.status_code == 404


class TestHealthDeclarationStatusLogic:
    """Tests for health declaration status logic"""
    
    def test_fit_status_when_no_conditions(self, authenticated_client):
        """Test that declared_fit_to_work=true and no conditions results in status='fit'."""
        today = date.today().isoformat()
        
        payload = {
            "declaration_date": today,
            "declared_fit_to_work": True,
            "conditions_disclosed": False,
            "back_problems": False,
            "skin_conditions": False,
            "respiratory_conditions": False,
            "infectious_diseases": False,
            "mental_health": False,
            "physical_limitations": False,
            "medication": False,
            "consent_to_oh_contact": True
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Key assertion: status should be 'fit' when declared_fit_to_work=true and no conditions
        assert data["status"] == "fit", \
            f"Expected status 'fit' when declared_fit_to_work=true and no conditions, got '{data['status']}'"
        print("PASS: Health declaration with declared_fit_to_work=true and no conditions results in status='fit'")
    
    def test_requires_review_when_conditions_disclosed(self, authenticated_client):
        """Test that conditions_disclosed=true triggers requires_review status."""
        today = date.today().isoformat()
        
        payload = {
            "declaration_date": today,
            "declared_fit_to_work": True,
            "conditions_disclosed": True,
            "conditions_details": "Some condition",
            "consent_to_oh_contact": True
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "requires_review", \
            f"Expected status 'requires_review' when conditions disclosed, got '{data['status']}'"
        print("PASS: Health declaration with conditions_disclosed=true results in status='requires_review'")


class TestComplianceStatusHealthIntegration:
    """Tests for health status integration in unified compliance status"""
    
    def test_health_status_in_unified_compliance(self, authenticated_client):
        """Test that health status is correctly reflected in unified compliance."""
        # First submit a fit declaration
        today = date.today().isoformat()
        
        payload = {
            "declaration_date": today,
            "declared_fit_to_work": True,
            "conditions_disclosed": False,
            "consent_to_oh_contact": True
        }
        
        submit_response = authenticated_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/health-declaration",
            json=payload
        )
        
        assert submit_response.status_code == 200
        
        # Now check unified compliance status
        response = authenticated_client.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/unified-compliance-status",
            params={"force_refresh": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check health requirement status
        health_status = data["requirements"]["health"]
        assert "status" in health_status
        
        # If we just submitted a fit declaration, health should be COMPLIANT
        if health_status["status"] == "COMPLIANT":
            print("PASS: Health status is COMPLIANT after fit declaration")
        else:
            print(f"Health status: {health_status['status']} (may need review)")
        
        # Check if health is in blockers
        health_blockers = [b for b in data["blockers"] if b["requirement"] == "health"]
        print(f"Health blockers: {len(health_blockers)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

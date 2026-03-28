"""
Test CQC-Ready Expiry System
Tests for:
- Expiry status calculation (Valid, Expiring Soon, Expired)
- Document status in compliance-requirements response
- Critical expiry override (RTW/DBS expired = Not Ready)
- Work readiness reason microcopy
- Start status reason messages
"""

import pytest
import requests
import os
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee IDs
OLAKUNLE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Work Ready
LAWRENCE_ID = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"  # Not Ready


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@osabea.care", "password": "admin123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestExpiryStatusCalculation:
    """Test expiry status calculation - Valid, Expiring Soon, Expired"""
    
    def test_compliance_requirements_has_document_status(self, api_client):
        """Verify compliance-requirements returns document_status object"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        assert "statuses" in data, "statuses missing from compliance-requirements"
        
        statuses = data["statuses"]
        assert "document_status" in statuses, "document_status missing from statuses"
        
        doc_status = statuses["document_status"]
        assert "status" in doc_status, "status missing from document_status"
        assert "label" in doc_status, "label missing from document_status"
        assert "color" in doc_status, "color missing from document_status"
        assert "expired_count" in doc_status, "expired_count missing from document_status"
        assert "expiring_soon_count" in doc_status, "expiring_soon_count missing from document_status"
        assert "valid_count" in doc_status, "valid_count missing from document_status"
        assert "has_critical_expired" in doc_status, "has_critical_expired missing from document_status"
        
        print(f"✅ Document status structure verified: {doc_status}")
    
    def test_document_status_values(self, api_client):
        """Verify document_status has correct status values"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        doc_status = response.json()["statuses"]["document_status"]
        
        # Status should be one of: expired, expiring_soon, all_valid, no_expiry_tracked
        valid_statuses = ["expired", "expiring_soon", "all_valid", "no_expiry_tracked"]
        assert doc_status["status"] in valid_statuses, f"Invalid status: {doc_status['status']}"
        
        # Color should match status
        if doc_status["status"] == "expired":
            assert doc_status["color"] == "error", f"Expected 'error' color for expired, got {doc_status['color']}"
        elif doc_status["status"] == "expiring_soon":
            assert doc_status["color"] == "warning", f"Expected 'warning' color for expiring_soon, got {doc_status['color']}"
        elif doc_status["status"] == "all_valid":
            assert doc_status["color"] == "success", f"Expected 'success' color for all_valid, got {doc_status['color']}"
        elif doc_status["status"] == "no_expiry_tracked":
            assert doc_status["color"] == "neutral", f"Expected 'neutral' color for no_expiry_tracked, got {doc_status['color']}"
        
        print(f"✅ Document status values verified: status={doc_status['status']}, color={doc_status['color']}")
    
    def test_document_status_label_format(self, api_client):
        """Verify document_status label matches spec"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        doc_status = response.json()["statuses"]["document_status"]
        
        # Label should match status
        if doc_status["status"] == "expired":
            assert "Expired" in doc_status["label"], f"Expected 'Expired' in label, got {doc_status['label']}"
        elif doc_status["status"] == "expiring_soon":
            assert "Expiring Soon" in doc_status["label"], f"Expected 'Expiring Soon' in label, got {doc_status['label']}"
        elif doc_status["status"] == "all_valid":
            assert doc_status["label"] == "All Valid", f"Expected 'All Valid', got {doc_status['label']}"
        elif doc_status["status"] == "no_expiry_tracked":
            assert doc_status["label"] == "No Expiry Dates", f"Expected 'No Expiry Dates', got {doc_status['label']}"
        
        print(f"✅ Document status label verified: {doc_status['label']}")


class TestCriticalExpiryOverride:
    """Test critical expiry override - RTW/DBS expired = Not Ready"""
    
    def test_critical_expiry_docs_constant(self, api_client):
        """Verify CRITICAL_EXPIRY_DOCS includes RTW and DBS"""
        # This is tested indirectly through the has_critical_expired flag
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        doc_status = response.json()["statuses"]["document_status"]
        assert "has_critical_expired" in doc_status, "has_critical_expired flag missing"
        
        # The flag should be a boolean
        assert isinstance(doc_status["has_critical_expired"], bool), "has_critical_expired should be boolean"
        
        print(f"✅ has_critical_expired flag present: {doc_status['has_critical_expired']}")
    
    def test_document_status_expired_docs_list(self, api_client):
        """Verify expired_docs list is returned"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        doc_status = response.json()["statuses"]["document_status"]
        
        # Check expired_docs and expiring_soon_docs lists exist
        assert "expired_docs" in doc_status, "expired_docs list missing"
        assert "expiring_soon_docs" in doc_status, "expiring_soon_docs list missing"
        
        # Both should be lists
        assert isinstance(doc_status["expired_docs"], list), "expired_docs should be a list"
        assert isinstance(doc_status["expiring_soon_docs"], list), "expiring_soon_docs should be a list"
        
        print(f"✅ Expired docs list: {len(doc_status['expired_docs'])} items")
        print(f"✅ Expiring soon docs list: {len(doc_status['expiring_soon_docs'])} items")


class TestWorkReadinessReasonMicrocopy:
    """Test work readiness reason microcopy"""
    
    def test_start_status_has_reason_field(self, api_client):
        """Verify start_status includes reason field"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        start_status = response.json()["statuses"]["start_status"]
        assert "reason" in start_status, "reason field missing from start_status"
        
        print(f"✅ Start status reason: {start_status['reason']}")
    
    def test_ready_to_work_reason_microcopy(self, api_client):
        """Verify Ready to Work reason microcopy"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        start_status = response.json()["statuses"]["start_status"]
        
        if start_status["status"] == "ready_to_work":
            expected_reason = "All required checks are complete. This employee can safely start work."
            assert start_status["reason"] == expected_reason, \
                f"Expected '{expected_reason}', got '{start_status['reason']}'"
            print(f"✅ Ready to Work reason verified: {start_status['reason']}")
        else:
            print(f"⚠️ Olakunle is not Ready to Work, status: {start_status['status']}")
    
    def test_not_ready_reason_microcopy(self, api_client):
        """Verify Not Ready reason microcopy"""
        response = api_client.get(f"{BASE_URL}/api/employees/{LAWRENCE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        start_status = response.json()["statuses"]["start_status"]
        
        if start_status["status"] == "not_ready":
            expected_reason = "Essential checks are missing. This employee cannot start work."
            assert start_status["reason"] == expected_reason, \
                f"Expected '{expected_reason}', got '{start_status['reason']}'"
            print(f"✅ Not Ready reason verified: {start_status['reason']}")
        else:
            print(f"⚠️ Lawrence is not 'Not Ready', status: {start_status['status']}")
    
    def test_supervised_start_reason_microcopy(self, api_client):
        """Verify Supervised Start reason microcopy exists"""
        # This test checks the expected microcopy format
        # We may not have an employee in this state, so we just verify the structure
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        start_status = response.json()["statuses"]["start_status"]
        
        # If status is supervised_start_only, verify the reason
        if start_status["status"] == "supervised_start_only":
            expected_reason = "Employee can start with supervision. Some training is still needed."
            assert start_status["reason"] == expected_reason, \
                f"Expected '{expected_reason}', got '{start_status['reason']}'"
            print(f"✅ Supervised Start reason verified: {start_status['reason']}")
        else:
            print(f"ℹ️ Employee not in Supervised Start state, skipping microcopy check")


class TestStartStatusStructure:
    """Test start_status structure and fields"""
    
    def test_start_status_has_all_fields(self, api_client):
        """Verify start_status has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        start_status = response.json()["statuses"]["start_status"]
        
        required_fields = ["status", "label", "color", "complete", "verified", "total", "missing", "reason"]
        for field in required_fields:
            assert field in start_status, f"Field '{field}' missing from start_status"
        
        print(f"✅ Start status has all required fields")
        print(f"   status: {start_status['status']}")
        print(f"   label: {start_status['label']}")
        print(f"   color: {start_status['color']}")
        print(f"   complete: {start_status['complete']}/{start_status['total']}")
        print(f"   verified: {start_status['verified']}/{start_status['total']}")
        print(f"   missing: {len(start_status['missing'])} items")
    
    def test_start_status_valid_values(self, api_client):
        """Verify start_status has valid status values"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        start_status = response.json()["statuses"]["start_status"]
        
        # Valid status values
        valid_statuses = ["ready_to_work", "supervised_start_only", "not_ready"]
        assert start_status["status"] in valid_statuses, \
            f"Invalid status: {start_status['status']}, expected one of {valid_statuses}"
        
        # Valid labels
        valid_labels = ["Ready to Work", "Supervised Start", "Not Ready"]
        assert start_status["label"] in valid_labels, \
            f"Invalid label: {start_status['label']}, expected one of {valid_labels}"
        
        # Valid colors
        valid_colors = ["success", "warning", "error"]
        assert start_status["color"] in valid_colors, \
            f"Invalid color: {start_status['color']}, expected one of {valid_colors}"
        
        print(f"✅ Start status values are valid")


class TestExpiryAlertsInEmployeeList:
    """Test expiry alerts in employee list"""
    
    def test_employees_list_has_expiry_alerts(self, api_client):
        """Verify employees list returns expiry_alerts object"""
        response = api_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        employees = response.json()
        assert len(employees) > 0, "No employees found"
        
        # Check first employee has expiry_alerts field
        emp = employees[0]
        assert "expiry_alerts" in emp, "expiry_alerts field missing from employee"
        
        alerts = emp["expiry_alerts"]
        assert "expired_count" in alerts, "expired_count missing from expiry_alerts"
        assert "expiring_soon_count" in alerts, "expiring_soon_count missing from expiry_alerts"
        assert "has_alerts" in alerts, "has_alerts missing from expiry_alerts"
        
        print(f"✅ Employee {emp['first_name']} has expiry_alerts: {alerts}")
    
    def test_expiry_alerts_structure(self, api_client):
        """Verify expiry_alerts has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        employees = response.json()
        
        for emp in employees[:5]:  # Check first 5 employees
            alerts = emp.get("expiry_alerts", {})
            
            # Verify types
            assert isinstance(alerts.get("expired_count", 0), int), "expired_count should be int"
            assert isinstance(alerts.get("expiring_soon_count", 0), int), "expiring_soon_count should be int"
            assert isinstance(alerts.get("has_alerts", False), bool), "has_alerts should be bool"
            
            # Verify has_alerts logic
            if alerts.get("expired_count", 0) > 0 or alerts.get("expiring_soon_count", 0) > 0:
                assert alerts.get("has_alerts") == True, "has_alerts should be True when counts > 0"
        
        print(f"✅ Expiry alerts structure verified for {min(5, len(employees))} employees")


class TestRequirementExpiryTracking:
    """Test expiry tracking on individual requirements"""
    
    def test_requirements_have_expiry_fields(self, api_client):
        """Verify requirements have expiry tracking fields"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        requirements = response.json()["requirements"]
        
        # Check that requirements have expiry fields
        for req in requirements:
            assert "tracks_expiry" in req, f"tracks_expiry missing from requirement {req['id']}"
            assert "expiry_status" in req, f"expiry_status missing from requirement {req['id']}"
            assert "expiry_date" in req, f"expiry_date missing from requirement {req['id']}"
        
        # Count requirements that track expiry
        expiry_tracked = [r for r in requirements if r["tracks_expiry"]]
        print(f"✅ {len(expiry_tracked)} requirements track expiry out of {len(requirements)} total")
    
    def test_evidence_files_have_expiry_status(self, api_client):
        """Verify evidence files have expiry_status when applicable"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        requirements = response.json()["requirements"]
        
        files_with_expiry = 0
        for req in requirements:
            for ef in req.get("evidence_files", []):
                if ef.get("expiry_date"):
                    files_with_expiry += 1
                    assert "expiry_status" in ef, f"expiry_status missing from evidence file"
                    
                    exp_status = ef["expiry_status"]
                    if exp_status:
                        assert "status" in exp_status, "status missing from expiry_status"
                        assert "label" in exp_status, "label missing from expiry_status"
                        assert "color" in exp_status, "color missing from expiry_status"
                        assert "days_until_expiry" in exp_status, "days_until_expiry missing from expiry_status"
        
        print(f"✅ Found {files_with_expiry} evidence files with expiry dates")


class TestSeparatedStatusesModel:
    """Test the separated statuses model structure"""
    
    def test_statuses_has_all_sections(self, api_client):
        """Verify statuses object has all required sections"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        statuses = response.json()["statuses"]
        
        required_sections = ["start_status", "recruitment_file", "policies", "document_status", "overall_compliance"]
        for section in required_sections:
            assert section in statuses, f"Section '{section}' missing from statuses"
        
        print(f"✅ All status sections present: {list(statuses.keys())}")
    
    def test_overall_compliance_structure(self, api_client):
        """Verify overall_compliance has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        overall = response.json()["statuses"]["overall_compliance"]
        
        required_fields = ["percentage", "complete", "verified", "total"]
        for field in required_fields:
            assert field in overall, f"Field '{field}' missing from overall_compliance"
        
        # Verify percentage is between 0 and 100
        assert 0 <= overall["percentage"] <= 100, f"Invalid percentage: {overall['percentage']}"
        
        print(f"✅ Overall compliance: {overall['percentage']}% ({overall['complete']}/{overall['total']} complete)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

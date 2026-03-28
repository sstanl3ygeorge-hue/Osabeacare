"""
Test Work Readiness System - CQC Standards Implementation
Tests for:
- Work readiness calculation (mandatory vs secondary requirements)
- Weighted compliance scoring (80% mandatory, 15% required_soon, 5% secondary)
- Work Ready status badges
- Priority visuals in What's Needed tab
- Work Readiness Alert Panel
"""

import pytest
import requests
import os

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


class TestEmployeesListWorkReadiness:
    """Test Work Ready column in employees list"""
    
    def test_employees_list_has_work_readiness_field(self, api_client):
        """Verify employees list returns work_readiness object"""
        response = api_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        employees = response.json()
        assert len(employees) > 0, "No employees found"
        
        # Check first employee has work_readiness field
        emp = employees[0]
        assert "work_readiness" in emp, "work_readiness field missing from employee"
        
        wr = emp["work_readiness"]
        assert "status" in wr, "status missing from work_readiness"
        assert "label" in wr, "label missing from work_readiness"
        assert "color" in wr, "color missing from work_readiness"
        print(f"✅ Employee {emp['first_name']} has work_readiness: {wr}")
    
    def test_olakunle_shows_work_ready(self, api_client):
        """Verify Olakunle Alonge shows 'Work Ready' badge"""
        response = api_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        employees = response.json()
        olakunle = next((e for e in employees if e["id"] == OLAKUNLE_ID), None)
        assert olakunle is not None, "Olakunle not found in employees list"
        
        wr = olakunle["work_readiness"]
        assert wr["status"] == "work_ready", f"Expected 'work_ready', got '{wr['status']}'"
        assert wr["label"] == "Work Ready", f"Expected 'Work Ready', got '{wr['label']}'"
        assert wr["color"] == "success", f"Expected 'success', got '{wr['color']}'"
        print(f"✅ Olakunle shows Work Ready badge: {wr}")
    
    def test_lawrence_shows_not_ready(self, api_client):
        """Verify Lawrence Egbeni shows 'Not Ready' badge"""
        response = api_client.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        employees = response.json()
        lawrence = next((e for e in employees if e["id"] == LAWRENCE_ID), None)
        assert lawrence is not None, "Lawrence not found in employees list"
        
        wr = lawrence["work_readiness"]
        assert wr["status"] in ["not_started", "in_progress"], f"Expected not ready status, got '{wr['status']}'"
        assert wr["label"] == "Not Ready", f"Expected 'Not Ready', got '{wr['label']}'"
        assert wr["color"] == "error", f"Expected 'error', got '{wr['color']}'"
        print(f"✅ Lawrence shows Not Ready badge: {wr}")


class TestComplianceRequirementsWorkReadiness:
    """Test Work Readiness in compliance-requirements endpoint"""
    
    def test_olakunle_compliance_has_work_readiness(self, api_client):
        """Verify Olakunle's compliance-requirements returns work_readiness object"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        data = response.json()
        assert "work_readiness" in data, "work_readiness missing from compliance-requirements"
        
        wr = data["work_readiness"]
        assert "status" in wr
        assert "status_label" in wr
        assert "status_color" in wr
        assert "weighted_score" in wr
        assert "mandatory" in wr
        print(f"✅ Olakunle compliance has work_readiness: {wr['status_label']}")
    
    def test_olakunle_work_ready_status(self, api_client):
        """Verify Olakunle is Work Ready with all mandatory items verified"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        wr = response.json()["work_readiness"]
        
        # Check status
        assert wr["status"] == "work_ready", f"Expected 'work_ready', got '{wr['status']}'"
        assert wr["status_label"] == "Work Ready"
        assert wr["status_color"] == "success"
        
        # Check mandatory breakdown
        mandatory = wr["mandatory"]
        assert mandatory["complete"] == mandatory["total"], \
            f"Not all mandatory items complete: {mandatory['complete']}/{mandatory['total']}"
        assert mandatory["verified"] == mandatory["total"], \
            f"Not all mandatory items verified: {mandatory['verified']}/{mandatory['total']}"
        assert len(mandatory["missing"]) == 0, f"Missing items: {mandatory['missing']}"
        
        print(f"✅ Olakunle Work Ready: {mandatory['verified']}/{mandatory['total']} mandatory verified")
    
    def test_olakunle_weighted_score(self, api_client):
        """Verify Olakunle's weighted compliance score is ~86%"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        wr = response.json()["work_readiness"]
        weighted_score = wr["weighted_score"]
        
        # Score should be around 86% (80% mandatory + some required_soon + some secondary)
        assert 80 <= weighted_score <= 100, f"Weighted score {weighted_score}% outside expected range"
        print(f"✅ Olakunle weighted score: {weighted_score}%")
    
    def test_lawrence_not_ready_status(self, api_client):
        """Verify Lawrence is Not Ready with missing mandatory items"""
        response = api_client.get(f"{BASE_URL}/api/employees/{LAWRENCE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        wr = response.json()["work_readiness"]
        
        # Check status
        assert wr["status"] in ["not_started", "in_progress"], f"Expected not ready, got '{wr['status']}'"
        assert wr["status_label"] == "Not Ready"
        assert wr["status_color"] == "error"
        
        # Check mandatory breakdown
        mandatory = wr["mandatory"]
        assert mandatory["complete"] < mandatory["total"], \
            f"All mandatory items complete but status is Not Ready"
        assert len(mandatory["missing"]) > 0, "Missing items list should not be empty"
        
        print(f"✅ Lawrence Not Ready: {mandatory['complete']}/{mandatory['total']} mandatory complete")
        print(f"   Missing: {[m['name'] for m in mandatory['missing']]}")
    
    def test_lawrence_missing_mandatory_items(self, api_client):
        """Verify Lawrence's missing mandatory items are listed"""
        response = api_client.get(f"{BASE_URL}/api/employees/{LAWRENCE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        missing = response.json()["work_readiness"]["mandatory"]["missing"]
        missing_names = [m["name"] for m in missing]
        
        # Expected missing items based on test data
        expected_missing = [
            "Right to Work Documents",
            "Right to Work Verification",
            "Identity Documents",
            "DBS Certificate",
            "DBS Update Service Check",
            "Safeguarding Training"
        ]
        
        for item in expected_missing:
            assert item in missing_names, f"Expected '{item}' in missing items"
        
        print(f"✅ Lawrence missing items verified: {missing_names}")


class TestRequirementPriorities:
    """Test priority fields on requirements"""
    
    def test_requirements_have_priority_field(self, api_client):
        """Verify requirements have priority field"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        requirements = response.json()["requirements"]
        assert len(requirements) > 0, "No requirements found"
        
        # Check that requirements have priority field
        for req in requirements:
            assert "priority" in req, f"priority missing from requirement {req['id']}"
            assert req["priority"] in ["mandatory", "required_soon", "secondary"], \
                f"Invalid priority '{req['priority']}' for {req['id']}"
        
        # Count by priority
        mandatory_count = len([r for r in requirements if r["priority"] == "mandatory"])
        required_soon_count = len([r for r in requirements if r["priority"] == "required_soon"])
        secondary_count = len([r for r in requirements if r["priority"] == "secondary"])
        
        print(f"✅ Requirements by priority: mandatory={mandatory_count}, required_soon={required_soon_count}, secondary={secondary_count}")
    
    def test_mandatory_items_have_work_ready_hint(self, api_client):
        """Verify mandatory items have work_ready_hint field"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        requirements = response.json()["requirements"]
        mandatory_items = [r for r in requirements if r["priority"] == "mandatory"]
        
        for req in mandatory_items:
            assert "work_ready_hint" in req, f"work_ready_hint missing from mandatory item {req['id']}"
            assert "Required before employee can start work" in req["work_ready_hint"], \
                f"Unexpected hint for {req['id']}: {req['work_ready_hint']}"
        
        print(f"✅ All {len(mandatory_items)} mandatory items have work_ready_hint")
    
    def test_is_mandatory_for_work_flag(self, api_client):
        """Verify is_mandatory_for_work flag on requirements"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        requirements = response.json()["requirements"]
        
        # Check mandatory items have is_mandatory_for_work = True
        mandatory_items = [r for r in requirements if r["priority"] == "mandatory"]
        for req in mandatory_items:
            assert req.get("is_mandatory_for_work") == True, \
                f"is_mandatory_for_work should be True for {req['id']}"
        
        # Check non-mandatory items have is_mandatory_for_work = False
        non_mandatory = [r for r in requirements if r["priority"] != "mandatory"]
        for req in non_mandatory:
            assert req.get("is_mandatory_for_work") == False, \
                f"is_mandatory_for_work should be False for {req['id']}"
        
        print(f"✅ is_mandatory_for_work flag verified for all requirements")


class TestWeightedScoring:
    """Test weighted compliance scoring (80% mandatory, 15% required_soon, 5% secondary)"""
    
    def test_weighted_score_calculation(self, api_client):
        """Verify weighted score follows 80/15/5 weighting"""
        response = api_client.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert response.status_code == 200
        
        wr = response.json()["work_readiness"]
        
        # Get breakdown
        mandatory = wr["mandatory"]
        required_soon = wr.get("required_soon", {})
        secondary = wr.get("secondary", {})
        
        # Calculate expected score
        mandatory_score = (mandatory["complete"] / mandatory["total"] * 80) if mandatory["total"] > 0 else 0
        required_soon_score = (required_soon.get("complete", 0) / required_soon.get("total", 1) * 15) if required_soon.get("total", 0) > 0 else 0
        secondary_score = (secondary.get("complete", 0) / secondary.get("total", 1) * 5) if secondary.get("total", 0) > 0 else 0
        
        expected_score = int(mandatory_score + required_soon_score + secondary_score)
        actual_score = wr["weighted_score"]
        
        # Allow small variance due to rounding
        assert abs(actual_score - expected_score) <= 2, \
            f"Weighted score mismatch: expected ~{expected_score}, got {actual_score}"
        
        print(f"✅ Weighted score verified: {actual_score}% (mandatory={mandatory_score:.0f}%, required_soon={required_soon_score:.0f}%, secondary={secondary_score:.0f}%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

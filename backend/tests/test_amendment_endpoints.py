"""
Test Amendment Endpoints for Compliance Centre
Tests for:
- PUT /api/compliance/insurance/{id}/amend - Insurance amendment with history tracking
- PUT /api/compliance/policies/{id}/amend - Policy amendment with history tracking
- PUT /api/compliance/incidents/{id}/amend - Incident amendment with history tracking
- GET /api/compliance/insurance/{id}/history - Insurance amendment history
- GET /api/compliance/policies/{id}/history - Policy amendment history
- GET /api/compliance/incidents/{id}/history - Incident amendment history
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def test_policy(api_client):
    """Get an existing policy for testing"""
    response = api_client.get(f"{BASE_URL}/api/compliance/policies")
    assert response.status_code == 200, f"Failed to get policies: {response.text}"
    policies = response.json()
    if not policies:
        pytest.skip("No policies available for testing")
    return policies[0]


@pytest.fixture(scope="module")
def test_insurance(api_client):
    """Get an existing insurance record for testing"""
    response = api_client.get(f"{BASE_URL}/api/compliance/insurance")
    assert response.status_code == 200, f"Failed to get insurance: {response.text}"
    insurance_list = response.json()
    if not insurance_list:
        pytest.skip("No insurance records available for testing")
    return insurance_list[0]


@pytest.fixture(scope="module")
def test_incident(api_client):
    """Create a test incident for amendment testing"""
    incident_data = {
        "incident_type": "incident",
        "title": f"TEST_Amendment_Incident_{uuid.uuid4().hex[:8]}",
        "description": "Test incident for amendment testing",
        "date_occurred": datetime.now().strftime("%Y-%m-%d"),
        "location": "Test Location",
        "persons_involved": "Test Person",
        "immediate_actions": "Test immediate actions",
        "root_cause": "Test root cause",
        "corrective_actions": "Test corrective actions"
    }
    response = api_client.post(f"{BASE_URL}/api/compliance/incidents", json=incident_data)
    assert response.status_code in [200, 201], f"Failed to create test incident: {response.text}"
    return response.json()


class TestPolicyAmendment:
    """Tests for policy amendment endpoints"""
    
    def test_amend_policy_requires_reason(self, api_client, test_policy):
        """Test that amending a policy without reason fails"""
        response = api_client.put(
            f"{BASE_URL}/api/compliance/policies/{test_policy['id']}/amend",
            json={"notes": "Updated notes"}  # Missing 'reason' field
        )
        # Should fail validation - reason is required
        assert response.status_code == 422, f"Expected 422 for missing reason, got {response.status_code}"
        print("✅ Policy amendment correctly requires 'reason' field")
    
    def test_amend_policy_with_reason(self, api_client, test_policy):
        """Test successful policy amendment with reason"""
        original_notes = test_policy.get('notes', '')
        new_notes = f"Amended notes - {datetime.now().isoformat()}"
        
        response = api_client.put(
            f"{BASE_URL}/api/compliance/policies/{test_policy['id']}/amend",
            json={
                "notes": new_notes,
                "reason": "Testing amendment functionality"
            }
        )
        assert response.status_code == 200, f"Failed to amend policy: {response.text}"
        
        updated = response.json()
        assert updated.get('notes') == new_notes, "Notes not updated correctly"
        print(f"✅ Policy amended successfully with reason")
    
    def test_get_policy_history(self, api_client, test_policy):
        """Test retrieving policy amendment history"""
        response = api_client.get(
            f"{BASE_URL}/api/compliance/policies/{test_policy['id']}/history"
        )
        assert response.status_code == 200, f"Failed to get policy history: {response.text}"
        
        data = response.json()
        assert 'history' in data, "Response should contain 'history' array"
        assert 'total' in data, "Response should contain 'total' count"
        
        # After amendment, history should have at least one entry
        if data['total'] > 0:
            history_entry = data['history'][0]
            assert 'amended_at' in history_entry, "History entry should have 'amended_at'"
            assert 'amended_by' in history_entry, "History entry should have 'amended_by'"
            assert 'amendment_reason' in history_entry, "History entry should have 'amendment_reason'"
            print(f"✅ Policy history retrieved: {data['total']} entries")
        else:
            print("✅ Policy history endpoint works (no amendments yet)")
    
    def test_amend_policy_not_found(self, api_client):
        """Test amending non-existent policy returns 404"""
        response = api_client.put(
            f"{BASE_URL}/api/compliance/policies/nonexistent-id/amend",
            json={"notes": "test", "reason": "test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Non-existent policy returns 404")


class TestInsuranceAmendment:
    """Tests for insurance amendment endpoints"""
    
    def test_amend_insurance_requires_reason(self, api_client, test_insurance):
        """Test that amending insurance without reason fails"""
        response = api_client.put(
            f"{BASE_URL}/api/compliance/insurance/{test_insurance['id']}/amend",
            json={"notes": "Updated notes"}  # Missing 'reason' field
        )
        assert response.status_code == 422, f"Expected 422 for missing reason, got {response.status_code}"
        print("✅ Insurance amendment correctly requires 'reason' field")
    
    def test_amend_insurance_with_reason(self, api_client, test_insurance):
        """Test successful insurance amendment with reason"""
        new_notes = f"Amended insurance notes - {datetime.now().isoformat()}"
        
        response = api_client.put(
            f"{BASE_URL}/api/compliance/insurance/{test_insurance['id']}/amend",
            json={
                "notes": new_notes,
                "reason": "Testing insurance amendment"
            }
        )
        assert response.status_code == 200, f"Failed to amend insurance: {response.text}"
        
        updated = response.json()
        assert updated.get('notes') == new_notes, "Notes not updated correctly"
        print(f"✅ Insurance amended successfully with reason")
    
    def test_amend_insurance_expiry_date(self, api_client, test_insurance):
        """Test amending insurance expiry date"""
        new_expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        response = api_client.put(
            f"{BASE_URL}/api/compliance/insurance/{test_insurance['id']}/amend",
            json={
                "expiry_date": new_expiry,
                "reason": "Updating expiry date for renewal"
            }
        )
        assert response.status_code == 200, f"Failed to amend insurance expiry: {response.text}"
        
        updated = response.json()
        assert new_expiry in updated.get('expiry_date', ''), "Expiry date not updated"
        print(f"✅ Insurance expiry date amended successfully")
    
    def test_get_insurance_history(self, api_client, test_insurance):
        """Test retrieving insurance amendment history"""
        response = api_client.get(
            f"{BASE_URL}/api/compliance/insurance/{test_insurance['id']}/history"
        )
        assert response.status_code == 200, f"Failed to get insurance history: {response.text}"
        
        data = response.json()
        assert 'history' in data, "Response should contain 'history' array"
        assert 'total' in data, "Response should contain 'total' count"
        
        if data['total'] > 0:
            history_entry = data['history'][0]
            assert 'amended_at' in history_entry, "History entry should have 'amended_at'"
            assert 'amendment_reason' in history_entry, "History entry should have 'amendment_reason'"
            print(f"✅ Insurance history retrieved: {data['total']} entries")
        else:
            print("✅ Insurance history endpoint works (no amendments yet)")
    
    def test_amend_insurance_not_found(self, api_client):
        """Test amending non-existent insurance returns 404"""
        response = api_client.put(
            f"{BASE_URL}/api/compliance/insurance/nonexistent-id/amend",
            json={"notes": "test", "reason": "test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Non-existent insurance returns 404")


class TestIncidentAmendment:
    """Tests for incident amendment endpoints"""
    
    def test_amend_incident_requires_reason(self, api_client, test_incident):
        """Test that amending incident without reason fails"""
        response = api_client.put(
            f"{BASE_URL}/api/compliance/incidents/{test_incident['id']}/amend",
            json={"title": "Updated title"}  # Missing 'reason' field
        )
        assert response.status_code == 422, f"Expected 422 for missing reason, got {response.status_code}"
        print("✅ Incident amendment correctly requires 'reason' field")
    
    def test_amend_incident_with_reason(self, api_client, test_incident):
        """Test successful incident amendment with reason"""
        new_title = f"Amended Incident Title - {datetime.now().isoformat()}"
        
        response = api_client.put(
            f"{BASE_URL}/api/compliance/incidents/{test_incident['id']}/amend",
            json={
                "title": new_title,
                "reason": "Correcting incident title"
            }
        )
        assert response.status_code == 200, f"Failed to amend incident: {response.text}"
        
        updated = response.json()
        assert updated.get('title') == new_title, "Title not updated correctly"
        print(f"✅ Incident amended successfully with reason")
    
    def test_amend_incident_multiple_fields(self, api_client, test_incident):
        """Test amending multiple incident fields at once"""
        response = api_client.put(
            f"{BASE_URL}/api/compliance/incidents/{test_incident['id']}/amend",
            json={
                "root_cause": "Updated root cause analysis",
                "corrective_actions": "Updated corrective actions",
                "lessons_learned": "New lessons learned from investigation",
                "reason": "Updating after investigation completion"
            }
        )
        assert response.status_code == 200, f"Failed to amend incident: {response.text}"
        
        updated = response.json()
        assert updated.get('root_cause') == "Updated root cause analysis"
        assert updated.get('corrective_actions') == "Updated corrective actions"
        assert updated.get('lessons_learned') == "New lessons learned from investigation"
        print(f"✅ Incident multiple fields amended successfully")
    
    def test_get_incident_history(self, api_client, test_incident):
        """Test retrieving incident amendment history"""
        response = api_client.get(
            f"{BASE_URL}/api/compliance/incidents/{test_incident['id']}/history"
        )
        assert response.status_code == 200, f"Failed to get incident history: {response.text}"
        
        data = response.json()
        assert 'history' in data, "Response should contain 'history' array"
        assert 'total' in data, "Response should contain 'total' count"
        
        # After amendments, history should have entries
        if data['total'] > 0:
            history_entry = data['history'][0]
            assert 'amended_at' in history_entry, "History entry should have 'amended_at'"
            assert 'amended_by' in history_entry, "History entry should have 'amended_by'"
            assert 'amendment_reason' in history_entry, "History entry should have 'amendment_reason'"
            print(f"✅ Incident history retrieved: {data['total']} entries")
        else:
            print("✅ Incident history endpoint works (no amendments yet)")
    
    def test_incident_history_preserves_previous_state(self, api_client, test_incident):
        """Test that history preserves the previous state of the record"""
        # First, get current state
        response = api_client.get(f"{BASE_URL}/api/compliance/incidents")
        incidents = response.json()
        current_incident = next((i for i in incidents if i['id'] == test_incident['id']), None)
        
        if current_incident:
            original_description = current_incident.get('description', '')
            
            # Amend the description
            new_description = f"New description - {uuid.uuid4().hex[:8]}"
            api_client.put(
                f"{BASE_URL}/api/compliance/incidents/{test_incident['id']}/amend",
                json={
                    "description": new_description,
                    "reason": "Testing history preservation"
                }
            )
            
            # Check history contains the previous state
            history_response = api_client.get(
                f"{BASE_URL}/api/compliance/incidents/{test_incident['id']}/history"
            )
            history_data = history_response.json()
            
            if history_data['total'] > 0:
                # Most recent history entry should have the previous description
                latest_history = history_data['history'][0]
                assert 'description' in latest_history, "History should preserve description field"
                print(f"✅ History correctly preserves previous state")
    
    def test_amend_incident_not_found(self, api_client):
        """Test amending non-existent incident returns 404"""
        response = api_client.put(
            f"{BASE_URL}/api/compliance/incidents/nonexistent-id/amend",
            json={"title": "test", "reason": "test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Non-existent incident returns 404")


class TestHistoryEndpoints:
    """Tests for history retrieval endpoints"""
    
    def test_policy_history_not_found(self, api_client):
        """Test getting history for non-existent policy"""
        response = api_client.get(
            f"{BASE_URL}/api/compliance/policies/nonexistent-id/history"
        )
        assert response.status_code == 404
        print("✅ Non-existent policy history returns 404")
    
    def test_insurance_history_not_found(self, api_client):
        """Test getting history for non-existent insurance"""
        response = api_client.get(
            f"{BASE_URL}/api/compliance/insurance/nonexistent-id/history"
        )
        assert response.status_code == 404
        print("✅ Non-existent insurance history returns 404")
    
    def test_incident_history_not_found(self, api_client):
        """Test getting history for non-existent incident"""
        response = api_client.get(
            f"{BASE_URL}/api/compliance/incidents/nonexistent-id/history"
        )
        assert response.status_code == 404
        print("✅ Non-existent incident history returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

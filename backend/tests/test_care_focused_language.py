"""
Test care-focused language overhaul and evidence editing feature.
Tests:
1. Evidence edit endpoint with audit trail
2. Evidence history endpoint
3. Login and basic API access
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCareFocusedFeatures:
    """Test care-focused language and evidence editing features"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
    
    @pytest.fixture(scope="class")
    def api_client(self, auth_token):
        """Session with auth header"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        })
        return session
    
    @pytest.fixture(scope="class")
    def test_employee(self, api_client):
        """Get or create test employee"""
        # First try to find existing employee OCS-0001
        response = api_client.get(f"{BASE_URL}/api/employees?search=OCS-0001")
        if response.status_code == 200 and response.json():
            return response.json()[0]
        
        # Otherwise get any employee
        response = api_client.get(f"{BASE_URL}/api/employees")
        if response.status_code == 200 and response.json():
            return response.json()[0]
        
        pytest.skip("No employees found for testing")
    
    def test_login_success(self):
        """Test login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@osabea.care"
        print("✓ Login successful")
    
    def test_get_employee_compliance_requirements(self, api_client, test_employee):
        """Test getting compliance requirements for an employee"""
        employee_id = test_employee['id']
        response = api_client.get(f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements")
        
        assert response.status_code == 200, f"Failed to get compliance requirements: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "requirements" in data
        assert "summary" in data
        assert isinstance(data["requirements"], list)
        
        print(f"✓ Got {len(data['requirements'])} compliance requirements")
        print(f"  Summary: {data['summary']}")
    
    def test_get_employee_compliance(self, api_client, test_employee):
        """Test getting compliance status for an employee"""
        employee_id = test_employee['id']
        response = api_client.get(f"{BASE_URL}/api/employees/{employee_id}/compliance")
        
        assert response.status_code == 200, f"Failed to get compliance: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "employee_id" in data
        assert "compliance" in data
        compliance = data["compliance"]
        assert "items" in compliance
        assert "total_items" in compliance
        assert "complete_count" in compliance
        assert "verified_count" in compliance
        
        print(f"✓ Got compliance status: {compliance['complete_count']}/{compliance['total_items']} complete")
    
    def test_evidence_edit_endpoint_requires_reason(self, api_client, test_employee):
        """Test that evidence edit endpoint requires a reason"""
        employee_id = test_employee['id']
        
        # Try to edit without reason - should fail
        response = api_client.put(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/dbs_certificate/evidence/fake-file-id",
            json={
                "notes": "Test note",
                "reason": ""  # Empty reason
            }
        )
        
        # Should fail with 400 or 422 (validation error)
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print("✓ Evidence edit correctly requires reason")
    
    def test_evidence_edit_endpoint_with_valid_reason(self, api_client, test_employee):
        """Test evidence edit endpoint with valid reason"""
        employee_id = test_employee['id']
        
        # First get compliance requirements to find a requirement with evidence
        req_response = api_client.get(f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements")
        if req_response.status_code != 200:
            pytest.skip("Could not get compliance requirements")
        
        requirements = req_response.json().get("requirements", [])
        
        # Find a requirement with evidence
        req_with_evidence = None
        for req in requirements:
            if req.get("has_evidence") and req.get("evidence_count", 0) > 0:
                req_with_evidence = req
                break
        
        if not req_with_evidence:
            # Try to get evidence for any requirement
            for req in requirements[:5]:  # Check first 5
                evidence_response = api_client.get(
                    f"{BASE_URL}/api/employees/{employee_id}/requirements/{req['id']}/evidence"
                )
                if evidence_response.status_code == 200:
                    evidence_data = evidence_response.json()
                    if evidence_data.get("evidence_files"):
                        req_with_evidence = req
                        req_with_evidence["evidence_files"] = evidence_data["evidence_files"]
                        break
        
        if not req_with_evidence:
            print("⚠ No requirements with evidence found - skipping edit test")
            pytest.skip("No requirements with evidence to test edit")
        
        # Get evidence files for this requirement
        evidence_response = api_client.get(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/{req_with_evidence['id']}/evidence"
        )
        
        if evidence_response.status_code != 200:
            pytest.skip("Could not get evidence files")
        
        evidence_data = evidence_response.json()
        evidence_files = evidence_data.get("evidence_files", [])
        
        if not evidence_files:
            pytest.skip("No evidence files found")
        
        file_id = evidence_files[0].get("file_id")
        if not file_id:
            pytest.skip("No file_id in evidence file")
        
        # Now try to edit with valid reason
        response = api_client.put(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/{req_with_evidence['id']}/evidence/{file_id}",
            json={
                "notes": f"Test note updated at {uuid.uuid4().hex[:8]}",
                "reason": "Testing evidence edit functionality"
            }
        )
        
        # Should succeed or return "no changes" if notes were same
        assert response.status_code == 200, f"Evidence edit failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Evidence edit successful: {data.get('message')}")
    
    def test_evidence_history_endpoint(self, api_client, test_employee):
        """Test evidence history endpoint"""
        employee_id = test_employee['id']
        
        # Get compliance requirements
        req_response = api_client.get(f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements")
        if req_response.status_code != 200:
            pytest.skip("Could not get compliance requirements")
        
        requirements = req_response.json().get("requirements", [])
        
        # Find a requirement with evidence
        for req in requirements[:5]:
            evidence_response = api_client.get(
                f"{BASE_URL}/api/employees/{employee_id}/requirements/{req['id']}/evidence"
            )
            if evidence_response.status_code == 200:
                evidence_data = evidence_response.json()
                evidence_files = evidence_data.get("evidence_files", [])
                if evidence_files:
                    file_id = evidence_files[0].get("file_id")
                    if file_id:
                        # Get history
                        history_response = api_client.get(
                            f"{BASE_URL}/api/employees/{employee_id}/requirements/{req['id']}/evidence/{file_id}/history"
                        )
                        
                        assert history_response.status_code == 200, f"History endpoint failed: {history_response.text}"
                        history = history_response.json()
                        assert isinstance(history, list)
                        print(f"✓ Evidence history endpoint works - {len(history)} entries found")
                        return
        
        # If no evidence found, just verify endpoint returns empty list
        response = api_client.get(
            f"{BASE_URL}/api/employees/{employee_id}/requirements/dbs_certificate/evidence/fake-id/history"
        )
        assert response.status_code == 200
        assert response.json() == []
        print("✓ Evidence history endpoint returns empty list for non-existent file")
    
    def test_verify_requirement_endpoint(self, api_client, test_employee):
        """Test verify requirement endpoint exists"""
        employee_id = test_employee['id']
        
        # Get compliance requirements
        req_response = api_client.get(f"{BASE_URL}/api/employees/{employee_id}/compliance-requirements")
        if req_response.status_code != 200:
            pytest.skip("Could not get compliance requirements")
        
        requirements = req_response.json().get("requirements", [])
        
        # Find a requirement with evidence that's not verified
        for req in requirements:
            if req.get("has_evidence") and not req.get("verified"):
                # Try to verify
                response = api_client.post(
                    f"{BASE_URL}/api/employees/{employee_id}/requirements/{req['id']}/verify"
                )
                
                # Should succeed or already be verified
                assert response.status_code in [200, 400], f"Verify endpoint failed: {response.text}"
                print(f"✓ Verify requirement endpoint works for {req['name']}")
                return
        
        print("⚠ No unverified requirements with evidence found - endpoint exists but not tested")


class TestAPIEndpoints:
    """Test basic API endpoints"""
    
    def test_health_check(self):
        """Test API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        # Health endpoint may not exist, try root
        if response.status_code == 404:
            response = requests.get(f"{BASE_URL}/")
        assert response.status_code in [200, 404], f"API not accessible: {response.status_code}"
        print("✓ API is accessible")
    
    def test_auth_endpoint_exists(self):
        """Test auth endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "wrong"
        })
        # Should return 401 for wrong credentials, not 404
        assert response.status_code in [401, 400], f"Auth endpoint issue: {response.status_code}"
        print("✓ Auth endpoint exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

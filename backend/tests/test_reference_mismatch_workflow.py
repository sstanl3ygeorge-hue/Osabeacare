"""
Test Reference-Employment Mismatch Explanation Workflow
NHS Safer Recruitment compliance feature - workers explain why references don't match employment history

Tests:
1. GET /api/worker/reference-mismatches - returns mismatch data
2. POST /api/worker/reference-mismatches/{ref_num}/explain - submits explanation
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
WORKER_EMAIL = "test.worker@example.com"
WORKER_PASSWORD = "Welcome123!"


class TestReferenceMismatchWorkflow:
    """Reference-Employment Mismatch Explanation Workflow Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with worker authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.worker_token = None
        self.employee_id = None
        
    def authenticate_worker(self):
        """Authenticate as worker and get token"""
        response = self.session.post(f"{BASE_URL}/api/worker/login", json={
            "email": WORKER_EMAIL,
            "password": WORKER_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            self.worker_token = data.get("token")
            self.employee_id = data.get("employee", {}).get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.worker_token}"})
            return True
        return False
    
    def test_01_worker_login(self):
        """Test worker can login with provided credentials"""
        response = self.session.post(f"{BASE_URL}/api/worker/login", json={
            "email": WORKER_EMAIL,
            "password": WORKER_PASSWORD
        })
        
        print(f"Worker login response: {response.status_code}")
        
        assert response.status_code == 200, f"Worker login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "No token in response"
        assert "employee" in data, "No employee in response"
        
        self.worker_token = data["token"]
        self.employee_id = data["employee"]["id"]
        
        print(f"Worker authenticated: {data['employee'].get('name', 'Unknown')}")
        print(f"Employee ID: {self.employee_id}")
    
    def test_02_get_reference_mismatches_api(self):
        """Test GET /api/worker/reference-mismatches returns mismatch data"""
        assert self.authenticate_worker(), "Worker authentication failed"
        
        response = self.session.get(f"{BASE_URL}/api/worker/reference-mismatches")
        
        print(f"Reference mismatches response: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        assert response.status_code == 200, f"API failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "has_mismatches" in data, "Missing has_mismatches field"
        assert "mismatch_count" in data, "Missing mismatch_count field"
        assert "mismatches" in data, "Missing mismatches array"
        assert "explanation_types" in data, "Missing explanation_types array"
        
        print(f"Has mismatches: {data['has_mismatches']}")
        print(f"Mismatch count: {data['mismatch_count']}")
        print(f"Employment records count: {data.get('employment_records_count', 0)}")
        
        # Verify explanation types are provided
        assert len(data["explanation_types"]) > 0, "No explanation types provided"
        
        expected_types = ["agency_work", "company_name_change", "supervisor_not_hr", "volunteer_work", "other"]
        actual_types = [t["value"] for t in data["explanation_types"]]
        
        for expected in expected_types:
            assert expected in actual_types, f"Missing explanation type: {expected}"
        
        print(f"Explanation types: {actual_types}")
        
        # If there are mismatches, verify structure
        if data["has_mismatches"]:
            for mismatch in data["mismatches"]:
                assert "reference_number" in mismatch, "Missing reference_number"
                assert "referee_name" in mismatch, "Missing referee_name"
                assert "referee_company" in mismatch, "Missing referee_company"
                assert "message" in mismatch, "Missing message"
                assert "needs_explanation" in mismatch, "Missing needs_explanation"
                
                print(f"Mismatch found: Ref {mismatch['reference_number']} - {mismatch['referee_name']} at {mismatch['referee_company']}")
                print(f"  Message: {mismatch['message']}")
                print(f"  Needs explanation: {mismatch['needs_explanation']}")
    
    def test_03_submit_mismatch_explanation_validation(self):
        """Test POST /api/worker/reference-mismatches/{ref_num}/explain validation"""
        assert self.authenticate_worker(), "Worker authentication failed"
        
        # First get mismatches to find one to explain
        response = self.session.get(f"{BASE_URL}/api/worker/reference-mismatches")
        assert response.status_code == 200
        
        data = response.json()
        
        if not data["has_mismatches"]:
            pytest.skip("No mismatches to test explanation submission")
        
        # Get first mismatch that needs explanation
        mismatch = None
        for m in data["mismatches"]:
            if m.get("needs_explanation", True):
                mismatch = m
                break
        
        if not mismatch:
            pytest.skip("No mismatches need explanation")
        
        ref_num = mismatch["reference_number"]
        
        # Test invalid reference number
        response = self.session.post(f"{BASE_URL}/api/worker/reference-mismatches/99/explain", json={
            "reference_number": 99,
            "explanation_type": "agency_work",
            "explanation_text": "This is a test explanation that is long enough"
        })
        
        assert response.status_code == 400, f"Should reject invalid ref number: {response.text}"
        print("Invalid reference number correctly rejected")
        
        # Test mismatched reference number in body
        response = self.session.post(f"{BASE_URL}/api/worker/reference-mismatches/{ref_num}/explain", json={
            "reference_number": 3 - ref_num,  # Different number
            "explanation_type": "agency_work",
            "explanation_text": "This is a test explanation that is long enough"
        })
        
        assert response.status_code == 400, f"Should reject mismatched ref number: {response.text}"
        print("Mismatched reference number correctly rejected")
    
    def test_04_submit_mismatch_explanation_success(self):
        """Test successful submission of mismatch explanation"""
        assert self.authenticate_worker(), "Worker authentication failed"
        
        # First get mismatches
        response = self.session.get(f"{BASE_URL}/api/worker/reference-mismatches")
        assert response.status_code == 200
        
        data = response.json()
        
        if not data["has_mismatches"]:
            pytest.skip("No mismatches to test explanation submission")
        
        # Get first mismatch that needs explanation
        mismatch = None
        for m in data["mismatches"]:
            if m.get("needs_explanation", True):
                mismatch = m
                break
        
        if not mismatch:
            pytest.skip("No mismatches need explanation")
        
        ref_num = mismatch["reference_number"]
        
        # Submit valid explanation
        explanation_payload = {
            "reference_number": ref_num,
            "explanation_type": "agency_work",
            "explanation_text": "I worked through ABC Agency who placed me at this care home. My referee was from the agency, not the care home directly. The agency handled all my employment paperwork."
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/worker/reference-mismatches/{ref_num}/explain",
            json=explanation_payload
        )
        
        print(f"Submit explanation response: {response.status_code}")
        print(f"Response body: {response.text}")
        
        assert response.status_code == 200, f"Explanation submission failed: {response.text}"
        
        result = response.json()
        
        assert result.get("success") == True, "Success flag not set"
        assert "message" in result, "No message in response"
        assert result.get("status") == "submitted", "Status should be 'submitted'"
        
        print(f"Explanation submitted successfully: {result['message']}")
    
    def test_05_verify_explanation_persisted(self):
        """Verify explanation was persisted after submission"""
        assert self.authenticate_worker(), "Worker authentication failed"
        
        # Get mismatches again to verify explanation was saved
        response = self.session.get(f"{BASE_URL}/api/worker/reference-mismatches")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check if any mismatch now has explanation_status = "submitted"
        submitted_count = 0
        for mismatch in data.get("mismatches", []):
            if mismatch.get("explanation_status") == "submitted":
                submitted_count += 1
                print(f"Reference {mismatch['reference_number']} has submitted explanation")
                
                # Verify existing_explanation is populated
                existing = mismatch.get("existing_explanation")
                if existing:
                    print(f"  Type: {existing.get('type')}")
                    print(f"  Text preview: {existing.get('text', '')[:50]}...")
        
        print(f"Total submitted explanations: {submitted_count}")
    
    def test_06_worker_dashboard_loads(self):
        """Test worker dashboard loads with reference mismatch data"""
        assert self.authenticate_worker(), "Worker authentication failed"
        
        response = self.session.get(f"{BASE_URL}/api/worker/dashboard")
        
        print(f"Dashboard response: {response.status_code}")
        
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        
        # Verify dashboard structure
        assert "employee" in data, "Missing employee data"
        assert "progress" in data, "Missing progress data"
        
        employee = data["employee"]
        print(f"Employee: {employee.get('name', 'Unknown')}")
        print(f"Status: {employee.get('status', 'Unknown')}")
        
        # Check if references are present
        ref1_name = employee.get("reference_1_name")
        ref2_name = employee.get("reference_2_name")
        
        print(f"Reference 1: {ref1_name or 'Not set'}")
        print(f"Reference 2: {ref2_name or 'Not set'}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

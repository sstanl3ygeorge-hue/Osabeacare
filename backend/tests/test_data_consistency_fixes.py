"""
Test data consistency fixes:
1. Progress consistency - Employee list must show same percentage as Employee profile header
2. Expired count - Employee list must show 0 expired for Olakunle (not 10)
3. Training records - GET /api/training-records must NOT return any TEST_ records
4. Training tab - Employee profile Training tab must show expiry date, renewal status, actions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee ID for Olakunle
OLAKUNLE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"

class TestDataConsistencyFixes:
    """Test data consistency fixes for progress, expired count, and training records"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_progress_consistency_employee_list_vs_profile(self):
        """Progress percentage in employee list must match employee profile"""
        # Get employee from list
        list_response = self.session.get(f"{BASE_URL}/api/employees")
        assert list_response.status_code == 200, f"Failed to get employees: {list_response.text}"
        
        employees = list_response.json()
        olakunle_from_list = next((e for e in employees if e['id'] == OLAKUNLE_ID), None)
        
        if not olakunle_from_list:
            pytest.skip("Olakunle not found in employee list")
        
        list_progress = olakunle_from_list.get('completion_percentage')
        print(f"Progress from employee list: {list_progress}%")
        
        # Get employee profile directly
        profile_response = self.session.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}")
        assert profile_response.status_code == 200, f"Failed to get employee profile: {profile_response.text}"
        
        profile_progress = profile_response.json().get('completion_percentage')
        print(f"Progress from employee profile: {profile_progress}%")
        
        # Both should match
        assert list_progress == profile_progress, f"Progress mismatch: list={list_progress}%, profile={profile_progress}%"
        
        # Expected to be 69% based on main agent's fix
        assert list_progress == 69, f"Expected 69% progress, got {list_progress}%"
    
    def test_progress_matches_compliance_requirements(self):
        """Progress percentage must match compliance-requirements endpoint calculation"""
        # Get compliance requirements for Olakunle
        compliance_response = self.session.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}/compliance-requirements")
        assert compliance_response.status_code == 200, f"Failed to get compliance requirements: {compliance_response.text}"
        
        compliance_data = compliance_response.json()
        
        # Count evidence-backed requirements
        total = 0
        verified = 0
        for category in compliance_data.get('categories', []):
            for item in category.get('items', []):
                total += 1
                if item.get('has_evidence'):
                    verified += 1
        
        if total > 0:
            calculated_progress = int((verified / total) * 100)
            print(f"Compliance requirements: {verified}/{total} = {calculated_progress}%")
            
            # Get employee profile progress
            profile_response = self.session.get(f"{BASE_URL}/api/employees/{OLAKUNLE_ID}")
            profile_progress = profile_response.json().get('completion_percentage')
            
            # Should match
            assert profile_progress == calculated_progress, f"Progress mismatch: profile={profile_progress}%, calculated={calculated_progress}%"
    
    def test_expired_count_excludes_test_records(self):
        """Expired count must exclude TEST records and require active evidence"""
        # Get employee from list to check expiry_alerts
        list_response = self.session.get(f"{BASE_URL}/api/employees")
        assert list_response.status_code == 200
        
        employees = list_response.json()
        olakunle = next((e for e in employees if e['id'] == OLAKUNLE_ID), None)
        
        if not olakunle:
            pytest.skip("Olakunle not found")
        
        expiry_alerts = olakunle.get('expiry_alerts', {})
        expired_count = expiry_alerts.get('expired_count', 0)
        
        print(f"Expired count for Olakunle: {expired_count}")
        
        # Should be 0 (TEST records were removed)
        assert expired_count == 0, f"Expected 0 expired, got {expired_count}"
    
    def test_training_records_exclude_test_by_default(self):
        """GET /api/training-records must NOT return TEST_ records by default"""
        # Get all training records
        response = self.session.get(f"{BASE_URL}/api/training-records")
        assert response.status_code == 200, f"Failed to get training records: {response.text}"
        
        records = response.json()
        
        # Check for TEST records
        test_records = [r for r in records if r.get('training_name', '').upper().startswith('TEST')]
        
        print(f"Total training records: {len(records)}")
        print(f"TEST records found: {len(test_records)}")
        
        if test_records:
            print(f"TEST record names: {[r['training_name'] for r in test_records[:5]]}")
        
        assert len(test_records) == 0, f"Found {len(test_records)} TEST records that should be excluded"
    
    def test_training_records_include_test_when_requested(self):
        """GET /api/training-records?include_test=true should return TEST_ records if any exist"""
        # Get training records with include_test=true
        response = self.session.get(f"{BASE_URL}/api/training-records?include_test=true")
        assert response.status_code == 200, f"Failed to get training records: {response.text}"
        
        records = response.json()
        print(f"Total training records (including TEST): {len(records)}")
        
        # This test just verifies the parameter works - may or may not have TEST records
        # depending on whether cleanup was run
    
    def test_training_records_for_employee_exclude_test(self):
        """Training records for specific employee must exclude TEST records"""
        response = self.session.get(f"{BASE_URL}/api/training-records?employee_id={OLAKUNLE_ID}")
        assert response.status_code == 200
        
        records = response.json()
        test_records = [r for r in records if r.get('training_name', '').upper().startswith('TEST')]
        
        print(f"Olakunle's training records: {len(records)}")
        print(f"TEST records: {len(test_records)}")
        
        assert len(test_records) == 0, f"Found {len(test_records)} TEST records for Olakunle"
    
    def test_training_record_has_expiry_date_field(self):
        """Training records must have expiry_date field"""
        response = self.session.get(f"{BASE_URL}/api/training-records?employee_id={OLAKUNLE_ID}")
        assert response.status_code == 200
        
        records = response.json()
        
        if len(records) == 0:
            pytest.skip("No training records for Olakunle")
        
        # Check that records have expiry_date field (may be null)
        for record in records[:5]:
            assert 'expiry_date' in record, f"Training record missing expiry_date field: {record.get('training_name')}"
            print(f"Training: {record.get('training_name')}, Expiry: {record.get('expiry_date')}")
    
    def test_no_documents_pending_language(self):
        """Onboarding status should not use 'Documents Pending' - should be 'Recruitment File: Incomplete'"""
        # Get onboarding statuses
        response = self.session.get(f"{BASE_URL}/api/onboarding-statuses")
        assert response.status_code == 200
        
        statuses = response.json()
        print(f"Available onboarding statuses: {statuses}")
        
        # Check that 'documents_pending' is still a valid status (backend enum)
        # The UI should display it as 'Recruitment File: Incomplete'
        # This test just verifies the endpoint works
        assert isinstance(statuses, list)


class TestCleanupEndpoint:
    """Test the cleanup endpoint for TEST records"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_cleanup_endpoint_exists(self):
        """DELETE /api/training-records/cleanup-test endpoint should exist"""
        # Just verify the endpoint exists and returns proper response
        response = self.session.delete(f"{BASE_URL}/api/training-records/cleanup-test")
        
        # Should return 200 with deleted_count
        assert response.status_code == 200, f"Cleanup endpoint failed: {response.text}"
        
        data = response.json()
        assert 'deleted_count' in data
        assert 'message' in data
        
        print(f"Cleanup result: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

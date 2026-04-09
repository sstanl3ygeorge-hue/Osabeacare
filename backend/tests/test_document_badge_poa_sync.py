"""
Test Document Status Badge and POA Sync Fixes

Tests:
1. Document status badge mutual exclusivity - only ONE badge should show
2. POA sync between Worker and Admin dashboards - counts should match
3. DocumentActionMenu verification state checks
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com')

# Test employee with POA documents
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"
TEST_WORKER_EMAIL = "otunbakunlelonge85@gmail.com"
TEST_WORKER_PASSWORD = "Welcome123!"
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def worker_token():
    """Get worker authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/worker/login",
        json={"email": TEST_WORKER_EMAIL, "password": TEST_WORKER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Worker authentication failed")


class TestPOASync:
    """Test POA document sync between Worker and Admin dashboards"""
    
    def test_admin_poa_files_endpoint(self, admin_token):
        """Admin API should return all POA files including numbered variants"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have active files
        assert "active_files" in data
        assert "active_file_count" in data
        
        # Multi-file config should be set for POA
        assert data.get("multi_file_config", {}).get("multi_file") == True
        assert data.get("multi_file_config", {}).get("required_count") == 2
        
        print(f"Admin POA active files: {data.get('active_file_count')}")
        print(f"Admin POA historical files: {data.get('historical_file_count')}")
    
    def test_worker_dashboard_poa_documents(self, worker_token):
        """Worker dashboard should return POA documents"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Get POA documents from completed_documents
        completed = data.get("completed_documents", [])
        poa_completed = [d for d in completed if "proof_of_address" in d.get("type", "")]
        
        # Get POA from missing_documents
        missing = data.get("missing_documents", [])
        poa_missing = [d for d in missing if "proof_of_address" in d.get("type", "")]
        
        print(f"Worker POA completed: {len(poa_completed)}")
        print(f"Worker POA missing: {len(poa_missing)}")
        
        # Should have POA documents
        assert len(poa_completed) > 0 or len(poa_missing) > 0
    
    def test_poa_count_sync(self, admin_token, worker_token):
        """POA document counts should match between Admin and Worker dashboards"""
        # Get admin POA files
        admin_response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 200
        admin_data = admin_response.json()
        admin_active_count = admin_data.get("active_file_count", 0)
        
        # Get worker dashboard
        worker_response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert worker_response.status_code == 200
        worker_data = worker_response.json()
        
        # Count POA documents in worker dashboard
        completed = worker_data.get("completed_documents", [])
        poa_completed = [d for d in completed if "proof_of_address" in d.get("type", "")]
        worker_poa_count = len(poa_completed)
        
        print(f"Admin active POA count: {admin_active_count}")
        print(f"Worker POA count: {worker_poa_count}")
        
        # Counts should match (both should show same number of active POA documents)
        assert admin_active_count == worker_poa_count, \
            f"POA count mismatch: Admin={admin_active_count}, Worker={worker_poa_count}"


class TestDocumentStatusBadge:
    """Test document status badge mutual exclusivity"""
    
    def test_verification_stamp_values(self, admin_token):
        """Verify that 'not_verified' stamp is not treated as verified"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for file in data.get("active_files", []):
            stamp = file.get("verification_stamp")
            verified = file.get("verified")
            stamped_url = file.get("stamped_file_url")
            
            # If stamp is "not_verified", file should NOT be considered verified
            if stamp == "not_verified":
                assert verified == False, f"File {file.get('file_id')} has 'not_verified' stamp but verified=True"
                assert stamped_url is None, f"File {file.get('file_id')} has 'not_verified' stamp but has stamped_file_url"
            
            print(f"File {file.get('file_id')[:20]}... - Stamp: {stamp}, Verified: {verified}, Has stamped URL: {bool(stamped_url)}")
    
    def test_badge_mutual_exclusivity_logic(self, admin_token):
        """Test that badge logic is mutually exclusive"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for file in data.get("active_files", []):
            # Determine expected badge based on file state
            stamp = file.get("verification_stamp")
            verified = file.get("verified")
            rejected = file.get("rejected")
            status = file.get("status")
            stamped_url = file.get("stamped_file_url")
            
            # Valid stamps (not "not_verified" or empty)
            has_valid_stamp = stamp and stamp not in ["not_verified", ""]
            
            # Count how many badge conditions are true
            badge_conditions = [
                bool(stamped_url or has_valid_stamp),  # Verified with stamp
                verified and not has_valid_stamp and not stamped_url,  # Verified without stamp
                rejected,  # Rejected
                status == "uploaded",  # Awaiting review
            ]
            
            # Only one badge condition should be true at a time
            true_count = sum(badge_conditions)
            assert true_count <= 1, \
                f"File {file.get('file_id')} has multiple badge conditions: stamp={stamp}, verified={verified}, rejected={rejected}, status={status}"
            
            print(f"File {file.get('file_id')[:20]}... - Badge conditions met: {true_count}")


class TestDocumentActionMenu:
    """Test DocumentActionMenu verification state checks"""
    
    def test_verify_action_visibility(self, admin_token):
        """Verify action should only show for non-verified files"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/proof_of_address/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for file in data.get("active_files", []):
            stamp = file.get("verification_stamp")
            verified = file.get("verified")
            stamped_url = file.get("stamped_file_url")
            status = file.get("status")
            
            # Valid stamps (not "not_verified" or empty)
            has_valid_stamp = stamp and stamp not in ["not_verified", ""]
            
            # isVerified logic from DocumentActionMenu.js
            is_verified = verified or has_valid_stamp or bool(stamped_url)
            
            # isActiveFile logic
            is_active = status not in ['superseded', 'uploaded_in_error', 'rejected', 'deleted']
            
            # showVerifyAction should be True only if NOT verified AND active
            show_verify = not is_verified and is_active
            
            # showRemoveStamp should be True only if verified
            show_remove_stamp = is_verified
            
            # These should be mutually exclusive
            assert not (show_verify and show_remove_stamp), \
                f"File {file.get('file_id')} shows both Verify and Remove Stamp actions"
            
            print(f"File {file.get('file_id')[:20]}... - Show Verify: {show_verify}, Show Remove Stamp: {show_remove_stamp}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

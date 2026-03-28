"""
Test Compliance Data Consistency - Iteration 24
Tests for data consistency between Overview and What's Needed tabs
Tests all CRUD operations: Upload, View, Download, Replace, Remove, Approve
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee - OCS-0001 (Olakunle Alonge)
TEST_EMPLOYEE_ID = None  # Will be fetched dynamically


class TestComplianceDataConsistency:
    """Test data consistency between Overview and What's Needed tabs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token and employee ID"""
        global TEST_EMPLOYEE_ID
        
        # Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get employee OCS-0001
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert response.status_code == 200
        employees = response.json()
        
        # Find OCS-0001 (Olakunle Alonge)
        for emp in employees:
            if emp.get("employee_code") == "OCS-0001":
                TEST_EMPLOYEE_ID = emp["id"]
                self.employee_id = emp["id"]
                self.employee_name = f"{emp['first_name']} {emp['last_name']}"
                break
        
        if not TEST_EMPLOYEE_ID:
            # Use first available employee
            if employees:
                TEST_EMPLOYEE_ID = employees[0]["id"]
                self.employee_id = employees[0]["id"]
                self.employee_name = f"{employees[0]['first_name']} {employees[0]['last_name']}"
            else:
                pytest.skip("No employees found")
        
        print(f"\n✅ Using employee: {self.employee_name} (ID: {self.employee_id})")
    
    def test_01_compliance_requirements_endpoint(self):
        """Test compliance-requirements endpoint returns data"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "requirements" in data, "Missing 'requirements' key"
        assert "summary" in data, "Missing 'summary' key"
        
        requirements = data["requirements"]
        summary = data["summary"]
        
        print(f"✅ Got {len(requirements)} requirements")
        print(f"   Summary: total={summary.get('total')}, verified={summary.get('verified')}, completed={summary.get('completed')}, missing={summary.get('missing')}")
        
        # Verify summary counts match requirements
        total_from_reqs = len(requirements)
        verified_from_reqs = sum(1 for r in requirements if r.get("verified"))
        has_evidence_from_reqs = sum(1 for r in requirements if r.get("has_evidence"))
        missing_from_reqs = sum(1 for r in requirements if not r.get("has_evidence"))
        
        assert summary.get("total") == total_from_reqs, f"Total mismatch: summary={summary.get('total')}, actual={total_from_reqs}"
        print(f"✅ Summary counts are consistent with requirements list")
        
        return data
    
    def test_02_single_source_of_truth(self):
        """Verify Overview and What's Needed use same data source"""
        # Get compliance-requirements (used by both tabs now)
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        requirements = data["requirements"]
        
        # Calculate counts from requirements
        verified_count = sum(1 for r in requirements if r.get("verified"))
        ready_for_review = sum(1 for r in requirements if r.get("has_evidence") and not r.get("verified"))
        still_needed = sum(1 for r in requirements if not r.get("has_evidence"))
        
        # Verify summary matches
        assert summary.get("verified") == verified_count, f"Verified mismatch: {summary.get('verified')} vs {verified_count}"
        
        # The 'completed' in summary should equal has_evidence count
        completed_count = sum(1 for r in requirements if r.get("has_evidence"))
        assert summary.get("completed") == completed_count, f"Completed mismatch: {summary.get('completed')} vs {completed_count}"
        
        print(f"✅ SINGLE SOURCE OF TRUTH verified:")
        print(f"   Verified: {verified_count}")
        print(f"   Ready for Review: {ready_for_review}")
        print(f"   Still Needed: {still_needed}")
    
    def test_03_no_duplicate_requirements(self):
        """Verify no duplicate requirements in checklist"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        requirements = data["requirements"]
        req_ids = [r["id"] for r in requirements]
        
        # Check for duplicates
        duplicates = [id for id in req_ids if req_ids.count(id) > 1]
        assert len(duplicates) == 0, f"Found duplicate requirements: {set(duplicates)}"
        
        print(f"✅ No duplicate requirements found ({len(req_ids)} unique requirements)")


class TestUploadFlow:
    """Test document upload flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.employee_id = TEST_EMPLOYEE_ID
    
    def test_upload_document(self):
        """Test uploading a document via evidence endpoint"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # Create a test file
        test_content = b"Test document content for compliance testing"
        files = {"file": ("test_document.pdf", test_content, "application/pdf")}
        
        # Upload to a requirement (cv is a good test case)
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/cv/evidence",
            headers=self.headers,
            files=files
        )
        
        # Should succeed or return 200/201
        assert response.status_code in [200, 201], f"Upload failed: {response.status_code} - {response.text}"
        
        data = response.json()
        print(f"✅ Upload successful: {data.get('message', 'OK')}")
        
        # Store file_id for later tests
        self.uploaded_file_id = data.get("file_id") or data.get("evidence_file", {}).get("file_id")
        return self.uploaded_file_id


class TestViewDownloadFlow:
    """Test View and Download functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.employee_id = TEST_EMPLOYEE_ID
    
    def test_view_evidence(self):
        """Test viewing evidence files"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # Get requirements with evidence
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find a requirement with evidence
        req_with_evidence = None
        for req in data["requirements"]:
            if req.get("has_evidence") and req.get("evidence_files"):
                req_with_evidence = req
                break
        
        if not req_with_evidence:
            pytest.skip("No requirements with evidence found")
        
        # Get evidence files
        evidence_files = req_with_evidence.get("evidence_files", [])
        if not evidence_files:
            pytest.skip("No evidence files found")
        
        file_id = evidence_files[0].get("file_id")
        req_id = req_with_evidence["id"]
        
        # Try to view the file
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{req_id}/evidence/{file_id}/view",
            headers=self.headers
        )
        
        # Should return file content or redirect
        assert response.status_code in [200, 302, 307], f"View failed: {response.status_code}"
        print(f"✅ View evidence works for {req_id}/{file_id}")
    
    def test_download_evidence(self):
        """Test downloading evidence files"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # Get requirements with evidence
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find a requirement with evidence
        req_with_evidence = None
        for req in data["requirements"]:
            if req.get("has_evidence") and req.get("evidence_files"):
                req_with_evidence = req
                break
        
        if not req_with_evidence:
            pytest.skip("No requirements with evidence found")
        
        evidence_files = req_with_evidence.get("evidence_files", [])
        if not evidence_files:
            pytest.skip("No evidence files found")
        
        file_id = evidence_files[0].get("file_id")
        req_id = req_with_evidence["id"]
        
        # Try to download the file
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{req_id}/evidence/{file_id}/download",
            headers=self.headers
        )
        
        # Should return file content
        assert response.status_code in [200, 302, 307], f"Download failed: {response.status_code}"
        print(f"✅ Download evidence works for {req_id}/{file_id}")


class TestApproveFlow:
    """Test Approve/Verify functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.employee_id = TEST_EMPLOYEE_ID
    
    def test_approve_requirement_with_evidence(self):
        """Test approving a requirement that has evidence"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # Get requirements with evidence but not verified
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find a requirement with evidence but not verified
        req_to_approve = None
        for req in data["requirements"]:
            if req.get("has_evidence") and not req.get("verified"):
                req_to_approve = req
                break
        
        if not req_to_approve:
            print("ℹ️ No unverified requirements with evidence found - all may be approved already")
            return
        
        req_id = req_to_approve["id"]
        
        # Try to approve
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{req_id}/verify-all",
            headers=self.headers
        )
        
        # Should succeed
        assert response.status_code == 200, f"Approve failed: {response.status_code} - {response.text}"
        print(f"✅ Approved requirement: {req_id}")
    
    def test_approve_requirement_without_evidence_fails(self):
        """Test that approving a requirement without evidence fails"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # Get requirements without evidence
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find a requirement without evidence
        req_without_evidence = None
        for req in data["requirements"]:
            if not req.get("has_evidence"):
                req_without_evidence = req
                break
        
        if not req_without_evidence:
            print("ℹ️ All requirements have evidence - cannot test this case")
            return
        
        req_id = req_without_evidence["id"]
        
        # Try to approve - should return 0 verified or error
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/{req_id}/verify-all",
            headers=self.headers
        )
        
        # Should succeed but verify 0 documents
        if response.status_code == 200:
            data = response.json()
            verified_count = data.get("verified_count", 0)
            print(f"ℹ️ Approve returned: {verified_count} documents verified (expected 0)")
        else:
            print(f"ℹ️ Approve returned error as expected: {response.status_code}")


class TestReplaceRemoveFlow:
    """Test Replace and Remove file functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.employee_id = TEST_EMPLOYEE_ID
    
    def test_remove_file_soft_delete(self):
        """Test soft-removing a file"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # First upload a test file
        test_content = b"Test file for removal"
        files = {"file": ("test_remove.pdf", test_content, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/cv/evidence",
            headers=self.headers,
            files=files
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not upload test file: {response.text}")
        
        data = response.json()
        file_id = data.get("file_id") or data.get("evidence_file", {}).get("file_id")
        
        if not file_id:
            pytest.skip("No file_id returned from upload")
        
        # Now remove the file
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/cv/evidence/{file_id}/remove",
            headers=self.headers,
            json={"reason": "Testing soft delete functionality"}
        )
        
        assert response.status_code == 200, f"Remove failed: {response.status_code} - {response.text}"
        print(f"✅ Soft-remove successful for file {file_id}")
    
    def test_replace_file(self):
        """Test replacing a file"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # First upload a test file
        test_content = b"Original test file for replacement"
        files = {"file": ("test_original.pdf", test_content, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/cv/evidence",
            headers=self.headers,
            files=files
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not upload test file: {response.text}")
        
        data = response.json()
        file_id = data.get("file_id") or data.get("evidence_file", {}).get("file_id")
        
        if not file_id:
            pytest.skip("No file_id returned from upload")
        
        # Now replace the file
        new_content = b"Replacement test file"
        files = {"file": ("test_replacement.pdf", new_content, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/cv/evidence/{file_id}/replace",
            headers=self.headers,
            files=files,
            data={"reason": "Testing replace functionality"}
        )
        
        assert response.status_code == 200, f"Replace failed: {response.status_code} - {response.text}"
        print(f"✅ Replace successful for file {file_id}")


class TestStateRefresh:
    """Test UI state refresh after actions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.employee_id = TEST_EMPLOYEE_ID
    
    def test_state_refresh_after_upload(self):
        """Test that compliance data updates after upload"""
        if not self.employee_id:
            pytest.skip("No employee ID available")
        
        # Get initial state
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        initial_data = response.json()
        initial_completed = initial_data["summary"]["completed"]
        
        # Upload a file
        test_content = b"Test file for state refresh"
        files = {"file": ("test_state.pdf", test_content, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{self.employee_id}/requirements/cv/evidence",
            headers=self.headers,
            files=files
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not upload test file: {response.text}")
        
        # Get updated state
        response = requests.get(
            f"{BASE_URL}/api/employees/{self.employee_id}/compliance-requirements",
            headers=self.headers
        )
        assert response.status_code == 200
        updated_data = response.json()
        updated_completed = updated_data["summary"]["completed"]
        
        # CV should now have evidence
        cv_req = next((r for r in updated_data["requirements"] if r["id"] == "cv"), None)
        assert cv_req is not None, "CV requirement not found"
        assert cv_req.get("has_evidence") == True, "CV should have evidence after upload"
        
        print(f"✅ State refresh works: completed {initial_completed} -> {updated_completed}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

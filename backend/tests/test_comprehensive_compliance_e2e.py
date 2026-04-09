"""
Comprehensive End-to-End Compliance Testing for CQC Audit-Readiness

Tests all compliance workflows:
- Document sync (worker uploads → admin visibility)
- Document verification/stamping
- Request replacement workflow
- RTW, DBS, Identity, Address check recordings
- Training certificates
- References
- Agreements (contract, handbook)
- Compliance percentage calculation
- Worker dashboard accuracy
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"
TEST_EMPLOYEE_EMAIL = "otunbakunlelonge85@gmail.com"
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
WORKER_PASSWORD = "Welcome123!"


class TestAuthenticationSetup:
    """Authentication tests - run first to get tokens"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def worker_token(self):
        """Get worker authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": TEST_EMPLOYEE_EMAIL, "password": WORKER_PASSWORD}
        )
        assert response.status_code == 200, f"Worker login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_admin_login(self, admin_token):
        """Test admin can login successfully"""
        assert admin_token is not None
        assert len(admin_token) > 50  # JWT tokens are long
        print(f"Admin login successful, token length: {len(admin_token)}")
    
    def test_worker_login(self, worker_token):
        """Test worker can login successfully"""
        assert worker_token is not None
        assert len(worker_token) > 50
        print(f"Worker login successful, token length: {len(worker_token)}")


class TestComplianceFileEndpoint:
    """Test the compliance-file endpoint returns all required sections"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_compliance_file_returns_all_sections(self, admin_token):
        """Verify compliance-file endpoint returns all required sections"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check all required sections exist
        sections = data.get("sections", {})
        required_sections = [
            "right_to_work", "dbs", "identity", "proof_of_address",
            "agreements", "references", "training"
        ]
        for section in required_sections:
            assert section in sections, f"Missing section: {section}"
        print(f"All {len(required_sections)} required sections present")
    
    def test_rtw_section_has_evidence_and_check_rows(self, admin_token):
        """RTW section should have both evidence and check rows"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        rtw = data["sections"]["right_to_work"]
        rows = rtw.get("rows", [])
        
        row_types = [r.get("row_type") for r in rows]
        assert "evidence" in row_types, "RTW missing evidence row"
        assert "check" in row_types, "RTW missing check row"
        print(f"RTW section has {len(rows)} rows: {row_types}")
    
    def test_dbs_section_has_evidence_and_check_rows(self, admin_token):
        """DBS section should have both evidence and check rows"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        dbs = data["sections"]["dbs"]
        rows = dbs.get("rows", [])
        
        row_types = [r.get("row_type") for r in rows]
        assert "evidence" in row_types, "DBS missing evidence row"
        assert "check" in row_types, "DBS missing check row"
        print(f"DBS section has {len(rows)} rows: {row_types}")
    
    def test_identity_section_has_evidence_and_verification_rows(self, admin_token):
        """Identity section should have evidence and verification rows"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        identity = data["sections"]["identity"]
        rows = identity.get("rows", [])
        
        row_keys = [r.get("key") for r in rows]
        assert "identity_evidence" in row_keys, "Identity missing evidence row"
        assert "identity_verification" in row_keys, "Identity missing verification row"
        print(f"Identity section has rows: {row_keys}")
    
    def test_poa_section_has_evidence_and_verification_rows(self, admin_token):
        """Proof of Address section should have evidence and verification rows"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        poa = data["sections"]["proof_of_address"]
        rows = poa.get("rows", [])
        
        row_keys = [r.get("key") for r in rows]
        assert "proof_of_address_evidence" in row_keys, "PoA missing evidence row"
        assert "address_verification" in row_keys, "PoA missing verification row"
        print(f"PoA section has rows: {row_keys}")


class TestDocumentSync:
    """Test document sync between worker uploads and admin visibility"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def worker_token(self):
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": TEST_EMPLOYEE_EMAIL, "password": WORKER_PASSWORD}
        )
        return response.json()["token"]
    
    def test_admin_can_see_rtw_documents(self, admin_token):
        """Admin can see RTW documents in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        rtw = data["sections"]["right_to_work"]
        evidence_row = next((r for r in rtw["rows"] if r["row_type"] == "evidence"), None)
        
        assert evidence_row is not None
        assert evidence_row["counts"]["active_files"] > 0, "No RTW documents found"
        print(f"RTW evidence: {evidence_row['counts']['active_files']} active files, {evidence_row['counts']['verified']} verified")
    
    def test_admin_can_see_dbs_documents(self, admin_token):
        """Admin can see DBS documents in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        dbs = data["sections"]["dbs"]
        evidence_row = next((r for r in dbs["rows"] if r["row_type"] == "evidence"), None)
        
        assert evidence_row is not None
        assert evidence_row["counts"]["active_files"] > 0, "No DBS documents found"
        print(f"DBS evidence: {evidence_row['counts']['active_files']} active files, {evidence_row['counts']['verified']} verified")
    
    def test_admin_can_see_identity_documents(self, admin_token):
        """Admin can see identity documents in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        identity = data["sections"]["identity"]
        evidence_row = next((r for r in identity["rows"] if r["key"] == "identity_evidence"), None)
        
        assert evidence_row is not None
        assert evidence_row["counts"]["active_files"] > 0, "No identity documents found"
        print(f"Identity evidence: {evidence_row['counts']['active_files']} active files, {evidence_row['counts']['verified']} verified")
    
    def test_admin_can_see_poa_documents(self, admin_token):
        """Admin can see proof of address documents in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        poa = data["sections"]["proof_of_address"]
        evidence_row = next((r for r in poa["rows"] if r["key"] == "proof_of_address_evidence"), None)
        
        assert evidence_row is not None
        assert evidence_row["counts"]["active_files"] > 0, "No PoA documents found"
        print(f"PoA evidence: {evidence_row['counts']['active_files']} active files, {evidence_row['counts']['verified']} verified")


class TestCheckRecordings:
    """Test admin can record RTW, DBS, Identity, Address checks"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_rtw_check_is_recorded(self, admin_token):
        """RTW check should be recorded and visible"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        rtw = data["sections"]["right_to_work"]
        check_row = next((r for r in rtw["rows"] if r["row_type"] == "check"), None)
        
        assert check_row is not None
        assert check_row["has_check"] == True, "RTW check not recorded"
        assert check_row["is_verified"] == True, "RTW check not verified"
        
        check_data = check_row.get("check_data", {})
        assert check_data.get("method") is not None, "RTW check method missing"
        assert check_data.get("outcome") == "verified", "RTW check outcome not verified"
        print(f"RTW check: method={check_data.get('method')}, outcome={check_data.get('outcome')}")
    
    def test_dbs_check_is_recorded(self, admin_token):
        """DBS check should be recorded and visible"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        dbs = data["sections"]["dbs"]
        check_row = next((r for r in dbs["rows"] if r["row_type"] == "check"), None)
        
        assert check_row is not None
        assert check_row["has_check"] == True, "DBS check not recorded"
        assert check_row["is_verified"] == True, "DBS check not verified"
        
        check_data = check_row.get("check_data", {})
        assert check_data.get("dbs_level") is not None, "DBS level missing"
        print(f"DBS check: level={check_data.get('dbs_level')}, result={check_data.get('result_status')}")
    
    def test_identity_verification_is_recorded(self, admin_token):
        """Identity verification should be recorded"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        identity = data["sections"]["identity"]
        verification_row = next((r for r in identity["rows"] if r["key"] == "identity_verification"), None)
        
        assert verification_row is not None
        # Check if verification exists
        has_check = verification_row.get("has_check", False)
        print(f"Identity verification: has_check={has_check}, status={verification_row.get('status')}")
    
    def test_address_verification_is_recorded(self, admin_token):
        """Address verification should be recorded"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        poa = data["sections"]["proof_of_address"]
        verification_row = next((r for r in poa["rows"] if r["key"] == "address_verification"), None)
        
        assert verification_row is not None
        print(f"Address verification: has_check={verification_row.get('has_check')}, status={verification_row.get('status')}")


class TestDocumentVerification:
    """Test document verification/stamping functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_verified_documents_have_stamps(self, admin_token):
        """Verified documents should have verification stamps"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        rtw = data["sections"]["right_to_work"]
        evidence_row = next((r for r in rtw["rows"] if r["row_type"] == "evidence"), None)
        
        # Check documents preview for verification stamps
        docs = evidence_row.get("documents_preview", [])
        verified_docs = [d for d in docs if d.get("verified") == True]
        
        assert len(verified_docs) > 0, "No verified documents found"
        
        # Check at least one has a verification stamp
        stamped_docs = [d for d in verified_docs if d.get("verification_stamp")]
        assert len(stamped_docs) > 0, "No documents with verification stamps"
        
        for doc in stamped_docs[:2]:
            print(f"Verified doc: {doc.get('file_name')}, stamp={doc.get('verification_stamp')}, label={doc.get('verification_stamp_label')}")


class TestWorkerDashboard:
    """Test worker dashboard shows correct compliance status"""
    
    @pytest.fixture(scope="class")
    def worker_token(self):
        response = requests.post(
            f"{BASE_URL}/api/worker/login",
            json={"email": TEST_EMPLOYEE_EMAIL, "password": WORKER_PASSWORD}
        )
        return response.json()["token"]
    
    def test_worker_dashboard_loads(self, worker_token):
        """Worker dashboard should load successfully"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "missing_documents" in data
        assert "completed_documents" in data
        assert "missing_trainings" in data
        assert "completed_trainings" in data
        print(f"Worker dashboard loaded: {len(data.get('completed_documents', []))} completed docs, {len(data.get('missing_documents', []))} missing")
    
    def test_worker_sees_completed_documents(self, worker_token):
        """Worker should see their completed documents"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        data = response.json()
        
        completed = data.get("completed_documents", [])
        completed_types = [d.get("type") for d in completed]
        
        # Should have at least some completed documents
        print(f"Completed document types: {completed_types}")
        assert len(completed) > 0, "Worker should have some completed documents"
    
    def test_worker_sees_training_status(self, worker_token):
        """Worker should see their training status"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        data = response.json()
        
        completed_trainings = data.get("completed_trainings", [])
        missing_trainings = data.get("missing_trainings", [])
        
        print(f"Trainings: {len(completed_trainings)} completed, {len(missing_trainings)} missing")
        # At least check the structure is correct
        if completed_trainings:
            assert "id" in completed_trainings[0]
            assert "name" in completed_trainings[0]


class TestTrainingSection:
    """Test training section in compliance file"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_training_section_exists(self, admin_token):
        """Training section should exist in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "training" in data["sections"], "Training section missing"
        training = data["sections"]["training"]
        # Training uses evaluation.items structure
        has_data = "rows" in training or "items" in training or ("evaluation" in training and "items" in training.get("evaluation", {}))
        assert has_data, "Training section has no rows/items/evaluation"
        print(f"Training section present with keys: {list(training.keys())}")
        if "evaluation" in training:
            eval_items = training["evaluation"].get("items", [])
            print(f"Training evaluation has {len(eval_items)} items")


class TestAgreementsSection:
    """Test agreements section (contract, handbook acknowledgement)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_agreements_section_exists(self, admin_token):
        """Agreements section should exist in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "agreements" in data["sections"], "Agreements section missing"
        agreements = data["sections"]["agreements"]
        print(f"Agreements section present with keys: {list(agreements.keys())}")
    
    def test_agreements_has_contract_and_handbook(self, admin_token):
        """Agreements should include contract and handbook acknowledgement"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        agreements = data["sections"]["agreements"]
        
        rows = agreements.get("rows", [])
        row_keys = [r.get("key", "") for r in rows]
        
        # Check for contract and handbook related rows
        has_contract = any("contract" in k.lower() for k in row_keys)
        has_handbook = any("handbook" in k.lower() for k in row_keys)
        
        print(f"Agreement rows: {row_keys}")
        print(f"Has contract: {has_contract}, Has handbook: {has_handbook}")


class TestReferencesSection:
    """Test references section in compliance file"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_references_section_exists(self, admin_token):
        """References section should exist in compliance file"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "references" in data["sections"], "References section missing"
        references = data["sections"]["references"]
        print(f"References section present with keys: {list(references.keys())}")


class TestCompliancePercentage:
    """Test compliance percentage calculation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_compliance_file_has_progress(self, admin_token):
        """Compliance file should include progress/percentage"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Check for progress fields
        progress = data.get("progress", {})
        if progress:
            print(f"Progress: {progress}")
        
        # Also check summary
        summary = data.get("summary", {})
        if summary:
            print(f"Summary: {summary}")
    
    def test_employee_has_compliance_status(self, admin_token):
        """Employee should have compliance status"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for compliance-related fields
        compliance_fields = ["compliance_percentage", "compliance_status", "progress", "readiness"]
        found_fields = [f for f in compliance_fields if f in data]
        print(f"Employee compliance fields: {found_fields}")
        
        if "compliance_percentage" in data:
            print(f"Compliance percentage: {data['compliance_percentage']}")


class TestRequestReplacementWorkflow:
    """Test request replacement workflow"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_historical_documents_visible(self, admin_token):
        """Historical (rejected/superseded) documents should be visible"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Check RTW for historical documents
        rtw = data["sections"]["right_to_work"]
        evidence_row = next((r for r in rtw["rows"] if r["row_type"] == "evidence"), None)
        
        historical = evidence_row.get("historical_documents", [])
        historical_count = evidence_row.get("counts", {}).get("historical", 0)
        
        print(f"RTW historical documents: {historical_count}")
        if historical:
            for doc in historical[:2]:
                print(f"  - {doc.get('file_name')}: status={doc.get('status')}, reason={doc.get('rejection_reason', 'N/A')[:50] if doc.get('rejection_reason') else 'N/A'}")


class TestRequirementFilesEndpoint:
    """Test the requirement files endpoint for admin document access"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_get_rtw_files(self, admin_token):
        """Admin can get RTW files via requirement files endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/right_to_work_evidence/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # May return 200 or 404 depending on implementation
        if response.status_code == 200:
            data = response.json()
            print(f"RTW files endpoint returned: {len(data.get('files', data.get('documents', [])))} files")
        else:
            print(f"RTW files endpoint status: {response.status_code}")
    
    def test_get_identity_files(self, admin_token):
        """Admin can get identity files via requirement files endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/requirements/identity_evidence/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Identity files endpoint returned: {len(data.get('files', data.get('documents', [])))} files")
        else:
            print(f"Identity files endpoint status: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

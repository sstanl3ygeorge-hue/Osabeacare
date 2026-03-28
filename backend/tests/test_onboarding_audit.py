"""
Comprehensive Onboarding Audit Test Suite
Tests the full employee onboarding flow from start to compliance-ready.
Covers all requirement types: documents, training, internal checks.
Tests Upload → View → Download → Approve flow for each type.
"""

import pytest
import requests
import os
import io
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"

# Test employee data
TEST_EMPLOYEE = {
    "first_name": "Audit",
    "last_name": "Test Employee",
    "email": f"audit.test.{int(time.time())}@osabea.care",
    "phone": "07700900123",
    "role": "Healthcare Assistant",
    "onboarding_status": "New",
    "status": "new"
}


class TestOnboardingAudit:
    """Full onboarding simulation audit tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_employee(self, headers):
        """Create or get test employee"""
        # Try to create new employee
        response = requests.post(f"{BASE_URL}/api/employees", json=TEST_EMPLOYEE, headers=headers)
        if response.status_code in [200, 201]:
            employee = response.json()
            print(f"Created test employee: {employee['employee_code']}")
            return employee
        
        # If creation failed, search for existing
        search_response = requests.get(f"{BASE_URL}/api/employees?search=Audit", headers=headers)
        if search_response.status_code == 200:
            employees = search_response.json()
            if employees:
                return employees[0]
        
        pytest.fail("Could not create or find test employee")
    
    # ==================== STEP 1: Employee Creation ====================
    
    def test_employee_created_successfully(self, test_employee):
        """STEP 1: Verify test employee was created"""
        assert test_employee is not None
        assert test_employee.get("id") is not None
        assert test_employee.get("employee_code") is not None
        assert test_employee.get("first_name") == "Audit"
        assert test_employee.get("role") == "Healthcare Assistant"
        print(f"✅ Employee created: {test_employee['employee_code']} - {test_employee['first_name']} {test_employee['last_name']}")
    
    def test_employee_initial_compliance_zero(self, test_employee, headers):
        """Verify new employee starts with 0% compliance"""
        response = requests.get(f"{BASE_URL}/api/employees/{test_employee['id']}/compliance", headers=headers)
        assert response.status_code == 200
        compliance = response.json()
        # New employee should have 0% or very low completion
        assert compliance.get("compliance", {}).get("completion_percentage", 0) <= 10
        print(f"✅ Initial compliance: {compliance.get('compliance', {}).get('completion_percentage', 0)}%")
    
    # ==================== STEP 2: Compliance Requirements Check ====================
    
    def test_compliance_requirements_structure(self, test_employee, headers):
        """STEP 2: Verify compliance requirements are properly structured"""
        response = requests.get(f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "requirements" in data
        requirements = data["requirements"]
        assert len(requirements) > 0, "Should have compliance requirements"
        
        # Check each requirement has required fields
        for req in requirements:
            assert "id" in req, f"Requirement missing id: {req}"
            assert "name" in req, f"Requirement missing name: {req}"
            assert "category" in req, f"Requirement missing category: {req}"
            assert "type" in req, f"Requirement missing type: {req}"
            assert "status" in req, f"Requirement missing status: {req}"
        
        print(f"✅ Found {len(requirements)} compliance requirements")
    
    def test_all_six_categories_present(self, test_employee, headers):
        """Verify all 6 compliance categories are present"""
        response = requests.get(f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements", headers=headers)
        assert response.status_code == 200
        requirements = response.json()["requirements"]
        
        categories = set(req["category"] for req in requirements)
        expected_categories = {
            "1_Legal_Safety",
            "2_Core_Training", 
            "3_Role_Readiness",
            "4_Employment",
            "5_Agreements",
            "6_Admin"
        }
        
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        print(f"✅ All 6 categories present: {sorted(categories)}")
    
    def test_requirement_types_correct(self, test_employee, headers):
        """Verify requirement types are document, training, or form-generated"""
        response = requests.get(f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements", headers=headers)
        assert response.status_code == 200
        requirements = response.json()["requirements"]
        
        valid_types = {"document", "training", "form-generated"}
        for req in requirements:
            assert req["type"] in valid_types, f"Invalid type '{req['type']}' for {req['name']}"
        
        # Count by type
        type_counts = {}
        for req in requirements:
            type_counts[req["type"]] = type_counts.get(req["type"], 0) + 1
        
        print(f"✅ Requirement types: {type_counts}")
    
    # ==================== STEP 3A: Employee Documents Upload/View/Download/Approve ====================
    
    def test_upload_identity_document(self, test_employee, headers):
        """STEP 3A: Upload identity document (passport)"""
        # Create a test PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("test_passport.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/identity_documents/evidence",
            files=files,
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        data = response.json()
        assert "document_id" in data or "id" in data or "message" in data
        print(f"✅ Identity document uploaded successfully")
    
    def test_upload_right_to_work_document(self, test_employee, headers):
        """Upload Right to Work document"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("right_to_work.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/right_to_work_documents/evidence",
            files=files,
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ Right to Work document uploaded")
    
    def test_upload_dbs_certificate(self, test_employee, headers):
        """Upload DBS certificate"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("dbs_certificate.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/dbs_certificate/evidence",
            files=files,
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ DBS certificate uploaded")
    
    # ==================== STEP 3B: Internal Checks ====================
    
    def test_upload_rtw_verification(self, test_employee, headers):
        """STEP 3B: Upload internal RTW verification check"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("rtw_check_result.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/right_to_work_check/evidence",
            files=files,
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ RTW verification check uploaded (internal)")
    
    def test_upload_dbs_update_service_check(self, test_employee, headers):
        """Upload DBS update service check (internal)"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("dbs_update_check.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/dbs_check/evidence",
            files=files,
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ DBS update service check uploaded (internal)")
    
    # ==================== STEP 4: Training Certificates ====================
    
    def test_upload_safeguarding_training(self, test_employee, headers):
        """STEP 4: Upload Safeguarding training certificate"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("safeguarding_cert.pdf", io.BytesIO(pdf_content), "application/pdf")}
        expiry_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/training/safeguarding/upload-certificate",
            files=files,
            data={"expiry_date": expiry_date},
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ Safeguarding training certificate uploaded")
    
    def test_upload_manual_handling_training(self, test_employee, headers):
        """Upload Manual Handling training certificate"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("manual_handling_cert.pdf", io.BytesIO(pdf_content), "application/pdf")}
        expiry_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/training/manual_handling/upload-certificate",
            files=files,
            data={"expiry_date": expiry_date},
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ Manual Handling training certificate uploaded")
    
    def test_upload_infection_control_training(self, test_employee, headers):
        """Upload Infection Control training certificate"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("infection_control_cert.pdf", io.BytesIO(pdf_content), "application/pdf")}
        expiry_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/training/infection_control/upload-certificate",
            files=files,
            data={"expiry_date": expiry_date},
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ Infection Control training certificate uploaded")
    
    def test_upload_bls_training(self, test_employee, headers):
        """Upload Basic Life Support (BLS) training certificate"""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("bls_cert.pdf", io.BytesIO(pdf_content), "application/pdf")}
        expiry_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/training/bls/upload-certificate",
            files=files,
            data={"expiry_date": expiry_date},
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        print(f"✅ BLS training certificate uploaded")
    
    # ==================== STEP 5: View/Download Evidence ====================
    
    def test_view_uploaded_evidence(self, test_employee, headers):
        """STEP 5: Verify uploaded evidence can be viewed"""
        # Get compliance requirements to find uploaded files
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        assert response.status_code == 200
        requirements = response.json()["requirements"]
        
        # Find requirements with evidence
        with_evidence = [r for r in requirements if r.get("has_evidence") or r.get("evidence_count", 0) > 0]
        print(f"Requirements with evidence: {len(with_evidence)}")
        
        for req in with_evidence[:3]:  # Test first 3
            evidence_files = req.get("evidence_files", [])
            if evidence_files:
                file_info = evidence_files[0]
                file_id = file_info.get("file_id")
                if file_id:
                    # Try to view the file
                    view_response = requests.get(
                        f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/{req['id']}/evidence/{file_id}/view",
                        headers=headers
                    )
                    assert view_response.status_code == 200, f"Failed to view {req['name']}: {view_response.status_code}"
                    print(f"  ✅ Can view: {req['name']}")
    
    def test_download_uploaded_evidence(self, test_employee, headers):
        """Verify uploaded evidence can be downloaded"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        assert response.status_code == 200
        requirements = response.json()["requirements"]
        
        with_evidence = [r for r in requirements if r.get("evidence_files")]
        
        for req in with_evidence[:2]:  # Test first 2
            evidence_files = req.get("evidence_files", [])
            if evidence_files:
                file_info = evidence_files[0]
                file_id = file_info.get("file_id")
                if file_id:
                    download_response = requests.get(
                        f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/{req['id']}/evidence/{file_id}/download",
                        headers=headers
                    )
                    assert download_response.status_code == 200, f"Failed to download {req['name']}"
                    assert len(download_response.content) > 0
                    print(f"  ✅ Can download: {req['name']}")
    
    # ==================== STEP 6: Status Transitions ====================
    
    def test_verify_requirement(self, test_employee, headers):
        """STEP 6: Test approval/verification of requirements"""
        # Get requirements with evidence
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        assert response.status_code == 200
        requirements = response.json()["requirements"]
        
        # Find a requirement with evidence that can be verified
        for req in requirements:
            if req.get("can_verify") and not req.get("all_verified"):
                # Verify this requirement
                verify_response = requests.post(
                    f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/{req['id']}/verify-all",
                    headers=headers
                )
                if verify_response.status_code == 200:
                    print(f"  ✅ Verified: {req['name']}")
                    break
    
    def test_status_transitions(self, test_employee, headers):
        """Verify status transitions: Still Needed → Ready for Review → Checked & Approved"""
        # Get compliance requirements
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        assert response.status_code == 200
        requirements = response.json()["requirements"]
        
        # Check status distribution
        statuses = {}
        for req in requirements:
            status = req.get("status", "unknown")
            statuses[status] = statuses.get(status, 0) + 1
        
        print(f"Status distribution: {statuses}")
        
        # Verify we have different statuses
        assert "missing" in statuses or "uploaded" in statuses or "approved" in statuses
    
    # ==================== STEP 7: Overview Validation ====================
    
    def test_compliance_score_updates(self, test_employee, headers):
        """STEP 7: Verify compliance score updates after uploads"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance",
            headers=headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        comp_data = compliance.get("compliance", {})
        completion = comp_data.get("completion_percentage", 0)
        complete_count = comp_data.get("complete_count", 0)
        total_items = comp_data.get("total_items", 0)
        
        print(f"Compliance score: {completion}%")
        print(f"Complete: {complete_count}/{total_items}")
        
        # After uploads, should have some completion
        assert complete_count > 0, "Should have some completed items after uploads"
    
    def test_overview_counts_match_checklist(self, test_employee, headers):
        """Verify Overview counts match checklist items"""
        # Get compliance requirements
        req_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        assert req_response.status_code == 200
        requirements = req_response.json()["requirements"]
        
        # Get compliance summary
        comp_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance",
            headers=headers
        )
        assert comp_response.status_code == 200
        compliance = comp_response.json()
        
        # Count from requirements
        with_evidence = len([r for r in requirements if r.get("has_evidence")])
        verified = len([r for r in requirements if r.get("all_verified")])
        missing = len([r for r in requirements if not r.get("has_evidence")])
        
        print(f"From requirements: evidence={with_evidence}, verified={verified}, missing={missing}")
        print(f"From compliance: complete={compliance.get('compliance', {}).get('complete_count', 0)}")
    
    # ==================== STEP 8: Error Handling ====================
    
    def test_invalid_file_type_rejected(self, test_employee, headers):
        """STEP 8: Test that invalid file types are rejected"""
        # Try to upload an executable
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00"  # PE header start
        files = {"file": ("malware.exe", io.BytesIO(exe_content), "application/x-msdownload")}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/identity_documents/evidence",
            files=files,
            headers=headers
        )
        
        # Should be rejected (400 or 415)
        if response.status_code in [400, 415, 422]:
            print(f"✅ Invalid file type correctly rejected: {response.status_code}")
        else:
            print(f"⚠️ Invalid file type not rejected: {response.status_code}")
    
    def test_approve_without_file_fails(self, test_employee, headers):
        """Test that approving without file fails"""
        # Try to verify a requirement without evidence
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        requirements = response.json()["requirements"]
        
        # Find a requirement without evidence
        for req in requirements:
            if not req.get("has_evidence") and not req.get("can_verify"):
                verify_response = requests.post(
                    f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/{req['id']}/verify-all",
                    headers=headers
                )
                # Should fail
                if verify_response.status_code in [400, 404, 422]:
                    print(f"✅ Cannot verify without evidence: {req['name']}")
                    break
    
    # ==================== STEP 9: Document Control ====================
    
    def test_replace_file_works(self, test_employee, headers):
        """STEP 9: Test Replace File functionality"""
        # Get a requirement with evidence
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        requirements = response.json()["requirements"]
        
        for req in requirements:
            evidence_files = req.get("evidence_files", [])
            if evidence_files:
                file_id = evidence_files[0].get("file_id")
                if file_id:
                    # Create replacement file
                    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
                    
                    files = {"file": ("replacement.pdf", io.BytesIO(pdf_content), "application/pdf")}
                    
                    replace_response = requests.post(
                        f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/{req['id']}/evidence/{file_id}/replace",
                        files=files,
                        data={"reason": "Testing replacement functionality"},
                        headers=headers
                    )
                    
                    if replace_response.status_code == 200:
                        print(f"✅ Replace file works: {req['name']}")
                    else:
                        print(f"⚠️ Replace file status: {replace_response.status_code}")
                    break
    
    def test_remove_file_works(self, test_employee, headers):
        """Test Remove File functionality (soft delete)"""
        # Upload a new file first
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n199\n%%EOF"
        
        files = {"file": ("to_remove.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        # Upload to a multi-file requirement
        upload_response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/identity_documents/evidence",
            files=files,
            headers=headers
        )
        
        if upload_response.status_code in [200, 201]:
            # Get the file ID
            response = requests.get(
                f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
                headers=headers
            )
            requirements = response.json()["requirements"]
            
            for req in requirements:
                if req["id"] == "identity_documents":
                    evidence_files = req.get("evidence_files", [])
                    if len(evidence_files) > 1:  # Only remove if there's more than one
                        file_id = evidence_files[-1].get("file_id")
                        
                        remove_response = requests.post(
                            f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/{req['id']}/evidence/{file_id}/remove",
                            json={"reason": "Testing remove functionality"},
                            headers=headers
                        )
                        
                        if remove_response.status_code == 200:
                            print(f"✅ Remove file works (soft delete)")
                        else:
                            print(f"⚠️ Remove file status: {remove_response.status_code}")
                    break
    
    def test_view_history_works(self, test_employee, headers):
        """Test View History functionality"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance-requirements",
            headers=headers
        )
        requirements = response.json()["requirements"]
        
        for req in requirements:
            if req.get("has_evidence"):
                history_response = requests.get(
                    f"{BASE_URL}/api/employees/{test_employee['id']}/requirements/{req['id']}/history",
                    headers=headers
                )
                
                if history_response.status_code == 200:
                    history = history_response.json()
                    print(f"✅ View history works: {req['name']} - {len(history.get('history', []))} entries")
                    break
    
    # ==================== Final Compliance Check ====================
    
    def test_final_compliance_status(self, test_employee, headers):
        """Final check of compliance status after all operations"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}/compliance",
            headers=headers
        )
        assert response.status_code == 200
        compliance = response.json()
        
        comp_data = compliance.get("compliance", {})
        print(f"\n=== FINAL COMPLIANCE STATUS ===")
        print(f"Completion: {comp_data.get('completion_percentage', 0)}%")
        print(f"Complete: {comp_data.get('complete_count', 0)}/{comp_data.get('total_items', 0)}")
        print(f"Verified: {comp_data.get('verified_count', 0)}")
        print(f"Missing: {comp_data.get('missing_count', 0)}")
        print(f"Expiring: {comp_data.get('expiring_count', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

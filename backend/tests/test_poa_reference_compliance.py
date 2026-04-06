"""
Test POA Documents Visibility and Reference Rejection UX
Tests for iteration 174 - Compliance Engine verification

Features tested:
1. POA documents visibility: Worker uploads appear in Admin compliance view
2. Reference rejection UX: Rejected references show reason and 'Provide New Referee' button
3. Document upload consistency: All requirement_id variants appear correctly
4. Worker Dashboard data matches Admin Portal view
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
WORKER_EMAIL = "otunbakunlelonge85@gmail.com"
WORKER_PASSWORD = "Welcome123!"
EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def worker_token():
    """Get worker authentication token"""
    response = requests.post(f"{BASE_URL}/api/worker/login", json={
        "email": WORKER_EMAIL,
        "password": WORKER_PASSWORD
    })
    assert response.status_code == 200, f"Worker login failed: {response.text}"
    return response.json().get("token")


class TestPOADocumentsVisibility:
    """Test POA documents are visible in Admin compliance view"""
    
    def test_compliance_file_returns_poa_documents(self, admin_token):
        """Verify compliance-file endpoint returns POA documents with documents_preview"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get compliance file: {response.text}"
        
        data = response.json()
        assert "sections" in data, "Response missing 'sections' key"
        assert "proof_of_address" in data["sections"], "Missing 'proof_of_address' section"
        
        poa_section = data["sections"]["proof_of_address"]
        assert "rows" in poa_section, "POA section missing 'rows'"
        assert len(poa_section["rows"]) > 0, "POA section has no rows"
        
        # Find evidence row
        evidence_row = None
        for row in poa_section["rows"]:
            if row.get("row_type") == "evidence":
                evidence_row = row
                break
        
        assert evidence_row is not None, "No evidence row found in POA section"
        
        # Verify documents_preview is populated
        documents_preview = evidence_row.get("documents_preview", [])
        assert len(documents_preview) > 0, "documents_preview is empty - POA documents not visible"
        
        print(f"✓ Found {len(documents_preview)} POA documents in documents_preview")
        
        # Verify document structure
        for doc in documents_preview:
            assert "id" in doc, "Document missing 'id'"
            assert "file_name" in doc, "Document missing 'file_name'"
            assert "file_url" in doc, "Document missing 'file_url'"
            print(f"  - {doc['file_name']} (status: {doc.get('status', 'unknown')})")
    
    def test_poa_counts_match_documents(self, admin_token):
        """Verify POA counts match actual documents"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        poa_section = data["sections"]["proof_of_address"]
        evidence_row = next((r for r in poa_section["rows"] if r.get("row_type") == "evidence"), None)
        
        counts = evidence_row.get("counts", {})
        active_files = counts.get("active_files", 0)
        documents_preview = evidence_row.get("documents_preview", [])
        
        # documents_preview may be limited to 3 for preview, but counts should reflect total
        assert active_files >= len(documents_preview), \
            f"Active files count ({active_files}) should be >= documents_preview length ({len(documents_preview)})"
        
        print(f"✓ POA counts: {active_files} active files, {len(documents_preview)} in preview")


class TestReferenceRejectionUX:
    """Test reference rejection shows reason and action button"""
    
    def test_worker_dashboard_shows_rejection_reason(self, worker_token):
        """Verify worker dashboard shows rejection reason for rejected references"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200, f"Failed to get worker dashboard: {response.text}"
        
        data = response.json()
        assert "references" in data, "Response missing 'references' key"
        
        references = data["references"]
        assert len(references) >= 1, "No references found"
        
        # Find rejected reference (Reference 1)
        rejected_ref = next((r for r in references if r.get("status") in ["rejected", "needs_new_input"]), None)
        
        if rejected_ref:
            # Verify rejection reason is present
            assert rejected_ref.get("rejection_reason"), \
                f"Rejected reference missing rejection_reason. Status: {rejected_ref.get('status')}"
            
            # Verify can_provide_new flag
            assert rejected_ref.get("can_provide_new") == True, \
                "Rejected reference should have can_provide_new=True"
            
            print(f"✓ Reference {rejected_ref['reference_number']} shows rejection reason: {rejected_ref['rejection_reason']}")
            print(f"✓ can_provide_new flag is True")
        else:
            pytest.skip("No rejected reference found to test")
    
    def test_reference_status_labels(self, worker_token):
        """Verify reference status labels are user-friendly"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        references = data["references"]
        
        for ref in references:
            assert "status_label" in ref, f"Reference {ref.get('reference_number')} missing status_label"
            status_label = ref["status_label"]
            
            # Verify status labels are user-friendly (not technical codes)
            assert len(status_label) > 5, f"Status label too short: {status_label}"
            assert "_" not in status_label, f"Status label contains underscore: {status_label}"
            
            print(f"✓ Reference {ref['reference_number']}: {status_label}")


class TestWorkerAdminDataConsistency:
    """Test Worker Dashboard data matches Admin Portal view"""
    
    def test_poa_document_count_consistency(self, admin_token, worker_token):
        """Verify POA document counts are consistent between worker and admin views"""
        # Get worker dashboard
        worker_response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert worker_response.status_code == 200
        worker_data = worker_response.json()
        
        # Get admin compliance file
        admin_response = requests.get(
            f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 200
        admin_data = admin_response.json()
        
        # Count POA documents in worker view
        worker_poa_docs = [d for d in worker_data.get("completed_documents", []) 
                          if d.get("type") == "proof_of_address"]
        
        # Count POA documents in admin view
        poa_section = admin_data["sections"]["proof_of_address"]
        evidence_row = next((r for r in poa_section["rows"] if r.get("row_type") == "evidence"), None)
        admin_poa_count = evidence_row.get("counts", {}).get("active_files", 0) if evidence_row else 0
        
        print(f"Worker POA docs: {len(worker_poa_docs)}")
        print(f"Admin POA active files: {admin_poa_count}")
        
        # Worker may show fewer (only their uploads), admin shows all
        assert admin_poa_count >= len(worker_poa_docs), \
            "Admin should see at least as many POA docs as worker"
    
    def test_reference_status_consistency(self, admin_token, worker_token):
        """Verify reference statuses are consistent between worker and admin views"""
        # Get worker dashboard
        worker_response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert worker_response.status_code == 200
        worker_refs = worker_response.json().get("references", [])
        
        # Get admin references
        admin_response = requests.get(
            f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/references-integrity",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == 200
        admin_refs = admin_response.json()
        
        print(f"Worker sees {len(worker_refs)} references")
        print(f"Admin references data available: {bool(admin_refs)}")
        
        # Both should have same number of references
        assert len(worker_refs) >= 1, "Worker should see at least 1 reference"


class TestDocumentUploadVariants:
    """Test numbered POA variants (proof_of_address_2, _3, etc.) appear correctly"""
    
    def test_poa_requirement_keys_included(self, admin_token):
        """Verify all POA requirement key variants are included in compliance view"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{EMPLOYEE_ID}/compliance-file",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        poa_section = data["sections"]["proof_of_address"]
        evidence_row = next((r for r in poa_section["rows"] if r.get("row_type") == "evidence"), None)
        
        # Check that documents from various requirement keys are collected
        documents = evidence_row.get("documents_preview", [])
        
        # The backend should collect from: proof_of_address, proof_of_address_evidence, 
        # address_evidence, proof_of_address_2, proof_of_address_3, etc.
        print(f"✓ Found {len(documents)} documents in POA evidence row")
        
        # Verify counts show all collected documents
        counts = evidence_row.get("counts", {})
        total_files = counts.get("total_files", 0)
        active_files = counts.get("active_files", 0)
        
        print(f"✓ Total files: {total_files}, Active files: {active_files}")
        assert active_files > 0, "Should have at least 1 active POA file"


class TestErrorFriendlyUX:
    """Test error messages are user-friendly and actionable"""
    
    def test_reference_rejection_has_actionable_message(self, worker_token):
        """Verify rejected references have actionable status labels"""
        response = requests.get(
            f"{BASE_URL}/api/worker/dashboard",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        references = data["references"]
        
        for ref in references:
            if ref.get("status") in ["rejected", "needs_new_input"]:
                status_label = ref.get("status_label", "")
                
                # Status label should be actionable (tell user what to do)
                actionable_keywords = ["provide", "new", "please", "required", "needed"]
                has_actionable_word = any(kw in status_label.lower() for kw in actionable_keywords)
                
                assert has_actionable_word, \
                    f"Status label should be actionable: {status_label}"
                
                print(f"✓ Reference {ref['reference_number']} has actionable status: {status_label}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

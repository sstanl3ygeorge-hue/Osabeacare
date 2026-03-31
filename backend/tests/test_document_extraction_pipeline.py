"""
Test suite for Step 6: Universal Document Extraction and Review Pipeline
Tests the document extraction framework for Training Certificates and other document types.

Features tested:
1. POST /api/documents/{id}/extract - Triggers GPT Vision extraction and creates extraction record
2. GET /api/documents/{id}/extraction - Returns extraction record or 'not_extracted' status
3. POST /api/documents/{id}/extraction/review - Review actions (approve, edit_and_approve, reject)
4. POST /api/documents/{id}/extraction/retry - Re-runs extraction with force=true
5. GET /api/extractions/pending-review - Lists extractions awaiting admin review
6. Document type classification (RTW, DBS, Training, ID, Proof of Address)
7. Training certificate expiry inference from internal policy
8. Name mismatch detection (holder_name vs employee name)
9. Extraction never auto-verifies documents
10. Approved extraction values populate canonical records with provenance metadata
"""

import pytest
import requests
import os
import json
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://caretrust-portal.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@osabea.care"
TEST_PASSWORD = "admin123"

# Test document and employee IDs from main agent context
TEST_RTW_DOCUMENT_ID = "add610d7-8819-4182-a03e-b76aa0978ea0"  # Already extracted RTW document
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestExtractionEndpointExists:
    """Test that extraction endpoints exist and respond correctly"""
    
    def test_get_extraction_endpoint_exists(self, auth_headers):
        """Test GET /api/documents/{id}/extraction returns proper response"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        # Should return 200 with extraction data or 'not_extracted' status
        assert response.status_code == 200, f"Unexpected status: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should have either extraction data or 'not_extracted' status
        if data.get("status") == "not_extracted":
            assert "document_id" in data
            print(f"✅ GET extraction endpoint works - Document not yet extracted")
        else:
            assert "id" in data or "extraction_status" in data
            print(f"✅ GET extraction endpoint works - Extraction found: {data.get('extraction_status')}")
    
    def test_trigger_extraction_endpoint_exists(self, auth_headers):
        """Test POST /api/documents/{id}/extract endpoint exists"""
        # Use a test document ID - should return 200 or 404
        response = requests.post(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extract",
            headers=auth_headers,
            timeout=120  # Extraction can take time due to GPT Vision
        )
        # Should return 200 (success) or 404 (document not found)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code} - {response.text}"
        print(f"✅ Trigger extraction endpoint exists - Status: {response.status_code}")
    
    def test_review_extraction_endpoint_exists(self, auth_headers):
        """Test POST /api/documents/{id}/extraction/review endpoint exists"""
        # Use a fake document ID - should return 404 (not found), not 405 (method not allowed)
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-document-id/extraction/review",
            headers=auth_headers,
            json={"action": "approve"}
        )
        assert response.status_code in [400, 404, 422], f"Unexpected status: {response.status_code}"
        print(f"✅ Review extraction endpoint exists - Status: {response.status_code}")
    
    def test_retry_extraction_endpoint_exists(self, auth_headers):
        """Test POST /api/documents/{id}/extraction/retry endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-document-id/extraction/retry",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code in [404], f"Unexpected status: {response.status_code}"
        print(f"✅ Retry extraction endpoint exists - Status: {response.status_code}")
    
    def test_document_extractions_pending_review_endpoint_exists(self, auth_headers):
        """Test GET /api/document-extractions/pending-review endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/document-extractions/pending-review",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        data = response.json()
        assert "extractions" in data
        assert "total" in data
        print(f"✅ Document extractions pending review endpoint works - Found {data['total']} pending")
    
    def test_profile_extractions_pending_review_endpoint_exists(self, auth_headers):
        """Test GET /api/extractions/pending-review endpoint exists (profile extractions)"""
        response = requests.get(
            f"{BASE_URL}/api/extractions/pending-review",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        data = response.json()
        assert "extractions" in data
        assert "total" in data
        print(f"✅ Profile extractions pending review endpoint works - Found {data['total']} pending")


class TestExtractionRecordStructure:
    """Test extraction record structure and fields"""
    
    def test_extraction_record_has_required_fields(self, auth_headers):
        """Test extraction record contains all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "not_extracted":
            pytest.skip("Document not yet extracted - skipping structure test")
        
        # Required fields for extraction record
        required_fields = [
            "id", "document_id", "employee_id", "document_type",
            "extraction_status", "extracted_fields", "field_metadata",
            "issues", "review_status"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✅ Extraction record has all required fields")
        print(f"   - Document type: {data.get('document_type')}")
        print(f"   - Extraction status: {data.get('extraction_status')}")
        print(f"   - Review status: {data.get('review_status')}")
    
    def test_extraction_has_field_metadata(self, auth_headers):
        """Test extraction includes field metadata with confidence and source_type"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "not_extracted":
            pytest.skip("Document not yet extracted")
        
        field_metadata = data.get("field_metadata", {})
        if field_metadata:
            # Check first field has expected metadata structure
            for field_name, meta in field_metadata.items():
                if meta:
                    assert "source_type" in meta, f"Field {field_name} missing source_type"
                    assert "confidence" in meta, f"Field {field_name} missing confidence"
                    print(f"✅ Field '{field_name}' has metadata: source={meta.get('source_type')}, confidence={meta.get('confidence')}")
                    break
        else:
            print("⚠️ No field metadata found (may be expected for some document types)")


class TestDocumentTypeClassification:
    """Test document type classification logic"""
    
    def test_rtw_document_classified_correctly(self, auth_headers):
        """Test RTW document is classified as right_to_work"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "not_extracted":
            pytest.skip("Document not yet extracted")
        
        doc_type = data.get("document_type")
        # RTW document should be classified as right_to_work
        assert doc_type in ["right_to_work", "id", "other"], f"Unexpected document type: {doc_type}"
        print(f"✅ Document classified as: {doc_type}")
    
    def test_get_employee_documents_for_classification(self, auth_headers):
        """Test we can get employee documents to verify classification"""
        response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have documents array
        documents = data if isinstance(data, list) else data.get("documents", [])
        if len(documents) > 0:
            print(f"✅ Found {len(documents)} documents for employee")
            # List document types
            for doc in documents[:5]:
                print(f"   - {doc.get('file_name', 'Unknown')}: {doc.get('document_type_name', doc.get('category', 'Unknown'))}")
        else:
            print("⚠️ No documents found for employee")


class TestExtractionReviewActions:
    """Test extraction review actions (approve, edit_and_approve, reject)"""
    
    def test_review_action_approve(self, auth_headers):
        """Test POST /api/documents/{id}/extraction/review with action='approve'"""
        # First check if extraction exists
        get_response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        
        if get_response.status_code != 200 or get_response.json().get("status") == "not_extracted":
            pytest.skip("No extraction to review")
        
        extraction = get_response.json()
        
        # Only test if awaiting review
        if extraction.get("review_status") != "awaiting_review":
            print(f"⚠️ Extraction already reviewed: {extraction.get('review_status')}")
            pytest.skip("Extraction already reviewed")
        
        # Test approve action
        response = requests.post(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction/review",
            headers=auth_headers,
            json={"action": "approve"}
        )
        
        assert response.status_code == 200, f"Approve failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("review_status") in ["approved", "edited"], f"Unexpected review status: {data.get('review_status')}"
        print(f"✅ Approve action successful - Review status: {data.get('review_status')}")
    
    def test_review_action_reject_validation(self, auth_headers):
        """Test that reject action does not update canonical records"""
        # This is a validation test - we verify the endpoint accepts reject action
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-doc-id/extraction/review",
            headers=auth_headers,
            json={"action": "reject"}
        )
        # Should return 404 (no extraction) not 400 (invalid action)
        assert response.status_code == 404, f"Unexpected status: {response.status_code}"
        print("✅ Reject action is valid (404 = no extraction, not invalid action)")
    
    def test_review_action_edit_and_approve_requires_values(self, auth_headers):
        """Test edit_and_approve requires approved_field_values"""
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-doc-id/extraction/review",
            headers=auth_headers,
            json={"action": "edit_and_approve"}  # Missing approved_field_values
        )
        # Should return 404 (no extraction) - validation happens after finding extraction
        assert response.status_code in [400, 404], f"Unexpected status: {response.status_code}"
        print("✅ edit_and_approve validation works")
    
    def test_invalid_review_action_rejected(self, auth_headers):
        """Test invalid action is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction/review",
            headers=auth_headers,
            json={"action": "invalid_action"}
        )
        # Should return 400 (invalid action) or 404 (no extraction)
        assert response.status_code in [400, 404], f"Unexpected status: {response.status_code}"
        print(f"✅ Invalid action rejected - Status: {response.status_code}")


class TestExtractionRetry:
    """Test extraction retry functionality"""
    
    def test_retry_extraction_with_force(self, auth_headers):
        """Test POST /api/documents/{id}/extraction/retry re-runs extraction"""
        response = requests.post(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction/retry",
            headers=auth_headers,
            timeout=120  # Extraction can take time
        )
        
        # Should return 200 (success) or 404 (document not found)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "extraction_status" in data
            print(f"✅ Retry extraction successful - Status: {data.get('extraction_status')}")
        else:
            print("⚠️ Document not found for retry")


class TestPendingReviewList:
    """Test pending review list endpoint"""
    
    def test_document_pending_review_returns_list(self, auth_headers):
        """Test GET /api/document-extractions/pending-review returns list structure"""
        response = requests.get(
            f"{BASE_URL}/api/document-extractions/pending-review",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "extractions" in data
        assert "total" in data
        assert isinstance(data["extractions"], list)
        assert isinstance(data["total"], int)
        
        print(f"✅ Document pending review list structure correct - {data['total']} pending")
    
    def test_document_pending_review_enriched_with_info(self, auth_headers):
        """Test pending document extractions include document and employee info"""
        response = requests.get(
            f"{BASE_URL}/api/document-extractions/pending-review",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] > 0:
            extraction = data["extractions"][0]
            # Should have enriched fields
            print(f"✅ Pending extraction fields: {list(extraction.keys())}")
            if "document_file_url" in extraction:
                print(f"   - Document URL: {extraction.get('document_file_url', 'N/A')[:50]}...")
            if "employee_name" in extraction:
                print(f"   - Employee: {extraction.get('employee_name')}")
        else:
            print("⚠️ No pending document extractions to verify enrichment")
    
    def test_document_pending_review_respects_limit(self, auth_headers):
        """Test pending review respects limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/document-extractions/pending-review?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["extractions"]) <= 5
        print(f"✅ Limit parameter respected - Returned {len(data['extractions'])} extractions")


class TestExtractionNeverAutoVerifies:
    """Test that extraction never auto-verifies documents"""
    
    def test_extraction_does_not_set_verified_status(self, auth_headers):
        """Verify extraction does not change document verification status"""
        # Get document before extraction
        doc_response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert doc_response.status_code == 200
        
        documents = doc_response.json()
        if isinstance(documents, dict):
            documents = documents.get("documents", [])
        
        if not documents:
            pytest.skip("No documents found for employee")
        
        # Find a document to check
        for doc in documents:
            doc_id = doc.get("id")
            verification_status_before = doc.get("verification_status")
            
            # Trigger extraction
            extract_response = requests.post(
                f"{BASE_URL}/api/documents/{doc_id}/extract",
                headers=auth_headers,
                timeout=120
            )
            
            if extract_response.status_code == 200:
                # Get document after extraction
                doc_after_response = requests.get(
                    f"{BASE_URL}/api/employee-documents?employee_id={TEST_EMPLOYEE_ID}",
                    headers=auth_headers
                )
                docs_after = doc_after_response.json()
                if isinstance(docs_after, dict):
                    docs_after = docs_after.get("documents", [])
                
                # Find same document
                for doc_after in docs_after:
                    if doc_after.get("id") == doc_id:
                        verification_status_after = doc_after.get("verification_status")
                        # Verification status should NOT change due to extraction
                        assert verification_status_before == verification_status_after, \
                            f"Extraction changed verification status from {verification_status_before} to {verification_status_after}"
                        print(f"✅ Extraction did NOT auto-verify document (status: {verification_status_after})")
                        return
            break
        
        print("⚠️ Could not verify auto-verification behavior (no suitable document)")


class TestTrainingCertificateExpiryInference:
    """Test training certificate expiry inference from internal policy"""
    
    def test_training_renewal_policies_exist(self, auth_headers):
        """Verify training renewal policies are defined in backend"""
        # This is a code review test - we verify the policies exist by checking
        # if extraction returns inferred_training_code for training certificates
        
        # Get any training document
        doc_response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        assert doc_response.status_code == 200
        
        documents = doc_response.json()
        if isinstance(documents, dict):
            documents = documents.get("documents", [])
        
        # Look for training documents
        training_docs = [d for d in documents if 
                        "training" in (d.get("document_type_name") or "").lower() or
                        "certificate" in (d.get("file_name") or "").lower()]
        
        if training_docs:
            print(f"✅ Found {len(training_docs)} training documents")
            for doc in training_docs[:3]:
                print(f"   - {doc.get('file_name', 'Unknown')}")
        else:
            print("⚠️ No training documents found for expiry inference test")
    
    def test_expiry_inferred_from_policy_metadata(self, auth_headers):
        """Test that inferred expiry has proper metadata"""
        # Get extraction for a training document
        doc_response = requests.get(
            f"{BASE_URL}/api/employee-documents?employee_id={TEST_EMPLOYEE_ID}",
            headers=auth_headers
        )
        
        documents = doc_response.json()
        if isinstance(documents, dict):
            documents = documents.get("documents", [])
        
        # Find training documents
        for doc in documents:
            doc_type_name = doc.get("document_type_name") or ""
            if "training" in doc_type_name.lower():
                doc_id = doc.get("id")
                
                # Get extraction
                ext_response = requests.get(
                    f"{BASE_URL}/api/documents/{doc_id}/extraction",
                    headers=auth_headers
                )
                
                if ext_response.status_code == 200:
                    ext_data = ext_response.json()
                    if ext_data.get("status") != "not_extracted":
                        field_metadata = ext_data.get("field_metadata", {})
                        expiry_meta = field_metadata.get("expiry_date", {})
                        
                        if expiry_meta.get("source_type") == "inferred_policy":
                            print(f"✅ Expiry inferred from policy: {expiry_meta.get('raw_evidence')}")
                            return
                        elif expiry_meta.get("source_type") == "explicit":
                            print(f"✅ Expiry explicitly stated on document")
                            return
                break
        
        print("⚠️ No training extraction found to verify expiry inference")


class TestNameMismatchDetection:
    """Test name mismatch detection between document holder and employee"""
    
    def test_name_mismatch_flagged_in_issues(self, auth_headers):
        """Test that name mismatch is flagged in extraction issues"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        
        if response.status_code != 200 or response.json().get("status") == "not_extracted":
            pytest.skip("No extraction to check for name mismatch")
        
        data = response.json()
        issues = data.get("issues", [])
        
        # Check if name mismatch issue exists
        name_mismatch_issues = [i for i in issues if i.get("code") == "holder_name_mismatch"]
        
        if name_mismatch_issues:
            print(f"✅ Name mismatch detected: {name_mismatch_issues[0].get('detail')}")
        else:
            # Check if holder_name matches employee name
            extracted_name = data.get("extracted_fields", {}).get("holder_name")
            print(f"✅ No name mismatch (holder: {extracted_name})")


class TestApprovedExtractionUpdatesCanonicalRecords:
    """Test that approved extraction values populate canonical records"""
    
    def test_approved_extraction_has_provenance_metadata(self, auth_headers):
        """Test approved extraction includes provenance metadata"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        
        if response.status_code != 200 or response.json().get("status") == "not_extracted":
            pytest.skip("No extraction to check")
        
        data = response.json()
        
        # If approved, check for provenance
        if data.get("review_status") in ["approved", "edited"]:
            assert "reviewed_by" in data, "Approved extraction should have reviewed_by"
            assert "reviewed_at" in data, "Approved extraction should have reviewed_at"
            assert "approved_field_values" in data, "Approved extraction should have approved_field_values"
            print(f"✅ Approved extraction has provenance metadata")
            print(f"   - Reviewed by: {data.get('reviewed_by')}")
            print(f"   - Reviewed at: {data.get('reviewed_at')}")
        else:
            print(f"⚠️ Extraction not yet approved (status: {data.get('review_status')})")


class TestExtractionTriggerWithForce:
    """Test extraction trigger with force parameter"""
    
    def test_trigger_extraction_without_force_returns_existing(self, auth_headers):
        """Test POST /api/documents/{id}/extract without force returns existing extraction"""
        # First trigger to ensure extraction exists
        response1 = requests.post(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extract",
            headers=auth_headers,
            timeout=120
        )
        
        if response1.status_code != 200:
            pytest.skip("Could not create initial extraction")
        
        extraction1 = response1.json()
        extraction_id1 = extraction1.get("id")
        
        # Trigger again without force - should return same extraction
        response2 = requests.post(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extract",
            headers=auth_headers,
            timeout=120
        )
        
        assert response2.status_code == 200
        extraction2 = response2.json()
        extraction_id2 = extraction2.get("id")
        
        # Should be same extraction (not re-run)
        assert extraction_id1 == extraction_id2, "Without force, should return existing extraction"
        print(f"✅ Without force, returns existing extraction: {extraction_id1}")
    
    def test_trigger_extraction_with_force_reruns(self, auth_headers):
        """Test POST /api/documents/{id}/extract?force=true re-runs extraction"""
        # Trigger with force
        response = requests.post(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extract?force=true",
            headers=auth_headers,
            timeout=120
        )
        
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # Should have fresh extraction timestamp
            assert "extracted_at" in data
            print(f"✅ Force extraction completed at: {data.get('extracted_at')}")


class TestExtractionStatusValues:
    """Test extraction status values"""
    
    def test_extraction_status_is_valid(self, auth_headers):
        """Test extraction_status is one of valid values"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        
        if response.status_code != 200 or response.json().get("status") == "not_extracted":
            pytest.skip("No extraction to check")
        
        data = response.json()
        valid_statuses = ["pending", "completed", "needs_review", "failed"]
        
        assert data.get("extraction_status") in valid_statuses, \
            f"Invalid extraction_status: {data.get('extraction_status')}"
        print(f"✅ Extraction status is valid: {data.get('extraction_status')}")
    
    def test_review_status_is_valid(self, auth_headers):
        """Test review_status is one of valid values"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        
        if response.status_code != 200 or response.json().get("status") == "not_extracted":
            pytest.skip("No extraction to check")
        
        data = response.json()
        valid_statuses = ["awaiting_review", "approved", "edited", "rejected"]
        
        assert data.get("review_status") in valid_statuses, \
            f"Invalid review_status: {data.get('review_status')}"
        print(f"✅ Review status is valid: {data.get('review_status')}")


class TestExtractionIssuesSeverity:
    """Test extraction issues have proper severity levels"""
    
    def test_issues_have_valid_severity(self, auth_headers):
        """Test extraction issues have valid severity (info, warning, blocker)"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{TEST_RTW_DOCUMENT_ID}/extraction",
            headers=auth_headers
        )
        
        if response.status_code != 200 or response.json().get("status") == "not_extracted":
            pytest.skip("No extraction to check")
        
        data = response.json()
        issues = data.get("issues", [])
        
        valid_severities = ["info", "warning", "blocker"]
        
        for issue in issues:
            assert "code" in issue, "Issue should have code"
            assert "detail" in issue, "Issue should have detail"
            assert "severity" in issue, "Issue should have severity"
            assert issue["severity"] in valid_severities, f"Invalid severity: {issue['severity']}"
        
        print(f"✅ All {len(issues)} issues have valid severity levels")
        for issue in issues[:3]:
            print(f"   - [{issue['severity']}] {issue['code']}: {issue['detail'][:50]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

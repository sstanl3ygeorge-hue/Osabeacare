"""
Phase 4: Cross-Document Intelligence - Name Mismatch Detection Tests

Tests for:
- GET /api/employees/{id}/name-mismatches - Name mismatch analysis
- GET /api/compliance/name-mismatches - All employees with mismatches
- POST /api/employees/{id}/name-mismatches/review - Review workflow
- Name comparison algorithm (title removal, normalization, similarity)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee with document extractions
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"
TEST_EMPLOYEE_NAME = "Olakunle Alonge"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@osabea.care", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestNameMismatchAnalysisEndpoint:
    """Tests for GET /api/employees/{id}/name-mismatches endpoint."""
    
    def test_get_name_mismatches_returns_200(self, api_client):
        """Test endpoint returns 200 for valid employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_get_name_mismatches_returns_correct_structure(self, api_client):
        """Test response contains all required fields."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        # Required fields
        assert "employee_id" in data
        assert "employee_name" in data
        assert "has_mismatches" in data
        assert "severity" in data
        assert "documents_analyzed" in data
        assert "name_variants" in data
        assert "comparisons" in data
        assert "recommendations" in data
        
        # Verify employee info
        assert data["employee_id"] == TEST_EMPLOYEE_ID
        assert data["employee_name"] == TEST_EMPLOYEE_NAME
    
    def test_get_name_mismatches_severity_is_valid(self, api_client):
        """Test severity is one of the valid values."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        valid_severities = ["none", "low", "medium", "high", "critical"]
        assert data["severity"] in valid_severities, f"Invalid severity: {data['severity']}"
    
    def test_get_name_mismatches_name_variants_structure(self, api_client):
        """Test name_variants contains correct structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        assert isinstance(data["name_variants"], list)
        if data["name_variants"]:
            variant = data["name_variants"][0]
            assert "name" in variant
            assert "count" in variant
            assert "documents" in variant
            assert "avg_confidence" in variant
    
    def test_get_name_mismatches_comparisons_structure(self, api_client):
        """Test comparisons contain correct structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        assert isinstance(data["comparisons"], list)
        if data["comparisons"]:
            comp = data["comparisons"][0]
            assert "name1" in comp
            assert "name2" in comp
            assert "similarity" in comp
            assert "match_type" in comp
            assert "common_parts" in comp
            assert "different_parts" in comp
    
    def test_get_name_mismatches_registered_name_comparison(self, api_client):
        """Test registered name comparison is included."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        assert "registered_name" in data
        assert "registered_comparison" in data
        
        if data["registered_comparison"]:
            reg_comp = data["registered_comparison"]
            assert "registered_name" in reg_comp
            assert "document_name" in reg_comp
            assert "similarity" in reg_comp
            assert "match_type" in reg_comp
    
    def test_get_name_mismatches_invalid_employee_returns_404(self, api_client):
        """Test endpoint returns 404 for non-existent employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/invalid-employee-id/name-mismatches")
        assert response.status_code == 404


class TestNameComparisonAlgorithm:
    """Tests for name comparison algorithm correctness."""
    
    def test_title_removal_exact_match(self, api_client):
        """
        Test that 'ALONGE OLAKUNLE MOSES' and 'ALONGE MR OLAKUNLE MOSES' 
        are identified as exact match after title normalization.
        """
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        # Find the comparison between the two document names
        comparisons = data.get("comparisons", [])
        
        # Should have at least one comparison
        assert len(comparisons) >= 1, "Expected at least one comparison"
        
        # The comparison should show exact match (title 'MR' removed)
        comp = comparisons[0]
        assert comp["match_type"] == "exact", f"Expected 'exact' match, got '{comp['match_type']}'"
        assert comp["similarity"] == 1.0, f"Expected similarity 1.0, got {comp['similarity']}"
    
    def test_partial_match_with_registered_name(self, api_client):
        """
        Test that registered name 'Olakunle Alonge' is partial match 
        with document name 'ALONGE OLAKUNLE MOSES' (missing 'moses').
        """
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        reg_comp = data.get("registered_comparison")
        assert reg_comp is not None, "Expected registered_comparison"
        
        # Should be partial match (registered name is subset of document name)
        assert reg_comp["match_type"] == "partial", f"Expected 'partial' match, got '{reg_comp['match_type']}'"
        
        # Similarity should be around 0.67 (2/3 parts match)
        assert 0.6 <= reg_comp["similarity"] <= 0.7, f"Expected similarity ~0.67, got {reg_comp['similarity']}"
        
        # Common parts should include 'olakunle' and 'alonge'
        common = [p.lower() for p in reg_comp.get("common_parts", [])]
        assert "olakunle" in common, "Expected 'olakunle' in common parts"
        assert "alonge" in common, "Expected 'alonge' in common parts"
        
        # Different parts should include 'moses'
        different = [p.lower() for p in reg_comp.get("different_parts", [])]
        assert "moses" in different, "Expected 'moses' in different parts"
    
    def test_severity_none_for_exact_matches(self, api_client):
        """
        Test that severity is 'none' when all document names match exactly.
        """
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        # Since the two document names match exactly after title removal,
        # severity should be 'none'
        assert data["severity"] == "none", f"Expected severity 'none', got '{data['severity']}'"
        assert data["has_mismatches"] == False, "Expected has_mismatches to be False"


class TestComplianceNameMismatchesEndpoint:
    """Tests for GET /api/compliance/name-mismatches endpoint."""
    
    def test_get_all_name_mismatches_returns_200(self, api_client):
        """Test endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/compliance/name-mismatches")
        assert response.status_code == 200
    
    def test_get_all_name_mismatches_structure(self, api_client):
        """Test response contains correct structure."""
        response = api_client.get(f"{BASE_URL}/api/compliance/name-mismatches")
        data = response.json()
        
        assert "total" in data
        assert "employees" in data
        assert "severity_counts" in data
        
        # Verify severity_counts structure
        counts = data["severity_counts"]
        assert "critical" in counts
        assert "high" in counts
        assert "medium" in counts
        assert "low" in counts
    
    def test_get_all_name_mismatches_employees_structure(self, api_client):
        """Test employees list contains correct structure if not empty."""
        response = api_client.get(f"{BASE_URL}/api/compliance/name-mismatches")
        data = response.json()
        
        assert isinstance(data["employees"], list)
        
        # If there are employees with mismatches, verify structure
        if data["employees"]:
            emp = data["employees"][0]
            assert "employee_id" in emp
            assert "employee_name" in emp
            assert "severity" in emp
            assert "unique_name_count" in emp
            assert "documents_analyzed" in emp
    
    def test_get_all_name_mismatches_sorted_by_severity(self, api_client):
        """Test employees are sorted by severity (critical first)."""
        response = api_client.get(f"{BASE_URL}/api/compliance/name-mismatches")
        data = response.json()
        
        employees = data["employees"]
        if len(employees) > 1:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(employees) - 1):
                current_order = severity_order.get(employees[i]["severity"], 4)
                next_order = severity_order.get(employees[i + 1]["severity"], 4)
                assert current_order <= next_order, "Employees not sorted by severity"


class TestNameMismatchReviewEndpoint:
    """Tests for POST /api/employees/{id}/name-mismatches/review endpoint."""
    
    def test_review_dismiss_action_returns_200(self, api_client):
        """Test dismiss action returns success."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches/review",
            json={
                "action": "dismiss",
                "reason": "Names match after title normalization - acceptable variation"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "review" in data
        assert data["review"]["action"] == "dismiss"
    
    def test_review_flag_for_investigation_action(self, api_client):
        """Test flag_for_investigation action returns success."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches/review",
            json={
                "action": "flag_for_investigation",
                "reason": "Need to verify identity documents with HR department"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["review"]["action"] == "flag_for_investigation"
    
    def test_review_resolved_action(self, api_client):
        """Test resolved action returns success."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches/review",
            json={
                "action": "resolved",
                "reason": "Investigation complete - names verified as same person",
                "notes": "Verified with original documents"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["review"]["action"] == "resolved"
        assert data["review"]["notes"] == "Verified with original documents"
    
    def test_review_invalid_action_returns_400(self, api_client):
        """Test invalid action returns 400."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches/review",
            json={
                "action": "invalid_action",
                "reason": "This should fail"
            }
        )
        assert response.status_code == 400
    
    def test_review_short_reason_returns_400(self, api_client):
        """Test reason less than 10 characters returns 400."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches/review",
            json={
                "action": "dismiss",
                "reason": "short"  # Less than 10 characters
            }
        )
        assert response.status_code == 400
    
    def test_review_invalid_employee_returns_404(self, api_client):
        """Test review for non-existent employee returns 404."""
        response = api_client.post(
            f"{BASE_URL}/api/employees/invalid-employee-id/name-mismatches/review",
            json={
                "action": "dismiss",
                "reason": "This should fail with 404"
            }
        )
        assert response.status_code == 404


class TestDocumentsAnalyzedCount:
    """Tests for documents analyzed count accuracy."""
    
    def test_documents_analyzed_count(self, api_client):
        """Test that documents_analyzed reflects actual extracted documents."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        # Should have 2 documents analyzed (RTW and ID with holder_name)
        assert data["documents_analyzed"] == 2, f"Expected 2 documents, got {data['documents_analyzed']}"
    
    def test_unique_name_count(self, api_client):
        """Test unique_name_count reflects distinct name variants."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        # Should have 2 unique names (before normalization)
        assert data["unique_name_count"] == 2, f"Expected 2 unique names, got {data['unique_name_count']}"
        
        # Verify name_variants list matches count
        assert len(data["name_variants"]) == data["unique_name_count"]


class TestPrimaryNameSelection:
    """Tests for primary name selection logic."""
    
    def test_primary_name_is_selected(self, api_client):
        """Test that primary_name is selected from variants."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        assert "primary_name" in data
        assert data["primary_name"] is not None
        assert len(data["primary_name"]) > 0
        
        # Primary name should be one of the variants
        variant_names = [v["name"] for v in data["name_variants"]]
        assert data["primary_name"] in variant_names


class TestRecommendationsGeneration:
    """Tests for recommendations based on severity."""
    
    def test_no_recommendations_for_none_severity(self, api_client):
        """Test that no recommendations are generated for severity 'none'."""
        response = api_client.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/name-mismatches")
        data = response.json()
        
        if data["severity"] == "none":
            # Should have no recommendations or empty list
            assert len(data.get("recommendations", [])) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

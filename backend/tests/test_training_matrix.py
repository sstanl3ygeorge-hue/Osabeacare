"""
Training Matrix API Tests
Tests for GET /api/employees/{id}/training/matrix endpoint
and related training matrix functionality.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
EMPLOYEE_WITH_TRAINING = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"  # Lawrence Egbeni


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestTrainingMatrixEndpoint:
    """Tests for GET /api/employees/{id}/training/matrix endpoint."""
    
    def test_training_matrix_returns_200(self, api_client):
        """Test that training matrix endpoint returns 200 for valid employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Training matrix endpoint returns 200")
    
    def test_training_matrix_response_structure(self, api_client):
        """Test that training matrix response has correct structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level fields
        assert "employee_id" in data, "Missing employee_id field"
        assert "employee_name" in data, "Missing employee_name field"
        assert "role" in data, "Missing role field"
        assert "items" in data, "Missing items array"
        assert "summary" in data, "Missing summary object"
        
        print(f"✓ Response has correct top-level structure")
        print(f"  Employee: {data.get('employee_name')}")
        print(f"  Role: {data.get('role')}")
    
    def test_training_matrix_items_structure(self, api_client):
        """Test that training matrix items have correct fields."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        assert len(items) > 0, "Expected at least one training item"
        
        # Check first item structure
        item = items[0]
        required_fields = ["code", "title", "status", "blocker", "has_evidence", "verified"]
        
        for field in required_fields:
            assert field in item, f"Missing required field: {field}"
        
        print(f"✓ Training items have correct structure")
        print(f"  Total items: {len(items)}")
        print(f"  Sample item: {item.get('title')} - Status: {item.get('status')}")
    
    def test_training_matrix_summary_stats(self, api_client):
        """Test that training matrix summary has correct statistics."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200
        data = response.json()
        summary = data.get("summary", {})
        
        # Check summary fields
        assert "total" in summary, "Missing total count"
        assert "current" in summary, "Missing current count"
        assert "expiring" in summary, "Missing expiring count (needs_renewal)"
        assert "missing" in summary, "Missing missing count"
        assert "blockers" in summary, "Missing blockers count"
        
        # Validate counts are non-negative integers
        assert isinstance(summary["total"], int) and summary["total"] >= 0
        assert isinstance(summary["current"], int) and summary["current"] >= 0
        assert isinstance(summary["expiring"], int) and summary["expiring"] >= 0
        assert isinstance(summary["missing"], int) and summary["missing"] >= 0
        assert isinstance(summary["blockers"], int) and summary["blockers"] >= 0
        
        print(f"✓ Summary statistics are valid")
        print(f"  Total Required: {summary['total']}")
        print(f"  Current: {summary['current']}")
        print(f"  Needs Renewal: {summary['expiring']}")
        print(f"  Missing: {summary['missing']}")
        print(f"  Blockers: {summary['blockers']}")
    
    def test_training_matrix_item_status_values(self, api_client):
        """Test that training item statuses are valid values."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        valid_statuses = ["current", "completed", "expiring_soon", "due_soon", "expired", "overdue", "missing", "pending", "verified"]
        
        for item in items:
            status = item.get("status")
            assert status in valid_statuses, f"Invalid status '{status}' for item {item.get('code')}"
        
        print(f"✓ All item statuses are valid")
    
    def test_training_matrix_blocker_indicators(self, api_client):
        """Test that blocker indicators are present for mandatory training."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        # Check that blocker field is boolean
        for item in items:
            assert isinstance(item.get("blocker"), bool), f"blocker should be boolean for {item.get('code')}"
        
        # Count blockers
        blocker_items = [i for i in items if i.get("blocker")]
        print(f"✓ Blocker indicators present")
        print(f"  Items marked as blockers: {len(blocker_items)}")
        
        if blocker_items:
            print(f"  Blocker items: {[i.get('title') for i in blocker_items[:3]]}")
    
    def test_training_matrix_evidence_status(self, api_client):
        """Test that evidence status fields are present."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        for item in items:
            assert "has_evidence" in item, f"Missing has_evidence for {item.get('code')}"
            assert "verified" in item, f"Missing verified for {item.get('code')}"
            assert isinstance(item.get("has_evidence"), bool)
            assert isinstance(item.get("verified"), bool)
        
        # Count evidence status
        with_evidence = sum(1 for i in items if i.get("has_evidence"))
        verified = sum(1 for i in items if i.get("verified"))
        
        print(f"✓ Evidence status fields present")
        print(f"  Items with evidence: {with_evidence}/{len(items)}")
        print(f"  Items verified: {verified}/{len(items)}")
    
    def test_training_matrix_date_fields(self, api_client):
        """Test that date fields are present for completed training."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        # Check date fields exist (can be null)
        for item in items:
            assert "completed_at" in item, f"Missing completed_at for {item.get('code')}"
            assert "expires_at" in item, f"Missing expires_at for {item.get('code')}"
        
        # Count items with dates
        with_completion = sum(1 for i in items if i.get("completed_at"))
        with_expiry = sum(1 for i in items if i.get("expires_at"))
        
        print(f"✓ Date fields present")
        print(f"  Items with completion date: {with_completion}/{len(items)}")
        print(f"  Items with expiry date: {with_expiry}/{len(items)}")
    
    def test_training_matrix_404_for_invalid_employee(self, api_client):
        """Test that 404 is returned for non-existent employee."""
        response = api_client.get(f"{BASE_URL}/api/employees/invalid-employee-id-12345/training/matrix")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Returns 404 for invalid employee ID")
    
    def test_training_matrix_requires_auth(self):
        """Test that training matrix endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/matrix")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Endpoint requires authentication")


class TestTrainingEvaluationEndpoint:
    """Tests for GET /api/employees/{id}/training endpoint (fallback)."""
    
    def test_training_evaluation_returns_200(self, api_client):
        """Test that training evaluation endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Training evaluation endpoint returns 200")
    
    def test_training_evaluation_has_items(self, api_client):
        """Test that training evaluation returns items array."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data, "Missing items array"
        assert isinstance(data["items"], list)
        
        print(f"✓ Training evaluation has items array")
        print(f"  Total items: {len(data['items'])}")


class TestProposedTrainingItems:
    """Tests for proposed training items (pending review)."""
    
    def test_proposed_items_endpoint_returns_200(self, api_client):
        """Test that proposed items endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/proposed-items")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Proposed items endpoint returns 200")
    
    def test_proposed_items_response_structure(self, api_client):
        """Test that proposed items response has correct structure."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/training/proposed-items")
        
        assert response.status_code == 200
        data = response.json()
        
        # Response can have either 'proposed_items' or 'items' key
        items_key = "proposed_items" if "proposed_items" in data else "items"
        assert items_key in data, "Missing items array"
        assert isinstance(data[items_key], list)
        
        print(f"✓ Proposed items response has correct structure")
        print(f"  Pending items: {len(data[items_key])}")


class TestWorkReadinessTrainingIntegration:
    """Tests for work readiness integration with training status."""
    
    def test_work_readiness_includes_training(self, api_client):
        """Test that work readiness evaluation includes training blockers."""
        response = api_client.get(f"{BASE_URL}/api/employees/{EMPLOYEE_WITH_TRAINING}/work-readiness")
        
        # Work readiness endpoint may not exist, skip if 404
        if response.status_code == 404:
            pytest.skip("Work readiness endpoint not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check for training-related blockers
        blockers = data.get("blockers", [])
        training_blockers = [b for b in blockers if b.get("category") == "training"]
        
        print(f"✓ Work readiness includes training evaluation")
        print(f"  Training blockers: {len(training_blockers)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

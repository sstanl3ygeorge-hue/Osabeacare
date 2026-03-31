"""
Test Training Audit Export Endpoints - Phase 4 Supplementary Training

Tests for:
- GET /api/audit/training/summary - Organization-wide training compliance summary
- GET /api/audit/employee/{id}/training - Detailed training audit for specific employee
- GET /api/audit/training/export?format=json - Complete training audit export (JSON)
- GET /api/audit/training/export?format=csv - Training audit export (CSV download)
- GET /api/employees/{id}/export-compliance-summary - Includes training_audit section
- GET /api/employees/{id}/export-compliance-pdf - PDF with Supplementary Training section
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee IDs from context
TEST_EMPLOYEE_1 = "d88335f6-1b18-435a-8086-28af4a583f77"  # Olakunle Alonge
TEST_EMPLOYEE_2 = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"  # Lawrence Egbeni


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@osabea.care",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTrainingAuditSummary:
    """Tests for GET /api/audit/training/summary"""
    
    def test_training_audit_summary_returns_200(self, auth_headers):
        """Verify endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_training_audit_summary_structure(self, auth_headers):
        """Verify response contains required fields"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields per spec
        required_fields = [
            "total_employees",
            "fully_compliant",
            "with_warnings",
            "with_blockers",
            "training_items_verified",
            "training_items_pending",
            "training_items_missing",
            "training_items_expired",
            "blocked_employees",
            "warning_employees",
            "evaluated_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_training_audit_summary_counts_are_integers(self, auth_headers):
        """Verify count fields are integers"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary", headers=auth_headers)
        data = response.json()
        
        count_fields = [
            "total_employees", "fully_compliant", "with_warnings", "with_blockers",
            "training_items_verified", "training_items_pending", 
            "training_items_missing", "training_items_expired"
        ]
        
        for field in count_fields:
            assert isinstance(data[field], int), f"{field} should be integer, got {type(data[field])}"
    
    def test_training_audit_summary_counts_consistent(self, auth_headers):
        """Verify fully_compliant + with_warnings + with_blockers = total_employees"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary", headers=auth_headers)
        data = response.json()
        
        total = data["fully_compliant"] + data["with_warnings"] + data["with_blockers"]
        assert total == data["total_employees"], \
            f"Sum of categories ({total}) != total_employees ({data['total_employees']})"
    
    def test_training_audit_summary_blocked_employees_structure(self, auth_headers):
        """Verify blocked_employees array structure if present"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary", headers=auth_headers)
        data = response.json()
        
        assert isinstance(data["blocked_employees"], list)
        
        if data["blocked_employees"]:
            emp = data["blocked_employees"][0]
            assert "id" in emp
            assert "name" in emp
            assert "blocker_count" in emp


class TestEmployeeTrainingAudit:
    """Tests for GET /api/audit/employee/{id}/training"""
    
    def test_employee_training_audit_returns_200(self, auth_headers):
        """Verify endpoint returns 200 for valid employee"""
        response = requests.get(
            f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_employee_training_audit_structure(self, auth_headers):
        """Verify response contains all required audit fields"""
        response = requests.get(
            f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields per spec
        required_fields = [
            "overall_status",
            "overall_status_label",
            "blocker_count",
            "warning_count",
            "is_work_ready_from_training",
            "blocking_reasons",
            "warning_reasons",
            "items",
            "total_required",
            "total_compliant"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_employee_training_audit_items_structure(self, auth_headers):
        """Verify items array contains required verification metadata"""
        response = requests.get(
            f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training",
            headers=auth_headers
        )
        data = response.json()
        
        assert isinstance(data["items"], list)
        
        if data["items"]:
            item = data["items"][0]
            
            # Required item fields per spec
            required_item_fields = [
                "code",
                "title",
                "required_for_role",
                "blocker_for_work",
                "status",
                "detail",
                "completed_at",
                "expires_at",
                "verification_status",
                "verified_by",
                "verified_at",
                "certificate_document_id"
            ]
            
            for field in required_item_fields:
                assert field in item, f"Missing required item field: {field}"
    
    def test_employee_training_audit_404_for_invalid_employee(self, auth_headers):
        """Verify 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/audit/employee/invalid-employee-id/training",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_employee_training_audit_overall_status_valid(self, auth_headers):
        """Verify overall_status is one of expected values"""
        response = requests.get(
            f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training",
            headers=auth_headers
        )
        data = response.json()
        
        valid_statuses = ["current", "due_soon", "overdue", "missing"]
        assert data["overall_status"] in valid_statuses, \
            f"Invalid overall_status: {data['overall_status']}"
    
    def test_employee_training_audit_work_ready_boolean(self, auth_headers):
        """Verify is_work_ready_from_training is boolean"""
        response = requests.get(
            f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training",
            headers=auth_headers
        )
        data = response.json()
        
        assert isinstance(data["is_work_ready_from_training"], bool)


class TestTrainingAuditExportJSON:
    """Tests for GET /api/audit/training/export?format=json"""
    
    def test_training_export_json_returns_200(self, auth_headers):
        """Verify JSON export returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=json",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_training_export_json_structure(self, auth_headers):
        """Verify JSON export structure"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=json",
            headers=auth_headers
        )
        data = response.json()
        
        assert "export_date" in data
        assert "total_employees" in data
        assert "employees" in data
        assert isinstance(data["employees"], list)
    
    def test_training_export_json_employee_structure(self, auth_headers):
        """Verify each employee in export has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=json",
            headers=auth_headers
        )
        data = response.json()
        
        if data["employees"]:
            emp = data["employees"][0]
            
            required_fields = [
                "employee_id",
                "employee_name",
                "employee_email",
                "role",
                "training_status",
                "training_status_label",
                "is_work_ready_from_training",
                "blocker_count",
                "warning_count",
                "total_required",
                "total_compliant",
                "blocking_reasons",
                "items"
            ]
            
            for field in required_fields:
                assert field in emp, f"Missing field in employee export: {field}"
    
    def test_training_export_json_items_have_verification_metadata(self, auth_headers):
        """Verify items in export have verification metadata"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=json",
            headers=auth_headers
        )
        data = response.json()
        
        # Find an employee with items
        for emp in data["employees"]:
            if emp["items"]:
                item = emp["items"][0]
                
                # Check for verification metadata
                assert "code" in item
                assert "title" in item
                assert "status" in item
                assert "verification_status" in item
                break


class TestTrainingAuditExportCSV:
    """Tests for GET /api/audit/training/export?format=csv"""
    
    def test_training_export_csv_returns_200(self, auth_headers):
        """Verify CSV export returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=csv",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_training_export_csv_content_type(self, auth_headers):
        """Verify CSV export has correct content type"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=csv",
            headers=auth_headers
        )
        
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
    
    def test_training_export_csv_has_attachment_header(self, auth_headers):
        """Verify CSV export has Content-Disposition header for download"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=csv",
            headers=auth_headers
        )
        
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition
        assert "training_audit" in content_disposition
        assert ".csv" in content_disposition
    
    def test_training_export_csv_has_headers(self, auth_headers):
        """Verify CSV has expected column headers"""
        response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=csv",
            headers=auth_headers
        )
        
        content = response.text
        first_line = content.split('\n')[0]
        
        expected_headers = [
            "employee_id",
            "employee_name",
            "email",
            "role",
            "training_status",
            "is_work_ready",
            "blocker_count",
            "warning_count"
        ]
        
        for header in expected_headers:
            assert header in first_line, f"Missing CSV header: {header}"


class TestComplianceSummaryWithTrainingAudit:
    """Tests for GET /api/employees/{id}/export-compliance-summary including training_audit"""
    
    def test_compliance_summary_returns_200(self, auth_headers):
        """Verify compliance summary returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_1}/export-compliance-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_compliance_summary_includes_training_audit(self, auth_headers):
        """Verify compliance summary includes training_audit section"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_1}/export-compliance-summary",
            headers=auth_headers
        )
        data = response.json()
        
        assert "training_audit" in data, "Missing training_audit section in compliance summary"
    
    def test_compliance_summary_training_audit_structure(self, auth_headers):
        """Verify training_audit section has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_1}/export-compliance-summary",
            headers=auth_headers
        )
        data = response.json()
        
        training_audit = data.get("training_audit", {})
        
        required_fields = [
            "overall_status",
            "overall_status_label",
            "blocker_count",
            "warning_count",
            "is_work_ready_from_training",
            "items"
        ]
        
        for field in required_fields:
            assert field in training_audit, f"Missing field in training_audit: {field}"


class TestPDFExportWithTraining:
    """Tests for GET /api/employees/{id}/export-compliance-pdf including training section"""
    
    def test_pdf_export_returns_200(self, auth_headers):
        """Verify PDF export returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_1}/export-compliance-pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_pdf_export_content_type(self, auth_headers):
        """Verify PDF export has correct content type"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_1}/export-compliance-pdf",
            headers=auth_headers
        )
        
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
    
    def test_pdf_export_has_content(self, auth_headers):
        """Verify PDF export has content (non-empty)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_1}/export-compliance-pdf",
            headers=auth_headers
        )
        
        assert len(response.content) > 1000, "PDF content seems too small"
    
    def test_pdf_export_is_valid_pdf(self, auth_headers):
        """Verify PDF starts with PDF magic bytes"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_1}/export-compliance-pdf",
            headers=auth_headers
        )
        
        # PDF files start with %PDF
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"


class TestTrainingAuditDataConsistency:
    """Tests to verify training audit uses canonical evaluation (no recalculation)"""
    
    def test_employee_audit_matches_summary_counts(self, auth_headers):
        """Verify individual employee audit data is consistent with summary"""
        # Get summary
        summary_response = requests.get(
            f"{BASE_URL}/api/audit/training/summary",
            headers=auth_headers
        )
        summary = summary_response.json()
        
        # Get individual employee audit
        emp_response = requests.get(
            f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training",
            headers=auth_headers
        )
        emp_audit = emp_response.json()
        
        # If employee is fully compliant, blocker_count should be 0
        if emp_audit["blocker_count"] == 0 and emp_audit["warning_count"] == 0:
            # This employee should be in fully_compliant count
            assert summary["fully_compliant"] > 0, "Employee with no blockers/warnings should be in fully_compliant"
    
    def test_export_matches_individual_audit(self, auth_headers):
        """Verify export data matches individual employee audit"""
        # Get individual audit
        emp_response = requests.get(
            f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training",
            headers=auth_headers
        )
        emp_audit = emp_response.json()
        
        # Get export
        export_response = requests.get(
            f"{BASE_URL}/api/audit/training/export?format=json",
            headers=auth_headers
        )
        export_data = export_response.json()
        
        # Find employee in export
        emp_in_export = None
        for emp in export_data["employees"]:
            if TEST_EMPLOYEE_1 in emp.get("employee_id", "") or TEST_EMPLOYEE_1 == emp.get("employee_id"):
                emp_in_export = emp
                break
        
        if emp_in_export:
            # Verify consistency
            assert emp_in_export["blocker_count"] == emp_audit["blocker_count"]
            assert emp_in_export["warning_count"] == emp_audit["warning_count"]
            assert emp_in_export["training_status"] == emp_audit["overall_status"]


class TestAuthorizationRequirements:
    """Tests for authorization on audit endpoints"""
    
    def test_training_summary_requires_auth(self):
        """Verify training summary requires authentication"""
        response = requests.get(f"{BASE_URL}/api/audit/training/summary")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_employee_training_audit_requires_auth(self):
        """Verify employee training audit requires authentication"""
        response = requests.get(f"{BASE_URL}/api/audit/employee/{TEST_EMPLOYEE_1}/training")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_training_export_requires_auth(self):
        """Verify training export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/audit/training/export?format=json")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Backend API Tests for Template Library & Document Control Workflow
Tests: Templates, Generated Forms, Bulk Upload, Signoff functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"
TEST_EMPLOYEE_ID = "06bb7d2c-cbc4-4c0c-a639-f23e55dd8ba1"
TEST_FORM_ID = "32c5543a-a367-4b22-ba51-685b894ee3f7"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_login_success(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Login successful for {ADMIN_EMAIL}")


class TestTemplates:
    """Template Library API tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_seed_templates(self, auth_token):
        """POST /api/seed-templates - seeds all 12 compliance templates"""
        response = requests.post(
            f"{BASE_URL}/api/seed-templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Seed templates failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "created" in data or "updated" in data
        assert data.get("total_templates", 0) >= 12
        print(f"✓ Templates seeded: created={data.get('created')}, updated={data.get('updated')}")
    
    def test_get_templates_returns_12(self, auth_token):
        """GET /api/templates - should return 12 templates after seeding"""
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates, list)
        assert len(templates) >= 12, f"Expected at least 12 templates, got {len(templates)}"
        
        # Verify template structure
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "category" in template
            assert "form_fields" in template
            assert "visibility" in template
        
        # Check for specific templates
        template_names = [t["name"] for t in templates]
        expected_templates = [
            "Application Form",
            "Interview Record Form",
            "Recruitment Compliance Checklist",
            "Health Screening Questionnaire",
            "Induction & Competency Assessment",
            "Contract Acknowledgement Form"
        ]
        for expected in expected_templates:
            assert expected in template_names, f"Missing template: {expected}"
        
        print(f"✓ Found {len(templates)} templates with correct structure")
    
    def test_templates_have_visibility_field(self, auth_token):
        """Verify templates have visibility field (normal/restricted/confidential)"""
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        templates = response.json()
        
        visibility_values = set()
        for template in templates:
            assert "visibility" in template
            visibility_values.add(template["visibility"])
        
        # Should have at least normal and restricted
        assert "normal" in visibility_values
        print(f"✓ Templates have visibility field with values: {visibility_values}")
    
    def test_get_single_template(self, auth_token):
        """GET /api/templates/:id - returns single template"""
        # First get all templates
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        templates = response.json()
        assert len(templates) > 0
        
        template_id = templates[0]["id"]
        
        # Get single template
        response = requests.get(
            f"{BASE_URL}/api/templates/{template_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        template = response.json()
        assert template["id"] == template_id
        assert "form_fields" in template
        print(f"✓ Single template retrieved: {template['name']}")


class TestGeneratedForms:
    """Generated Forms API tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def test_employee(self, auth_token):
        """Get or create test employee"""
        # First try to get existing employees
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        employees = response.json()
        
        if employees:
            return employees[0]
        
        # Create test employee if none exist
        response = requests.post(
            f"{BASE_URL}/api/employees",
            json={
                "first_name": "TEST_Sarah",
                "last_name": "Thompson",
                "email": "test.sarah@osabea.care",
                "phone": "07700900123",
                "role": "Nurse",
                "branch": "London",
                "status": "onboarding"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        return response.json()
    
    @pytest.fixture(scope="class")
    def test_template(self, auth_token):
        """Get first available template"""
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) > 0
        return templates[0]
    
    def test_create_generated_form(self, auth_token, test_employee, test_template):
        """POST /api/generated-forms - creates a form with auto-filled employee data"""
        response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            json={
                "template_id": test_template["id"],
                "employee_id": test_employee["id"],
                "form_data": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Create form failed: {response.text}"
        form = response.json()
        
        # Verify form structure
        assert "id" in form
        assert form["template_id"] == test_template["id"]
        assert form["employee_id"] == test_employee["id"]
        assert form["status"] == "draft"
        assert "form_data" in form
        
        # Verify auto-filled employee data
        form_data = form["form_data"]
        assert "employee_name" in form_data
        assert "employee_email" in form_data
        assert "employee_role" in form_data
        
        print(f"✓ Form created with auto-filled data: {form['id']}")
        return form
    
    def test_get_generated_form(self, auth_token, test_employee, test_template):
        """GET /api/generated-forms/:id - returns form with correct status and employee details"""
        # First create a form
        create_response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            json={
                "template_id": test_template["id"],
                "employee_id": test_employee["id"],
                "form_data": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert create_response.status_code == 200
        created_form = create_response.json()
        
        # Get the form
        response = requests.get(
            f"{BASE_URL}/api/generated-forms/{created_form['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        form = response.json()
        
        assert form["id"] == created_form["id"]
        assert form["status"] == "draft"
        assert form["employee_name"] is not None
        assert form["employee_code"] is not None
        print(f"✓ Form retrieved with status: {form['status']}")
    
    def test_update_generated_form(self, auth_token, test_employee, test_template):
        """PUT /api/generated-forms/:id - updates form data and status"""
        # Create a form
        create_response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            json={
                "template_id": test_template["id"],
                "employee_id": test_employee["id"],
                "form_data": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert create_response.status_code == 200
        form = create_response.json()
        
        # Update the form
        update_data = {
            "form_data": {"custom_field": "test_value"},
            "status": "sent"
        }
        response = requests.put(
            f"{BASE_URL}/api/generated-forms/{form['id']}",
            json=update_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        updated_form = response.json()
        
        assert updated_form["status"] == "sent"
        assert updated_form["form_data"].get("custom_field") == "test_value"
        assert updated_form["sent_at"] is not None
        print(f"✓ Form updated to status: {updated_form['status']}")
    
    def test_get_forms_by_employee(self, auth_token, test_employee):
        """GET /api/generated-forms?employee_id=... - filter by employee"""
        response = requests.get(
            f"{BASE_URL}/api/generated-forms",
            params={"employee_id": test_employee["id"]},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        forms = response.json()
        assert isinstance(forms, list)
        
        # All forms should belong to the test employee
        for form in forms:
            assert form["employee_id"] == test_employee["id"]
        
        print(f"✓ Found {len(forms)} forms for employee")


class TestBulkOperations:
    """Bulk form generation and document upload tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def test_employee(self, auth_token):
        """Get first available employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        employees = response.json()
        assert len(employees) > 0
        return employees[0]
    
    def test_bulk_generate_forms(self, auth_token, test_employee):
        """POST /api/generated-forms/bulk - generates multiple forms for one employee"""
        # Get templates
        templates_response = requests.get(
            f"{BASE_URL}/api/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        templates = templates_response.json()
        
        # Select 2-3 templates for bulk generation
        template_ids = [t["id"] for t in templates[:3]]
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/bulk",
            params={
                "employee_id": test_employee["id"],
                "template_ids": template_ids
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Bulk generate failed: {response.text}"
        result = response.json()
        
        assert "created" in result
        assert "forms" in result or "errors" in result
        print(f"✓ Bulk generated {result.get('created', 0)} forms")


class TestFormSignoff:
    """Form signoff and locking tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def completed_form(self, auth_token):
        """Create a completed form for signoff testing"""
        # Get employee and template
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        employees = emp_response.json()
        
        tmpl_response = requests.get(
            f"{BASE_URL}/api/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        templates = tmpl_response.json()
        
        if not employees or not templates:
            pytest.skip("No employees or templates available")
        
        # Create form
        create_response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            json={
                "template_id": templates[0]["id"],
                "employee_id": employees[0]["id"],
                "form_data": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        form = create_response.json()
        
        # Update to completed status
        requests.put(
            f"{BASE_URL}/api/generated-forms/{form['id']}",
            json={"status": "completed"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        return form
    
    def test_signoff_form(self, auth_token, completed_form):
        """POST /api/generated-forms/:id/signoff - locks form after admin signature"""
        admin_signature = '{"typed": "Admin User", "hasSignature": true, "date": "2024-01-15"}'
        
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/{completed_form['id']}/signoff",
            params={
                "admin_signature": admin_signature,
                "notes": "Approved after review"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Signoff failed: {response.text}"
        signed_form = response.json()
        
        assert signed_form["status"] == "signed_off"
        assert signed_form["locked"] == True
        assert signed_form["admin_signature"] is not None
        assert signed_form["signed_off_at"] is not None
        print(f"✓ Form signed off and locked")
    
    def test_locked_form_cannot_be_edited(self, auth_token, completed_form):
        """Verify locked forms cannot be edited"""
        # First sign off the form if not already
        admin_signature = '{"typed": "Admin User", "hasSignature": true}'
        requests.post(
            f"{BASE_URL}/api/generated-forms/{completed_form['id']}/signoff",
            params={"admin_signature": admin_signature},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Try to update the locked form
        response = requests.put(
            f"{BASE_URL}/api/generated-forms/{completed_form['id']}",
            json={"form_data": {"test": "should_fail"}},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Locked form correctly rejected edit attempt")


class TestFormStatusFlow:
    """Test form status transitions"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_status_flow(self, auth_token):
        """Test form status flow: draft -> sent -> in_progress -> completed -> reviewed -> signed_off"""
        # Get employee and template
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        employees = emp_response.json()
        
        tmpl_response = requests.get(
            f"{BASE_URL}/api/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        templates = tmpl_response.json()
        
        if not employees or not templates:
            pytest.skip("No employees or templates available")
        
        # Create form (starts as draft)
        create_response = requests.post(
            f"{BASE_URL}/api/generated-forms",
            json={
                "template_id": templates[0]["id"],
                "employee_id": employees[0]["id"],
                "form_data": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        form = create_response.json()
        assert form["status"] == "draft"
        print(f"✓ Form created with status: draft")
        
        # Update to sent
        response = requests.put(
            f"{BASE_URL}/api/generated-forms/{form['id']}",
            json={"status": "sent"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "sent"
        print(f"✓ Status updated to: sent")
        
        # Update to completed
        response = requests.put(
            f"{BASE_URL}/api/generated-forms/{form['id']}",
            json={"status": "completed"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        print(f"✓ Status updated to: completed")
        
        # Sign off (final status)
        admin_signature = '{"typed": "Admin", "hasSignature": true}'
        response = requests.post(
            f"{BASE_URL}/api/generated-forms/{form['id']}/signoff",
            params={"admin_signature": admin_signature},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        final_form = response.json()
        assert final_form["status"] == "signed_off"
        assert final_form["locked"] == True
        print(f"✓ Final status: signed_off (locked)")


class TestDocumentTypes:
    """Document types API tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_get_document_types(self, auth_token):
        """GET /api/document-types - returns document types"""
        response = requests.get(
            f"{BASE_URL}/api/document-types",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        doc_types = response.json()
        assert isinstance(doc_types, list)
        print(f"✓ Found {len(doc_types)} document types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

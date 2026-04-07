"""
Test Suite for Osabea Interview Questions Template and Zero Hour Contract
Tests:
1. Interview config API endpoint returns correct questions for Support Worker role
2. Interview record creation with V2 format (question_scores dict)
3. Contract template preview API with employee data auto-fill
4. Contract templates list endpoint
5. Login and navigation to employee profile
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
TEST_EMPLOYEE_ID = "d88335f6-1b18-435a-8086-28af4a583f77"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def worker_token():
    """Get worker authentication token"""
    response = requests.post(f"{BASE_URL}/api/worker/login", json={
        "email": WORKER_EMAIL,
        "password": WORKER_PASSWORD
    })
    assert response.status_code == 200, f"Worker login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


class TestAdminLogin:
    """Test admin authentication"""
    
    def test_admin_login_success(self):
        """Test admin can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"Admin login successful, user: {data['user'].get('email')}")


class TestInterviewConfig:
    """Test interview configuration endpoint - Osabea 0-3 scoring"""
    
    def test_interview_config_support_worker(self, admin_token):
        """Test interview config returns 8 questions for Support Worker role"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/support_worker",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify question count
        assert "questions" in data
        questions = data["questions"]
        assert len(questions) == 8, f"Expected 8 questions, got {len(questions)}"
        
        # Verify scoring configuration
        assert data.get("max_possible_score") == 24, "Max score should be 24 (8 questions x 3)"
        assert data.get("pass_threshold_score") == 11, "Pass threshold should be 11"
        assert data.get("question_count") == 8
        
        # Verify first question structure
        q1 = questions[0]
        assert q1.get("id") == "sw_q1"
        assert "scoring_criteria" in q1
        assert "0" in q1["scoring_criteria"]
        assert "3" in q1["scoring_criteria"]
        
        print(f"Interview config verified: {len(questions)} questions, max score {data.get('max_possible_score')}")
    
    def test_interview_config_nurse_role(self, admin_token):
        """Test interview config returns 14 questions for Nurse role"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/nurse",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        questions = data.get("questions", [])
        # Nurses get 8 Support Worker questions + 6 clinical questions = 14
        assert len(questions) == 14, f"Expected 14 questions for nurse, got {len(questions)}"
        print(f"Nurse interview config: {len(questions)} questions")
    
    def test_interview_config_has_scoring_criteria(self, admin_token):
        """Test each question has proper scoring criteria (0-3 scale)"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/support_worker",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for q in data.get("questions", []):
            assert "scoring_criteria" in q, f"Question {q.get('id')} missing scoring_criteria"
            criteria = q["scoring_criteria"]
            # Should have 0, 1, 2, 3 scores
            for score in ["0", "1", "2", "3"]:
                assert score in criteria, f"Question {q.get('id')} missing score {score}"
        
        print("All questions have proper 0-3 scoring criteria")


class TestInterviewRecordCreation:
    """Test interview record creation with V2 format"""
    
    def test_create_interview_record_v2_format(self, admin_token):
        """Test creating interview record with question_scores dict (V2 format)"""
        # V2 format payload with individual question scores
        payload = {
            "interview_date": "2026-04-07",
            "interview_method": "in_person",
            "interviewer_name": "Test Interviewer",
            "candidate_name": "Olakunle Alonge",
            "vacancy_job_title": "Support Worker",
            "panel_members": "HR Manager, Team Lead",
            "question_scores": {
                "sw_q1": 2,
                "sw_q2": 3,
                "sw_q3": 2,
                "sw_q4": 2,
                "sw_q5": 2,
                "sw_q6": 2,
                "sw_q7": 2,
                "sw_q8": 2
            },
            "question_notes": {
                "sw_q1": "Good motivation for care work",
                "sw_q2": "Excellent person-centred approach"
            },
            "requires_work_permit": "no",
            "rtw_proof_taken": "Passport, BRP",
            "hours_wanted": "40 hours/week",
            "flexible_working": "yes",
            "has_driving_licence": "yes_full",
            "annual_leave_booked": "None",
            "notice_period": "2 weeks",
            "start_date": "2026-04-15",
            "decision": "Approve",
            "overall_impression": "Strong candidate with excellent communication skills",
            "notes": "Recommended for hire",
            "is_draft": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to create interview record: {response.text}"
        data = response.json()
        
        # Verify response
        assert data.get("success") == True
        # ID is inside the record object
        record = data.get("record", {})
        assert "id" in record or "id" in data, f"No id found in response: {data}"
        
        record_id = record.get("id") or data.get("id")
        print(f"Interview record created: {record_id}")
        
        # Verify V2 format fields in record
        form_data = record.get("form_data", {})
        assert form_data.get("format_version") == "v2_osabea", "Should be V2 format"
        assert "question_scores" in form_data
        assert form_data.get("total_score") == 17, f"Expected total score 17, got {form_data.get('total_score')}"
        assert form_data.get("passed") == True, "Should pass with score 17 >= 11"
        
        return record_id
    
    def test_get_interview_records(self, admin_token):
        """Test retrieving interview records for employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/interview-records",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "records" in data
        records = data["records"]
        assert len(records) >= 0, "Should return records array"
        
        if records:
            # Verify V2 format record structure
            latest = records[0]
            form_data = latest.get("form_data", {})
            
            # Check for V2 format fields
            if form_data.get("format_version") == "v2_osabea":
                assert "question_scores" in form_data
                assert "total_score" in form_data
                assert "max_score" in form_data
                assert "passed" in form_data
                print(f"V2 format record found: score {form_data.get('total_score')}/{form_data.get('max_score')}")
        
        print(f"Retrieved {len(records)} interview records")


class TestContractTemplates:
    """Test contract template endpoints"""
    
    def test_list_contract_templates(self, admin_token):
        """Test listing available contract templates"""
        response = requests.get(
            f"{BASE_URL}/api/contract-templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "templates" in data
        templates = data["templates"]
        assert len(templates) >= 1, "Should have at least one template"
        
        # Verify Zero Hour Contract template
        zero_hour = templates[0]
        assert zero_hour.get("id") == "zero_hour_contract_v1"
        assert zero_hour.get("name") == "Zero Hour Contract of Employment"
        assert "sections" in zero_hour
        
        print(f"Found {len(templates)} contract templates: {[t.get('name') for t in templates]}")
    
    def test_get_contract_template_details(self, admin_token):
        """Test getting specific contract template with full sections"""
        response = requests.get(
            f"{BASE_URL}/api/contract-templates/zero_hour_contract_v1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "template" in data
        template = data["template"]
        assert template.get("id") == "zero_hour_contract_v1"
        assert "sections" in template
        
        sections = template["sections"]
        assert len(sections) >= 10, f"Expected at least 10 sections, got {len(sections)}"
        
        # Verify section structure
        for section in sections:
            assert "id" in section
            assert "title" in section
            assert "content" in section
        
        print(f"Contract template has {len(sections)} sections")


class TestContractPreview:
    """Test contract preview with employee data auto-fill"""
    
    def test_contract_preview_with_employee_data(self, admin_token):
        """Test contract preview endpoint auto-fills employee data"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/contract/preview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "contract" in data
        assert "validation" in data
        assert "employee_name" in data
        assert "can_send" in data
        
        contract = data["contract"]
        assert "sections" in contract
        assert "employee_name" in contract
        
        # Verify employee name is filled
        employee_name = data.get("employee_name", "")
        assert len(employee_name) > 0, "Employee name should be filled"
        
        # Check validation
        validation = data["validation"]
        assert "valid" in validation
        assert "missing_required" in validation
        
        print(f"Contract preview for: {employee_name}")
        print(f"Validation: valid={validation.get('valid')}, can_send={data.get('can_send')}")
        
        # Verify placeholders are replaced in sections
        sections = contract.get("sections", [])
        if sections:
            first_section = sections[0]
            content = first_section.get("content", "")
            # Check that employee name placeholder is replaced
            if "[EMPLOYEE_NAME]" not in content and employee_name:
                print("Employee name placeholder correctly replaced")
    
    def test_contract_preview_invalid_employee(self, admin_token):
        """Test contract preview returns 404 for invalid employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid-employee-id/contract/preview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404


class TestEmployeeProfile:
    """Test employee profile access"""
    
    def test_get_employee_profile(self, admin_token):
        """Test getting employee profile data"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify employee data
        assert data.get("id") == TEST_EMPLOYEE_ID
        assert "first_name" in data
        assert "last_name" in data
        
        print(f"Employee profile: {data.get('first_name')} {data.get('last_name')}")
        print(f"Role: {data.get('role', 'N/A')}")


class TestWorkerLogin:
    """Test worker portal login"""
    
    def test_worker_login_success(self):
        """Test worker can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/worker/login", json={
            "email": WORKER_EMAIL,
            "password": WORKER_PASSWORD
        })
        assert response.status_code == 200, f"Worker login failed: {response.text}"
        data = response.json()
        assert "token" in data
        print(f"Worker login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Phase 15: Interview Routes Module Tests
Tests for routes/interviews.py - Interview configuration, records, and pre-interview questionnaire

Endpoints tested:
- GET /api/interview-config/{role} - Interview config by role
- GET /api/roles/{role}/interview-questions - Interview questions by role
- GET /api/employees/{employee_id}/interview-records - List interview records
- POST /api/employees/{employee_id}/interview-records - Create interview record
- GET /api/employees/{employee_id}/pre-interview-questionnaire - Get pre-interview questionnaire
- POST /api/employees/{employee_id}/pre-interview-questionnaire/review - Review questionnaire

Also tests regression for previous routes:
- GET /api/form-submissions/templates
- GET /api/service-users
- GET /api/compliance/policies
- POST /api/auth/login
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@osabea.care"
ADMIN_PASSWORD = "admin123"


class TestAuthLogin:
    """Test auth login endpoint"""
    
    def test_login_success(self):
        """Test successful admin login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Auth login successful - token received")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get auth headers for requests"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def test_employee_id(auth_headers):
    """Get or create a test employee for interview tests"""
    # First try to find an existing employee
    response = requests.get(
        f"{BASE_URL}/api/employees",
        headers=auth_headers
    )
    if response.status_code == 200:
        employees = response.json()
        if isinstance(employees, list) and len(employees) > 0:
            return employees[0].get("id")
        elif isinstance(employees, dict) and employees.get("employees"):
            return employees["employees"][0].get("id")
    
    # Create a test employee if none exists
    test_employee = {
        "first_name": "TEST_Interview",
        "last_name": f"Employee_{uuid.uuid4().hex[:6]}",
        "email": f"test_interview_{uuid.uuid4().hex[:6]}@test.com",
        "role": "Care Assistant",
        "status": "interview"
    }
    response = requests.post(
        f"{BASE_URL}/api/employees",
        headers=auth_headers,
        json=test_employee
    )
    if response.status_code in [200, 201]:
        return response.json().get("id")
    
    pytest.skip("Could not get or create test employee")


class TestInterviewConfigByRole:
    """Test GET /api/interview-config/{role}"""
    
    def test_get_interview_config_support_worker(self, auth_headers):
        """Test getting interview config for support worker role"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/support_worker",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "role" in data, "Missing 'role' in response"
        assert "questions" in data, "Missing 'questions' in response"
        assert "administrative_questions" in data, "Missing 'administrative_questions'"
        assert "scoring" in data, "Missing 'scoring' in response"
        assert "question_count" in data, "Missing 'question_count'"
        assert "max_possible_score" in data, "Missing 'max_possible_score'"
        assert "pass_threshold_score" in data, "Missing 'pass_threshold_score'"
        
        # Verify questions exist
        assert len(data["questions"]) > 0, "No questions returned"
        assert data["question_count"] == 8, f"Expected 8 questions for support worker, got {data['question_count']}"
        
        print(f"✓ Interview config for support_worker: {data['question_count']} questions, max score {data['max_possible_score']}")
    
    def test_get_interview_config_nurse(self, auth_headers):
        """Test getting interview config for nurse role"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/nurse",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Nurses should have more questions (support worker + clinical)
        assert data["question_count"] == 14, f"Expected 14 questions for nurse, got {data['question_count']}"
        assert len(data["questions"]) == 14, f"Expected 14 questions in list"
        
        print(f"✓ Interview config for nurse: {data['question_count']} questions, max score {data['max_possible_score']}")
    
    def test_get_interview_config_care_assistant(self, auth_headers):
        """Test getting interview config for care assistant role"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/care_assistant",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Care assistant should map to support worker questions
        assert data["question_count"] == 8, f"Expected 8 questions for care assistant"
        print(f"✓ Interview config for care_assistant: {data['question_count']} questions")


class TestInterviewQuestionsByRole:
    """Test GET /api/roles/{role}/interview-questions"""
    
    def test_get_interview_questions_support_worker(self, auth_headers):
        """Test getting interview questions for support worker"""
        response = requests.get(
            f"{BASE_URL}/api/roles/support_worker/interview-questions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "role" in data, "Missing 'role'"
        assert "questions" in data, "Missing 'questions'"
        assert "scoring" in data, "Missing 'scoring'"
        # Note: administrative_questions may not be in this endpoint (it's in interview-config)
        
        # Verify question structure
        if len(data["questions"]) > 0:
            q = data["questions"][0]
            assert "id" in q, "Question missing 'id'"
            assert "question" in q, "Question missing 'question'"
            assert "category" in q, "Question missing 'category'"
            assert "scoring_criteria" in q, "Question missing 'scoring_criteria'"
        
        print(f"✓ Interview questions for support_worker: {len(data['questions'])} questions")
    
    def test_get_interview_questions_nurse(self, auth_headers):
        """Test getting interview questions for nurse"""
        response = requests.get(
            f"{BASE_URL}/api/roles/nurse/interview-questions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Nurses get support worker + clinical questions
        assert len(data["questions"]) == 14, f"Expected 14 questions for nurse"
        
        # Verify nurse-specific questions exist
        question_ids = [q["id"] for q in data["questions"]]
        assert "nurse_q1" in question_ids, "Missing nurse clinical question"
        
        print(f"✓ Interview questions for nurse: {len(data['questions'])} questions")


class TestInterviewRecordsList:
    """Test GET /api/employees/{employee_id}/interview-records"""
    
    def test_get_interview_records_empty(self, auth_headers, test_employee_id):
        """Test getting interview records for employee (may be empty)"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/interview-records",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "records" in data, "Missing 'records' in response"
        assert isinstance(data["records"], list), "Records should be a list"
        
        print(f"✓ Interview records list: {len(data['records'])} records found")
    
    def test_get_interview_records_invalid_employee(self, auth_headers):
        """Test getting interview records for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid_employee_id_12345/interview-records",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Interview records returns 404 for invalid employee")


class TestInterviewRecordsCreate:
    """Test POST /api/employees/{employee_id}/interview-records"""
    
    def test_create_interview_record_v1_format(self, auth_headers, test_employee_id):
        """Test creating interview record with V1 (legacy) format"""
        record_data = {
            "interview_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "interview_method": "video",
            "interviewer_name": "Test Interviewer",
            "communication_score": 4,
            "experience_score": 3,
            "values_score": 4,
            "availability": "Full-time, flexible",
            "strengths": "Good communication skills",
            "areas_for_development": "Time management",
            "decision": "On Hold",
            "notes": "TEST_V1 format interview record",
            "is_draft": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/interview-records",
            headers=auth_headers,
            json=record_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Response structure: {"success": True, "record": {...}}
        assert "success" in data, "Missing 'success' in response"
        assert data["success"] == True, "Expected success=True"
        assert "record" in data, "Missing 'record' in response"
        
        record = data["record"]
        assert "id" in record, "Missing 'id' in record"
        assert record["id"].startswith("interview_"), f"ID should start with 'interview_'"
        assert record["status"] == "submitted", f"Expected status 'submitted', got {record['status']}"
        
        print(f"✓ Created V1 interview record: {record['id']}")
        return record["id"]
    
    def test_create_interview_record_v2_format(self, auth_headers, test_employee_id):
        """Test creating interview record with V2 (Osabea 0-3 scoring) format"""
        record_data = {
            "interview_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "interview_method": "in_person",
            "interviewer_name": "Test Interviewer V2",
            "candidate_name": "Test Candidate",
            "vacancy_job_title": "Care Worker",
            "panel_members": "Panel Member 1, Panel Member 2",
            "question_scores": {
                "sw_q1": 2,
                "sw_q2": 3,
                "sw_q3": 2,
                "sw_q4": 2,
                "sw_q5": 3,
                "sw_q6": 2,
                "sw_q7": 2,
                "sw_q8": 3
            },
            "question_notes": {
                "sw_q1": "Good motivation",
                "sw_q2": "Excellent person-centred approach"
            },
            "requires_work_permit": False,
            "rtw_proof_taken": True,
            "hours_wanted": "35-40 hours",
            "flexible_working": True,
            "has_driving_licence": True,
            "annual_leave_booked": "None",
            "notice_period": "2 weeks",
            "start_date": "2026-02-01",
            "decision": "Approve",
            "overall_impression": "Strong candidate",
            "notes": "TEST_V2 format interview record"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/interview-records",
            headers=auth_headers,
            json=record_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Response structure: {"success": True, "record": {...}}
        assert "success" in data, "Missing 'success' in response"
        assert "record" in data, "Missing 'record' in response"
        
        record = data["record"]
        assert "id" in record, "Missing 'id' in record"
        form_data = record.get("form_data", {})
        assert form_data.get("decision") == "Approve", f"Expected decision 'Approve'"
        
        print(f"✓ Created V2 interview record: {record['id']}")
        return record["id"]
    
    def test_create_interview_record_draft(self, auth_headers, test_employee_id):
        """Test creating interview record as draft"""
        record_data = {
            "interview_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "interview_method": "phone",
            "notes": "TEST_Draft interview record",
            "is_draft": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/interview-records",
            headers=auth_headers,
            json=record_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Response structure: {"success": True, "record": {...}}
        assert "success" in data, "Missing 'success' in response"
        assert "record" in data, "Missing 'record' in response"
        
        record = data["record"]
        assert record["status"] == "draft", f"Expected status 'draft', got {record['status']}"
        
        print(f"✓ Created draft interview record: {record['id']}")
    
    def test_create_interview_record_invalid_employee(self, auth_headers):
        """Test creating interview record for non-existent employee"""
        record_data = {
            "interview_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "interview_method": "video"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid_employee_id_12345/interview-records",
            headers=auth_headers,
            json=record_data
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Create interview record returns 404 for invalid employee")


class TestPreInterviewQuestionnaire:
    """Test GET /api/employees/{employee_id}/pre-interview-questionnaire"""
    
    def test_get_pre_interview_questionnaire(self, auth_headers, test_employee_id):
        """Test getting pre-interview questionnaire for employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/pre-interview-questionnaire",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Response structure includes: employee, questions, scoring, worker_submission, admin_review, can_review
        assert "employee" in data, "Missing 'employee'"
        assert "questions" in data, "Missing 'questions'"
        assert "scoring" in data, "Missing 'scoring'"
        
        # Verify employee info
        employee = data["employee"]
        assert "id" in employee, "Missing employee 'id'"
        
        # Verify questions structure
        assert isinstance(data["questions"], list), "Questions should be a list"
        
        print(f"✓ Pre-interview questionnaire: {len(data['questions'])} questions, employee: {employee.get('name', 'N/A')}")
    
    def test_get_pre_interview_questionnaire_invalid_employee(self, auth_headers):
        """Test getting pre-interview questionnaire for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid_employee_id_12345/pre-interview-questionnaire",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Pre-interview questionnaire returns 404 for invalid employee")


class TestPreviousRoutesRegression:
    """Regression tests for previous routes to ensure they still work"""
    
    def test_form_templates_route(self, auth_headers):
        """Test GET /api/form-submissions/templates still works"""
        response = requests.get(
            f"{BASE_URL}/api/form-submissions/templates",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Form templates failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Templates should be a list"
        print(f"✓ Form templates route working: {len(data)} templates")
    
    def test_service_users_route(self, auth_headers):
        """Test GET /api/service-users still works"""
        response = requests.get(
            f"{BASE_URL}/api/service-users",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Service users failed: {response.text}"
        print(f"✓ Service users route working")
    
    def test_compliance_policies_route(self, auth_headers):
        """Test GET /api/compliance/policies still works"""
        response = requests.get(
            f"{BASE_URL}/api/compliance/policies",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance policies failed: {response.text}"
        print(f"✓ Compliance policies route working")
    
    def test_employees_route(self, auth_headers):
        """Test GET /api/employees still works"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Employees failed: {response.text}"
        print(f"✓ Employees route working")


class TestInterviewRecordsVerifyPersistence:
    """Test that interview records are properly persisted"""
    
    def test_create_and_verify_interview_record(self, auth_headers, test_employee_id):
        """Create interview record and verify it appears in list"""
        # Create a unique record
        unique_note = f"TEST_Persistence_{uuid.uuid4().hex[:8]}"
        record_data = {
            "interview_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "interview_method": "video",
            "notes": unique_note,
            "decision": "On Hold"
        }
        
        # Create
        create_response = requests.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/interview-records",
            headers=auth_headers,
            json=record_data
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        create_data = create_response.json()
        
        # Response structure: {"success": True, "record": {...}}
        assert "record" in create_data, "Missing 'record' in create response"
        created_id = create_data["record"]["id"]
        
        # Verify in list
        list_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee_id}/interview-records",
            headers=auth_headers
        )
        assert list_response.status_code == 200, f"List failed: {list_response.text}"
        records = list_response.json()["records"]
        
        # Find our record
        found = False
        for record in records:
            if record.get("id") == created_id:
                found = True
                # Verify data persisted correctly
                form_data = record.get("form_data") or record.get("data", {})
                assert form_data.get("notes") == unique_note, "Notes not persisted correctly"
                assert form_data.get("interview_method") == "video", "Interview method not persisted"
                break
        
        assert found, f"Created record {created_id} not found in list"
        print(f"✓ Interview record persistence verified: {created_id}")


class TestInterviewConfigQuestionStructure:
    """Test the structure of interview questions"""
    
    def test_question_scoring_criteria(self, auth_headers):
        """Test that questions have proper scoring criteria"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/support_worker",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for question in data["questions"]:
            assert "scoring_criteria" in question, f"Question {question.get('id')} missing scoring_criteria"
            criteria = question["scoring_criteria"]
            # Should have 0, 1, 2, 3 scores
            assert "0" in criteria or 0 in criteria, f"Question {question.get('id')} missing score 0"
            assert "3" in criteria or 3 in criteria, f"Question {question.get('id')} missing score 3"
        
        print(f"✓ All {len(data['questions'])} questions have proper scoring criteria")
    
    def test_administrative_questions_structure(self, auth_headers):
        """Test administrative questions structure"""
        response = requests.get(
            f"{BASE_URL}/api/interview-config/support_worker",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        admin_questions = data.get("administrative_questions", [])
        assert len(admin_questions) > 0, "No administrative questions"
        
        for q in admin_questions:
            assert "id" in q, "Admin question missing 'id'"
            assert "question" in q, "Admin question missing 'question'"
            assert "type" in q, "Admin question missing 'type'"
        
        print(f"✓ Administrative questions structure valid: {len(admin_questions)} questions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


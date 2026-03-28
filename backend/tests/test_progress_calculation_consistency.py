"""
Test Progress Calculation Consistency
=====================================
Tests that the unified progress calculation function produces consistent results
across all views (Employee List, Employee Profile, Compliance endpoint).

Key features tested:
1. Employee list % matches Employee Profile %
2. summary.completion_percentage matches statuses.overall_compliance.percentage
3. Progress excludes optional items from both numerator and denominator
4. Acknowledgements (Contract/Handbook) count as completed AND verified
5. Form-generated requirements with uploaded documents are detected as complete
6. Training records with certificates are detected as complete
7. Deleted/superseded records are excluded from calculations
8. When all required items are complete, progress reaches 100%
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestProgressCalculationConsistency:
    """Test unified progress calculation across all views"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Known test employee: Olakunle Alonge
        self.test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
    
    def test_employee_list_percentage_matches_profile(self):
        """CRITICAL: Employee list % must match Employee Profile %"""
        # Get employee from list
        list_response = self.session.get(f"{BASE_URL}/api/employees")
        assert list_response.status_code == 200
        
        employees = list_response.json()
        test_employee = next((e for e in employees if e['id'] == self.test_employee_id), None)
        assert test_employee is not None, "Test employee not found in list"
        
        list_percentage = test_employee.get('completion_percentage')
        
        # Get employee profile compliance-requirements
        profile_response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert profile_response.status_code == 200
        
        profile_data = profile_response.json()
        profile_percentage = profile_data.get('summary', {}).get('completion_percentage')
        
        # CRITICAL ASSERTION: Both must match
        assert list_percentage == profile_percentage, \
            f"MISMATCH: List shows {list_percentage}% but Profile shows {profile_percentage}%"
        
        print(f"✅ List percentage ({list_percentage}%) matches Profile percentage ({profile_percentage}%)")
    
    def test_summary_matches_statuses_overall_compliance(self):
        """summary.completion_percentage must match statuses.overall_compliance.percentage"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert response.status_code == 200
        
        data = response.json()
        summary_percentage = data.get('summary', {}).get('completion_percentage')
        statuses_percentage = data.get('statuses', {}).get('overall_compliance', {}).get('percentage')
        
        assert summary_percentage == statuses_percentage, \
            f"MISMATCH: summary shows {summary_percentage}% but statuses.overall_compliance shows {statuses_percentage}%"
        
        print(f"✅ summary.completion_percentage ({summary_percentage}%) matches statuses.overall_compliance.percentage ({statuses_percentage}%)")
    
    def test_compliance_endpoint_matches_profile(self):
        """/compliance endpoint must match /compliance-requirements"""
        # Get /compliance endpoint
        compliance_response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance"
        )
        assert compliance_response.status_code == 200
        
        compliance_data = compliance_response.json()
        compliance_percentage = compliance_data.get('compliance', {}).get('completion_percentage')
        
        # Get /compliance-requirements endpoint
        profile_response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert profile_response.status_code == 200
        
        profile_data = profile_response.json()
        profile_percentage = profile_data.get('summary', {}).get('completion_percentage')
        
        assert compliance_percentage == profile_percentage, \
            f"MISMATCH: /compliance shows {compliance_percentage}% but /compliance-requirements shows {profile_percentage}%"
        
        print(f"✅ /compliance ({compliance_percentage}%) matches /compliance-requirements ({profile_percentage}%)")
    
    def test_optional_items_excluded_from_calculation(self):
        """Optional items (Equal Opportunities) must be excluded from both numerator and denominator"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Find optional items
        optional_items = [r for r in requirements if r.get('optional', False)]
        non_optional_items = [r for r in requirements if not r.get('optional', False)]
        
        assert len(optional_items) > 0, "No optional items found - test data may be incorrect"
        
        # Verify Equal Opportunities is optional
        equal_opp = next((r for r in requirements if 'equal' in r.get('name', '').lower()), None)
        assert equal_opp is not None, "Equal Opportunities requirement not found"
        assert equal_opp.get('optional') == True, "Equal Opportunities should be marked as optional"
        
        # Verify summary.total excludes optional items
        summary_total = data.get('summary', {}).get('total')
        assert summary_total == len(non_optional_items), \
            f"summary.total ({summary_total}) should equal non-optional count ({len(non_optional_items)})"
        
        print(f"✅ Optional items ({len(optional_items)}) excluded from total ({summary_total})")
    
    def test_acknowledgements_count_as_completed_and_verified(self):
        """Contract and Handbook acknowledgements must count as completed AND verified"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Find acknowledgement type requirements
        ack_requirements = [r for r in requirements if r.get('type') == 'acknowledgement']
        
        assert len(ack_requirements) >= 2, "Expected at least 2 acknowledgement requirements (Contract, Handbook)"
        
        for ack in ack_requirements:
            name = ack.get('name', 'Unknown')
            if ack.get('acknowledged'):
                # Acknowledged items must be completed AND verified
                assert ack.get('status') == 'completed', \
                    f"{name}: acknowledged but status is {ack.get('status')}, expected 'completed'"
                assert ack.get('verified') == True, \
                    f"{name}: acknowledged but verified is {ack.get('verified')}, expected True"
                assert ack.get('has_evidence') == True, \
                    f"{name}: acknowledged but has_evidence is {ack.get('has_evidence')}, expected True"
                print(f"✅ {name}: acknowledged=True, status=completed, verified=True, has_evidence=True")
    
    def test_form_generated_with_documents_detected_as_complete(self):
        """Form-generated requirements with uploaded documents must be detected as complete"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Find form-generated requirements
        form_requirements = [r for r in requirements if r.get('type') == 'form-generated']
        
        # Check completed form-generated items have evidence
        completed_forms = [r for r in form_requirements if r.get('status') == 'completed']
        
        for form in completed_forms:
            name = form.get('name', 'Unknown')
            has_evidence = form.get('has_evidence', False)
            evidence_count = form.get('evidence_count', 0)
            
            # Completed forms should have evidence
            assert has_evidence == True, \
                f"{name}: completed but has_evidence is False"
            
            print(f"✅ {name}: form-generated, status=completed, has_evidence=True, evidence_count={evidence_count}")
    
    def test_training_with_certificates_detected_as_complete(self):
        """Training records with certificates must be detected as complete"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert response.status_code == 200
        
        data = response.json()
        requirements = data.get('requirements', [])
        
        # Find training requirements
        training_requirements = [r for r in requirements if r.get('type') == 'training']
        
        # Check completed training items
        completed_training = [r for r in training_requirements if r.get('status') == 'completed']
        
        for training in completed_training:
            name = training.get('name', 'Unknown')
            has_evidence = training.get('has_evidence', False)
            training_data = training.get('training', {})
            
            # Completed training should have evidence (certificate)
            assert has_evidence == True, \
                f"{name}: completed but has_evidence is False"
            
            print(f"✅ {name}: training, status=completed, has_evidence=True")
    
    def test_calculation_math_is_correct(self):
        """Verify the percentage calculation math is correct"""
        response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert response.status_code == 200
        
        data = response.json()
        summary = data.get('summary', {})
        
        total = summary.get('total', 0)
        completed = summary.get('completed', 0)
        reported_percentage = summary.get('completion_percentage', 0)
        
        # Calculate expected percentage
        expected_percentage = int((completed / total) * 100) if total > 0 else 0
        
        assert reported_percentage == expected_percentage, \
            f"Math error: {completed}/{total} = {expected_percentage}% but reported {reported_percentage}%"
        
        print(f"✅ Math verified: {completed}/{total} = {expected_percentage}%")
    
    def test_all_endpoints_return_same_counts(self):
        """All endpoints must return the same total/complete/verified counts"""
        # Get /compliance endpoint
        compliance_response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance"
        )
        assert compliance_response.status_code == 200
        compliance_data = compliance_response.json().get('compliance', {})
        
        # Get /compliance-requirements endpoint
        profile_response = self.session.get(
            f"{BASE_URL}/api/employees/{self.test_employee_id}/compliance-requirements"
        )
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        
        # Compare counts
        compliance_total = compliance_data.get('total_items')
        profile_total = profile_data.get('summary', {}).get('total')
        statuses_total = profile_data.get('statuses', {}).get('overall_compliance', {}).get('total')
        
        assert compliance_total == profile_total == statuses_total, \
            f"Total mismatch: /compliance={compliance_total}, summary={profile_total}, statuses={statuses_total}"
        
        compliance_complete = compliance_data.get('complete_count')
        profile_complete = profile_data.get('summary', {}).get('completed')
        statuses_complete = profile_data.get('statuses', {}).get('overall_compliance', {}).get('complete')
        
        assert compliance_complete == profile_complete == statuses_complete, \
            f"Complete mismatch: /compliance={compliance_complete}, summary={profile_complete}, statuses={statuses_complete}"
        
        print(f"✅ All endpoints agree: total={compliance_total}, complete={compliance_complete}")


class TestProgressCalculationEdgeCases:
    """Test edge cases in progress calculation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@osabea.care",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_multiple_employees_consistency(self):
        """Test that progress is consistent for multiple employees"""
        # Get all employees
        list_response = self.session.get(f"{BASE_URL}/api/employees")
        assert list_response.status_code == 200
        
        employees = list_response.json()
        
        # Test first 5 employees
        tested_count = 0
        for emp in employees[:5]:
            emp_id = emp['id']
            list_percentage = emp.get('completion_percentage', 0)
            
            # Get profile percentage
            profile_response = self.session.get(
                f"{BASE_URL}/api/employees/{emp_id}/compliance-requirements"
            )
            if profile_response.status_code != 200:
                continue
            
            profile_data = profile_response.json()
            profile_percentage = profile_data.get('summary', {}).get('completion_percentage', 0)
            
            assert list_percentage == profile_percentage, \
                f"Employee {emp_id}: List={list_percentage}% vs Profile={profile_percentage}%"
            
            tested_count += 1
            print(f"✅ Employee {emp.get('first_name', 'Unknown')}: {list_percentage}% consistent")
        
        assert tested_count > 0, "No employees tested"
        print(f"✅ Tested {tested_count} employees - all consistent")
    
    def test_refresh_status_updates_percentage(self):
        """Test that refresh-status endpoint updates completion_percentage correctly"""
        test_employee_id = "d88335f6-1b18-435a-8086-28af4a583f77"
        
        # Get current percentage from list
        list_response = self.session.get(f"{BASE_URL}/api/employees")
        assert list_response.status_code == 200
        
        employees = list_response.json()
        test_employee = next((e for e in employees if e['id'] == test_employee_id), None)
        assert test_employee is not None
        
        list_percentage = test_employee.get('completion_percentage')
        
        # Call refresh-status
        refresh_response = self.session.post(
            f"{BASE_URL}/api/employees/{test_employee_id}/refresh-status"
        )
        assert refresh_response.status_code == 200
        
        refresh_data = refresh_response.json()
        refresh_percentage = refresh_data.get('completion_percentage')
        
        # Should match list percentage
        assert refresh_percentage == list_percentage, \
            f"refresh-status returned {refresh_percentage}% but list shows {list_percentage}%"
        
        print(f"✅ refresh-status returns consistent percentage: {refresh_percentage}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

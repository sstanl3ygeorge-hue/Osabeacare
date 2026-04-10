"""
Regression tests for canonical review metadata on form submission verification flows.

These tests ensure that admin actions write the new canonical fields:
- review_status
- review_reason
- reviewed_at
- reviewed_by
- reviewed_by_name

They also verify reopen/unverify semantics preserve pending review state.
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_EMAIL = os.environ.get('TEST_ADMIN_EMAIL', 'admin@osabea.care')
ADMIN_PASSWORD = os.environ.get('TEST_ADMIN_PASSWORD', 'admin123')
TEST_EMPLOYEE_ID = os.environ.get('TEST_EMPLOYEE_ID', 'd88335f6-1b18-435a-8086-28af4a583f77')


@pytest.fixture(scope='module')
def auth_token():
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json().get('token')


@pytest.fixture(scope='module')
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


def create_submission(auth_headers, requirement_id, form_type):
    payload = {
        "employee_id": TEST_EMPLOYEE_ID,
        "requirement_id": requirement_id,
        "form_type": form_type,
        "data": {"test_field": "test_value"},
        "status": "submitted"
    }
    response = requests.post(
        f"{BASE_URL}/api/form-submissions",
        json=payload,
        headers=auth_headers
    )
    response.raise_for_status()
    return response.json().get('id')


def fetch_submission(submission_id, auth_headers):
    response = requests.get(
        f"{BASE_URL}/api/form-submissions/{submission_id}",
        headers=auth_headers
    )
    response.raise_for_status()
    return response.json()


class TestCanonicalReviewFields:
    def test_verify_form_submission_writes_canonical_review_fields(self, auth_headers):
        submission_id = create_submission(auth_headers, 'staff_health_questionnaire', 'staff_health_questionnaire')
        try:
            verify_response = requests.post(
                f"{BASE_URL}/api/form-submissions/{submission_id}/verify",
                headers=auth_headers
            )
            assert verify_response.status_code == 200, verify_response.text

            submission = fetch_submission(submission_id, auth_headers)

            assert submission.get('status') == 'verified'
            assert submission.get('verified') is True
            assert submission.get('review_status') == 'verified'
            assert submission.get('review_reason') is None
            assert submission.get('reviewed_at') is not None
            assert submission.get('reviewed_by') is not None
            assert submission.get('reviewed_by_name') is not None
        finally:
            requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)

    def test_unverify_form_submission_sets_pending_review(self, auth_headers):
        submission_id = create_submission(auth_headers, 'interview_record', 'interview_record')
        try:
            # First verify so unverify path is exercised on an existing verified submission
            verify_response = requests.post(
                f"{BASE_URL}/api/form-submissions/{submission_id}/verify",
                headers=auth_headers
            )
            assert verify_response.status_code == 200, verify_response.text

            unverify_response = requests.post(
                f"{BASE_URL}/api/form-submissions/{submission_id}/unverify",
                headers=auth_headers
            )
            assert unverify_response.status_code == 200, unverify_response.text

            submission = fetch_submission(submission_id, auth_headers)

            assert submission.get('status') == 'submitted'
            assert submission.get('verified') is False
            assert submission.get('review_status') == 'pending'
            assert submission.get('review_reason') is None
            assert submission.get('reviewed_at') is not None
            assert submission.get('reviewed_by') is not None
            assert submission.get('reviewed_by_name') is not None
        finally:
            requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)

    def test_reject_form_submission_writes_canonical_rejection_fields(self, auth_headers):
        submission_id = create_submission(auth_headers, 'equal_opportunities', 'equal_opportunities')
        rejection_reason = 'Please provide missing answers before resubmitting.'
        try:
            reject_response = requests.post(
                f"{BASE_URL}/api/form-submissions/{submission_id}/reject",
                params={"reason": rejection_reason},
                headers=auth_headers
            )
            assert reject_response.status_code == 200, reject_response.text

            submission = fetch_submission(submission_id, auth_headers)

            assert submission.get('status') == 'rejected'
            assert submission.get('review_status') == 'rejected'
            assert submission.get('review_reason') == rejection_reason
            assert submission.get('reviewed_at') is not None
            assert submission.get('reviewed_by') is not None
            assert submission.get('reviewed_by_name') is not None
        finally:
            requests.delete(f"{BASE_URL}/api/form-submissions/{submission_id}", headers=auth_headers)

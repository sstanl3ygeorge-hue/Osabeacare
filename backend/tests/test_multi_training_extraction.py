"""
Test Multi-Training Extraction Feature
Tests for:
- GET /api/employees/{employee_id}/training-records endpoint
- POST /api/employees/{employee_id}/training/bulk-upload endpoint
- Mandatory vs Additional training categorization
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMPLOYEE_ID = "ccfcbdbb-feda-4043-a8b2-2f1f9da88bdf"  # Lawrence Egbeni


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@osabea.care", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def auth_headers(admin_token):
    """Headers with admin token"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestTrainingRecordsEndpoint:
    """Tests for GET /api/employees/{employee_id}/training-records"""
    
    def test_training_records_returns_200(self, auth_headers):
        """Endpoint returns 200 for valid employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        assert response.status_code == 200
        print(f"✓ Training records endpoint returned 200")
    
    def test_training_records_has_trainings_array(self, auth_headers):
        """Response contains trainings array"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        assert "trainings" in data
        assert isinstance(data["trainings"], list)
        print(f"✓ Response contains trainings array with {len(data['trainings'])} items")
    
    def test_training_records_has_mandatory_count(self, auth_headers):
        """Response contains mandatory_count field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        assert "mandatory_count" in data
        assert isinstance(data["mandatory_count"], int)
        print(f"✓ mandatory_count: {data['mandatory_count']}")
    
    def test_training_records_has_additional_count(self, auth_headers):
        """Response contains additional_count field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        assert "additional_count" in data
        assert isinstance(data["additional_count"], int)
        print(f"✓ additional_count: {data['additional_count']}")
    
    def test_training_records_has_mandatory_complete(self, auth_headers):
        """Response contains mandatory_complete field"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        assert "mandatory_complete" in data
        assert isinstance(data["mandatory_complete"], int)
        print(f"✓ mandatory_complete: {data['mandatory_complete']}")
    
    def test_trainings_have_is_mandatory_flag(self, auth_headers):
        """Each training has is_mandatory flag"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        if len(trainings) == 0:
            pytest.skip("No trainings found for employee")
        
        for training in trainings:
            assert "is_mandatory" in training, f"Training {training.get('training_name')} missing is_mandatory"
            assert isinstance(training["is_mandatory"], bool)
        
        print(f"✓ All {len(trainings)} trainings have is_mandatory flag")
    
    def test_trainings_have_blocks_promotion_flag(self, auth_headers):
        """Each training has blocks_promotion flag"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        if len(trainings) == 0:
            pytest.skip("No trainings found for employee")
        
        for training in trainings:
            assert "blocks_promotion" in training, f"Training {training.get('training_name')} missing blocks_promotion"
            assert isinstance(training["blocks_promotion"], bool)
        
        print(f"✓ All {len(trainings)} trainings have blocks_promotion flag")
    
    def test_mandatory_trainings_categorized_correctly(self, auth_headers):
        """Mandatory trainings (safeguarding, manual handling, etc.) are flagged correctly"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        mandatory_keywords = ['safeguarding', 'manual handling', 'fire safety', 
                             'health safety', 'health & safety', 'basic life support', 
                             'infection control']
        
        for training in trainings:
            name_lower = training.get("training_name", "").lower()
            is_mandatory = training.get("is_mandatory", False)
            
            # Check if name contains mandatory keyword
            should_be_mandatory = any(kw in name_lower for kw in mandatory_keywords)
            
            if should_be_mandatory:
                assert is_mandatory, f"Training '{training.get('training_name')}' should be mandatory"
        
        print(f"✓ Mandatory trainings categorized correctly")
    
    def test_training_records_requires_auth(self):
        """Endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records"
        )
        assert response.status_code in [401, 403]
        print(f"✓ Endpoint requires authentication (returned {response.status_code})")
    
    def test_training_records_404_for_invalid_employee(self, auth_headers):
        """Endpoint returns 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/training-records",
            headers=auth_headers
        )
        assert response.status_code == 404
        print(f"✓ Returns 404 for invalid employee")


class TestBulkUploadEndpoint:
    """Tests for POST /api/employees/{employee_id}/training/bulk-upload"""
    
    def test_bulk_upload_requires_auth(self):
        """Endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/bulk-upload"
        )
        assert response.status_code in [401, 403]
        print(f"✓ Bulk upload requires authentication (returned {response.status_code})")
    
    def test_bulk_upload_requires_file(self, auth_headers):
        """Endpoint requires file upload"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/bulk-upload",
            headers=auth_headers
        )
        # Should return 422 (validation error) when no file provided
        assert response.status_code == 422
        print(f"✓ Bulk upload requires file (returned {response.status_code})")
    
    def test_bulk_upload_rejects_invalid_file_type(self, auth_headers):
        """Endpoint rejects unsupported file types"""
        # Create a fake text file
        files = {'file': ('test.txt', b'This is a test file', 'text/plain')}
        data = {'extract_multiple': 'true'}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/bulk-upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json().get("detail", "")
        print(f"✓ Bulk upload rejects invalid file types")
    
    def test_bulk_upload_404_for_invalid_employee(self, auth_headers):
        """Endpoint returns 404 for non-existent employee"""
        # Create a minimal PDF-like file
        files = {'file': ('test.pdf', b'%PDF-1.4 test content', 'application/pdf')}
        data = {'extract_multiple': 'true'}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/invalid-employee-id-12345/training/bulk-upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        assert response.status_code == 404
        print(f"✓ Bulk upload returns 404 for invalid employee")
    
    def test_bulk_upload_accepts_pdf(self, auth_headers):
        """Endpoint accepts PDF files"""
        # Create a minimal PDF file
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'
        files = {'file': ('training_cert.pdf', pdf_content, 'application/pdf')}
        data = {'extract_multiple': 'true'}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/bulk-upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        # Should return 200 or 500 (if AI extraction fails on minimal PDF)
        # We're testing that the endpoint accepts the file type
        assert response.status_code in [200, 500]
        print(f"✓ Bulk upload accepts PDF files (returned {response.status_code})")
    
    def test_bulk_upload_accepts_jpg(self, auth_headers):
        """Endpoint accepts JPG files"""
        # Create a minimal JPEG file header
        jpg_content = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46])
        files = {'file': ('training_cert.jpg', jpg_content, 'image/jpeg')}
        data = {'extract_multiple': 'true'}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/bulk-upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        # Should return 200 or 500 (if AI extraction fails on minimal image)
        assert response.status_code in [200, 500]
        print(f"✓ Bulk upload accepts JPG files (returned {response.status_code})")
    
    def test_bulk_upload_accepts_png(self, auth_headers):
        """Endpoint accepts PNG files"""
        # Create a minimal PNG file header
        png_content = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        files = {'file': ('training_cert.png', png_content, 'image/png')}
        data = {'extract_multiple': 'true'}
        
        response = requests.post(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training/bulk-upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        # Should return 200 or 500 (if AI extraction fails on minimal image)
        assert response.status_code in [200, 500]
        print(f"✓ Bulk upload accepts PNG files (returned {response.status_code})")


class TestMandatoryTrainingTypes:
    """Tests for the 6 mandatory training types"""
    
    def test_safeguarding_is_mandatory(self, auth_headers):
        """Safeguarding training is categorized as mandatory"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        safeguarding = [t for t in trainings if 'safeguarding' in t.get('training_name', '').lower()]
        if safeguarding:
            assert safeguarding[0].get('is_mandatory') == True
            print(f"✓ Safeguarding training is mandatory")
        else:
            pytest.skip("No safeguarding training found")
    
    def test_manual_handling_is_mandatory(self, auth_headers):
        """Manual Handling training is categorized as mandatory"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        manual_handling = [t for t in trainings if 'manual handling' in t.get('training_name', '').lower()]
        if manual_handling:
            assert manual_handling[0].get('is_mandatory') == True
            print(f"✓ Manual Handling training is mandatory")
        else:
            pytest.skip("No manual handling training found")
    
    def test_fire_safety_is_mandatory(self, auth_headers):
        """Fire Safety training is categorized as mandatory"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        fire_safety = [t for t in trainings if 'fire safety' in t.get('training_name', '').lower()]
        if fire_safety:
            assert fire_safety[0].get('is_mandatory') == True
            print(f"✓ Fire Safety training is mandatory")
        else:
            pytest.skip("No fire safety training found")
    
    def test_health_safety_is_mandatory(self, auth_headers):
        """Health & Safety training is categorized as mandatory"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        health_safety = [t for t in trainings if 'health' in t.get('training_name', '').lower() and 'safety' in t.get('training_name', '').lower()]
        if health_safety:
            assert health_safety[0].get('is_mandatory') == True
            print(f"✓ Health & Safety training is mandatory")
        else:
            pytest.skip("No health & safety training found")
    
    def test_basic_life_support_is_mandatory(self, auth_headers):
        """Basic Life Support training is categorized as mandatory"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        bls = [t for t in trainings if 'basic life support' in t.get('training_name', '').lower() or 'bls' in t.get('training_name', '').lower()]
        if bls:
            assert bls[0].get('is_mandatory') == True
            print(f"✓ Basic Life Support training is mandatory")
        else:
            pytest.skip("No basic life support training found")
    
    def test_infection_control_is_mandatory(self, auth_headers):
        """Infection Control training is categorized as mandatory"""
        response = requests.get(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}/training-records",
            headers=auth_headers
        )
        data = response.json()
        trainings = data.get("trainings", [])
        
        infection_control = [t for t in trainings if 'infection control' in t.get('training_name', '').lower()]
        if infection_control:
            assert infection_control[0].get('is_mandatory') == True
            print(f"✓ Infection Control training is mandatory")
        else:
            pytest.skip("No infection control training found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

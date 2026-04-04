# Document Extraction Service
# Uses Google Gemini 2.5 Flash Vision for UK compliance document extraction
# Production-grade prompts for high accuracy extraction

import json
import re
import os
import logging
from typing import Dict, Optional, Any
from io import BytesIO

from google import genai

logger = logging.getLogger(__name__)


# =============================================================================
# PRODUCTION-GRADE EXTRACTION PROMPTS (UK Compliance Documents)
# =============================================================================

RTW_EXTRACTION_PROMPT = """You are an AI system extracting structured compliance data from UK Right to Work documents.

Extract the following fields and return ONLY valid JSON.

If a field cannot be found, return null.

Fields:

permission_type (e.g., British Citizen, Skilled Worker Visa, Student Visa, Pre-Settled Status)
permission_start
permission_end
share_code
pvn_number
work_restrictions
indefinite_right_to_work (true/false)
holder_name
document_type
document_number
nationality
issue_date
expiry_date

Rules:

If the document states "no time limit" or "indefinite leave", set indefinite_right_to_work = true.
If a visa expiry date exists, populate permission_end.
Share codes are usually 9 characters.
PVN numbers typically begin with "PVN".
Use ISO date format YYYY-MM-DD.

Return JSON only, no markdown code blocks.

Example:

{
  "holder_name": "Jane Smith",
  "document_type": "BRP",
  "document_number": "ZN1234567",
  "nationality": "Nigerian",
  "permission_type": "Skilled Worker Visa",
  "permission_start": "2023-05-10",
  "permission_end": "2026-05-10",
  "share_code": "ABC123DEF",
  "pvn_number": null,
  "work_restrictions": null,
  "indefinite_right_to_work": false,
  "issue_date": "2023-05-10",
  "expiry_date": "2026-05-10"
}"""


DBS_EXTRACTION_PROMPT = """Extract DBS certificate information from the document.

Return JSON only, no markdown code blocks.

Fields:

certificate_number
applicant_name
issue_date
check_type (basic, standard, enhanced)
status (clear, information_present)

Rules:

If the certificate states "No information recorded", status = clear.
If offences or cautions appear, status = information_present.
Certificate numbers are 12 digits.
Use ISO date format YYYY-MM-DD.

Return JSON only.

Example:

{
  "certificate_number": "001234567890",
  "applicant_name": "Jane Smith",
  "issue_date": "2025-10-12",
  "check_type": "enhanced",
  "status": "clear"
}"""


IDENTITY_EXTRACTION_PROMPT = """You are extracting structured identity data from an identity document.

Return only valid JSON, no markdown code blocks.

Fields:

document_type (passport, driving_licence, national_id)
full_name
date_of_birth
nationality
document_number
issue_date
expiry_date

Rules:

Use ISO date format YYYY-MM-DD if possible.
If multiple names appear, return the full legal name.
If a field is missing, return null.

Return JSON only.

Example output:

{
  "document_type": "passport",
  "full_name": "Jane Smith",
  "date_of_birth": "1994-11-02",
  "nationality": "British",
  "document_number": "123456789",
  "issue_date": "2019-06-01",
  "expiry_date": "2029-06-01"
}"""


ADDRESS_EXTRACTION_PROMPT = """Extract structured proof of address data from the document.

Return valid JSON only, no markdown code blocks.

Fields:

document_type (utility_bill, bank_statement, council_tax, hmrc_letter, tenancy_agreement)
name_on_document
address
issue_date
issuer

Rules:

The address must be a full UK postal address.
Issue date is the statement date or letter date.
If multiple addresses exist, return the primary residential address.
If a field cannot be found, return null.

Return JSON only.

Example:

{
  "document_type": "bank_statement",
  "name_on_document": "Jane Smith",
  "address": "12 King Street, London, SW1A 1AA",
  "issue_date": "2026-03-01",
  "issuer": "Barclays Bank"
}"""


# =============================================================================
# GEMINI CLIENT
# =============================================================================

def get_gemini_client() -> genai.Client:
    """Get Gemini client with API key from environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)


def parse_json_response(response_text: str) -> Dict:
    """
    Parse JSON from model response, handling markdown code blocks.
    JSON Guard - models sometimes add text before JSON.
    """
    if not response_text:
        return {}
    
    # Remove markdown code blocks if present
    text = response_text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    # Try to find JSON in the response
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    # Try parsing the whole thing
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


# =============================================================================
# EXTRACTION SERVICE
# =============================================================================

class DocumentExtractor:
    """
    Document extraction service using Google Gemini 2.5 Flash Vision.
    
    Architecture:
    Upload Evidence → Backend /api/{requirement}/extract → Gemini Vision → Structured JSON → Populate Result Panel
    
    Key behaviors:
    - Extraction is assistive, not blocking
    - Failed extraction still allows manual form completion
    - Frontend pre-fills fields from extraction but allows edits
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Gemini API key."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key required")
        self.client = genai.Client(api_key=self.api_key)
    
    async def extract_rtw(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract Right to Work fields from document image."""
        return await self._extract_document(
            image_base64=image_base64,
            prompt=RTW_EXTRACTION_PROMPT,
            extraction_type="rtw"
        )
    
    async def extract_dbs(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract DBS certificate fields from document image."""
        return await self._extract_document(
            image_base64=image_base64,
            prompt=DBS_EXTRACTION_PROMPT,
            extraction_type="dbs"
        )
    
    async def extract_identity(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None,
        employee_dob: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract identity document fields from document image."""
        return await self._extract_document(
            image_base64=image_base64,
            prompt=IDENTITY_EXTRACTION_PROMPT,
            extraction_type="identity"
        )
    
    async def extract_address(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None,
        expected_address: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Extract proof of address fields from document image."""
        return await self._extract_document(
            image_base64=image_base64,
            prompt=ADDRESS_EXTRACTION_PROMPT,
            extraction_type="address"
        )
    
    async def _extract_document(
        self,
        image_base64: str,
        prompt: str,
        extraction_type: str
    ) -> Dict[str, Any]:
        """
        Core extraction method using Gemini 2.5 Flash Vision.
        """
        try:
            # Determine image media type
            if image_base64.startswith('/9j/'):
                media_type = "image/jpeg"
            elif image_base64.startswith('iVBOR'):
                media_type = "image/png"
            elif image_base64.startswith('JVBERi'):
                media_type = "application/pdf"
            else:
                media_type = "image/png"  # Default
            
            # Call Gemini Vision API
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": media_type, "data": image_base64}}
                        ]
                    }
                ]
            )
            
            result = response.text
            
            if not result:
                return {
                    "fields": {},
                    "success": False,
                    "error": "No response from Gemini",
                    "confidence": 0.0
                }
            
            # Parse JSON with guard
            fields = parse_json_response(result)
            
            if not fields:
                return {
                    "fields": {},
                    "success": False,
                    "error": "Could not parse response as JSON",
                    "confidence": 0.0
                }
            
            # Clean up fields - remove null values
            cleaned_fields = {k: v for k, v in fields.items() if v is not None}
            
            # Calculate confidence
            total_fields = len(fields)
            extracted_fields = len(cleaned_fields)
            confidence = extracted_fields / total_fields if total_fields > 0 else 0.0
            
            logger.info(f"{extraction_type} extraction: {extracted_fields}/{total_fields} fields, confidence={confidence:.2f}")
            
            return {
                "fields": cleaned_fields,
                "success": True,
                "error": None,
                "confidence": confidence,
                "extracted_count": extracted_fields,
                "total_fields": total_fields
            }
            
        except Exception as e:
            logger.error(f"{extraction_type} extraction failed: {str(e)}")
            return {
                "fields": {},
                "success": False,
                "error": str(e),
                "confidence": 0.0
            }


# =============================================================================
# STANDALONE EXTRACTION FUNCTIONS (for server.py)
# =============================================================================

async def extract_rtw_fields(image_base64: str) -> Dict[str, Any]:
    """Standalone RTW extraction function."""
    extractor = DocumentExtractor()
    return await extractor.extract_rtw(image_base64)


async def extract_dbs_fields(image_base64: str) -> Dict[str, Any]:
    """Standalone DBS extraction function."""
    extractor = DocumentExtractor()
    return await extractor.extract_dbs(image_base64)


async def extract_identity_fields(image_base64: str) -> Dict[str, Any]:
    """Standalone identity extraction function."""
    extractor = DocumentExtractor()
    return await extractor.extract_identity(image_base64)


async def extract_address_fields(image_base64: str) -> Dict[str, Any]:
    """Standalone address extraction function."""
    extractor = DocumentExtractor()
    return await extractor.extract_address(image_base64)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def resize_image_for_extraction(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Resize image to reduce payload size for faster extraction."""
    try:
        from PIL import Image
        
        img = Image.open(BytesIO(image_bytes))
        ratio = max_size / max(img.size)
        if ratio < 1:
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        output = BytesIO()
        img.save(output, format=img.format or 'PNG', quality=85)
        return output.getvalue()
        
    except Exception:
        return image_bytes


def pdf_first_page_to_image(pdf_bytes: bytes) -> Optional[bytes]:
    """Convert first page of PDF to image for extraction."""
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            return None
        
        page = doc[0]
        mat = fitz.Matrix(150/72, 150/72)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
        
    except Exception:
        return None

# Document Extraction Service
# Uses OpenAI GPT-5.2 Vision via Emergent Integrations for document field extraction

import json
import re
import uuid
import logging
from typing import Dict, Optional, Any
from io import BytesIO

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION PROMPTS
# =============================================================================

RTW_EXTRACTION_PROMPT = """You are a UK Right to Work document extraction specialist.

Extract the following fields from this document:
- permission_type: Type of permission (e.g., "British Citizen", "Indefinite Leave to Remain", "Tier 2 Visa", "BRP", "EU Settlement Scheme")
- permission_start: Permission start date (format: YYYY-MM-DD)
- permission_end: Permission end date (format: YYYY-MM-DD), null if indefinite
- share_code: Share code if present (format: XXX-XXX-XXX)
- pvn_number: Positive Verification Notice number if present
- work_restrictions: Any work restrictions mentioned
- indefinite: true if permission is indefinite/permanent, false otherwise
- holder_name: Full name on document
- document_type: Document type (Passport, BRP, Visa, Share Code Letter)
- document_number: Document/passport number
- nationality: Nationality
- expiry_date: Document expiry date (format: YYYY-MM-DD)

Return valid JSON only:
{
  "permission_type": "string or null",
  "permission_start": "YYYY-MM-DD or null",
  "permission_end": "YYYY-MM-DD or null",
  "share_code": "XXX-XXX-XXX or null",
  "pvn_number": "string or null",
  "work_restrictions": "string or null",
  "indefinite": true/false,
  "holder_name": "string or null",
  "document_type": "string or null",
  "document_number": "string or null",
  "nationality": "string or null",
  "expiry_date": "YYYY-MM-DD or null"
}"""


DBS_EXTRACTION_PROMPT = """You are a UK DBS (Disclosure and Barring Service) certificate extraction specialist.

Extract the following fields from this DBS certificate or Update Service screenshot:
- certificate_number: DBS certificate number (format: XXXXXXXXXXXXXX, 12 digits)
- dbs_level: Level of check (Basic, Standard, Enhanced, Enhanced with Barred List(s))
- certificate_issue_date: Issue date on certificate (format: YYYY-MM-DD)
- name_on_certificate: Full name as shown on certificate
- workforce: Workforce type (Adult, Child, Adult and Child, Other)
- result_status: Result (clear, information_present)
- update_service_status: If Update Service screenshot, status shown (active, not_registered, etc.)

Return valid JSON only:
{
  "certificate_number": "string or null",
  "dbs_level": "Basic|Standard|Enhanced|Enhanced with Barred List(s) or null",
  "certificate_issue_date": "YYYY-MM-DD or null",
  "name_on_certificate": "string or null",
  "workforce": "Adult|Child|Adult and Child|Other or null",
  "result_status": "clear|information_present or null",
  "update_service_status": "string or null"
}"""


IDENTITY_EXTRACTION_PROMPT = """You are a UK identity document extraction specialist.

Extract the following fields from this identity document (passport, driving licence, national ID card):
- document_type: Type of document (Passport, Driving Licence, National ID Card, etc.)
- full_name: Full name as shown on document
- date_of_birth: Date of birth (format: YYYY-MM-DD)
- document_number: Document/passport number
- issue_date: Issue date (format: YYYY-MM-DD)
- expiry_date: Expiry date (format: YYYY-MM-DD)
- nationality: Nationality/citizenship
- issuing_authority: Issuing authority/country

Return valid JSON only:
{
  "document_type": "Passport|Driving Licence|National ID Card or null",
  "full_name": "string or null",
  "date_of_birth": "YYYY-MM-DD or null",
  "document_number": "string or null",
  "issue_date": "YYYY-MM-DD or null",
  "expiry_date": "YYYY-MM-DD or null",
  "nationality": "string or null",
  "issuing_authority": "string or null"
}"""


ADDRESS_EXTRACTION_PROMPT = """You are a UK proof of address document extraction specialist.

Extract the following fields from this proof of address document (utility bill, bank statement, council tax, etc.):
- document_type: Type of document (Utility Bill, Bank Statement, Council Tax, HMRC Letter, Tenancy Agreement, etc.)
- name_on_document: Name as shown on document
- address_line1: First line of address
- address_line2: Second line of address (if present)
- city: City/town
- postcode: UK postcode
- issue_date: Document date/issue date (format: YYYY-MM-DD)
- issuer: Company/organization that issued the document

Return valid JSON only:
{
  "document_type": "Utility Bill|Bank Statement|Council Tax|HMRC Letter|Tenancy Agreement|Other or null",
  "name_on_document": "string or null",
  "address_line1": "string or null",
  "address_line2": "string or null",
  "city": "string or null",
  "postcode": "string or null",
  "issue_date": "YYYY-MM-DD or null",
  "issuer": "string or null"
}"""


# =============================================================================
# EXTRACTION SERVICE
# =============================================================================

class DocumentExtractor:
    """
    Document extraction service using OpenAI GPT-5.2 Vision via Emergent Integrations.
    
    Architecture:
    Upload Evidence → Backend /api/{requirement}/extract → OpenAI Vision → Structured JSON → Populate Result Panel
    
    Key behaviors:
    - Extraction is assistive, not blocking
    - Failed extraction still allows manual form completion
    - Frontend pre-fills fields from extraction but allows edits
    """
    
    def __init__(self, api_key: str):
        """Initialize with Emergent LLM API key."""
        self.api_key = api_key
    
    async def extract_rtw(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract Right to Work fields from document image.
        
        Returns:
            Dict with 'fields', 'success', 'error' keys
        """
        return await self._extract_document(
            image_base64=image_base64,
            prompt=RTW_EXTRACTION_PROMPT,
            extraction_type="rtw",
            context={"employee_name": employee_name}
        )
    
    async def extract_dbs(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract DBS certificate fields from document image.
        
        Returns:
            Dict with 'fields', 'success', 'error' keys
        """
        return await self._extract_document(
            image_base64=image_base64,
            prompt=DBS_EXTRACTION_PROMPT,
            extraction_type="dbs",
            context={"employee_name": employee_name}
        )
    
    async def extract_identity(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None,
        employee_dob: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract identity document fields from document image.
        
        Returns:
            Dict with 'fields', 'success', 'error' keys
        """
        return await self._extract_document(
            image_base64=image_base64,
            prompt=IDENTITY_EXTRACTION_PROMPT,
            extraction_type="identity",
            context={"employee_name": employee_name, "employee_dob": employee_dob}
        )
    
    async def extract_address(
        self, 
        image_base64: str,
        employee_name: Optional[str] = None,
        expected_address: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract proof of address fields from document image.
        
        Returns:
            Dict with 'fields', 'success', 'error' keys
        """
        return await self._extract_document(
            image_base64=image_base64,
            prompt=ADDRESS_EXTRACTION_PROMPT,
            extraction_type="address",
            context={"employee_name": employee_name, "expected_address": expected_address}
        )
    
    async def _extract_document(
        self,
        image_base64: str,
        prompt: str,
        extraction_type: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Core extraction method using GPT-5.2 Vision.
        
        Args:
            image_base64: Base64 encoded image data
            prompt: System prompt with extraction instructions
            extraction_type: Type of extraction (rtw, dbs, identity, address)
            context: Optional context like employee name for validation
        
        Returns:
            Dict with:
            - fields: Extracted field values
            - success: Whether extraction succeeded
            - error: Error message if failed (but NOT blocking)
            - confidence: Overall extraction confidence
        """
        try:
            # Create chat with GPT-5.2 Vision
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"extract-{extraction_type}-{uuid.uuid4()}",
                system_message=prompt
            ).with_model("openai", "gpt-5.2")
            
            # Build user message with image
            image_content = ImageContent(image_base64=image_base64)
            user_message = UserMessage(
                text=f"Extract all fields from this {extraction_type.upper()} document. Return valid JSON only.",
                file_contents=[image_content]
            )
            
            # Send to model
            result = await chat.send_message(user_message)
            
            if not result:
                return {
                    "fields": {},
                    "success": False,
                    "error": "No response from AI model",
                    "confidence": 0.0
                }
            
            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', result)
            if not json_match:
                return {
                    "fields": {},
                    "success": False,
                    "error": "Could not parse AI response as JSON",
                    "confidence": 0.0
                }
            
            try:
                fields = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                return {
                    "fields": {},
                    "success": False,
                    "error": f"Invalid JSON in response: {str(e)}",
                    "confidence": 0.0
                }
            
            # Clean up fields - remove null values
            cleaned_fields = {k: v for k, v in fields.items() if v is not None}
            
            # Calculate confidence based on how many fields were extracted
            total_fields = len(fields)
            extracted_fields = len(cleaned_fields)
            confidence = extracted_fields / total_fields if total_fields > 0 else 0.0
            
            logger.info(f"{extraction_type} extraction completed: {extracted_fields}/{total_fields} fields, confidence={confidence:.2f}")
            
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
# HELPER FUNCTIONS
# =============================================================================

def resize_image_for_extraction(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """
    Resize image to reduce payload size for faster extraction.
    
    Vision models work fine with smaller images for document extraction.
    This reduces latency significantly.
    """
    try:
        from PIL import Image
        
        img = Image.open(BytesIO(image_bytes))
        
        # Calculate new size maintaining aspect ratio
        ratio = max_size / max(img.size)
        if ratio < 1:
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = BytesIO()
        img.save(output, format=img.format or 'PNG', quality=85)
        return output.getvalue()
        
    except ImportError:
        # PIL not available, return original
        return image_bytes
    except Exception:
        # Any other error, return original
        return image_bytes


def pdf_first_page_to_image(pdf_bytes: bytes) -> Optional[bytes]:
    """
    Convert first page of PDF to image for extraction.
    
    Most compliance documents have key info on first page.
    This is much faster than processing entire PDF.
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            return None
        
        # Get first page
        page = doc[0]
        
        # Render at reasonable DPI (150 is enough for text extraction)
        mat = fitz.Matrix(150/72, 150/72)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PNG bytes
        return pix.tobytes("png")
        
    except ImportError:
        return None
    except Exception:
        return None

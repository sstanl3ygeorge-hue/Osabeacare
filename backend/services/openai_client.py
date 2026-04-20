# Centralised OpenAI client for all AI extraction paths.
# Every extraction module must import from here instead of initialising its own provider.

import os
import json
import re
import base64
import logging
from typing import Dict, List, Optional, Any

from openai import OpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """Return a shared OpenAI client, created on first call."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = OpenAI(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _media_type_from_base64(b64: str) -> str:
    """Guess MIME type from the first bytes of a base64 string."""
    if b64.startswith("/9j/"):
        return "image/jpeg"
    if b64.startswith("iVBOR"):
        return "image/png"
    if b64.startswith("JVBERi"):
        # PDF — OpenAI vision doesn't natively accept PDFs; callers should
        # convert pages to images first.  Fall back to png.
        return "image/png"
    return "image/png"


def parse_json_response(response_text: str) -> Dict:
    """Parse JSON from model response, handling markdown code blocks."""
    if not response_text:
        return {}

    text = response_text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


def parse_json_array_response(response_text: str) -> List:
    """Parse a JSON *array* from model response."""
    if not response_text:
        return []

    text = response_text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Core extraction call — text + optional images
# ---------------------------------------------------------------------------

def call_openai_vision(
    prompt: str,
    *,
    system_message: str = "You are an expert document extraction assistant.",
    image_base64_list: Optional[List[str]] = None,
    image_url_list: Optional[List[str]] = None,
    model: str = "gpt-4o",
    max_tokens: int = 4096,
) -> Optional[str]:
    """
    Synchronous OpenAI chat-completion call with optional base64 images or image URLs.

    Returns the assistant's text response, or None on failure.
    """
    client = get_openai_client()

    user_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]

    for b64 in (image_base64_list or []):
        media = _media_type_from_base64(b64)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media};base64,{b64}"},
        })

    for url in (image_url_list or []):
        user_content.append({
            "type": "image_url",
            "image_url": {"url": url},
        })

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI vision call failed: {e}")
        return None


async def call_openai_vision_async(
    prompt: str,
    *,
    system_message: str = "You are an expert document extraction assistant.",
    image_base64_list: Optional[List[str]] = None,
    image_url_list: Optional[List[str]] = None,
    model: str = "gpt-4o",
    max_tokens: int = 4096,
) -> Optional[str]:
    """
    Async wrapper — runs the synchronous OpenAI call in a thread so it
    doesn't block the event loop.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: call_openai_vision(
            prompt,
            system_message=system_message,
            image_base64_list=image_base64_list,
            image_url_list=image_url_list,
            model=model,
            max_tokens=max_tokens,
        ),
    )


# ---------------------------------------------------------------------------
# Gemini fallback
# ---------------------------------------------------------------------------

def call_gemini_vision(
    prompt: str,
    *,
    system_message: str = "You are an expert document extraction assistant.",
    image_base64_list: Optional[List[str]] = None,
    model: str = "gemini-1.5-flash",
    max_tokens: int = 4096,
) -> Optional[str]:
    """
    Synchronous Gemini Vision call used as a fallback when OpenAI is unavailable.

    Returns the assistant's text response, or None on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("Gemini fallback skipped: GEMINI_API_KEY not set")
        return None

    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        import PIL.Image
        import io

        genai.configure(api_key=api_key)
        gen_model = genai.GenerativeModel(model_name=model, system_instruction=system_message)

        parts: List[Any] = [prompt]
        for b64 in (image_base64_list or []):
            img_bytes = base64.b64decode(b64)
            img = PIL.Image.open(io.BytesIO(img_bytes))
            parts.append(img)

        response = gen_model.generate_content(
            parts,
            generation_config={"max_output_tokens": max_tokens},
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini vision fallback failed: {e}")
        return None


async def call_gemini_vision_async(
    prompt: str,
    *,
    system_message: str = "You are an expert document extraction assistant.",
    image_base64_list: Optional[List[str]] = None,
    model: str = "gemini-1.5-flash",
    max_tokens: int = 4096,
) -> Optional[str]:
    """Async wrapper for call_gemini_vision."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: call_gemini_vision(
            prompt,
            system_message=system_message,
            image_base64_list=image_base64_list,
            model=model,
            max_tokens=max_tokens,
        ),
    )

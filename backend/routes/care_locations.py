"""
Care Locations (Client Sites) backend foundation routes.

Scope:
- Canonical care_locations collection
- Admin/manager-only CRUD-style operations
- Archive/restore via is_active flag
- Audit logging on all mutations

Out of scope:
- Shift attendance clock-in/out
- Payroll/timesheets
- QR token generation
- GPS/photo verification workflows
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .dependencies import get_db, require_manager_or_admin, log_audit_action

router = APIRouter(tags=["Care Locations"])

ALLOWED_LOCATION_TYPES = {"care_home", "supported_living", "community", "other"}


class CareLocationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2)
    location_type: str = Field(..., min_length=2)
    address_line_1: str = Field(..., min_length=2)
    city: str = Field(..., min_length=2)
    postcode: str = Field(..., min_length=2)
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    qr_enabled: bool = False
    geofence_enabled: bool = False
    geofence_lat: Optional[float] = None
    geofence_lng: Optional[float] = None
    geofence_radius_m: Optional[float] = None


class CareLocationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2)
    location_type: Optional[str] = Field(default=None, min_length=2)
    address_line_1: Optional[str] = Field(default=None, min_length=2)
    city: Optional[str] = Field(default=None, min_length=2)
    postcode: Optional[str] = Field(default=None, min_length=2)
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    qr_enabled: Optional[bool] = None
    geofence_enabled: Optional[bool] = None
    geofence_lat: Optional[float] = None
    geofence_lng: Optional[float] = None
    geofence_radius_m: Optional[float] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = (value or "").strip()
    if len(normalized) < 2:
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    return normalized


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_location_type(value: str) -> str:
    normalized = _normalize_required_text(value, "location_type").lower().replace(" ", "_")
    if normalized not in ALLOWED_LOCATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"location_type must be one of: {', '.join(sorted(ALLOWED_LOCATION_TYPES))}",
        )
    return normalized


def _validate_geofence_fields(payload: Dict[str, Any]):
    geofence_enabled = bool(payload.get("geofence_enabled"))
    lat = payload.get("geofence_lat")
    lng = payload.get("geofence_lng")
    radius = payload.get("geofence_radius_m")

    if geofence_enabled:
        if lat is None or lng is None or radius is None:
            raise HTTPException(
                status_code=400,
                detail="geofence_lat, geofence_lng, and geofence_radius_m are required when geofence_enabled=true",
            )
        if radius <= 0:
            raise HTTPException(status_code=400, detail="geofence_radius_m must be greater than 0")
    elif lat is None and lng is None and radius is None:
        return

    if lat is not None and (lat < -90 or lat > 90):
        raise HTTPException(status_code=400, detail="geofence_lat must be between -90 and 90")
    if lng is not None and (lng < -180 or lng > 180):
        raise HTTPException(status_code=400, detail="geofence_lng must be between -180 and 180")
    if radius is not None and radius <= 0:
        raise HTTPException(status_code=400, detail="geofence_radius_m must be greater than 0")


async def _get_location_or_404(location_id: str) -> Dict[str, Any]:
    db = get_db()
    item = await db.care_locations.find_one({"id": location_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Care location not found")
    return item


@router.post("/care-locations")
async def create_care_location(
    payload: CareLocationCreateRequest,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    now = _now_iso()
    location_id = str(uuid.uuid4())

    location = {
        "id": location_id,
        "name": _normalize_required_text(payload.name, "name"),
        "location_type": _normalize_location_type(payload.location_type),
        "address_line_1": _normalize_required_text(payload.address_line_1, "address_line_1"),
        "city": _normalize_required_text(payload.city, "city"),
        "postcode": _normalize_required_text(payload.postcode, "postcode"),
        "contact_name": _normalize_optional_text(payload.contact_name),
        "contact_phone": _normalize_optional_text(payload.contact_phone),
        "is_active": True,
        "qr_enabled": bool(payload.qr_enabled),
        "geofence_enabled": bool(payload.geofence_enabled),
        "geofence_lat": payload.geofence_lat,
        "geofence_lng": payload.geofence_lng,
        "geofence_radius_m": payload.geofence_radius_m,
        "created_at": now,
        "created_by": user.get("user_id"),
        "updated_at": now,
        "updated_by": user.get("user_id"),
    }
    _validate_geofence_fields(location)

    await db.care_locations.insert_one(location)
    await log_audit_action(
        user.get("user_id"),
        "care_location_created",
        "care_location",
        location_id,
        {
            "name": location["name"],
            "location_type": location["location_type"],
            "is_active": location["is_active"],
        },
    )
    return {"success": True, "care_location": location}


@router.get("/care-locations")
async def list_care_locations(
    include_inactive: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    location_type: Optional[str] = Query(default=None),
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    query: Dict[str, Any] = {}

    if not include_inactive:
        query["is_active"] = True

    if location_type:
        query["location_type"] = _normalize_location_type(location_type)

    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": regex},
            {"address_line_1": regex},
            {"city": regex},
            {"postcode": regex},
            {"contact_name": regex},
        ]

    rows = await db.care_locations.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return {"care_locations": rows}


@router.get("/care-locations/{location_id}")
async def get_care_location(
    location_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    row = await _get_location_or_404(location_id)
    return {"care_location": row}


@router.put("/care-locations/{location_id}")
async def update_care_location(
    location_id: str,
    payload: CareLocationUpdateRequest,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    existing = await _get_location_or_404(location_id)

    update_doc = payload.model_dump(exclude_none=True)
    if not update_doc:
        return {"success": True, "care_location": existing}

    normalized: Dict[str, Any] = {}
    for key, value in update_doc.items():
        if key in {"name", "address_line_1", "city", "postcode"}:
            normalized[key] = _normalize_required_text(value, key)
        elif key == "location_type":
            normalized[key] = _normalize_location_type(value)
        elif key in {"contact_name", "contact_phone"}:
            normalized[key] = _normalize_optional_text(value)
        else:
            normalized[key] = value

    candidate = dict(existing)
    candidate.update(normalized)
    _validate_geofence_fields(candidate)

    now = _now_iso()
    normalized["updated_at"] = now
    normalized["updated_by"] = user.get("user_id")

    await db.care_locations.update_one({"id": location_id}, {"$set": normalized})
    updated = await _get_location_or_404(location_id)

    await log_audit_action(
        user.get("user_id"),
        "care_location_updated",
        "care_location",
        location_id,
        {"fields_updated": sorted(list(normalized.keys()))},
    )
    return {"success": True, "care_location": updated}


@router.post("/care-locations/{location_id}/archive")
async def archive_care_location(
    location_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    existing = await _get_location_or_404(location_id)
    if not existing.get("is_active", True):
        return {"success": True, "care_location": existing}

    now = _now_iso()
    await db.care_locations.update_one(
        {"id": location_id},
        {"$set": {"is_active": False, "updated_at": now, "updated_by": user.get("user_id")}},
    )
    updated = await _get_location_or_404(location_id)

    await log_audit_action(
        user.get("user_id"),
        "care_location_archived",
        "care_location",
        location_id,
        {"name": updated.get("name")},
    )
    return {"success": True, "care_location": updated}


@router.post("/care-locations/{location_id}/restore")
async def restore_care_location(
    location_id: str,
    user: dict = Depends(require_manager_or_admin),
):
    db = get_db()
    existing = await _get_location_or_404(location_id)
    if existing.get("is_active", True):
        return {"success": True, "care_location": existing}

    now = _now_iso()
    await db.care_locations.update_one(
        {"id": location_id},
        {"$set": {"is_active": True, "updated_at": now, "updated_by": user.get("user_id")}},
    )
    updated = await _get_location_or_404(location_id)

    await log_audit_action(
        user.get("user_id"),
        "care_location_restored",
        "care_location",
        location_id,
        {"name": updated.get("name")},
    )
    return {"success": True, "care_location": updated}

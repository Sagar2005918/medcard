"""
Public router – no authentication required

GET /api/public/verify/{health_id}  – verify a citizen's health card (for emergency rooms, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .. import schemas, models, database, utils

router = APIRouter()


@router.get("/verify/{health_id}", response_model=schemas.PublicVerificationResponse)
async def verify_health_id(
    health_id: str,
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.Citizen).where(models.Citizen.health_id == health_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Health ID not found")

    checkup_info = utils.evaluate_checkup_status(citizen.last_checkup_at)

    return {
        "success": True,
        "cardVerification": {
            "health_id": citizen.health_id,
            "full_name": citizen.full_name,
            "date_of_birth": str(citizen.date_of_birth),
            "gender": citizen.gender,
            "blood_group": citizen.blood_group,
            "organ_donor": citizen.organ_donor,
            "emergency_contact_name": citizen.emergency_contact_name,
            "emergency_contact_phone": citizen.emergency_contact_phone,
            "allergies": citizen.allergies or [],
            "critical_alert": citizen.critical_alert,
            "checkup_status": citizen.checkup_status,
            "checkup_info": checkup_info,
            "qr_code_data": citizen.qr_code_data,
        },
    }

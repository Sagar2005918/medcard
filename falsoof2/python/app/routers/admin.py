"""
Admin router – requires ADMIN role.

Routes:
  GET  /api/admin/hospitals/pending         – list hospitals awaiting approval
  POST /api/admin/hospitals/{id}/approve    – approve a hospital (makes it GOV_APPROVED)
  POST /api/admin/hospitals/{id}/reject     – reject with a reason
  POST /api/admin/citizens                  – register a new citizen + seed insurance policy
  GET  /api/admin/citizens                  – list all citizens
  GET  /api/admin/stats                     – dashboard counters
"""

from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
import secrets

from .. import schemas, models, utils, dependencies, database

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Pending hospitals
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/hospitals/pending", response_model=list[schemas.HospitalOut])
async def list_pending_hospitals(
    current_user: models.User = Depends(dependencies.role_required("ADMIN")),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.Hospital).where(models.Hospital.approval_status == "PENDING")
    )
    return result.scalars().all()


@router.post("/hospitals/{hospital_id}/approve", response_model=schemas.HospitalOut)
async def approve_hospital(
    hospital_id: int,
    current_user: models.User = Depends(dependencies.role_required("ADMIN")),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.Hospital).where(models.Hospital.id == hospital_id)
    )
    hospital = result.scalars().first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    hospital.approval_status = "APPROVED"
    hospital.is_gov_approved = True
    hospital.approved_by = current_user.id
    hospital.approved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(hospital)
    return hospital


@router.post("/hospitals/{hospital_id}/reject", response_model=schemas.HospitalOut)
async def reject_hospital(
    hospital_id: int,
    reason: str = "Does not meet criteria",
    current_user: models.User = Depends(dependencies.role_required("ADMIN")),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.Hospital).where(models.Hospital.id == hospital_id)
    )
    hospital = result.scalars().first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    hospital.approval_status = "REJECTED"
    hospital.is_gov_approved = False
    hospital.rejection_reason = reason
    hospital.approved_by = current_user.id
    hospital.approved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(hospital)
    return hospital


# ─────────────────────────────────────────────────────────────────────────────
# Citizens
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/citizens", response_model=schemas.CitizenProfile)
async def create_citizen(
    payload: schemas.CitizenCreate,
    current_user: models.User = Depends(dependencies.role_required("ADMIN")),
    db: AsyncSession = Depends(database.get_db),
):
    health_id = utils.generate_health_id()
    masked_aadhaar = utils.generate_masked_aadhaar()

    allergies = [a.strip() for a in payload.allergies.split(",")] if payload.allergies else []
    chronic   = [c.strip() for c in payload.chronicConditions.split(",")] if payload.chronicConditions else []

    new_citizen = models.Citizen(
        health_id=health_id,
        aadhaar_masked=masked_aadhaar,
        full_name=payload.fullName,
        date_of_birth=payload.dateOfBirth,
        gender=payload.gender,
        blood_group=payload.bloodGroup,
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        emergency_contact_name=payload.emergencyName,
        emergency_contact_phone=payload.emergencyPhone,
        emergency_contact_relation=payload.emergencyRelation,
        organ_donor=payload.organDonor or False,
        height_cm=payload.heightCm,
        weight_kg=payload.weightKg,
        allergies=allergies,
        chronic_conditions=chronic,
        past_medical_history=payload.pastMedicalHistory,
        current_medications=payload.currentMedications,
        critical_alert=payload.criticalAlert,
    )
    db.add(new_citizen)
    await db.flush()   # get the new citizen.id

    # Seed an insurance policy for this citizen
    policy = models.InsurancePolicy(
        citizen_id=new_citizen.id,
        policy_number=f"POL-{secrets.token_hex(5).upper()}",
        provider_name=payload.insuranceProvider or "Ayushman Bharat - PM-JAY",
        policy_type="GOVERNMENT_SCHEME",
        total_sum_insured=payload.totalSumInsured or 500000.0,
        remaining_sum_balance=payload.totalSumInsured or 500000.0,
        used_sum_amount=0,
        valid_from=date.today(),
        valid_to=date(date.today().year + 1, date.today().month, date.today().day),
        status="ACTIVE",
    )
    db.add(policy)
    await db.commit()
    await db.refresh(new_citizen)
    return new_citizen


@router.get("/citizens", response_model=list[schemas.CitizenProfile])
async def list_citizens(
    current_user: models.User = Depends(dependencies.role_required("ADMIN")),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(select(models.Citizen))
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard stats
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/stats")
async def admin_stats(
    current_user: models.User = Depends(dependencies.role_required("ADMIN")),
    db: AsyncSession = Depends(database.get_db),
):
    citizen_cnt  = (await db.execute(select(func.count()).select_from(models.Citizen))).scalar()
    hospital_cnt = (await db.execute(select(func.count()).select_from(models.Hospital))).scalar()
    approved_cnt = (await db.execute(
        select(func.count()).select_from(models.Hospital)
        .where(models.Hospital.approval_status == "APPROVED")
    )).scalar()
    policy_cnt   = (await db.execute(select(func.count()).select_from(models.InsurancePolicy))).scalar()
    claims_cnt   = (await db.execute(select(func.count()).select_from(models.InsuranceClaim))).scalar()

    return {
        "total_citizens":  citizen_cnt,
        "total_hospitals": hospital_cnt,
        "approved_hospitals": approved_cnt,
        "total_policies":  policy_cnt,
        "total_claims":    claims_cnt,
    }

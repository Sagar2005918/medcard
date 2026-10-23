"""
Citizens router

GET  /api/citizens/me               – current citizen's own profile
GET  /api/citizens/{health_id}      – any authenticated hospital fetches citizen by health-ID
PUT  /api/citizens/vitals           – update vitals (GOV_APPROVED_HOSPITAL only)
POST /api/citizens/checkup          – periodic checkup record (GOV_APPROVED_HOSPITAL only)
POST /api/citizens/visits           – log a medical visit (any approved hospital)
GET  /api/citizens/visits/{health_id} – list visits for a citizen
"""

from datetime import datetime, date, timedelta
import hashlib, secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .. import schemas, models, utils, dependencies, database

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
async def _get_citizen_by_health_id(health_id: str, db: AsyncSession) -> models.Citizen:
    result = await db.execute(
        select(models.Citizen).where(models.Citizen.health_id == health_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    return citizen


# ─────────────────────────────────────────────────────────────────────────────
# Own profile
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=schemas.CitizenProfile)
async def get_my_profile(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    if not current_user.citizen_id:
        raise HTTPException(status_code=404, detail="No citizen profile linked to this account")
    result = await db.execute(
        select(models.Citizen).where(models.Citizen.id == current_user.citizen_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen record not found")
    return citizen


# ─────────────────────────────────────────────────────────────────────────────
# Fetch any citizen by Health-ID  (any authenticated hospital)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{health_id}", response_model=schemas.CitizenProfile)
async def get_citizen_by_health_id(
    health_id: str,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    citizen = await _get_citizen_by_health_id(health_id, db)

    # Log the access
    log = models.HospitalAccessLog(
        citizen_id=citizen.id,
        hospital_id=current_user.hospital_id,
        accessed_by_user_id=current_user.id,
        access_type="VIEW_RECORD",
        purpose="Hospital retrieved citizen profile",
    )
    db.add(log)
    await db.commit()
    return citizen


# ─────────────────────────────────────────────────────────────────────────────
# Vitals update  (GOV_APPROVED_HOSPITAL only)
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/vitals", response_model=schemas.CitizenProfile)
async def update_vitals(
    health_id: str,
    vitals: schemas.VitalsUpdate,
    current_user: models.User = Depends(dependencies.role_required("GOV_APPROVED_HOSPITAL")),
    db: AsyncSession = Depends(database.get_db),
):
    citizen = await _get_citizen_by_health_id(health_id, db)

    update_data = vitals.model_dump(exclude_none=True)

    # Recalculate BMI if height/weight provided
    h = update_data.get("height_cm", citizen.height_cm)
    w = update_data.get("weight_kg", citizen.weight_kg)
    if h and w and float(h) > 0:
        update_data["bmi"] = round(float(w) / ((float(h) / 100) ** 2), 1)

    update_data["updated_at"] = datetime.utcnow()

    if update_data:
        await db.execute(
            update(models.Citizen)
            .where(models.Citizen.id == citizen.id)
            .values(**update_data)
        )
        await db.commit()
        await db.refresh(citizen)

    return citizen


# ─────────────────────────────────────────────────────────────────────────────
# Periodic checkup  (GOV_APPROVED_HOSPITAL only) – 3–5 month certification
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/checkup", response_model=schemas.GenericResponse)
async def submit_checkup(
    payload: schemas.PeriodicCheckup,
    current_user: models.User = Depends(dependencies.role_required("GOV_APPROVED_HOSPITAL")),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.Citizen).where(models.Citizen.id == payload.citizen_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    now = datetime.utcnow()
    next_due = date.today() + timedelta(days=90)   # next checkup in 3 months
    cert_raw = f"CERT-{citizen.id}-{current_user.hospital_id}-{now.isoformat()}-{secrets.token_hex(8)}"
    cert_hash = hashlib.sha256(cert_raw.encode()).hexdigest()[:64].upper()

    bmi = round(payload.weight_kg / ((payload.height_cm / 100) ** 2), 1)

    record = models.CheckupRecord(
        citizen_id=citizen.id,
        hospital_id=current_user.hospital_id,
        doctor_name=payload.doctor_name,
        doctor_registration_no=payload.doctor_registration_no,
        checkup_date=now,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        bmi=bmi,
        blood_pressure=payload.blood_pressure,
        pulse_bpm=payload.pulse_bpm,
        sp_o2=payload.sp_o2,
        blood_sugar_fasting=payload.blood_sugar_fasting,
        clinical_summary=payload.clinical_summary,
        recommendations=payload.recommendations,
        next_checkup_due=next_due,
        certificate_hash=cert_hash,
    )
    db.add(record)

    # Update citizen's checkup metadata + vitals
    await db.execute(
        update(models.Citizen)
        .where(models.Citizen.id == citizen.id)
        .values(
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            bmi=bmi,
            last_checkup_at=now,
            last_checkup_hospital_id=current_user.hospital_id,
            checkup_valid_until=now + timedelta(days=150),
            checkup_status="ACTIVE",
            updated_at=now,
        )
    )
    await db.commit()
    return {"success": True, "message": f"Checkup recorded. Next due by {next_due}"}


# ─────────────────────────────────────────────────────────────────────────────
# Medical visit log  (any authenticated hospital user)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/visits", response_model=schemas.MedicalVisitOut)
async def add_medical_visit(
    visit: schemas.MedicalVisitCreate,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    if not current_user.hospital_id:
        raise HTTPException(status_code=400, detail="User is not linked to any hospital")

    # Verify citizen exists
    result = await db.execute(
        select(models.Citizen).where(models.Citizen.id == visit.citizen_id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Citizen not found")

    new_visit = models.MedicalVisit(
        citizen_id=visit.citizen_id,
        hospital_id=current_user.hospital_id,
        doctor_name=visit.doctor_name,
        department=visit.department,
        symptoms=visit.symptoms,
        diagnosis=visit.diagnosis,
        prescription=visit.prescription,
        advice=visit.advice,
        follow_up_date=visit.follow_up_date,
    )
    db.add(new_visit)
    await db.commit()
    await db.refresh(new_visit)
    return new_visit


@router.get("/visits/{health_id}", response_model=list[schemas.MedicalVisitOut])
async def list_visits(
    health_id: str,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    citizen = await _get_citizen_by_health_id(health_id, db)
    result = await db.execute(
        select(models.MedicalVisit)
        .where(models.MedicalVisit.citizen_id == citizen.id)
        .order_by(models.MedicalVisit.visit_date.desc())
    )
    return result.scalars().all()

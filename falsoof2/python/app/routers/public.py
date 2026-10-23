"""
Public router – no authentication required

GET /api/public/verify/{health_id}  – verify a citizen's health card (for emergency rooms, etc.)
"""

from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt
import secrets

from .. import schemas, models, database, utils

router = APIRouter()


@router.get("/demo-info")
async def get_demo_info(db: AsyncSession = Depends(database.get_db)):
    """Provides sample credentials and active citizen Health-ID for immediate demonstration."""
    cit_res = await db.execute(select(models.Citizen).limit(1))
    citizen = cit_res.scalars().first()
    demo_hid = citizen.health_id if citizen else "1234-5678-9012"
    return {
        "sample_health_id": demo_hid,
        "demo_citizen_name": citizen.full_name if citizen else "John Doe",
        "accounts": [
            {"label": "Administrator", "username": "admin", "password": "Admin@123", "role": "ADMIN"},
            {"label": "AIIMS Govt Hospital", "username": "govhospital", "password": "Hospital@123", "role": "GOV_APPROVED_HOSPITAL"},
            {"label": "Apollo Private Hospital", "username": "stdhospital", "password": "Hospital@123", "role": "STANDARD_HOSPITAL"}
        ]
    }


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(database.get_db)):
    """Seed demo accounts and citizen data if not already present."""
    result = await db.execute(select(models.User).where(models.User.username == "admin"))
    existing_admin = result.scalars().first()
    if existing_admin:
        cit_res = await db.execute(select(models.Citizen).limit(1))
        citizen = cit_res.scalars().first()
        return {
            "success": True,
            "message": "Demo data is already active in database.",
            "health_id": citizen.health_id if citizen else "1234-5678-9012"
        }

    def hash_pw(pw: str) -> str:
        return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    admin_user = models.User(
        username="admin",
        email="admin@healthid.gov.in",
        password_hash=hash_pw("Admin@123"),
        role="ADMIN",
        is_active=True,
    )
    db.add(admin_user)
    await db.flush()

    hosp1 = models.Hospital(
        license_number="LIC-GOV-001",
        name="AIIMS National Hospital",
        email="contact@aiims.gov.in",
        phone="+911123456789",
        address="Ansari Nagar East",
        city="New Delhi",
        state="Delhi",
        pincode="110029",
        hospital_type="GOVERNMENT",
        approval_status="APPROVED",
        is_gov_approved=True,
        approved_by=admin_user.id,
        approved_at=datetime.utcnow(),
    )
    db.add(hosp1)
    await db.flush()

    hosp2 = models.Hospital(
        license_number="LIC-PRV-002",
        name="Apollo Metro Hospital",
        email="contact@apollometro.com",
        phone="+912223456789",
        address="Jubilee Hills",
        city="Hyderabad",
        state="Telangana",
        pincode="500033",
        hospital_type="PRIVATE_GENERAL",
        approval_status="APPROVED",
        is_gov_approved=False,
        approved_by=admin_user.id,
        approved_at=datetime.utcnow(),
    )
    db.add(hosp2)
    await db.flush()

    gov_user = models.User(
        username="govhospital",
        email="staff@aiims.gov.in",
        password_hash=hash_pw("Hospital@123"),
        role="GOV_APPROVED_HOSPITAL",
        hospital_id=hosp1.id,
        is_active=True,
    )
    std_user = models.User(
        username="stdhospital",
        email="staff@apollometro.com",
        password_hash=hash_pw("Hospital@123"),
        role="STANDARD_HOSPITAL",
        hospital_id=hosp2.id,
        is_active=True,
    )
    db.add_all([gov_user, std_user])
    await db.flush()

    health_id = "1234-5678-9012"
    citizen = models.Citizen(
        health_id=health_id,
        aadhaar_masked="XXXX-XXXX-4589",
        full_name="John Doe",
        date_of_birth=date(1990, 5, 15),
        gender="Male",
        blood_group="O+",
        phone="+919876543210",
        email="johndoe@example.com",
        address="42 MG Road",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001",
        emergency_contact_name="Jane Doe",
        emergency_contact_phone="+919876543211",
        emergency_contact_relation="Spouse",
        organ_donor=True,
        height_cm=175.0,
        weight_kg=72.0,
        bmi=23.5,
        allergies=["Penicillin", "Dust"],
        chronic_conditions=["Hypertension"],
        past_medical_history="Appendectomy in 2010",
        current_medications="Amlodipine 5mg",
        critical_alert="Allergic to Penicillin – use alternatives",
        checkup_status="ACTIVE",
        last_checkup_at=datetime.utcnow(),
        last_checkup_hospital_id=hosp1.id,
    )
    db.add(citizen)
    await db.flush()
    admin_user.citizen_id = citizen.id

    policy = models.InsurancePolicy(
        citizen_id=citizen.id,
        policy_number="PM-JAY-99201",
        provider_name="Ayushman Bharat - PM-JAY",
        policy_type="GOVERNMENT_SCHEME",
        total_sum_insured=500000.00,
        remaining_sum_balance=500000.00,
        used_sum_amount=0.00,
        valid_from=date.today(),
        valid_to=date(date.today().year + 1, date.today().month, date.today().day),
        status="ACTIVE",
        tpa_name="National Health Authority",
        coverage_details="Covers hospitalisation, surgery, ICU, medicines up to ₹5 lakh/year.",
    )
    db.add(policy)

    visit = models.MedicalVisit(
        citizen_id=citizen.id,
        hospital_id=hosp1.id,
        doctor_name="Dr. Arvind Sharma",
        department="General Medicine",
        symptoms="Mild fever and seasonal cough",
        diagnosis="Viral Upper Respiratory Tract Infection",
        prescription="Paracetamol 650mg TDS x 3 days, Cetirizine 10mg OD",
        advice="Warm saline gargles, adequate hydration and rest.",
        follow_up_date=date.today()
    )
    db.add(visit)

    await db.commit()
    return {
        "success": True,
        "message": "Demo database successfully initialized!",
        "health_id": health_id
    }


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

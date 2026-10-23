"""
Seed script for the National Healthcare ID System.

Creates:
  • 1 admin user          (username: admin / password: Admin@123)
  • 2 hospitals           (1 govt-approved, 1 standard)
  • 1 hospital user       (username: govhospital / password: Hospital@123)  → GOV_APPROVED_HOSPITAL
  • 1 standard user       (username: stdhospital / password: Hospital@123)  → STANDARD_HOSPITAL
  • 1 demo citizen        (John Doe, Health-ID auto-generated)
  • 1 insurance policy    (Ayushman Bharat, ₹5 lakh cover)

Run from the python/ directory:
    python seed.py
"""

import asyncio
import os
import secrets
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

from app.database import engine, Base
from app import models, utils

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def seed():
    # 1. Create all tables (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        # ── Admin user ──────────────────────────────────────────────────────
        admin_user = models.User(
            username="admin",
            email="admin@healthid.gov.in",
            password_hash=hash_pw("Admin@123"),
            role="ADMIN",
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()   # get admin_user.id

        # ── Government-approved hospital ────────────────────────────────────
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
        session.add(hosp1)
        await session.flush()

        # ── Standard (private) hospital ─────────────────────────────────────
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
        session.add(hosp2)
        await session.flush()

        # ── Hospital user accounts ───────────────────────────────────────────
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
        session.add_all([gov_user, std_user])
        await session.flush()

        # ── Demo citizen ─────────────────────────────────────────────────────
        health_id = utils.generate_health_id()
        citizen = models.Citizen(
            health_id=health_id,
            aadhaar_masked=utils.generate_masked_aadhaar(),
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
            bmi=round(72.0 / (1.75 ** 2), 1),
            allergies=["Penicillin", "Dust"],
            chronic_conditions=["Hypertension"],
            past_medical_history="Appendectomy in 2010",
            current_medications="Amlodipine 5mg",
            critical_alert="Allergic to Penicillin – use alternatives",
            checkup_status="ACTIVE",
            last_checkup_at=datetime.utcnow(),
            last_checkup_hospital_id=hosp1.id,
        )
        session.add(citizen)
        await session.flush()

        # Link admin user to citizen profile
        admin_user.citizen_id = citizen.id

        # ── Insurance policy ─────────────────────────────────────────────────
        policy = models.InsurancePolicy(
            citizen_id=citizen.id,
            policy_number=f"PM-JAY-{secrets.token_hex(5).upper()}",
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
        session.add(policy)

        await session.commit()

    print("\n✅  Seed complete!")
    print(f"   Health-ID  : {health_id}")
    print("   Admin      : admin / Admin@123")
    print("   Gov hosp   : govhospital / Hospital@123")
    print("   Std hosp   : stdhospital / Hospital@123")
    print("   Citizen    : John Doe")
    print("   Insurance  : Ayushman Bharat ₹5,00,000\n")


if __name__ == "__main__":
    asyncio.run(seed())

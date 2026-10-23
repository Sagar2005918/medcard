#!/usr/bin/env python3
"""
Standalone Neon Database Uploader & Seeder
Run directly with:
    python3 upload_to_neon.py
"""

import asyncio
import os
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from datetime import date, datetime, timedelta
import bcrypt

# Ensure python directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "python")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "python", ".env"))

# Fallback default to the user's Neon connection
DEFAULT_DATABASE_URL = "postgresql://neondb_owner:npg_1Cz7oBawAjhV@ep-steep-leaf-aoddxezu-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

def normalize_database_url(url: str) -> str:
    parts = urlsplit(url)
    scheme = "postgresql+asyncpg"
    query_params = dict(parse_qsl(parts.query))
    clean_params = {"ssl": "require"}
    new_parts = parts._replace(scheme=scheme, query=urlencode(clean_params))
    return urlunsplit(new_parts)

CLEAN_URL = normalize_database_url(DATABASE_URL)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.database import Base
from app import models, utils

engine = create_async_engine(CLEAN_URL, echo=False)

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

async def upload():
    print(f"🚀 Connecting to Neon PostgreSQL...")
    
    # 1. Create tables
    async with engine.begin() as conn:
        print("📦 Creating all schema tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Schema created.")

    # 2. Seed data
    async with AsyncSession(engine, expire_on_commit=False) as session:
        print("🌱 Seeding initial demo data...")
        
        # Check if already seeded
        from sqlalchemy import select
        res = await session.execute(select(models.User).where(models.User.username == "admin"))
        if res.scalars().first():
            print("ℹ️ Admin user already exists in Neon DB. Database is already seeded!")
            return

        # Admin
        admin_user = models.User(
            username="admin",
            email="admin@healthid.gov.in",
            password_hash=hash_pw("Admin@123"),
            role="ADMIN",
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()

        # Hospitals
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
        session.add_all([hosp1, hosp2])
        await session.flush()

        # Users
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

        # Citizen
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
        session.add(citizen)
        await session.flush()

        admin_user.citizen_id = citizen.id

        # Insurance Policy
        policy = models.InsurancePolicy(
            citizen_id=citizen.id,
            policy_number="PM-JAY-7889A1B2",
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

        print(f"\n🎉 Successfully uploaded to Neon PostgreSQL!")
        print(f"   Demo Health-ID : {health_id}")
        print(f"   Admin Login    : admin / Admin@123")
        print(f"   Gov Hospital   : govhospital / Hospital@123")
        print(f"   Std Hospital   : stdhospital / Hospital@123")

if __name__ == "__main__":
    asyncio.run(upload())

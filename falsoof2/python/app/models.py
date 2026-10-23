"""
SQLAlchemy ORM models for the National Healthcare ID System.

PostgreSQL is the target database (Neon on Render).
ARRAY(String) is used for allergies / chronic_conditions – fully supported by
PostgreSQL / asyncpg. The ambiguous FK between Hospital ↔ User is resolved
by explicitly specifying foreign_keys on both sides.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    Text, Numeric, ForeignKey,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from .database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Hospitals Table
# ─────────────────────────────────────────────────────────────────────────────
class Hospital(Base):
    __tablename__ = "hospitals"

    id               = Column(Integer, primary_key=True, index=True)
    license_number   = Column(String(100), unique=True, nullable=False)
    name             = Column(String(255), nullable=False)
    email            = Column(String(255), unique=True, nullable=False)
    phone            = Column(String(50), nullable=False)
    address          = Column(Text, nullable=False)
    city             = Column(String(100), nullable=False)
    state            = Column(String(100), nullable=False)
    pincode          = Column(String(20), nullable=False)
    hospital_type    = Column(String(50), nullable=False, default="PRIVATE_GENERAL")
    approval_status  = Column(String(50), nullable=False, default="PENDING")
    is_gov_approved  = Column(Boolean, nullable=False, default=False)
    approved_by      = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at      = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # users that belong to this hospital (via User.hospital_id)
    users = relationship(
        "User",
        back_populates="hospital",
        foreign_keys="User.hospital_id",
        lazy="select",
    )
    # the admin who approved this hospital (via Hospital.approved_by → users.id)
    approved_by_user = relationship(
        "User",
        foreign_keys=[approved_by],
        lazy="select",
    )
    checkup_records = relationship("CheckupRecord", back_populates="hospital")
    visits          = relationship("MedicalVisit",  back_populates="hospital")
    claims          = relationship("InsuranceClaim", back_populates="hospital")
    access_logs     = relationship("HospitalAccessLog", back_populates="hospital")


# ─────────────────────────────────────────────────────────────────────────────
# Users Table  (Admins, Hospital staff, Citizens)
# ─────────────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(100), unique=True, nullable=False)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(50), nullable=False)
    # ADMIN | GOV_APPROVED_HOSPITAL | STANDARD_HOSPITAL | CITIZEN
    hospital_id   = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    citizen_id    = Column(Integer, ForeignKey("citizens.id"),  nullable=True)
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # The hospital this user works at
    hospital = relationship(
        "Hospital",
        back_populates="users",
        foreign_keys=[hospital_id],
        lazy="select",
    )
    citizen = relationship("Citizen", back_populates="user", uselist=False)


# ─────────────────────────────────────────────────────────────────────────────
# Citizens Table  (Core Health Card profile)
# ─────────────────────────────────────────────────────────────────────────────
class Citizen(Base):
    __tablename__ = "citizens"

    id                         = Column(Integer, primary_key=True, index=True)
    health_id                  = Column(String(50),  unique=True, nullable=False, index=True)
    aadhaar_masked             = Column(String(20),  nullable=False)
    full_name                  = Column(String(255), nullable=False)
    date_of_birth              = Column(Date,        nullable=False)
    gender                     = Column(String(20),  nullable=False)
    blood_group                = Column(String(10),  nullable=False)
    phone                      = Column(String(50),  nullable=False)
    email                      = Column(String(255), nullable=True)
    address                    = Column(Text,        nullable=False)
    city                       = Column(String(100), nullable=False)
    state                      = Column(String(100), nullable=False)
    pincode                    = Column(String(20),  nullable=False)
    photo_url                  = Column(Text,        nullable=True)
    emergency_contact_name     = Column(String(255), nullable=False)
    emergency_contact_phone    = Column(String(50),  nullable=False)
    emergency_contact_relation = Column(String(100), nullable=False)
    organ_donor                = Column(Boolean,     nullable=False, default=False)

    # Vitals (updated by gov-approved hospitals)
    height_cm  = Column(Numeric(5, 2), nullable=True)
    weight_kg  = Column(Numeric(5, 2), nullable=True)
    bmi        = Column(Numeric(4, 1), nullable=True)

    # Medical records stored as PostgreSQL arrays
    allergies           = Column(ARRAY(String), nullable=False, default=list)
    chronic_conditions  = Column(ARRAY(String), nullable=False, default=list)
    past_medical_history  = Column(Text, nullable=True)
    current_medications   = Column(Text, nullable=True)
    critical_alert        = Column(Text, nullable=True)

    # Checkup status
    last_checkup_at        = Column(DateTime(timezone=True), nullable=True)
    last_checkup_hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    checkup_valid_until    = Column(DateTime(timezone=True), nullable=True)
    checkup_status         = Column(String(50), nullable=False, default="RENEWAL_DUE")

    qr_code_data = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    last_checkup_hospital = relationship(
        "Hospital",
        foreign_keys=[last_checkup_hospital_id],
    )
    user              = relationship("User",           back_populates="citizen",           uselist=False)
    checkup_records   = relationship("CheckupRecord",  back_populates="citizen")
    visits            = relationship("MedicalVisit",   back_populates="citizen")
    insurance_policies= relationship("InsurancePolicy",back_populates="citizen")
    access_logs       = relationship("HospitalAccessLog", back_populates="citizen")
    claims            = relationship("InsuranceClaim", back_populates="citizen")


# ─────────────────────────────────────────────────────────────────────────────
# Checkup Records  (3–5 month periodic certification by gov-approved hospitals)
# ─────────────────────────────────────────────────────────────────────────────
class CheckupRecord(Base):
    __tablename__ = "checkup_records"

    id                    = Column(Integer, primary_key=True, index=True)
    citizen_id            = Column(Integer, ForeignKey("citizens.id"),  nullable=False)
    hospital_id           = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    doctor_name           = Column(String(255), nullable=False)
    doctor_registration_no= Column(String(100), nullable=True)
    checkup_date          = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    height_cm             = Column(Numeric(5, 2), nullable=False)
    weight_kg             = Column(Numeric(5, 2), nullable=False)
    bmi                   = Column(Numeric(4, 1), nullable=True)
    blood_pressure        = Column(String(20), nullable=False)
    pulse_bpm             = Column(Integer, nullable=False)
    sp_o2                 = Column(Integer, nullable=True)
    blood_sugar_fasting   = Column(Numeric(5, 1), nullable=True)
    clinical_summary      = Column(Text, nullable=False)
    recommendations       = Column(Text, nullable=True)
    next_checkup_due      = Column(Date, nullable=False)
    certificate_hash      = Column(String(128), nullable=False, unique=True)
    created_at            = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    citizen  = relationship("Citizen",  back_populates="checkup_records")
    hospital = relationship("Hospital", back_populates="checkup_records")


# ─────────────────────────────────────────────────────────────────────────────
# Insurance Policies
# ─────────────────────────────────────────────────────────────────────────────
class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id                    = Column(Integer, primary_key=True, index=True)
    citizen_id            = Column(Integer, ForeignKey("citizens.id"), nullable=False)
    policy_number         = Column(String(100), unique=True, nullable=False)
    provider_name         = Column(String(255), nullable=False)
    policy_type           = Column(String(50),  nullable=False, default="GOVERNMENT_SCHEME")
    total_sum_insured     = Column(Numeric(12, 2), nullable=False)
    remaining_sum_balance = Column(Numeric(12, 2), nullable=False)
    used_sum_amount       = Column(Numeric(12, 2), nullable=False, default=0)
    valid_from            = Column(Date, nullable=False)
    valid_to              = Column(Date, nullable=False)
    status                = Column(String(50), nullable=False, default="ACTIVE")
    tpa_name              = Column(String(255), nullable=True)
    coverage_details      = Column(Text, nullable=True)
    created_at            = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at            = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    citizen = relationship("Citizen",        back_populates="insurance_policies")
    claims  = relationship("InsuranceClaim", back_populates="policy")


# ─────────────────────────────────────────────────────────────────────────────
# Insurance Claims
# ─────────────────────────────────────────────────────────────────────────────
class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id                = Column(Integer, primary_key=True, index=True)
    claim_reference   = Column(String(100), unique=True, nullable=False)
    policy_id         = Column(Integer, ForeignKey("insurance_policies.id"), nullable=False)
    citizen_id        = Column(Integer, ForeignKey("citizens.id"),           nullable=False)
    hospital_id       = Column(Integer, ForeignKey("hospitals.id"),          nullable=False)
    treatment_title   = Column(String(255), nullable=False)
    diagnosis_summary = Column(Text, nullable=False)
    claimed_amount    = Column(Numeric(12, 2), nullable=False)
    approved_amount   = Column(Numeric(12, 2), nullable=False)
    balance_before    = Column(Numeric(12, 2), nullable=False)
    balance_after     = Column(Numeric(12, 2), nullable=False)
    claim_status      = Column(String(50), nullable=False, default="SETTLED")
    admission_date    = Column(Date, nullable=True)
    discharge_date    = Column(Date, nullable=True)
    notes             = Column(Text, nullable=True)
    processed_at      = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at        = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    policy   = relationship("InsurancePolicy", back_populates="claims")
    citizen  = relationship("Citizen",         back_populates="claims")
    hospital = relationship("Hospital",        back_populates="claims")


# ─────────────────────────────────────────────────────────────────────────────
# Medical Visits & Prescriptions
# ─────────────────────────────────────────────────────────────────────────────
class MedicalVisit(Base):
    __tablename__ = "medical_visits"

    id            = Column(Integer, primary_key=True, index=True)
    citizen_id    = Column(Integer, ForeignKey("citizens.id"),  nullable=False)
    hospital_id   = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    doctor_name   = Column(String(255), nullable=False)
    department    = Column(String(100), nullable=False)
    visit_date    = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    symptoms      = Column(Text, nullable=False)
    diagnosis     = Column(Text, nullable=False)
    prescription  = Column(Text, nullable=True)
    advice        = Column(Text, nullable=True)
    follow_up_date= Column(Date, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    citizen  = relationship("Citizen",  back_populates="visits")
    hospital = relationship("Hospital", back_populates="visits")


# ─────────────────────────────────────────────────────────────────────────────
# Hospital Access Logs  (full audit trail)
# ─────────────────────────────────────────────────────────────────────────────
class HospitalAccessLog(Base):
    __tablename__ = "hospital_access_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    citizen_id          = Column(Integer, ForeignKey("citizens.id"),  nullable=False)
    hospital_id         = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    accessed_by_user_id = Column(Integer, ForeignKey("users.id"),     nullable=True)
    # VIEW_RECORD | EMERGENCY_ACCESS | CHECKUP_UPDATE | CLAIM_VERIFICATION
    access_type  = Column(String(50),  nullable=False)
    purpose      = Column(String(255), nullable=False)
    ip_address   = Column(String(50),  nullable=True)
    accessed_at  = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    citizen  = relationship("Citizen",  back_populates="access_logs")
    hospital = relationship("Hospital", back_populates="access_logs")
    user     = relationship("User", foreign_keys=[accessed_by_user_id])

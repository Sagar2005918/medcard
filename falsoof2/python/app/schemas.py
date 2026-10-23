"""Pydantic v2-compatible schemas for the National Healthcare ID System."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ─────────────────────────────────────────────────────────────────────────────
# Auth / Token
# ─────────────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Username or email")
    password: str

class UserInfo(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    hospital_id: Optional[int] = None
    citizen_id: Optional[int] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Hospital
# ─────────────────────────────────────────────────────────────────────────────
class HospitalCreate(BaseModel):
    license_number: str
    name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    state: str
    pincode: str
    hospital_type: Optional[str] = "PRIVATE_GENERAL"

class HospitalOut(BaseModel):
    id: int
    license_number: str
    name: str
    email: EmailStr
    phone: str
    city: str
    state: str
    hospital_type: str
    approval_status: str
    is_gov_approved: bool
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

# Alias kept for backwards-compat
HospitalInfo = HospitalOut


# ─────────────────────────────────────────────────────────────────────────────
# Citizen
# ─────────────────────────────────────────────────────────────────────────────
class CitizenCreate(BaseModel):
    fullName: str
    dateOfBirth: date
    gender: str
    bloodGroup: str
    phone: str
    email: Optional[EmailStr] = None
    address: str
    city: str
    state: str
    pincode: str
    emergencyName: str
    emergencyPhone: str
    emergencyRelation: str
    organDonor: Optional[bool] = False
    heightCm: Optional[float] = None
    weightKg: Optional[float] = None
    allergies: Optional[str] = None          # comma-separated
    chronicConditions: Optional[str] = None  # comma-separated
    pastMedicalHistory: Optional[str] = None
    currentMedications: Optional[str] = None
    criticalAlert: Optional[str] = None
    insuranceProvider: Optional[str] = "Ayushman Bharat - PM-JAY"
    totalSumInsured: Optional[float] = 500000.0

class CitizenProfile(BaseModel):
    """Returned to callers who read citizen data."""
    id: int
    health_id: str
    aadhaar_masked: str
    full_name: str
    date_of_birth: date
    gender: str
    blood_group: str
    phone: str
    email: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: str
    organ_donor: bool
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    allergies: Optional[List[str]] = []
    chronic_conditions: Optional[List[str]] = []
    past_medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    critical_alert: Optional[str] = None
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_contact_relation: str
    last_checkup_at: Optional[datetime] = None
    checkup_status: str
    qr_code_data: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Vitals update  (gov-approved hospital)
# ─────────────────────────────────────────────────────────────────────────────
class VitalsUpdate(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    past_medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    critical_alert: Optional[str] = None
    organ_donor: Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# Periodic Checkup  (gov-approved hospital)
# ─────────────────────────────────────────────────────────────────────────────
class PeriodicCheckup(BaseModel):
    citizen_id: int
    doctor_name: str
    doctor_registration_no: Optional[str] = None
    height_cm: float
    weight_kg: float
    blood_pressure: str
    pulse_bpm: int
    sp_o2: Optional[int] = None
    blood_sugar_fasting: Optional[float] = None
    clinical_summary: str
    recommendations: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Medical Visit
# ─────────────────────────────────────────────────────────────────────────────
class MedicalVisitCreate(BaseModel):
    citizen_id: int
    doctor_name: str
    department: str
    symptoms: str
    diagnosis: str
    prescription: Optional[str] = None
    advice: Optional[str] = None
    follow_up_date: Optional[date] = None

class MedicalVisitOut(BaseModel):
    id: int
    citizen_id: int
    hospital_id: int
    doctor_name: str
    department: str
    visit_date: datetime
    symptoms: str
    diagnosis: str
    prescription: Optional[str] = None
    advice: Optional[str] = None
    follow_up_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Insurance
# ─────────────────────────────────────────────────────────────────────────────
class InsurancePolicyOut(BaseModel):
    id: int
    policy_number: str
    provider_name: str
    policy_type: str
    total_sum_insured: float
    remaining_sum_balance: float
    used_sum_amount: float
    valid_from: date
    valid_to: date
    status: str
    tpa_name: Optional[str] = None
    coverage_details: Optional[str] = None

    model_config = {"from_attributes": True}

# Keep old name for compat
InsurancePolicyInfo = InsurancePolicyOut

class InsuranceClaimCreate(BaseModel):
    citizen_id: int
    policy_id: int
    treatment_title: str
    diagnosis_summary: Optional[str] = None
    claimed_amount: float
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None
    notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Generic / Public
# ─────────────────────────────────────────────────────────────────────────────
class GenericResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None

class PublicVerificationResponse(BaseModel):
    success: bool
    cardVerification: dict

    model_config = {"from_attributes": True}

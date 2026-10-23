"""
Auth router

POST /api/auth/login             – username/password → JWT
POST /api/auth/register_hospital – register a hospital (creates pending record)
GET  /api/auth/me                – return currently-logged-in user info
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt

from .. import schemas, models, utils, dependencies, database

router = APIRouter()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifies plain password against bcrypt hash or fallback to direct compare."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return plain == hashed


# ─────────────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    payload: schemas.LoginRequest,
    db: AsyncSession = Depends(database.get_db),
):
    # Try username first, then email
    result = await db.execute(
        select(models.User).where(models.User.username == payload.identifier)
    )
    user = result.scalars().first()
    if not user:
        result = await db.execute(
            select(models.User).where(models.User.email == payload.identifier)
        )
        user = result.scalars().first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    access_token = utils.create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register_hospital", response_model=schemas.HospitalOut)
async def register_hospital(
    payload: schemas.HospitalCreate,
    db: AsyncSession = Depends(database.get_db),
):
    """Any party can self-register a hospital; an Admin must approve it."""
    # Check for duplicate license / email
    dup = await db.execute(
        select(models.Hospital).where(
            (models.Hospital.license_number == payload.license_number) |
            (models.Hospital.email == payload.email)
        )
    )
    if dup.scalars().first():
        raise HTTPException(status_code=400, detail="Hospital with this license or email already exists")

    new_hospital = models.Hospital(
        license_number=payload.license_number,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        hospital_type=payload.hospital_type or "PRIVATE_GENERAL",
        approval_status="PENDING",
        is_gov_approved=False,
    )
    db.add(new_hospital)
    await db.commit()
    await db.refresh(new_hospital)
    return new_hospital


@router.get("/me", response_model=schemas.UserInfo)
async def get_me(
    current_user: models.User = Depends(dependencies.get_current_user),
):
    return current_user

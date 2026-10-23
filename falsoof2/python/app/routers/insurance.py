"""
Insurance router

GET  /api/insurance/{health_id}    – get all active policies + balance for a citizen
GET  /api/insurance/policy/{id}    – single policy detail
POST /api/insurance/claim          – file a claim (hospital only)
GET  /api/insurance/claims/{health_id} – claim history for a citizen
"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .. import schemas, models, dependencies, database

router = APIRouter()


@router.get("/{health_id}", response_model=list[schemas.InsurancePolicyOut])
async def get_insurance_by_health_id(
    health_id: str,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.Citizen).where(models.Citizen.health_id == health_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    # Anyone authenticated can view insurance summary; citizen can only view own
    if current_user.role == "CITIZEN" and current_user.citizen_id != citizen.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(models.InsurancePolicy)
        .where(models.InsurancePolicy.citizen_id == citizen.id)
    )
    return result.scalars().all()


@router.get("/policy/{policy_id}", response_model=schemas.InsurancePolicyOut)
async def get_policy(
    policy_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.InsurancePolicy).where(models.InsurancePolicy.id == policy_id)
    )
    policy = result.scalars().first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if current_user.role == "CITIZEN" and policy.citizen_id != current_user.citizen_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return policy


@router.post("/claim", response_model=schemas.GenericResponse)
async def file_claim(
    claim: schemas.InsuranceClaimCreate,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    if not current_user.hospital_id:
        raise HTTPException(status_code=400, detail="Only hospital users can file claims")

    # Fetch policy
    result = await db.execute(
        select(models.InsurancePolicy).where(models.InsurancePolicy.id == claim.policy_id)
    )
    policy = result.scalars().first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if policy.citizen_id != claim.citizen_id:
        raise HTTPException(status_code=400, detail="Policy does not belong to this citizen")
    if policy.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Policy is not active")
    if float(policy.remaining_sum_balance) < claim.claimed_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ₹{policy.remaining_sum_balance}",
        )

    balance_before = float(policy.remaining_sum_balance)
    balance_after  = balance_before - claim.claimed_amount

    new_claim = models.InsuranceClaim(
        claim_reference=f"CLM-{secrets.token_hex(6).upper()}",
        policy_id=policy.id,
        citizen_id=claim.citizen_id,
        hospital_id=current_user.hospital_id,
        treatment_title=claim.treatment_title,
        diagnosis_summary=claim.diagnosis_summary or "",
        claimed_amount=claim.claimed_amount,
        approved_amount=claim.claimed_amount,  # auto-approve for demo
        balance_before=balance_before,
        balance_after=balance_after,
        claim_status="SETTLED",
        admission_date=claim.admission_date,
        discharge_date=claim.discharge_date,
        notes=claim.notes,
    )
    db.add(new_claim)

    await db.execute(
        update(models.InsurancePolicy)
        .where(models.InsurancePolicy.id == policy.id)
        .values(
            remaining_sum_balance=balance_after,
            used_sum_amount=float(policy.used_sum_amount) + claim.claimed_amount,
        )
    )
    await db.commit()
    return {"success": True, "message": f"Claim {new_claim.claim_reference} filed successfully"}


@router.get("/claims/{health_id}")
async def get_claim_history(
    health_id: str,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(models.Citizen).where(models.Citizen.health_id == health_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    result = await db.execute(
        select(models.InsuranceClaim)
        .where(models.InsuranceClaim.citizen_id == citizen.id)
        .order_by(models.InsuranceClaim.processed_at.desc())
    )
    claims = result.scalars().all()
    return [
        {
            "id": c.id,
            "claim_reference": c.claim_reference,
            "treatment_title": c.treatment_title,
            "claimed_amount": float(c.claimed_amount),
            "approved_amount": float(c.approved_amount),
            "balance_before": float(c.balance_before),
            "balance_after": float(c.balance_after),
            "claim_status": c.claim_status,
            "processed_at": c.processed_at.isoformat() if c.processed_at else None,
        }
        for c in claims
    ]

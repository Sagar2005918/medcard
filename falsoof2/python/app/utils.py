import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

# Load secret from env (Render can generate automatically)
JWT_SECRET = os.getenv("JWT_SECRET", "replace-this-with-a-secure-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_IN = os.getenv("JWT_EXPIRES_IN", "7d")

def _parse_expire(delta: str) -> int:
    """Parse expire string like '7d' or '12h' to seconds."""
    if delta.endswith("d"):
        return int(delta[:-1]) * 24 * 60 * 60
    if delta.endswith("h"):
        return int(delta[:-1]) * 60 * 60
    if delta.endswith("m"):
        return int(delta[:-1]) * 60
    return int(delta)  # assume seconds

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire_seconds = _parse_expire(JWT_EXPIRES_IN)
    expire = datetime.utcnow() + timedelta(seconds=expire_seconds)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

# --------------------
# Health ID utilities
# --------------------

def generate_health_id() -> str:
    # 12 digits grouped as XXXX-XXXX-XXXX
    parts = [str(secrets.randbelow(9000) + 1000) for _ in range(3)]
    return "-".join(parts)

def generate_masked_aadhaar() -> str:
    last4 = str(secrets.randbelow(9000) + 1000)
    return f"XXXX-XXXX-{last4}"

def generate_certificate_hash(citizen_id: int, hospital_id: int, timestamp: datetime) -> str:
    raw = f"CERT-{citizen_id}-{hospital_id}-{timestamp.isoformat()}-{secrets.token_hex(8)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32].upper()

# --------------------
# Checkup status evaluation (3‑5 month rule)
# --------------------

def evaluate_checkup_status(last_checkup: Optional[datetime]):
    if not last_checkup:
        return {
            "status": "EXPIRED",
            "label": "Initial Checkup Required",
            "description": "No periodic checkup recorded yet.",
            "days_elapsed": None,
            "days_remaining": 0,
        }
    now = datetime.utcnow()
    diff_days = (now - last_checkup).days
    MIN_DAYS = 90  # 3 months
    MAX_DAYS = 150  # 5 months
    if diff_days <= MIN_DAYS:
        return {
            "status": "ACTIVE",
            "label": "Active & Certified",
            "description": f"Valid checkup. {MAX_DAYS - diff_days} days remaining.",
            "days_elapsed": diff_days,
            "days_remaining": MAX_DAYS - diff_days,
        }
    elif diff_days <= MAX_DAYS:
        return {
            "status": "RENEWAL_DUE",
            "label": "Renewal Due (3‑5 mo window)",
            "description": f"Last updated {diff_days // 30} months ago. Renewal required.",
            "days_elapsed": diff_days,
            "days_remaining": MAX_DAYS - diff_days,
        }
    else:
        overdue = diff_days - MAX_DAYS
        return {
            "status": "EXPIRED",
            "label": "Checkup Expired (>5 mo)",
            "description": f"Overdue by {overdue} days. Mandatory re‑certification required.",
            "days_elapsed": diff_days,
            "days_remaining": 0,
        }
